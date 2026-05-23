# providers/

Platform-specific bootstrap files for the llmemos protocol, organized by
`company.product` convention.

Each provider directory contains the instruction file(s) needed to activate
the llmemos Bootstrapping Protocol on that platform. All files use placeholder
values — substitute your own corpus repo URL and GPG fingerprints before use.

## Directories

| Directory | Platform | Protocol Path |
|---|---|---|
| `anthropic.claude-code/` | Claude Code (terminal) | Path A — git CLI via Bash tool |
| `anthropic.claude-ai/` | Claude.ai Projects | Path B — gh-mcp remote MCP server |

## anthropic.claude-code

**File:** `llmemos-bootstrap.instructions.md`

Copy to `~/.claude/bootstrap/` (or wherever your Claude Code instructions live).
Edit to set:
- Your corpus repo URL (replace `<your-username>/<your-corpus-repo>`)
- Your GPG key fingerprints (replace the placeholder `AAAA...` / `BBBB...` values)
- Your preferred default loading directive at the bottom of the file

The launcher (`bin/llmemos`) passes this file as the system prompt prefix via
`--bootstrap-file`. See `bin/llmemos --help` for usage.

## anthropic.claude-ai

**File:** `llmemos-project-instructions.md`

Paste the contents into your Claude.ai Project instructions (Settings → Instructions).
Edit to set:
- Your corpus repo URL
- Your GPG key fingerprints
- Your gh-mcp server URL (deploy from `mcp-server/` — see that directory's README)
- Your preferred default loading directive at the bottom of the file

Register your deployed gh-mcp server as an MCP integration in Claude.ai Settings →
Integrations before starting a session.

## Adding a new provider

Create a new directory using the `company.product` naming convention and add the
platform-specific instruction file(s). Update this README and the main `README.md`
layout table.

See `llmemos-protocol.md` for the full protocol specification and the security
requirements each path must satisfy.
