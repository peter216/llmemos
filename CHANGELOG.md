# Changelog

## v1.3.0 (2026-05-22)

### Added
- Path C (Google Gemini Web / Google Workspace) documented in protocol spec as an advanced
  platform-specific path using the Chain of Provenance security model; not implemented in
  this repository for v1.x
- `platform_defaults` section in `taxonomy.yml` for per-platform default loading directives,
  using the `company.product` naming convention (`anthropic.claude-code`, `anthropic.claude-ai`,
  `google.gemini`)
- Directive usage logging in `bin/llmemos` — appends to `~/.llmemos/directive-usage.log`
  on non-default directives; supports `uuidgen`-based invocation tracking
- `bin/llmemos_logger.py` — colored logging with NOTICE (25) and SUCCESS (35) levels;
  falls back to stdlib logging if `coloredlogs` is not installed
- `providers/` directory structure using `company.product` convention for
  platform-specific bootstrap files
- `mcp-server/` — gh-mcp source merged in (Python/FastMCP server for Path B)
- `corpus-template/` — starter corpus for new users
- `.env.example` and `.envrc.example` template files for environment configuration

### Changed
- Protocol spec updated: Path C documented, Chain of Provenance security model added,
  Known Capability Dependency updated to reference all three paths
- `AGENTS.md` frontmatter example updated to `protocol-version: "1.3.0"`
- Session Resume Path A: corrected script name from `claude-memos` to `llmemos`
- `.gitignore`: replaced `.env*` glob with specific `.env` and `.envrc` entries so that
  `.env.example` and `.envrc.example` are correctly tracked

### Removed
- `llmemos-protocol.cand.md` — candidate draft merged into `llmemos-protocol.md`

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
