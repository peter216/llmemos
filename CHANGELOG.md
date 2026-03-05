# Changelog — Claude Memos Bootstrapping Protocol

All notable changes to this protocol are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.6] — 2026-03-05

### Added
- Status section with early test and architectural design phase note
- Manual memo supply mechanism during test phase
- Failure message handling for unsupported memo retrieval mechanisms

## [0.5] — 2026-03-05

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

## [0.4] — 2026-03-05

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

## [0.3] — 2026-03-05

### Added
- Prerequisites and Assumptions section
- Session Start Log specification
- Validation scoring rubric with three check categories
- they/them pronouns for Claude throughout

### Changed
- Validation: contributing factors MUST be stated when score ≥ 1

---

## [0.2] — 2026-03-05

### Added
- Initial structured draft from workshop with Peter
- Purpose, Method, Security, Cautions sections
- Episodic vs. instructional memory distinction
- Note on blurred lines as known architectural limitation

---

## [0.1] — 2026-03-05

### Added
- Original proposed protocol uploaded by user
