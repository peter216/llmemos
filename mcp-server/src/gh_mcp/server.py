"""MCP server — tool registration, SSE transport, and HTTP health endpoint."""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from gh_mcp.config import Config, load_config
from gh_mcp.tools import fetch_memos as _fetch_memos
from gh_mcp.tools import read_repo_file as _read_repo_file
from gh_mcp.tools import verify_repo_state as _verify_repo_state

VERSION = "0.1.0"


def create_app(config: Config) -> FastMCP:
    """Create and configure the FastMCP application.

    Registers both MCP tools and the HTTP health endpoint.
    Config is injected via closure — no global state, fully testable.

    Args:
        config: Runtime configuration for this server instance.

    Returns:
        A configured FastMCP instance ready to serve.
    """
    security = None
    if config.allowed_hosts:
        security = TransportSecuritySettings(allowed_hosts=config.allowed_hosts)

    mcp = FastMCP("gh-mcp", port=config.port, transport_security=security)

    @mcp.tool()
    def verify_repo_state(repo: str, branch: str) -> dict:
        """Return commit metadata and GPG signature trust status for a repo.

        Args:
            repo: GitHub slug (owner/name) or absolute local path.
            branch: Branch to inspect.

        Returns:
            Dict with commit, branch, sig_status, signer, trusted — or error key on failure.
        """
        return _verify_repo_state(repo, branch, config)

    @mcp.tool()
    def fetch_memos(repo: str, branch: str) -> dict:
        """Return AGENTS.md content and commit metadata for a repo.

        Args:
            repo: GitHub slug (owner/name) or absolute local path.
            branch: Branch to read from.

        Returns:
            Dict with content, commit, sig_status, error — error is None on success.
        """
        return _fetch_memos(repo, branch, config)

    @mcp.tool()
    def read_repo_file(repo: str, branch: str, path: str) -> dict:
        """Return the content of a file from a repo by its path relative to the repo root.

        Args:
            repo: GitHub slug (owner/name) or absolute local path.
            branch: Branch to read from.
            path: File path relative to repo root (e.g., "taxonomy.yml",
                  "memos/session-memo-001.md"). Must not be absolute or contain "..".

        Returns:
            Dict with content, commit, error — error is None on success, content is None
            on error.
        """
        return _read_repo_file(repo, branch, path, config)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": VERSION})

    return mcp


def main() -> None:
    """Entry point: load config from environment and run the server."""
    config = load_config()
    mcp = create_app(config)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
