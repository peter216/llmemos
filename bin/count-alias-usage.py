#!/usr/bin/env python3
# count-alias-usage.py
# Tallies memo loading directives from memo frontmatter and filenames in git log

import re
import subprocess
from collections import Counter

# Known aliases to scan for in opening messages / memo topics
ALIASES = [
    "batman",
    "memos",
    "memory",
    "protocol",
    "bruce-wayne",
    "work",
    "pitch",
    "centaur",
    "quality",
    "deep",
    "philosophy",
    "retirement",
    "money",
    "nest-egg",
    "tools",
    "plumbing",
    "ops",
]


def get_git_log(repo_path="."):
    # Also scan file contents, not just commit messages
    # For now, restrict to commit messages and look for the actual directive pattern
    result = subprocess.run(
        ["git", "log", "--all", "--format=%s %b"],  # subject + body
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    return result.stdout


def count_aliases(log_text):
    counts = Counter()
    for alias in ALIASES:
        # Must be at start of line, standalone directive only
        pattern = rf"^--{re.escape(alias)}\s*$"
        matches = re.findall(pattern, log_text, re.IGNORECASE | re.MULTILINE)
        if matches:
            counts[alias] = len(matches)
    return counts


if __name__ == "__main__":
    log = get_git_log()
    counts = count_aliases(log)
    print("\nAlias usage counts:")
    for alias, count in counts.most_common():
        print(f"  --{alias:<15} {count}")
