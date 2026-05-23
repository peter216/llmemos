"""MCP tool handlers — thin orchestration over git_ops and cache."""

from gh_mcp.cache import get_repo
from gh_mcp.config import Config
from gh_mcp.git_ops import get_commit_info, read_agents_md, verify_signature
from gh_mcp.git_ops import read_repo_file as _read_repo_file


def _normalize_repo(repo: str) -> str:
    """Strip github.com/ prefix from repo identifiers.

    The protocol document stores canonical-repo as 'github.com/owner/name'
    for human readability; the tools expect the bare slug 'owner/name'.
    """
    if repo.startswith("github.com/"):
        return repo[len("github.com/") :]
    return repo


def _repo_to_url(repo: str, github_token: str | None) -> str:
    """Convert a repo slug or local path to a clonable URL.

    GitHub slugs (owner/name) are converted to HTTPS URLs.
    A token, when provided, is embedded in the URL for private repo access.
    Absolute local paths are returned unchanged.
    """
    if repo.startswith("/") or repo.startswith("."):
        return repo

    # GitHub slug: owner/name
    if github_token:
        return f"https://{github_token}@github.com/{repo}"
    return f"https://github.com/{repo}"


def verify_repo_state(repo: str, branch: str, config: Config) -> dict:
    """Return commit metadata and signature trust status for a repo.

    Args:
        repo: GitHub slug (owner/name), github.com/-prefixed slug, or absolute local path.
        branch: Branch to inspect.
        config: Runtime configuration (allowlist, trusted keys, cache settings).

    Returns:
        Dict with keys: commit, branch, sig_status, signer, trusted.
        On error: dict with a single 'error' key.
    """
    repo = _normalize_repo(repo)
    if repo not in config.allowed_repos:
        return {"error": f"repo {repo!r} not in allowed repos"}

    repo_url = _repo_to_url(repo, config.github_token)

    try:
        repo_path = get_repo(repo_url, branch, config.cache_dir, config.cache_ttl)
    except Exception as exc:
        return {"error": str(exc)}

    info = get_commit_info(repo_path)
    sig_result = verify_signature(repo_path, config.trusted_keys)

    return {
        "commit": info["hash"],
        "branch": info["branch"],
        "sig_status": "PASS" if sig_result is True else "FAIL",
        "signer": info["signer_key"],
        "trusted": sig_result is True,
    }


def fetch_memos(repo: str, branch: str, config: Config) -> dict:
    """Return AGENTS.md content and commit metadata for a repo.

    Args:
        repo: GitHub slug (owner/name), github.com/-prefixed slug, or absolute local path.
        branch: Branch to read from.
        config: Runtime configuration (allowlist, trusted keys, cache settings).

    Returns:
        Dict with keys: content, commit, sig_status, error.
        'error' is None on success; 'content' is None on error.
    """
    repo = _normalize_repo(repo)
    if repo not in config.allowed_repos:
        return {
            "content": None,
            "commit": None,
            "sig_status": None,
            "error": f"repo {repo!r} not in allowed repos",
        }

    repo_url = _repo_to_url(repo, config.github_token)

    try:
        repo_path = get_repo(repo_url, branch, config.cache_dir, config.cache_ttl)
    except Exception as exc:
        return {"content": None, "commit": None, "sig_status": None, "error": str(exc)}

    info = get_commit_info(repo_path)
    sig_result = verify_signature(repo_path, config.trusted_keys)

    try:
        content = read_agents_md(repo_path)
        error = None
    except FileNotFoundError as exc:
        content = None
        error = str(exc)

    return {
        "content": content,
        "commit": info["hash"],
        "sig_status": "PASS" if sig_result is True else "FAIL",
        "error": error,
    }


def read_repo_file(repo: str, branch: str, path: str, config: Config) -> dict:
    """Return the content of a file from a repo by its path relative to the repo root.

    Args:
        repo: GitHub slug (owner/name), github.com/-prefixed slug, or absolute local path.
        branch: Branch to read from.
        path: File path relative to repo root (e.g., "taxonomy.yml",
              "memos/session-memo-001.md"). Must not be absolute or contain "..".
        config: Runtime configuration (allowlist, trusted keys, cache settings).

    Returns:
        Dict with keys: content (str), commit (str), error (str or None).
        content is None on error.
    """
    repo = _normalize_repo(repo)
    if repo not in config.allowed_repos:
        return {
            "content": None,
            "commit": None,
            "error": f"repo {repo!r} not in allowed repos",
        }

    repo_url = _repo_to_url(repo, config.github_token)

    try:
        repo_path = get_repo(repo_url, branch, config.cache_dir, config.cache_ttl)
    except Exception as exc:
        return {"content": None, "commit": None, "error": str(exc)}

    info = get_commit_info(repo_path)

    try:
        content = _read_repo_file(repo_path, path)
        error = None
    except (FileNotFoundError, ValueError) as exc:
        content = None
        error = str(exc)

    return {
        "content": content,
        "commit": info["hash"],
        "error": error,
    }
