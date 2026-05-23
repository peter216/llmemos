"""Environment-driven configuration for gh-mcp."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Runtime configuration, sourced from environment variables via load_config().

    All fields can also be set directly for testing without touching the environment.
    """

    allowed_repos: list[str]
    trusted_keys: list[str]
    cache_dir: Path = field(default_factory=lambda: Path("/tmp/gh-mcp-cache"))
    cache_ttl: int = 300
    github_token: str | None = None
    port: int = 8788
    allowed_hosts: list[str] = field(default_factory=list)


def load_config() -> Config:
    """Build a Config from environment variables.

    Env vars:
        ALLOWED_REPOS   Comma-separated repo slugs or paths (required — no default)
        TRUSTED_KEYS    Comma-separated GPG fingerprints (required for signature verification)
        CACHE_DIR       Local cache root (default: /tmp/gh-mcp-cache)
        CACHE_TTL       Seconds before re-pull (default: 300)
        GITHUB_TOKEN    GitHub personal access token (required for private repos)
        PORT            Server listen port (default: 8788)
        ALLOWED_HOSTS   Comma-separated hostnames accepted in Host header (for reverse proxy)
    """
    allowed_repos_raw = os.environ.get("ALLOWED_REPOS", "")
    trusted_keys_raw = os.environ.get("TRUSTED_KEYS", "")
    allowed_hosts_raw = os.environ.get("ALLOWED_HOSTS", "")

    return Config(
        allowed_repos=[r.strip() for r in allowed_repos_raw.split(",") if r.strip()],
        trusted_keys=[k.strip() for k in trusted_keys_raw.split(",") if k.strip()],
        cache_dir=Path(os.environ.get("CACHE_DIR", "/tmp/gh-mcp-cache")),
        cache_ttl=int(os.environ.get("CACHE_TTL", "300")),
        github_token=os.environ.get("GITHUB_TOKEN"),
        port=int(os.environ.get("PORT", "8788")),
        allowed_hosts=[h.strip() for h in allowed_hosts_raw.split(",") if h.strip()],
    )
