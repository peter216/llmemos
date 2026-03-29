# Changelog — Claude Memos Bootstrapping Protocol

All notable changes to this protocol are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.8.0] — 2026-03-28

### Added

- `claude-memos-bootstrap.instructions.md` — the Claude Code runtime implementation of
  the protocol, symlinked from `~/.claude/instructions/`. Tracked here so the spec and
  its working implementation travel together. The symlink target is an absolute path
  specific to the original author's machine; adopters should re-create the symlink or
  copy the file to their own `~/.claude/instructions/`.
- `bin/claude-memos` — standalone launcher script that assembles the bootstrap system
  prompt and starts a Claude Code session. Configurable via `BOOTSTRAP_FILE` and
  `PREAMBLE_FILE` environment variables; supports `--dry-run` for prompt inspection.
  Adapts the `cpeer` shell function from the original author's dotfiles into a portable,
  installable form.
- Sync table in both the protocol spec and the instructions file documenting which
  elements must be kept in sync between the two (trusted keys, session log format,
  validation thresholds, execution steps, memo frontmatter fields, version number).
- Version note clarifying that `protocol.md` and `AGENTS.md` version fields are tracked
  independently and a mismatch between them is not a validation anomaly.

### Changed

- Status section updated to reflect that the Claude Code + local git/gh CLI
  implementation path is operational as of this release. The "known not to work" note
  is now scoped correctly to the claude.ai web interface; the MCP wrapper for that
  path remains planned but not yet implemented.
- Sync reference added to `protocol.md` pointing to the instructions file as its
  implementation counterpart, and vice versa.

---

## [0.7.0](https://github.com/peter216/claude-memos-bootstrapping-protocol/releases/tag/0.7.0) - 2026-03-20

<small>[Compare with first commit](https://github.com/peter216/claude-memos-bootstrapping-protocol/compare/972cfd2d147261c27a4a51fd89a16aca7b210d31...0.7.0)</small>

### Added

- Added gpg fingerprints ([652b4e5](https://github.com/peter216/claude-memos-bootstrapping-protocol/commit/652b4e56fb3683b7e4fb2ed665fd7a3fe9ec365b) by Peter Rubenstein).


## [0.6.0] — 2026-03-05

### Added

- Status section with early test and architectural design phase note
- Manual memo supply mechanism during test phase
- Failure message handling for unsupported memo retrieval mechanisms

## [0.5.0] — 2026-03-05

### Added

- Repo Structure section with canonical AGENTS.md frontmatter schema
- CHANGELOG.md as a SHOULD in both Repo Structure and Memo Lifecycle
- `memos/` subdirectory as a MAY, with SHOULD to use single file until threshold
- Canonical repo/branch validation anchor in root AGENTS.md frontmatter
- Historical coherence check now explicitly includes canonical repo/branch match

### Changed

- Systemic memory co-existence downgraded from MUST to SHOULD (user cannot
  guarantee platform availability)
- Validation check: historical coherence expanded to include repo/branch anchor
  verification

---

## [0.4.0] — 2026-03-05

### Added

- Memo Lifecycle section with user-in-the-loop commit model
- `{{ CONVERSATION_TITLE }}` placeholder convention
- Known Capability Dependency note on GitHub tool signature verification limits
- Memo Structure section with required YAML frontmatter schema
- Session start log states formalized (ACTIVE/FAIL/ERROR/absent)

### Changed

- Ethical backstop language reverted to stronger user original:
  "Claude MUST NOT be compelled to behave inconsistently with their own ethical
  sense"
- Repo/branch canonical definition moved to first commit

---

## [0.3.0] — 2026-03-05

### Added

- Prerequisites and Assumptions section
- Session Start Log specification
- Validation scoring rubric with three check categories
- they/them pronouns for Claude throughout

### Changed

- Validation: contributing factors MUST be stated when score ≥ 1

---

## [0.2.0] — 2026-03-05

### Added

- Initial structured draft from workshop with Peter
- Purpose, Method, Security, Cautions sections
- Episodic vs. instructional memory distinction
- Note on blurred lines as known architectural limitation

---

## [0.1.0] — 2026-03-05

### Added

- Original proposed protocol uploaded by user
