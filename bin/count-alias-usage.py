#!/usr/bin/env python3
"""count-alias-usage.py

Tallies llmemos memo loading directives from two sources:

  1. ~/.llmemos/directive-usage.log — written by llmemos and compatible launchers.
     Each line: <timestamp>\\t<source>\\t<type>\\t<value>\\t<uuid>
     This is the primary source for launcher-invoked directives.

  2. Claude Code .jsonl session files — catches directives typed directly as
     the opening line of a user message (Path B / manual sessions).

Counts are merged; a directive appearing in both sources for the same session
is not deduplicated (log entries and JSONL entries are independent records).

Required env vars:
  MEMO_REPO_PATH         Path to a local clone of your memo corpus (for taxonomy.yml).

Optional env vars:
  CLAUDE_PROJECT_PATH    Root of Claude Code project storage.
                         Default: ~/.claude/projects
  LLMEMOS_LOG            Path to the directive usage log.
                         Default: ~/.llmemos/directive-usage.log
  DEBUG=1                Enable debug logging.
"""

import json
import logging
import os
import re
import sys
from collections import Counter
from glob import glob
from pathlib import Path

import yaml

debug = os.environ.get("DEBUG") == "1"

try:
    from llmemos_logger import get_logger  # optional: colored output + NOTICE/SUCCESS levels
    logger = get_logger(__name__, level=logging.DEBUG if debug else logging.INFO)
except ImportError:
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    logger = logging.getLogger(__name__)


def load_taxonomy(taxonomy_path: str) -> dict:
    """Load and parse taxonomy.yml, exiting with a clear message on failure."""
    try:
        with open(taxonomy_path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"taxonomy.yml not found: {taxonomy_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse taxonomy.yml: {e}")
        sys.exit(1)


def get_opening_text(entry: dict) -> str:
    """Extract the user-authored text from a JSONL message entry.

    Claude Code stores content as either a plain string or a list of typed
    blocks. For list format, the first text block is the user's actual input;
    subsequent blocks are system-injected context (system-reminder, etc.).
    """
    content = entry.get("message", {}).get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
    return ""


def extract_session_directive(filepath: str):
    """Return (directive_type, value) from the opening user message, or None.

    Scans the session file for the first substantive (non-meta) user message
    and checks whether its first line is an llmemos loading directive. Stops
    after the first substantive message — directives only appear there.

    Returns:
        ("alias", "protocol") or ("tags", "finance,personal") or None
    """
    try:
        with open(filepath) as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    logger.debug(f"{filepath}: JSON parse error: {exc}")
                    continue

                if entry.get("type") != "user":
                    continue
                if entry.get("isMeta"):
                    continue

                text = get_opening_text(entry)
                if not text:
                    continue

                first_line = text.strip().splitlines()[0] if text.strip() else ""
                m = re.match(r"--(alias|tags)\s+(\S+)", first_line)
                if m:
                    return m.group(1), m.group(2)

                # First substantive user message found, no directive — stop looking.
                break
    except OSError as exc:
        logger.debug(f"Could not read {filepath}: {exc}")

    return None


def count_from_log(
    log_path: Path, tags: dict, aliases: dict
) -> tuple[Counter, Counter]:
    """Count directives from the llmemos directive-usage.log file.

    Log format (tab-separated):
        <timestamp>  <source>  <type>  <value>  <uuid>

    Each line is one launcher invocation. Source identifies the launcher
    (e.g. "llmemos", "claude-launcher"). UUID is unique per invocation.
    """
    alias_counts: Counter = Counter()
    tag_counts: Counter = Counter()

    if not log_path.exists():
        logger.debug(f"No directive log found at {log_path}")
        return alias_counts, tag_counts

    with open(log_path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 5:
                logger.debug(f"{log_path}:{lineno}: unexpected format: {line!r}")
                continue
            _timestamp, source, directive_type, value, _uuid = parts
            logger.debug(f"Log entry: source={source} type={directive_type} value={value} uuid={_uuid}")
            if directive_type == "alias":
                if value in aliases:
                    alias_counts[value] += 1
                else:
                    logger.debug(f"Unknown alias '{value}' at line {lineno}")
            elif directive_type == "tags":
                for tag in (t.strip() for t in value.split(",")):
                    if tag in tags:
                        tag_counts[tag] += 1
                    else:
                        logger.debug(f"Unknown tag '{tag}' at line {lineno}")

    logger.debug(f"Log: {sum(alias_counts.values())} alias hits, {sum(tag_counts.values())} tag hits")
    return alias_counts, tag_counts


def count_from_jsonl(
    project_path: str, tags: dict, aliases: dict
) -> tuple[Counter, Counter]:
    """Count directives typed as the opening line of user messages in .jsonl files."""
    session_files = glob(
        os.path.join(project_path, "**", "*.jsonl"), recursive=True
    )
    logger.debug(f"Found {len(session_files)} session files under {project_path}")

    alias_counts: Counter = Counter()
    tag_counts: Counter = Counter()

    for filepath in session_files:
        result = extract_session_directive(filepath)
        if result is None:
            continue
        directive_type, value = result
        if directive_type == "alias":
            if value in aliases:
                alias_counts[value] += 1
            else:
                logger.debug(f"Unknown alias '{value}' in {filepath}")
        elif directive_type == "tags":
            for tag in (t.strip() for t in value.split(",")):
                if tag in tags:
                    tag_counts[tag] += 1
                else:
                    logger.debug(f"Unknown tag '{tag}' in {filepath}")

    logger.debug(f"JSONL: {sum(alias_counts.values())} alias hits, {sum(tag_counts.values())} tag hits")
    return alias_counts, tag_counts


if __name__ == "__main__":
    memo_repo_path = os.environ.get("MEMO_REPO_PATH")
    if not memo_repo_path:
        print("MEMO_REPO_PATH not set; cannot load taxonomy.yml", file=sys.stderr)
        sys.exit(1)

    project_path = os.environ.get(
        "CLAUDE_PROJECT_PATH",
        str(Path.home() / ".claude" / "projects"),
    )
    log_path = Path(os.environ.get(
        "LLMEMOS_LOG",
        str(Path.home() / ".llmemos" / "directive-usage.log"),
    ))

    taxonomy = load_taxonomy(os.path.join(memo_repo_path, "taxonomy.yml"))
    tags = taxonomy.get("tags", {})
    aliases = taxonomy.get("aliases", {})
    logger.debug(f"Loaded {len(aliases)} aliases, {len(tags)} tags from taxonomy")

    log_aliases, log_tags = count_from_log(log_path, tags, aliases)
    jsonl_aliases, jsonl_tags = count_from_jsonl(project_path, tags, aliases)

    alias_counts = log_aliases + jsonl_aliases
    tag_counts = log_tags + jsonl_tags

    print("\nAlias usage counts:")
    if alias_counts:
        for alias, count in alias_counts.most_common():
            print(f"  {alias:<20} {count}")
    else:
        print("  (none found)")

    print("\nTag usage counts:")
    if tag_counts:
        for tag, count in tag_counts.most_common():
            print(f"  {tag:<20} {count}")
    else:
        print("  (none found)")
