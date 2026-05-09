# Changelog

## v1.2.0 (2026-04-04)

### Added
- Claude.ai path (Path B) fully operational via gh-mcp remote MCP server
- `read_repo_file` MCP tool for reading individual memo files from the corpus
- Per-session memo loading directive via opening message (overrides static default)
- `platform_defaults` section in taxonomy.yml for per-platform default directives

### Changed
- Project renamed from `claude-memos-bootstrapping-protocol` to `llmemos`
- Bootstrap instructions moved to `~/.claude/bootstrap/` (`applyTo: '**'` mechanism)
- Launcher renamed from `claude-memos` to `llmemos`
- Protocol spec renamed from `claude-memos-bootstrapping-protocol.md` to `llmemos-protocol.md`

## v1.0.0 (2026-03-28)

### Added
- Claude Code path (Path A) fully operational: git CLI via Bash tool
- `bin/llmemos` launcher with `--alias`, `--tags`, `--recent`, `--all`, `--memos` flags
- GPG commit signature verification against trusted key list
- `AGENTS.md` memo index format with sticky flags, topics, and digests
- `taxonomy.yml` tag definitions and named alias expansions
- Validation scoring (0–3) for policy, aim consistency, and historical coherence
- Session start log line format
- Mid-session memo loading by id, tag, alias, or name
