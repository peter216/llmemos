# gh-mcp — llmemos MCP Server

The MCP server that powers **Path B** (Claude.ai and other MCP-capable agents) of the
llmemos Bootstrapping Protocol. It exposes three tools over HTTP that let the AI verify
GPG-signed commits and read memo files from a private GitHub corpus repo:

| Tool | What it does |
|---|---|
| `verify_repo_state(repo, branch)` | Returns commit hash + GPG signature trust status |
| `fetch_memos(repo, branch)` | Returns the full contents of `AGENTS.md` |
| `read_repo_file(repo, branch, path)` | Returns any file in the repo by path |

## Requirements

- Linux host with systemd (tested on Ubuntu 22.04+)
- Python 3.12+, `uv` for environment management
- A stable HTTPS endpoint — see [Exposing the server](#exposing-the-server) below
- GPG installed and the corpus repo's trusted keys imported into the server's keyring

## Quick start

**1. Clone and install**

```bash
git clone https://github.com/your-username/llmemos.git
cd llmemos/mcp-server
uv sync
```

**2. Configure**

```bash
sudo mkdir /etc/gh-mcp
sudo cp deploy/env.example /etc/gh-mcp/env
sudo chmod 600 /etc/gh-mcp/env
sudo $EDITOR /etc/gh-mcp/env   # fill in ALLOWED_REPOS, TRUSTED_KEYS, ALLOWED_HOSTS
```

**3. Create a service user and install**

```bash
sudo useradd -r -s /bin/false gh-mcp
sudo mkdir /opt/gh-mcp
sudo rsync -a . /opt/gh-mcp/
sudo chown -R gh-mcp:gh-mcp /opt/gh-mcp /etc/gh-mcp
cd /opt/gh-mcp && sudo -u gh-mcp uv sync
```

**4. Install and start the systemd service**

```bash
sudo cp deploy/gh-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gh-mcp
sudo systemctl status gh-mcp
```

**5. Verify**

```bash
curl http://localhost:8788/health
# → {"status": "ok", "version": "..."}
```

## Exposing the server

The server listens on `localhost:8788` by default and must be reachable over HTTPS
from Claude.ai (or whichever MCP-capable client you use).

### Plan A — Cloudflare Tunnel (recommended)

Cloudflare Tunnel is the easiest approach: no port-forwarding, no firewall changes,
free persistent subdomain, automatic TLS.

```bash
# Install cloudflared
curl -L https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /etc/apt/keyrings/cloudflare-main.gpg > /dev/null
echo 'deb [signed-by=/etc/apt/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install cloudflared

# Authenticate and create a tunnel
cloudflared tunnel login
cloudflared tunnel create llmemos-mcp

# Create config at ~/.cloudflared/config.yml:
#   tunnel: <tunnel-id>
#   credentials-file: /home/<user>/.cloudflared/<tunnel-id>.json
#   ingress:
#     - hostname: llmemos-mcp.your-domain.example.com
#       service: http://localhost:8788
#     - service: http_status:404

cloudflared tunnel route dns llmemos-mcp llmemos-mcp.your-domain.example.com
cloudflared tunnel run llmemos-mcp
# Or install cloudflared as a systemd service: cloudflared service install
```

Set `ALLOWED_HOSTS=llmemos-mcp.your-domain.example.com` in `/etc/gh-mcp/env`.

### Plan B — nginx + Let's Encrypt

Any reverse proxy with a valid TLS cert works. Example nginx config:

```nginx
server {
    listen 443 ssl;
    server_name llmemos-mcp.your-domain.example.com;
    ssl_certificate     /etc/letsencrypt/live/your-domain.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8788;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Registering with Claude.ai

1. In Claude.ai Settings → Integrations, add a new MCP integration
2. URL: `https://llmemos-mcp.your-domain.example.com/mcp`
3. Copy the contents of `providers/anthropic.claude-ai/llmemos-project-instructions.md`
   into your Claude.ai Project instructions; fill in your corpus repo URL, fingerprints,
   and MCP server hostname

## Running the tests

```bash
cd mcp-server
uv run pytest tests/ -v
```

Signed-commit tests require a GPG key available in your agent (no passphrase prompt):

```bash
TEST_SIGNING_KEY=<your-fingerprint> uv run pytest tests/ -v
```

The GPG agent must have the key unlocked (e.g. YubiKey plugged in, or passphrase cached).
Tests that need signing are skipped automatically if `TEST_SIGNING_KEY` is not set.
They will error if the key is set but the agent requires a passphrase prompt (no TTY).

Integration tests against a real GitHub repo also require `GITHUB_TOKEN` and `TEST_REPO`:

```bash
GITHUB_TOKEN=<token> TEST_REPO=your-username/your-corpus-repo \
TEST_SIGNING_KEY=<fingerprint> uv run pytest tests/ -v
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ALLOWED_REPOS` | Yes | — | Comma-separated `owner/repo` slugs to allow |
| `TRUSTED_KEYS` | Yes | — | Comma-separated GPG fingerprints to trust |
| `ALLOWED_HOSTS` | When behind proxy | — | Comma-separated public hostnames |
| `GITHUB_TOKEN` | For private repos | — | GitHub PAT with `repo` read scope |
| `PORT` | No | `8788` | Listen port |
| `CACHE_DIR` | No | `/tmp/gh-mcp-cache` | Repo cache location |
| `CACHE_TTL` | No | `300` | Seconds before re-pulling cached repos |
