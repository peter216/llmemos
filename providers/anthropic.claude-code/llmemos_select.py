#!/usr/bin/env python3
"""llmemos_select.py — memo/section selection and load-plan builder.

Implements the "Select memos to load" / "Loading granularity" / per-memo
loading logic from llmemos-protocol.md (Path A / Claude Code, Step 3).
Given a cloned corpus repo (AGENTS.md, taxonomy.yml, and an optional
section-index.json) and a loading directive, emits a JSON load plan: a
list of {memo, mode, ...} entries.

Content emission (--emit / --emit-file):
    Without these flags the agent turns the load plan into N Read tool
    calls — one per entry.  The emission flags collapse that to a single
    read by assembling all selected content into one document.

    --emit              Write assembled content to stdout; JSON metadata
                        goes to stderr.  Intended for tool/pipeline consumers.
    --emit-file PATH    Write assembled content to PATH (the string
                        "{commit}" in PATH is substituted with the short
                        corpus commit hash, e.g.
                        "/tmp/llmemos-content-{commit}.md").
                        JSON output (stdout) gains two extra fields:
                          emit_sha256  SHA-256 hex digest of the file written
                          emit_file    Resolved path actually written

    The assembled document begins with a header comment and then one
    provenance comment per entry followed immediately by its content:

        <!-- llmemos-content | generated: … | memos: N | granularity: … | commit: … -->

        <!-- llmemos-provenance | memo: … | mode: whole | reason: … | source: … | commit: … -->
        <full file content>

        <!-- llmemos-provenance | memo: … | section: … | lines: S-E | reason: … | source: … | commit: … -->
        <section content>

    Provenance comments let the agent (or a spot-check step) trace any
    assembled block back to its source file and line range in the
    verified repo clone.

Directive (choose at most one; default is sticky-only):
    --recent N
    --tags t1,t2
    --alias NAME
    --all
    --memos id1,id2

Granularity (one-shot vs persistent default — see protocol "Loading
granularity" / "tag-search-default"):
    --tag-search {all,sections,memos}
    --tag-search-default {all,sections,memos}   (default: all)

Usage:
    python3 llmemos_select.py \\
        --repo-path /tmp/claude-memos-session \\
        --tags claude-code \\
        --tag-search-default all

Output schema:
{
  "granularity_used": "whole-memo|sections|mixed",
  "total_memos": 44,
  "loaded_memo_count": 19,
  "load_plan": [
    {"memo_id": "...", "file": "memos/....md", "mode": "whole",
     "reason": "memo-sticky"},
    {"memo_id": "...", "file": "memos/....md", "mode": "section",
     "section_id": "...", "title": "...", "start_line": 11,
     "end_line": 90, "reason": "sticky-section-sweep"}
  ]
}

For a "section" entry, the corresponding Read call is:
    Read(file, offset=start_line, limit=end_line - start_line + 1)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

import yaml

try:
    from llmemos_logger import get_logger

    logger = get_logger(__name__)
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


def load_agents_md(repo_path: str) -> tuple[dict, list[dict]]:
    """Parse AGENTS.md frontmatter and the `## Memo Index` memo list.

    Returns (frontmatter_dict, memos_list). Raises FileNotFoundError /
    ValueError if AGENTS.md is missing or malformed — this file is
    mandatory, unlike taxonomy.yml and section-index.json.
    """
    path = os.path.join(repo_path, "AGENTS.md")
    with open(path) as f:
        content = f.read()

    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.S)
    if not fm_match:
        raise ValueError(f"No frontmatter found in {path}")
    frontmatter = yaml.safe_load(fm_match.group(1)) or {}

    index_match = re.search(r"## Memo Index", content)
    if not index_match:
        raise ValueError(f"No '## Memo Index' section found in {path}")

    rest = content[index_match.end() :]
    fence_match = re.search(r"```yaml\n(.*?)```", rest, re.S)
    if not fence_match:
        raise ValueError(f"No fenced yaml block found under Memo Index in {path}")

    index_data = yaml.safe_load(fence_match.group(1)) or {}
    memos = index_data.get("memos") or []
    return frontmatter, memos


def load_taxonomy(repo_path: str) -> dict:
    """Load taxonomy.yml. Returns {} (graceful degradation) if absent."""
    path = os.path.join(repo_path, "taxonomy.yml")
    if not os.path.isfile(path):
        logger.warning("taxonomy.yml not found at %s", path)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_section_index(repo_path: str) -> dict | None:
    """Load section-index.json. Returns None (graceful degradation) if absent."""
    path = os.path.join(repo_path, "section-index.json")
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return json.load(f)


def resolve_directive_tags(args: argparse.Namespace, taxonomy: dict) -> set[str] | None:
    """Resolve --tags/--alias into a set of tags. None for non-tag directives."""
    if args.tags:
        requested = {t.strip() for t in args.tags.split(",") if t.strip()}
        known_tags = set((taxonomy.get("tags") or {}).keys())
        unknown = requested - known_tags
        if unknown:
            logger.warning(
                "Tags not defined in taxonomy.yml (warn, not abort): %s",
                ", ".join(sorted(unknown)),
            )
        return requested

    if args.alias:
        aliases = taxonomy.get("aliases") or {}
        expansion = aliases.get(args.alias)
        if expansion is None:
            logger.warning(
                "Alias '%s' not found in taxonomy.yml; treating as empty.",
                args.alias,
            )
            return set()
        return set(expansion)

    return None


def resolve_memo_level_selection(
    args: argparse.Namespace, memos: list[dict], directive_tags: set[str] | None
) -> set[str]:
    """Resolve the memo-level selection set per the directive table.

    This mirrors the "Select memos to load" table in the protocol. The
    result always includes all memo-level `sticky: true` memos.
    """
    sticky_ids = {m["id"] for m in memos if m.get("sticky")}

    if args.all:
        return {m["id"] for m in memos}

    if args.memos:
        requested = {i.strip() for i in args.memos.split(",") if i.strip()}
        known_ids = {m["id"] for m in memos}
        unknown = requested - known_ids
        if unknown:
            logger.warning(
                "--memos referenced unknown ids (ignored): %s",
                ", ".join(sorted(unknown)),
            )
        return sticky_ids | (requested & known_ids)

    if args.recent is not None:
        non_sticky = [m for m in memos if not m.get("sticky")]
        non_sticky.sort(key=lambda m: m.get("created", ""), reverse=True)
        recent_ids = {m["id"] for m in non_sticky[: args.recent]}
        return sticky_ids | recent_ids

    if directive_tags is not None:
        tag_matches = {m["id"] for m in memos if set(m.get("topics") or []) & directive_tags}
        return sticky_ids | tag_matches

    # No directive: sticky memos only.
    return sticky_ids


def memo_section_entries(section_index: dict | None, memo_id: str) -> list[dict]:
    """Return the section list for `memo_id`, or [] if absent/no index."""
    if section_index is None:
        return []
    for memo in section_index["memos"]:
        if memo["id"] == memo_id:
            return memo.get("sections") or []
    return []


def build_load_plan(
    memos: list[dict],
    memo_level_selected: set[str],
    directive_tags: set[str] | None,
    section_index: dict | None,
    granularity: str,
) -> tuple[list[dict], str]:
    """Build the load plan and determine the `granularity_used` field.

    See module docstring for the output schema. `granularity` is the
    resolved --tag-search / --tag-search-default value ("all", "sections",
    or "memos"). Falls back to whole-memo loading if no section-index is
    present, regardless of `granularity` (graceful degradation).
    """
    memo_by_id = {m["id"]: m for m in memos}
    load_plan: list[dict] = []
    covered_memo_ids: set[str] = set()
    loaded_section_ids: set[str] = set()
    used_whole = False
    used_section = False

    def add_whole(memo_id: str, reason: str) -> None:
        nonlocal used_whole
        load_plan.append(
            {
                "memo_id": memo_id,
                "file": memo_by_id[memo_id]["file"],
                "mode": "whole",
                "reason": reason,
            }
        )
        covered_memo_ids.add(memo_id)
        used_whole = True

    def add_section(memo_id: str, section: dict, reason: str) -> None:
        nonlocal used_section
        section_id = section["section_id"]
        if section_id in loaded_section_ids:
            return
        load_plan.append(
            {
                "memo_id": memo_id,
                "file": memo_by_id[memo_id]["file"],
                "mode": "section",
                "section_id": section_id,
                "title": section.get("title"),
                "start_line": section["start_line"],
                "end_line": section["end_line"],
                "reason": reason,
            }
        )
        loaded_section_ids.add(section_id)
        used_section = True

    if section_index is None or granularity == "memos":
        for memo_id in memo_level_selected:
            add_whole(memo_id, "directive-selected")
        # Sticky-section sweep still applies (whole-memo mode: pull in the
        # containing memo) — sticky sections are corpus-wide, independent
        # of memo-level selection. See "Sticky sections apply corpus-wide"
        # in llmemos-protocol.md.
        if section_index is not None:
            for memo_sec in section_index["memos"]:
                memo_id = memo_sec["id"]
                if memo_id in covered_memo_ids:
                    continue
                if any(s.get("sticky") for s in memo_sec.get("sections") or []):
                    add_whole(memo_id, "sticky-section-sweep")
        return load_plan, "whole-memo"

    # granularity in {"sections", "all"}
    for memo_id in memo_level_selected:
        memo = memo_by_id[memo_id]
        sections = memo_section_entries(section_index, memo_id)

        if not sections:
            # No sections defined: graceful degradation to whole-memo
            # (nothing finer to load regardless of granularity).
            add_whole(memo_id, "memo-sticky" if memo.get("sticky") else "no-sections")
            continue

        if granularity == "sections":
            # sections mode: always use section-level loading, even for
            # memo-level sticky memos — the sticky-→-whole shortcut is an
            # "all" read-efficiency optimisation only. When no sections
            # exist we already fell through to whole-memo above.
            for section in sections:
                if section.get("sticky"):
                    add_section(memo_id, section, "sticky-section")
                elif directive_tags and set(section.get("tags") or []) & directive_tags:
                    add_section(memo_id, section, "tag-match-section")
            continue

        # granularity == "all" from here.
        if memo.get("sticky"):
            # Memo-level sticky: load whole (read-efficiency optimisation
            # for "all" granularity — see protocol Step 3 rule 1).
            add_whole(memo_id, "memo-sticky")
            continue

        if directive_tags is None:
            # Non-tag-based directive (--all, --memos, --recent): the
            # memo was explicitly selected by identity, so load it whole
            # rather than guessing which sections are "relevant".
            add_whole(memo_id, "directive-selected-whole")
            continue

        # granularity == "all" with tag-based directive: load whole; the
        # corpus-wide section sweep below extends recall to non-selected memos.
        add_whole(memo_id, "directive-selected-whole")

    # Corpus-wide expansion for "all": tag-matching sections in memos not
    # already covered by a whole-memo load.
    if granularity == "all" and directive_tags and section_index is not None:
        for memo_sec in section_index["memos"]:
            memo_id = memo_sec["id"]
            if memo_id in covered_memo_ids:
                continue
            for section in memo_sec.get("sections") or []:
                if set(section.get("tags") or []) & directive_tags:
                    add_section(memo_id, section, "tag-match-section-extra")

    # Corpus-wide sticky-section sweep (both "sections" and "all"):
    # independent of memo-level selection/topics — see "Sticky sections
    # apply corpus-wide" in llmemos-protocol.md.
    if section_index is not None:
        for memo_sec in section_index["memos"]:
            memo_id = memo_sec["id"]
            if memo_id in covered_memo_ids:
                continue
            for section in memo_sec.get("sections") or []:
                if section.get("sticky"):
                    add_section(memo_id, section, "sticky-section-sweep")

    if used_whole and used_section:
        granularity_used = "mixed"
    elif used_section:
        granularity_used = "sections"
    else:
        granularity_used = "whole-memo"

    return load_plan, granularity_used


# ---------------------------------------------------------------------------
# Content emission helpers
# ---------------------------------------------------------------------------


def get_commit_short(repo_path: str, section_index: dict | None) -> str:
    """Short commit hash for provenance: section-index first, then git, then 'unknown'.

    Reading from section-index avoids a subprocess call in the common case
    (the index is already loaded) while remaining correct for corpora that
    lack an index.
    """
    if section_index and section_index.get("corpus_commit"):
        return str(section_index["corpus_commit"])
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def read_entry_content(repo_path: str, entry: dict) -> str:
    """Return the text for one load-plan entry: whole file or a line-range slice.

    start_line / end_line in the load plan are 1-indexed (the same convention
    as the Read tool's offset/limit parameters).  We convert to 0-indexed
    slices here: start_line-1 (inclusive) → end_line (exclusive, because
    end_line is the last line *included* in the section, so end_line as a
    Python slice upper bound gives us exactly that line).
    """
    path = os.path.join(repo_path, entry["file"])
    with open(path) as fh:
        lines = fh.readlines()
    if entry["mode"] == "whole":
        return "".join(lines)
    start = entry["start_line"] - 1
    end = entry["end_line"]  # inclusive 1-indexed == exclusive 0-indexed
    return "".join(lines[start:end])


def assemble_content(
    load_plan: list[dict],
    repo_path: str,
    commit: str,
    granularity_used: str,
    loaded_memo_count: int,
) -> str:
    """Assemble all load-plan entries into one Markdown document.

    Each entry is preceded by an HTML comment carrying full provenance:
    memo id, mode (whole/section), source file, line range (sections only),
    selection reason, and the corpus commit hash.  These comments let the
    agent (or a spot-check step) trace any block back to its origin in the
    verified repo clone without re-reading the original files.

    Read errors for individual entries are logged as warnings and replaced
    by an inline error comment so a single bad file does not abort the
    entire assembly.
    """
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [
        f"<!-- llmemos-content"
        f" | generated: {now}"
        f" | memos: {loaded_memo_count}"
        f" | granularity: {granularity_used}"
        f" | commit: {commit}"
        f" -->\n"
    ]

    for entry in load_plan:
        if entry["mode"] == "whole":
            prov = (
                f"<!-- llmemos-provenance"
                f" | memo: {entry['memo_id']}"
                f" | mode: whole"
                f" | reason: {entry['reason']}"
                f" | source: {entry['file']}"
                f" | commit: {commit}"
                f" -->"
            )
        else:
            prov = (
                f"<!-- llmemos-provenance"
                f" | memo: {entry['memo_id']}"
                f" | section: {entry['section_id']}"
                f" | lines: {entry['start_line']}-{entry['end_line']}"
                f" | reason: {entry['reason']}"
                f" | source: {entry['file']}"
                f" | commit: {commit}"
                f" -->"
            )

        try:
            body = read_entry_content(repo_path, entry)
        except OSError as exc:
            logger.warning("Could not read %s: %s", entry["file"], exc)
            body = f"<!-- ERROR: could not read {entry['file']}: {exc} -->\n"

        parts.append(f"\n{prov}\n{body}")

    return "".join(parts)


def sha256_hex(text: str) -> str:
    """SHA-256 hex digest of UTF-8-encoded text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an llmemos memo/section load plan (Step 3)."
    )
    parser.add_argument("--repo-path", required=True)

    directive = parser.add_mutually_exclusive_group()
    directive.add_argument("--recent", type=int, metavar="N")
    directive.add_argument("--tags", metavar="t1,t2")
    directive.add_argument("--alias", metavar="NAME")
    directive.add_argument("--all", action="store_true")
    directive.add_argument("--memos", metavar="id1,id2")

    parser.add_argument(
        "--tag-search",
        choices=["all", "sections", "memos"],
        help="One-shot granularity for this load (consumed and discarded).",
    )
    parser.add_argument(
        "--tag-search-default",
        choices=["all", "sections", "memos"],
        default="all",
        help="Persistent granularity preference (default: all). Used "
        "when --tag-search is not given.",
    )

    emit_group = parser.add_mutually_exclusive_group()
    emit_group.add_argument(
        "--emit",
        action="store_true",
        help="Assemble and write memo content to stdout; JSON metadata goes to "
        "stderr.  Intended for tool/pipeline consumers.",
    )
    emit_group.add_argument(
        "--emit-file",
        metavar="PATH",
        help="Assemble and write memo content to PATH.  The substring {commit} "
        "in PATH is replaced with the short corpus commit hash.  JSON output "
        "(stdout) gains emit_sha256 and emit_file fields.",
    )

    args = parser.parse_args()

    try:
        _frontmatter, memos = load_agents_md(args.repo_path)
    except (FileNotFoundError, ValueError) as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    taxonomy = load_taxonomy(args.repo_path)
    section_index = load_section_index(args.repo_path)

    directive_tags = resolve_directive_tags(args, taxonomy)
    memo_level_selected = resolve_memo_level_selection(args, memos, directive_tags)

    granularity = args.tag_search or args.tag_search_default
    load_plan, granularity_used = build_load_plan(
        memos, memo_level_selected, directive_tags, section_index, granularity
    )

    loaded_memo_count = len({entry["memo_id"] for entry in load_plan})

    output: dict = {
        "granularity_used": granularity_used,
        "total_memos": len(memos),
        "loaded_memo_count": loaded_memo_count,
        "load_plan": load_plan,
    }

    if args.emit or args.emit_file:
        commit = get_commit_short(args.repo_path, section_index)
        content = assemble_content(
            load_plan, args.repo_path, commit, granularity_used, loaded_memo_count
        )
        digest = sha256_hex(content)

        if args.emit:
            # Content → stdout; metadata JSON → stderr so tool consumers can
            # separate them (e.g. capture content with stdout, metadata with 2>).
            sys.stdout.write(content)
            sys.stderr.write(json.dumps(output, indent=2) + "\n")
            return

        # --emit-file: substitute {commit} in the path, write content, add
        # hash + resolved path to the JSON output on stdout.
        emit_path = args.emit_file.replace("{commit}", commit)
        try:
            with open(emit_path, "w") as fh:
                fh.write(content)
        except OSError as exc:
            print(json.dumps({"error": f"Could not write emit file {emit_path!r}: {exc}"}))
            sys.exit(1)
        output["emit_sha256"] = digest
        output["emit_file"] = emit_path

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
