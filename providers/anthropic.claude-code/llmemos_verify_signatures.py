#!/usr/bin/env python3
"""llmemos_verify_signatures.py — commit signature scoring for llmemos.

Implements the "Commit Signature Scoring Rules" from llmemos-protocol.md
(Path A / Claude Code, Step 2). Scores the most recent N commits of a
cloned corpus repo for the "historical coherence" validation check,
walking the first-parent chain past consecutive infrastructure-signed
commits (bounded) to find the nearest personally-signed or
non-infrastructure-signed ancestor.

Scoring rules (see llmemos-protocol.md, "Commit Signature Scoring Rules"):
  1. Personal trusted key, valid signature -> 0 (clean)
  2. Infrastructure key -> walk up to --max-walk first-parent hops
     (including the commit itself) for the first commit that is either
     personally signed or not infrastructure-signed:
       - personal key found       -> 0
       - unsigned commit found     -> 3 (per rule 4)
       - unknown-key commit found  -> 2 (per rule 3)
       - bound exhausted           -> 2
  3. Unknown key (neither trusted list) -> 2
  4. No signature -> 3

Usage:
    python3 llmemos_verify_signatures.py \\
        --repo-path /tmp/claude-memos-session \\
        --personal-key 63611E761833B99242003DE2D8DDC4C14D0B745A \\
        --personal-key 757BECAFEA8B1E5EA35C5BE5CE435ECBE860D0D0 \\
        --agents-md /tmp/claude-memos-session/AGENTS.md \\
        --commits 5 --max-walk 10

Output: a single JSON object on stdout (schema below). Exit code is
always 0 — the agent decides what to do with `max_score`; this script
only reports.

Output schema:
{
  "head_commit": "<sha>",
  "commits": [
    {
      "sha": "...",
      "subject": "...",
      "classification": "personal|infrastructure|unknown|none",
      "key_id": "...",            // %GK, may be empty
      "fingerprint": "...",       // %GF, may be empty
      "raw_status": "G|U|X|Y|R|B|E|N",
      "score": 0,
      "walk": [                   // only present for "infrastructure" hops
        {"sha": "...", "classification": "...", "key_id": "...",
         "fingerprint": "...", "raw_status": "..."}
      ],
      "resolution": "personal-ancestor|unsigned-ancestor|"
                     "unknown-ancestor|bound-exhausted|history-exhausted|"
                     null
    }
  ],
  "max_score": 0
}
"""

from __future__ import annotations

import argparse
import json
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

# Field separator unlikely to appear in commit subjects; git emits the
# literal byte for %x notation.
FIELD_SEP = "\x1f"

# git log format: hash, raw signature status, signer fingerprint, signer
# key id, subject. One record per line (default "format:" behavior).
LOG_FORMAT = FIELD_SEP.join(["%H", "%G?", "%GF", "%GK", "%s"])


def run_git_log(repo_path: str, count: int) -> list[dict]:
    """Return up to `count` commits in first-parent order from HEAD.

    Because `--first-parent` is used, entry i+1 in the returned list is
    exactly the first-parent ancestor of entry i — this lets the
    walk-back logic simply advance an index rather than re-querying git
    for each hop.

    Raises:
        RuntimeError: if `git log` fails (e.g. invalid repo path).
    """
    cmd = [
        "git",
        "-C",
        repo_path,
        "log",
        "--first-parent",
        f"-n{count}",
        f"--format={LOG_FORMAT}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git log failed: {result.stderr.strip()}")

    commits = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        sha, status, fingerprint, key_id, subject = line.split(FIELD_SEP, 4)
        commits.append(
            {
                "sha": sha,
                "raw_status": status,
                "fingerprint": fingerprint,
                "key_id": key_id,
                "subject": subject,
            }
        )
    return commits


def load_infra_keys_from_agents_md(path: str) -> list[str]:
    """Extract `trusted-infrastructure-signing-keys` from AGENTS.md frontmatter.

    Returns an empty list if the file, frontmatter, or field is absent —
    this is graceful degradation, not an error (the field is optional per
    the protocol).
    """
    try:
        with open(path) as f:
            content = f.read()
    except FileNotFoundError:
        logger.warning("AGENTS.md not found at %s; no infra keys loaded", path)
        return []

    match = re.match(r"^---\n(.*?)\n---\n", content, re.S)
    if not match:
        logger.warning("No frontmatter found in %s", path)
        return []

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        logger.warning("Failed to parse frontmatter in %s: %s", path, e)
        return []

    keys = frontmatter.get("trusted-infrastructure-signing-keys") or []
    return [str(k) for k in keys]


def classify(commit: dict, personal_keys: set[str], infra_keys: set[str]) -> str:
    """Classify a commit's signature as personal/infrastructure/unknown/none.

    `personal_keys` are full fingerprints (compared against %GF).
    `infra_keys` are short key IDs (compared against %GK).
    """
    status = commit["raw_status"]
    fingerprint = commit["fingerprint"].upper().replace(" ", "")
    key_id = commit["key_id"].upper()

    if status == "N":
        return "none"

    # "G", "U", "X", "Y" are signatures git could verify (good, or good but
    # untrusted/expired). "R"/"B" (revoked/bad) and "E" (can't check, no
    # pubkey) cannot be trusted as personal even if a fingerprint happens
    # to be present.
    if status in ("G", "U", "X", "Y") and fingerprint in personal_keys:
        return "personal"

    if key_id and key_id in infra_keys:
        return "infrastructure"

    return "unknown"


def score_commit(
    index: int,
    commits: list[dict],
    personal_keys: set[str],
    infra_keys: set[str],
    max_walk: int,
) -> dict:
    """Score a single commit (by index into the first-parent `commits` list)."""
    commit = commits[index]
    classification = classify(commit, personal_keys, infra_keys)

    entry = {
        "sha": commit["sha"],
        "subject": commit["subject"],
        "classification": classification,
        "key_id": commit["key_id"],
        "fingerprint": commit["fingerprint"],
        "raw_status": commit["raw_status"],
        "resolution": None,
    }

    if classification == "personal":
        entry["score"] = 0
        return entry
    if classification == "none":
        entry["score"] = 3
        return entry
    if classification == "unknown":
        entry["score"] = 2
        return entry

    # classification == "infrastructure": walk the first-parent chain.
    walk = []
    resolution = "history-exhausted"
    score = 2
    for hop in range(1, max_walk):
        j = index + hop
        if j >= len(commits):
            # Ran out of fetched history before resolving or exhausting
            # the bound. Caller should consider a deeper fetch.
            break
        ancestor = commits[j]
        ancestor_class = classify(ancestor, personal_keys, infra_keys)
        walk.append(
            {
                "sha": ancestor["sha"],
                "classification": ancestor_class,
                "key_id": ancestor["key_id"],
                "fingerprint": ancestor["fingerprint"],
                "raw_status": ancestor["raw_status"],
            }
        )
        if ancestor_class == "personal":
            score = 0
            resolution = "personal-ancestor"
            break
        if ancestor_class == "none":
            score = 3
            resolution = "unsigned-ancestor"
            break
        if ancestor_class == "unknown":
            score = 2
            resolution = "unknown-ancestor"
            break
        # ancestor_class == "infrastructure": keep walking
        if hop == max_walk - 1:
            resolution = "bound-exhausted"

    entry["walk"] = walk
    entry["score"] = score
    entry["resolution"] = resolution
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score commit signatures per the llmemos protocol "
        "(Step 2, historical coherence)."
    )
    parser.add_argument("--repo-path", required=True, help="Path to the cloned corpus repo.")
    parser.add_argument(
        "--personal-key",
        action="append",
        default=[],
        metavar="FINGERPRINT",
        help="Personal trusted key fingerprint (repeatable).",
    )
    parser.add_argument(
        "--infra-key",
        action="append",
        default=[],
        metavar="KEYID",
        help="Trusted infrastructure signing key ID (repeatable).",
    )
    parser.add_argument(
        "--agents-md",
        metavar="PATH",
        help="Also load trusted-infrastructure-signing-keys from this AGENTS.md frontmatter.",
    )
    parser.add_argument(
        "--commits",
        type=int,
        default=5,
        help="Number of most recent commits to score (default: 5).",
    )
    parser.add_argument(
        "--max-walk",
        type=int,
        default=10,
        help="Max first-parent hops to inspect when walking back past "
        "infrastructure-signed commits, including the commit itself "
        "(default: 10).",
    )
    args = parser.parse_args()

    if not args.personal_key:
        logger.warning(
            "No --personal-key fingerprints supplied; no commit can score as 'personal'."
        )

    infra_keys = {k.upper() for k in args.infra_key}
    if args.agents_md:
        infra_keys |= {k.upper() for k in load_infra_keys_from_agents_md(args.agents_md)}

    personal_keys = {k.upper().replace(" ", "") for k in args.personal_key}

    # Fetch enough history for `--commits` checked commits plus a full
    # `--max-walk` walk from the last of them.
    fetch_count = args.commits + args.max_walk
    try:
        commits = run_git_log(args.repo_path, fetch_count)
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    if not commits:
        print(json.dumps({"error": "no commits found"}))
        sys.exit(1)

    scored = []
    max_score = 0
    for i in range(min(args.commits, len(commits))):
        result = score_commit(i, commits, personal_keys, infra_keys, args.max_walk)
        scored.append(result)
        max_score = max(max_score, result["score"])

    print(
        json.dumps(
            {
                "head_commit": commits[0]["sha"],
                "commits": scored,
                "max_score": max_score,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
