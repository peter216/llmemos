"""Simple file-based repo cache with (repo_url, branch)-keyed TTL expiry."""

import hashlib
import subprocess
import time
from pathlib import Path

from gh_mcp.git_ops import clone_or_pull


def _cache_key(repo_url: str, branch: str) -> str:
    """Return a deterministic 16-char hex key for a (repo_url, branch) pair."""
    return hashlib.sha256(f"{repo_url}:{branch}".encode()).hexdigest()[:16]


def get_repo(repo_url: str, branch: str, cache_dir: Path, ttl: int) -> Path:
    """Return the local path to a cached clone of repo_url at branch.

    Clones on first call. Re-pulls when the cached entry is older than ttl seconds.
    Returns the cached path without any git operation when the entry is still fresh.

    Args:
        repo_url: URL or local path of the remote repo.
        branch: Branch to check out after clone/pull.
        cache_dir: Root directory for all cached repos.
        ttl: Seconds before a re-pull is triggered. 0 always pulls.

    Returns:
        Path to the local repo directory inside the cache.
    """
    cache_dir = Path(cache_dir)
    key = _cache_key(repo_url, branch)
    entry_dir = cache_dir / key
    repo_path = entry_dir / "repo"
    timestamp_file = entry_dir / ".last_pull"

    entry_dir.mkdir(parents=True, exist_ok=True)

    needs_update = True
    if repo_path.is_dir() and timestamp_file.exists():
        age = time.time() - float(timestamp_file.read_text().strip())
        needs_update = age > ttl

    if needs_update:
        clone_or_pull(repo_url, repo_path)
        subprocess.run(
            ["git", "-C", str(repo_path), "checkout", branch],
            check=True,
            capture_output=True,
        )
        timestamp_file.write_text(str(time.time()))

    return repo_path
