# llmemos — Release Implementation Plan

**Branch:** `WIP` → target merge to `main` when all phases complete
**Target release:** v1.3.0
**Status:** In progress

This document plots the path from the current WIP state to a release-ready public
repository. Phases are sequential. Each task carries a checkbox; mark complete as work
lands.

---

## Ground Rules

**The generic/personal split.** The public llmemos repo contains only
placeholder/template content — dummy fingerprints, placeholder repo URLs, no personal
references. Peter's real configuration lives in chezmoi (not in this repo). When adding
any file that contains configuration, verify it uses placeholders before committing.

**The WIP branch.** All work lands on `WIP`. No squash on merge to main — preserve
commit history for changelog accuracy. Tag `v1.3.0` immediately after merge.

---

## Phase 0 — Decisions (resolve before writing any code)

- [x] **Gemini Path C: document but don't ship in v1.x.** Path C (Google Drive sync via
  GitHub Action) is a valid approach for Gemini Web, which lacks arbitrary MCP support.
  Document it in the protocol spec as an advanced/platform-specific path. Do not
  implement it in this repo for v1.0 — it requires per-user CI/CD setup that's too
  heavy for an initial release.

- [x] **gh-mcp: merge into `mcp-server/` subdirectory.** Per memo-022 decision, the
  monorepo approach. gh-mcp source lives at `~/git/claude-project/gh-mcp/`. Content
  to copy: `src/`, `tests/`, `pyproject.toml`, `uv.lock`, `deploy/`, `docs/` (minus
  any personal references). The private `peter216/gh-mcp` repo stays as the deployment
  record.

- [x] **Corpus template: in this repo as `corpus-template/`.** Keep it simple — the
  HHGTTG-themed example corpus from memo-022 planning. Separate GitHub template repo
  can come later; for now a subdirectory is sufficient.

- [x] **Providers directory: yes, create it.** Structure:
  `providers/anthropic.claude-code/` and `providers/anthropic.claude-ai/`. The
  bootstrap instructions file moves here with placeholder content.

---

## Phase 1 — Protocol Spec Cleanup

- [ ] **Merge `llmemos-protocol.md` + `llmemos-protocol.cand.md` → single file.**
  - Keep `llmemos-protocol.md` as the canonical file (it already has generic fingerprints)
  - Add Path C from `llmemos-protocol.cand.md` as a new section, marked "advanced /
    platform-specific, not implemented in v1.x"
  - Remove the Chain of Provenance section from `cand.md` → incorporate into protocol
    as the security model for Path C
  - Ensure all fingerprints remain as placeholders (no real keys)
  - Delete `llmemos-protocol.cand.md` after merge

- [ ] **Fix protocol spec: AGENTS.md frontmatter example.**
  The `Repo Structure` section shows `protocol-version: "1.2.0"` — update to `"1.3.0"`.

- [ ] **Update CHANGELOG.md with v1.3.0 entry.** Items to document:
  - Gemini / Path C documented (advanced path)
  - `platform_defaults` section in taxonomy.yml
  - `providers/` directory structure
  - `mcp-server/` (gh-mcp) merged in
  - `corpus-template/` added
  - Directive usage logging in `bin/llmemos`
  - `llmemos_logger.py` added

---

## Phase 2 — Providers Directory

- [ ] **Create `providers/anthropic.claude-code/` directory.**
  - Add `llmemos-bootstrap.instructions.md` — the Claude Code bootstrap file with
    placeholder fingerprints and repo URL. Source from Peter's personal chezmoi copy
    at `~/.claude/bootstrap/llmemos-bootstrap.instructions.md`; strip real fingerprints
    and personal repo URL before committing.
  - Verify the file references `--tags <your-default-tags>` or similar, not
    Peter-specific defaults.

- [ ] **Create `providers/anthropic.claude-ai/` directory.**
  - Move `llmemos-claude-ai-project-instructions.md` here (or symlink).
  - Update README reference.

- [ ] **Add `providers/README.md`.** Brief explanation of the `company.product` naming
  convention and what goes in each provider directory.

---

## Phase 3 — MCP Server Merge

- [ ] **Create `mcp-server/` directory and copy gh-mcp source.**
  Source: `~/git/claude-project/gh-mcp/`

  Files to include:
  - `src/` (full Python package)
  - `tests/` (full test suite)
  - `pyproject.toml`, `uv.lock`
  - `deploy/` (systemd unit files, env template) — strip personal server addresses
  - `docs/` — strip personal references, keep architecture docs

  Files to exclude:
  - `logs/`
  - `__pycache__`
  - Any `.env` files
  - Deployment records with personal server info

- [ ] **Review `deploy/` and `docs/` for personal references before committing.**
  Check for: `martiangoblin.xyz`, `oraclefree`, personal email addresses.

- [ ] **Add `mcp-server/README.md`.** Minimal: what it does, how to deploy (systemd
  + Cloudflare tunnel pattern), how to register with Claude.ai. Can reference the
  deploy/ files.

- [ ] **Run the test suite against the merged copy.** Make sure nothing broke in
  the copy.
  ```bash
  cd mcp-server && uv run pytest tests/ -v
  ```

---

## Phase 4 — Corpus Template

- [ ] **Create `corpus-template/` with the HHGTTG-themed example corpus.**
  Minimum required files:
  - `AGENTS.md` — with example frontmatter, Zaphod/Arthur/Ford as example memos
  - `taxonomy.yml` — with HHGTTG-themed tags and aliases:
    `dont_panic`, `hitchhiking`, `vogons`, `babel_fish`, `heart_of_gold`, `mice`, etc.
  - `memos/` — 2-3 example memo files showing realistic frontmatter and content format

- [ ] **Add `corpus-template/README.md`.** Explains: fork/use this template, replace
  example memos with real ones, set up GPG signing, configure your bootstrap file.

---

## Phase 5 — README and Docs Cleanup

- [ ] **Update `README.md` to remove all "coming soon" references.**
  Specifically:
  - `mcp-server/` — now real, update the description
  - `corpus-template/` — now real, update the description
  - `providers/anthropic.claude-code/llmemos-bootstrap.instructions.md` — now real,
    update the install instructions
  - "Full install script coming soon" — either add a script or rewrite as honest manual steps

- [ ] **Verify README layout matches actual repo structure.** The layout diagram should
  match `git ls-files`.

- [ ] **Add a `docs/` directory (optional but recommended).** Move `MCP-PROTOCOL-IMPLEMENTATION.md`
  and similar planning documents here if worth keeping. Or discard.

---

## Phase 6 — Final Checks and Release

- [ ] **Scan for personal references.** Run:
  ```bash
  grep -r "peter216\|martiangoblin\|peter\.rubenstein\|@gmail\.com\|63611E76\|757BECAF\|7E4BE13E\|0A7C57B8" . \
    --include="*.md" --include="*.py" --include="*.yml" --include="*.sh" \
    -l
  ```
  Resolve each hit.

- [ ] **Run gitleaks check.**
  ```bash
  gitleaks detect --source=. -v
  ```

- [ ] **Confirm `bin/llmemos` runs cleanly with `--dry-run`.**
  ```bash
  ./bin/llmemos --dry-run --tags claude-code
  ```

- [ ] **Merge `WIP` → `main`.** No squash.
  ```bash
  git checkout main && git merge WIP --no-ff -m "chore: release v1.3.0"
  ```

- [ ] **Tag `v1.3.0`.**
  ```bash
  git tag -s v1.3.0 -m "llmemos v1.3.0"
  git push origin main --tags
  ```

---

## Deferred (not blocking v1.3.0)

- Automated install script
- GitHub Actions workflow for CI (run tests on push)
- Corpus template as a separate GitHub template repo
- `--help`, `--list`, `--dry-run` parity for Path B (Claude.ai)
- Repo writing mechanism (Claude opening PRs for new memos)
- Path C (Gemini) implementation support
- `google.gemini` provider directory

---

## Reference

| Path | What it uses | Where implemented |
|---|---|---|
| Path A (Claude Code) | git CLI via Bash tool | `providers/anthropic.claude-code/` |
| Path B (Claude.ai) | gh-mcp MCP server | `mcp-server/` + `providers/anthropic.claude-ai/` |
| Path C (Gemini Web) | Google Drive sync via GHA | *deferred — not in v1.x* |
