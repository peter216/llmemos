#!/usr/bin/env python3
"""llmemos_select.py — memo/section selection and load-plan builder.

Implements the "Select memos to load" / "Loading granularity" / per-memo
loading logic from llmemos-protocol.md (Path A / Claude Code, Step 3).
Given a cloned corpus repo (AGENTS.md, taxonomy.yml, and an optional
section-index.json) and a loading directive, emits a JSON load plan: a
list of {memo, mode, ...} entries the agent can turn directly into Read
tool calls (whole-file reads, or offset/limit reads for section-level
entries).

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
import json
import os
import re
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

        if memo.get("sticky") or not sections:
            # Memo-level sticky memos always load whole (read-efficiency
            # optimization — see protocol Step 3 rule 1). Memos with no
            # section entries also load whole (nothing finer to load).
            add_whole(memo_id, "memo-sticky" if memo.get("sticky") else "no-sections")
            continue

        if directive_tags is None:
            # Non-tag-based directive (--all, --memos, --recent): the
            # memo was explicitly selected by identity, so load it whole
            # rather than guessing which sections are "relevant".
            add_whole(memo_id, "directive-selected-whole")
            continue

        if granularity == "all":
            # "all": memo-level matches load whole; corpus-wide
            # tag-matching sections (below) extend recall to memos
            # outside this selection set.
            add_whole(memo_id, "directive-selected-whole")
            continue

        # granularity == "sections": load only matching/sticky sections.
        for section in sections:
            if section.get("sticky"):
                add_section(memo_id, section, "sticky-section")
            elif set(section.get("tags") or []) & directive_tags:
                add_section(memo_id, section, "tag-match-section")

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

    print(
        json.dumps(
            {
                "granularity_used": granularity_used,
                "total_memos": len(memos),
                "loaded_memo_count": loaded_memo_count,
                "load_plan": load_plan,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
