"""Core git operations — thin subprocess wrappers with no side effects beyond the filesystem."""

import subprocess
from pathlib import Path


def clone_or_pull(repo_url: str, dest_dir: Path) -> Path:
    """Clone repo_url into dest_dir, or pull if dest_dir already contains a git repo.

    Returns dest_dir as a Path.
    """
    dest_dir = Path(dest_dir)
    if (dest_dir / ".git").is_dir():
        subprocess.run(
            ["git", "-C", str(dest_dir), "pull", "--ff-only"],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            ["git", "clone", repo_url, str(dest_dir)],
            check=True,
            capture_output=True,
        )
    return dest_dir


def get_commit_info(repo_dir: Path) -> dict:
    """Return metadata about HEAD in repo_dir.

    Returns a dict with keys: hash, branch, sig_status, signer_key.
    sig_status is the raw git character: G (good), B (bad), N (none), U (untrusted), etc.
    """
    repo_dir = Path(repo_dir)

    short_hash = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    branch = subprocess.run(
        ["git", "-C", str(repo_dir), "symbolic-ref", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Use a pipe separator so empty %GK doesn't cause ambiguous splits
    sig_raw = subprocess.run(
        ["git", "-C", str(repo_dir), "log", "-1", "--format=%G?|%GK"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    sig_status, _, signer_key = sig_raw.partition("|")

    return {
        "hash": short_hash,
        "branch": branch,
        "sig_status": sig_status,
        "signer_key": signer_key,
    }


def read_agents_md(repo_dir: Path) -> str:
    """Return the full text of AGENTS.md from repo_dir.

    Raises FileNotFoundError if AGENTS.md is not present.
    """
    agents_md = Path(repo_dir) / "AGENTS.md"
    if not agents_md.is_file():
        raise FileNotFoundError(f"AGENTS.md not found in {repo_dir}")
    return agents_md.read_text()


def read_repo_file(repo_dir: Path, path: str) -> str:
    """Return the content of a file at path relative to repo_dir.

    Raises ValueError if path is absolute or contains '..' components — path traversal
    protection. Raises FileNotFoundError if the file does not exist within the repo.
    """
    repo_dir = Path(repo_dir).resolve()

    # Reject absolute paths and paths with .. components before any filesystem access
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError(f"path {path!r} is not a safe relative path")

    target = (repo_dir / path).resolve()

    # Final containment check: resolved path must still be inside repo_dir
    if not str(target).startswith(str(repo_dir) + "/") and target != repo_dir:
        raise ValueError(f"path {path!r} would escape the repo root")

    if not target.is_file():
        raise FileNotFoundError(f"file not found in repo: {path}")

    return target.read_text()


def verify_signature(repo_dir: Path, trusted_keys: list[str]) -> bool | str:
    """Return True if HEAD commit is signed by a key in trusted_keys, else a failure reason.

    trusted_keys: list of full GPG fingerprints (40 hex chars).

    git's %GK format returns the long key ID (last 16 hex chars of the fingerprint), so
    comparison is done against the last 16 chars of each trusted key, case-insensitively.
    """
    info = get_commit_info(repo_dir)
    sig_status = info["sig_status"]
    signer_key = info["signer_key"].upper()

    if not signer_key or sig_status == "N":
        return "commit is not signed"

    # Normalize trusted keys to their long key IDs (last 16 hex chars) for comparison
    trusted_long_ids = {k.upper()[-16:] for k in trusted_keys}
    if signer_key in trusted_long_ids:
        return True

    return f"signer key {signer_key!r} not in trusted keys"
