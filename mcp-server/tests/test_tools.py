"""Tests for tools.py — verify_repo_state and fetch_memos MCP tool handlers."""

import os
from pathlib import Path

from gh_mcp.config import Config
from gh_mcp.tools import _repo_to_url, fetch_memos, read_repo_file, verify_repo_state

# GPG key constants — must match the constants in conftest.py
# Set TEST_SIGNING_KEY env var to your GPG fingerprint to enable signed-commit tests
TEST_SIGNING_KEY = os.environ.get("TEST_SIGNING_KEY", "")  # gitleaks:allow
OTHER_KEY = "AAAA0000111122223333444455556666BBBB7777"  # gitleaks:allow — placeholder untrusted key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(bare_repo: Path, tmp_path: Path, trusted_keys: list[str] | None = None) -> Config:
    """Build a Config scoped to a single bare repo and a temp cache dir."""
    return Config(
        allowed_repos=[str(bare_repo)],
        trusted_keys=trusted_keys if trusted_keys is not None else [TEST_SIGNING_KEY],
        cache_dir=tmp_path / "cache",
        cache_ttl=300,
        github_token=None,
    )


# ---------------------------------------------------------------------------
# verify_repo_state
# ---------------------------------------------------------------------------


class TestVerifyRepoState:
    def test_returns_correct_fields_for_valid_signed_repo(self, signed_bare_repo, tmp_path):
        """verify_repo_state returns the expected dict shape for a signed, trusted repo."""
        config = _config(signed_bare_repo, tmp_path)

        result = verify_repo_state(str(signed_bare_repo), "main", config)

        assert "commit" in result
        assert result["branch"] == "main"
        assert result["sig_status"] == "PASS"
        assert result["trusted"] is True
        assert isinstance(result["signer"], str)
        assert len(result["commit"]) == 7

    def test_trusted_false_when_signer_not_in_trusted_keys(self, signed_bare_repo, tmp_path):
        """verify_repo_state returns trusted=False when the signer key is not in TRUSTED_KEYS."""
        config = _config(signed_bare_repo, tmp_path, trusted_keys=[OTHER_KEY])

        result = verify_repo_state(str(signed_bare_repo), "main", config)

        assert result["trusted"] is False
        assert result["sig_status"] == "FAIL"

    def test_returns_error_for_repo_not_in_allowlist(self, tmp_path):
        """verify_repo_state returns an error dict when repo is not in ALLOWED_REPOS."""
        config = Config(
            allowed_repos=["example-user/example-corpus"],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
            cache_ttl=300,
        )

        result = verify_repo_state("owner/some-other-repo", "main", config)

        assert "error" in result
        assert "not in allowed" in result["error"].lower()


# ---------------------------------------------------------------------------
# fetch_memos
# ---------------------------------------------------------------------------


class TestFetchMemos:
    def test_returns_content_and_metadata_for_valid_repo(
        self, signed_bare_repo_with_agents, tmp_path
    ):
        """fetch_memos returns AGENTS.md content plus commit metadata."""
        config = _config(signed_bare_repo_with_agents, tmp_path)

        result = fetch_memos(str(signed_bare_repo_with_agents), "main", config)

        assert result["error"] is None
        assert "# Test AGENTS.md" in result["content"]
        assert len(result["commit"]) == 7
        assert result["sig_status"] == "PASS"

    def test_returns_error_field_when_agents_md_missing(self, signed_bare_repo, tmp_path):
        """fetch_memos returns error in the dict (not an exception) when AGENTS.md is absent."""
        config = _config(signed_bare_repo, tmp_path)

        result = fetch_memos(str(signed_bare_repo), "main", config)

        assert result["error"] is not None
        assert "AGENTS.md" in result["error"]
        assert result["content"] is None

    def test_returns_error_for_repo_not_in_allowlist(self, tmp_path):
        """fetch_memos returns an error dict when repo is not in ALLOWED_REPOS."""
        config = Config(
            allowed_repos=["example-user/example-corpus"],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
            cache_ttl=300,
        )

        result = fetch_memos("owner/some-other-repo", "main", config)

        assert result["error"] is not None
        assert "not in allowed" in result["error"].lower()
        assert result["content"] is None

    def test_returns_error_when_clone_fails(self, tmp_path):
        """fetch_memos returns an error dict (not an exception) when the clone fails."""
        nonexistent = str(tmp_path / "does_not_exist.git")
        config = Config(
            allowed_repos=[nonexistent],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
            cache_ttl=300,
        )

        result = fetch_memos(nonexistent, "main", config)

        assert result["error"] is not None
        assert result["content"] is None


# ---------------------------------------------------------------------------
# read_repo_file
# ---------------------------------------------------------------------------


class TestReadRepoFile:
    def test_returns_content_for_existing_file(self, signed_bare_repo_with_files, tmp_path):
        """read_repo_file returns file content for a valid path in an allowed repo."""
        config = _config(signed_bare_repo_with_files, tmp_path)

        result = read_repo_file(str(signed_bare_repo_with_files), "main", "taxonomy.yml", config)

        assert result["error"] is None
        assert "memo-protocol" in result["content"]
        assert len(result["commit"]) == 7

    def test_returns_content_for_file_in_subdirectory(self, signed_bare_repo_with_files, tmp_path):
        """read_repo_file returns content for a file nested in a subdirectory."""
        config = _config(signed_bare_repo_with_files, tmp_path)

        result = read_repo_file(
            str(signed_bare_repo_with_files), "main", "memos/session-memo-001.md", config
        )

        assert result["error"] is None
        assert "episodic content" in result["content"]

    def test_returns_error_for_missing_file(self, signed_bare_repo_with_files, tmp_path):
        """read_repo_file returns error in dict (not exception) when file is absent."""
        config = _config(signed_bare_repo_with_files, tmp_path)

        result = read_repo_file(str(signed_bare_repo_with_files), "main", "nonexistent.md", config)

        assert result["error"] is not None
        assert "nonexistent.md" in result["error"]
        assert result["content"] is None

    def test_returns_error_for_path_traversal_attempt(self, signed_bare_repo_with_files, tmp_path):
        """read_repo_file returns error dict (not exception) for '..' path traversal attempt."""
        config = _config(signed_bare_repo_with_files, tmp_path)

        result = read_repo_file(str(signed_bare_repo_with_files), "main", "../etc/passwd", config)

        assert result["error"] is not None
        assert "safe" in result["error"].lower()
        assert result["content"] is None

    def test_returns_error_for_repo_not_in_allowlist(self, tmp_path):
        """read_repo_file returns error dict when repo is not in ALLOWED_REPOS."""
        config = Config(
            allowed_repos=["example-user/example-corpus"],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
            cache_ttl=300,
        )

        result = read_repo_file("owner/other-repo", "main", "taxonomy.yml", config)

        assert result["error"] is not None
        assert "not in allowed" in result["error"].lower()
        assert result["content"] is None

    def test_returns_error_when_clone_fails(self, tmp_path):
        """read_repo_file returns error dict (not exception) when the clone fails."""
        nonexistent = str(tmp_path / "does_not_exist.git")
        config = Config(
            allowed_repos=[nonexistent],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
            cache_ttl=300,
        )

        result = read_repo_file(nonexistent, "main", "taxonomy.yml", config)

        assert result["error"] is not None
        assert result["content"] is None


# ---------------------------------------------------------------------------
# _repo_to_url — URL construction for GitHub slugs and local paths
# ---------------------------------------------------------------------------


class TestRepoToUrl:
    def test_github_slug_with_token_embeds_token_in_url(self):
        """GitHub slug + token → HTTPS URL with token embedded for auth."""
        url = _repo_to_url("example-user/example-corpus", "mytoken123")

        assert url == "https://mytoken123@github.com/example-user/example-corpus"

    def test_github_slug_without_token_uses_plain_https(self):
        """GitHub slug without token → plain HTTPS URL."""
        url = _repo_to_url("example-user/example-corpus", None)

        assert url == "https://github.com/example-user/example-corpus"

    def test_local_absolute_path_returned_unchanged(self):
        """Absolute local path is returned as-is — no GitHub URL construction."""
        url = _repo_to_url("/tmp/my-repo.git", None)

        assert url == "/tmp/my-repo.git"
