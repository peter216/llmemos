# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-05-26

### Added

- Added cliff.toml for 'keep a changelog' automation

### Changed

- Ability to accept defaults in llmemos-publish script

---

## v1.0.0 (2026-05-25) — llmemos-bootstrapping public release

### Added

- `agent-write-access: pull-request` optional field in `AGENTS.md` frontmatter — when
  set, the agent MAY push a branch and open a PR; user MUST GPG-sign the merge commit;
  the agent MUST NOT push directly to the canonical branch
- Agent-Assisted Lifecycle section in protocol spec documenting the PR-based write path
- Protocol Lineage section in protocol spec documenting derivation from
  `claude-memos-bootstrapping` and backwards compatibility note for existing corpora
- `corpus-template/` — HHGTTG-themed example corpus for new users to fork

### Changed

- Protocol renamed: `claude-memos-bootstrapping` → `llmemos-bootstrapping`; existing
  corpora using `protocol: claude-memos-bootstrapping` remain valid (backwards-compatible)
- Version numbering reset to 1.0.0 as the first public release of the renamed protocol
- All generic "Claude" references in protocol spec replaced with "the agent"; product-
  specific names (Claude Code, Claude.ai) retained where appropriate
- `AGENTS.md` frontmatter example updated to `protocol-version: "1.0.0"`
- `providers/anthropic.claude-code/llmemos-bootstrap.instructions.md`: version → 1.0.0
- `providers/anthropic.claude-ai/llmemos-project-instructions.md`: version → 1.0.0

---

## Prior history (claude-memos-bootstrapping)

The entries below document the evolution of this protocol under its previous name.
Version numbers are preserved as originally assigned.

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
