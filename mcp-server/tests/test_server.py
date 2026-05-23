"""Phase 5 — server.py tests.

Tests the MCP server layer: tool registration, health endpoint, error handling
via call_tool, and an optional integration test against the live claude-memos repo.
"""

import json
import os

import pytest
from gh_mcp.config import Config
from starlette.testclient import TestClient

# GPG key fingerprints — must match the constants in conftest.py
# Set TEST_SIGNING_KEY env var to your GPG fingerprint to enable signed-commit tests
TEST_SIGNING_KEY = os.environ.get("TEST_SIGNING_KEY", "")  # gitleaks:allow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(bare_repo, tmp_path, trusted_keys=None):
    """Build a test Config scoped to a local bare repo fixture."""
    return Config(
        allowed_repos=[str(bare_repo)],
        trusted_keys=trusted_keys or [TEST_SIGNING_KEY],
        cache_dir=tmp_path / "cache",
        cache_ttl=300,
    )


def _parse(call_tool_result) -> dict:
    """Extract the dict from a call_tool TextContent result."""
    return json.loads(call_tool_result[0].text)


# ---------------------------------------------------------------------------
# TestToolRegistration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_both_tools_are_registered(self):
        """create_app registers verify_repo_state, fetch_memos, and read_repo_file."""
        from gh_mcp.server import create_app

        mcp = create_app(Config(allowed_repos=[], trusted_keys=[]))
        tool_names = {t.name for t in mcp._tool_manager.list_tools()}
        assert "verify_repo_state" in tool_names
        assert "fetch_memos" in tool_names
        assert "read_repo_file" in tool_names

    async def test_verify_repo_state_is_callable(self, signed_bare_repo_with_agents, tmp_path):
        """verify_repo_state returns a dict with expected keys when called via call_tool."""
        from gh_mcp.server import create_app

        mcp = create_app(_config(signed_bare_repo_with_agents, tmp_path))
        result = await mcp.call_tool(
            "verify_repo_state",
            {"repo": str(signed_bare_repo_with_agents), "branch": "main"},
        )
        data = _parse(result)
        assert set(data.keys()) == {"commit", "branch", "sig_status", "signer", "trusted"}

    async def test_fetch_memos_is_callable(self, signed_bare_repo_with_agents, tmp_path):
        """fetch_memos returns a dict with expected keys when called via call_tool."""
        from gh_mcp.server import create_app

        mcp = create_app(_config(signed_bare_repo_with_agents, tmp_path))
        result = await mcp.call_tool(
            "fetch_memos",
            {"repo": str(signed_bare_repo_with_agents), "branch": "main"},
        )
        data = _parse(result)
        assert set(data.keys()) == {"content", "commit", "sig_status", "error"}

    async def test_read_repo_file_is_callable(self, signed_bare_repo_with_files, tmp_path):
        """read_repo_file returns a dict with expected keys when called via call_tool."""
        from gh_mcp.server import create_app

        mcp = create_app(_config(signed_bare_repo_with_files, tmp_path))
        result = await mcp.call_tool(
            "read_repo_file",
            {"repo": str(signed_bare_repo_with_files), "branch": "main", "path": "taxonomy.yml"},
        )
        data = _parse(result)
        assert set(data.keys()) == {"content", "commit", "error"}
        assert data["error"] is None
        assert "memo-protocol" in data["content"]


# ---------------------------------------------------------------------------
# TestHealthEndpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_200(self):
        """GET /health returns HTTP 200."""
        from gh_mcp.server import create_app

        mcp = create_app(Config(allowed_repos=[], trusted_keys=[]))
        client = TestClient(mcp.streamable_http_app())
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_contains_status_and_version(self):
        """GET /health response body has 'status' and 'version' keys."""
        from gh_mcp.server import create_app

        mcp = create_app(Config(allowed_repos=[], trusted_keys=[]))
        client = TestClient(mcp.streamable_http_app())
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert "version" in data
        assert data["version"]  # non-empty


# ---------------------------------------------------------------------------
# TestToolErrorPaths
# ---------------------------------------------------------------------------


class TestToolErrorPaths:
    async def test_verify_repo_state_non_whitelisted_returns_error_dict(self, tmp_path):
        """Non-whitelisted repo returns an error dict — no exception propagates."""
        from gh_mcp.server import create_app

        config = Config(
            allowed_repos=["owner/allowed"],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
        )
        mcp = create_app(config)
        result = await mcp.call_tool("verify_repo_state", {"repo": "owner/other", "branch": "main"})
        data = _parse(result)
        assert "error" in data

    async def test_fetch_memos_non_whitelisted_returns_error_dict(self, tmp_path):
        """Non-whitelisted repo returns an error dict with null content — no exception."""
        from gh_mcp.server import create_app

        config = Config(
            allowed_repos=["owner/allowed"],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
        )
        mcp = create_app(config)
        result = await mcp.call_tool("fetch_memos", {"repo": "owner/other", "branch": "main"})
        data = _parse(result)
        assert "error" in data
        assert data["content"] is None

    async def test_verify_repo_state_clone_failure_returns_error_dict(self, tmp_path):
        """Clone failure (nonexistent path) surfaces as error dict, not exception."""
        from gh_mcp.server import create_app

        nonexistent = str(tmp_path / "does-not-exist.git")
        config = Config(
            allowed_repos=[nonexistent],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
        )
        mcp = create_app(config)
        result = await mcp.call_tool("verify_repo_state", {"repo": nonexistent, "branch": "main"})
        data = _parse(result)
        assert "error" in data

    async def test_fetch_memos_clone_failure_returns_error_dict(self, tmp_path):
        """Clone failure (nonexistent path) surfaces as error dict, not exception."""
        from gh_mcp.server import create_app

        nonexistent = str(tmp_path / "does-not-exist.git")
        config = Config(
            allowed_repos=[nonexistent],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
        )
        mcp = create_app(config)
        result = await mcp.call_tool("fetch_memos", {"repo": nonexistent, "branch": "main"})
        data = _parse(result)
        assert "error" in data
        assert data["content"] is None

    async def test_read_repo_file_non_whitelisted_returns_error_dict(self, tmp_path):
        """Non-whitelisted repo returns an error dict with null content — no exception."""
        from gh_mcp.server import create_app

        config = Config(
            allowed_repos=["owner/allowed"],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
        )
        mcp = create_app(config)
        result = await mcp.call_tool(
            "read_repo_file",
            {"repo": "owner/other", "branch": "main", "path": "taxonomy.yml"},
        )
        data = _parse(result)
        assert "error" in data
        assert data["content"] is None

    async def test_read_repo_file_path_traversal_returns_error_dict(
        self, signed_bare_repo_with_files, tmp_path
    ):
        """Path traversal attempt returns error dict — no exception propagates."""
        from gh_mcp.server import create_app

        mcp = create_app(_config(signed_bare_repo_with_files, tmp_path))
        result = await mcp.call_tool(
            "read_repo_file",
            {
                "repo": str(signed_bare_repo_with_files),
                "branch": "main",
                "path": "../etc/passwd",
            },
        )
        data = _parse(result)
        assert data["error"] is not None
        assert data["content"] is None


# ---------------------------------------------------------------------------
# TestIntegration — requires GITHUB_TOKEN and network access
# ---------------------------------------------------------------------------

_NEEDS_TOKEN = pytest.mark.skipif(
    not os.environ.get("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN not set — skipping live integration test",
)

EXAMPLE_CORPUS_REPO = os.environ.get("TEST_REPO", "example-user/example-corpus")


class TestIntegration:
    @_NEEDS_TOKEN
    async def test_verify_repo_state_against_live_claude_memos(self, tmp_path):
        """In-process MCP call against the real claude-memos repo."""
        from gh_mcp.server import create_app

        config = Config(
            allowed_repos=[EXAMPLE_CORPUS_REPO],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
            cache_ttl=300,
            github_token=os.environ["GITHUB_TOKEN"],
        )
        mcp = create_app(config)
        result = await mcp.call_tool(
            "verify_repo_state",
            {"repo": EXAMPLE_CORPUS_REPO, "branch": "main"},
        )
        data = _parse(result)
        assert "error" not in data
        assert data["sig_status"] == "PASS"
        assert data["trusted"] is True
        assert len(data["commit"]) == 7

    @_NEEDS_TOKEN
    async def test_fetch_memos_against_live_claude_memos(self, tmp_path):
        """In-process MCP call fetches AGENTS.md from the real claude-memos repo."""
        from gh_mcp.server import create_app

        config = Config(
            allowed_repos=[EXAMPLE_CORPUS_REPO],
            trusted_keys=[TEST_SIGNING_KEY],
            cache_dir=tmp_path / "cache",
            cache_ttl=300,
            github_token=os.environ["GITHUB_TOKEN"],
        )
        mcp = create_app(config)
        result = await mcp.call_tool(
            "fetch_memos",
            {"repo": EXAMPLE_CORPUS_REPO, "branch": "main"},
        )
        data = _parse(result)
        assert data["error"] is None
        assert data["content"] is not None
        assert "canonical-repo" in data["content"]
        assert data["sig_status"] == "PASS"
