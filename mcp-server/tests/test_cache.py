"""Tests for cache.py — (repo, branch)-keyed TTL-based local git cache."""

import os
import subprocess
import time
from pathlib import Path

from gh_mcp.cache import get_repo

# ---------------------------------------------------------------------------
# Helper — push a new commit to a bare repo via a scratch clone
# ---------------------------------------------------------------------------


def _push_new_commit(bare: Path, tmp_path: Path, filename: str, content: str) -> None:
    """Push one new unsigned commit to bare's main branch."""
    env = {
        "HOME": str(tmp_path),
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    work = tmp_path / f"push_{filename}"
    subprocess.run(["git", "clone", str(bare), str(work)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "Test User"], check=True)
    (work / filename).write_text(content)
    subprocess.run(["git", "-C", str(work), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(work), "commit", "--no-gpg-sign", "-m", f"add {filename}"],
        check=True,
        capture_output=True,
        env={**os.environ, **env},
    )
    subprocess.run(
        ["git", "-C", str(work), "push", "origin", "main"], check=True, capture_output=True
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetRepo:
    def test_first_request_creates_cache_entry(self, local_bare_repo, tmp_path):
        """First call clones the repo and returns a valid, populated path."""
        cache_dir = tmp_path / "cache"

        result = get_repo(str(local_bare_repo), "main", cache_dir, ttl=300)

        assert result.exists()
        assert (result / ".git").is_dir()
        assert (result / "README.md").exists()

    def test_second_request_within_ttl_skips_pull(self, local_bare_repo, tmp_path):
        """Second call within TTL returns cached path without pulling new remote commits."""
        cache_dir = tmp_path / "cache"

        # Warm the cache
        get_repo(str(local_bare_repo), "main", cache_dir, ttl=300)

        # Push a new commit to the remote while the cache is still fresh
        _push_new_commit(local_bare_repo, tmp_path, "remote_only.txt", "should not appear\n")

        # Second call is within TTL — must NOT pull
        result = get_repo(str(local_bare_repo), "main", cache_dir, ttl=300)

        assert not (result / "remote_only.txt").exists()

    def test_request_after_ttl_expiry_triggers_pull(self, local_bare_repo, tmp_path):
        """Call after TTL expiry re-pulls and picks up new remote commits."""
        cache_dir = tmp_path / "cache"

        # Warm the cache
        get_repo(str(local_bare_repo), "main", cache_dir, ttl=300)

        # Push a new commit to the remote
        _push_new_commit(local_bare_repo, tmp_path, "after_expiry.txt", "pulled content\n")

        # Backdate the .last_pull timestamp so the cache entry looks expired
        timestamp_files = list(cache_dir.rglob(".last_pull"))
        assert len(timestamp_files) == 1, "Expected exactly one .last_pull file"
        timestamp_files[0].write_text(str(time.time() - 400))  # 400s ago, TTL=300

        # Call with TTL=300 — cache is expired, must pull
        result = get_repo(str(local_bare_repo), "main", cache_dir, ttl=300)

        assert (result / "after_expiry.txt").exists()

    def test_different_branches_use_independent_cache_entries(self, two_branch_bare_repo, tmp_path):
        """(repo, main) and (repo, dev) are stored in separate directories."""
        cache_dir = tmp_path / "cache"

        main_path = get_repo(str(two_branch_bare_repo), "main", cache_dir, ttl=300)
        dev_path = get_repo(str(two_branch_bare_repo), "dev", cache_dir, ttl=300)

        assert main_path != dev_path
        assert main_path.parent != dev_path.parent
