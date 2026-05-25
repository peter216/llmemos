# llmemos — Release Implementation Plan

**Branch:** `WIP` → target merge to `main` when all phases complete
**Target release:** v1.0.0
**Status:** Phases 0–5 complete. Phase 6 remaining.

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
commit history for changelog accuracy. Tag `v1.0.0` immediately after merge.

**Commits on WIP are unsigned** (GPG signing requires a TTY; Claude Code runs without
one). Before merging to main, amend or re-sign the WIP commits, or accept them as-is
and sign the merge commit itself.

---

## Phase 0 — Decisions (resolve before writing any code)

- [x] **Gemini Path C: document but don't ship in v1.x.** Path C (Google Drive sync via
  GitHub Action) is a valid approach for Gemini Web, which lacks arbitrary MCP support.
  Document it in the protocol spec as an advanced/platform-specific path. Do not
  implement it in this repo for v1.0 — it requires per-user CI/CD setup that's too
  heavy for an initial release.

- [x] **gh-mcp: merge into `mcp-server/` subdirectory.** Per memo-022 decision, the
  monorepo approach. gh-mcp source lives at `~/git/claude-project/gh-mcp/`. The private
  The private deployment repo stays as the deployment record.
  *Note: `docs/` from gh-mcp was discarded — too many personal server references
  (personal server hostnames and host details) too deeply embedded to be worth cleaning.
  The MCP implementation lessons are captured in memo-010 instead.*

- [x] **Corpus template: in this repo as `corpus-template/`.** Keep it simple — the
  HHGTTG-themed example corpus from memo-022 planning. Separate GitHub template repo
  can come later; for now a subdirectory is sufficient.

- [x] **Providers directory: yes, create it.** Structure:
  `providers/anthropic.claude-code/` and `providers/anthropic.claude-ai/`. The
  bootstrap instructions file moves here with placeholder content.

- [x] **Env file convention: `.env.example` / `.envrc.example` (committed templates).**
  `.gitignore` uses specific entries `.env` and `.envrc` (not the glob `.env*`) so that
  example files are tracked. gopass path patterns are documented as comments in the
  example file; no real secrets are committed anywhere.

- [x] **Deploy target: generic Linux + Cloudflare Tunnel as Plan A.** No Oracle or
  Cloudflare hard dependency. Service file uses `/opt/gh-mcp` and a dedicated `gh-mcp`
  system user. Cloudflare Tunnel is recommended as Plan A (free, persistent, no
  port-forwarding) with nginx as Plan B. Oracle Free Tier mentioned as a no-cost host
  option in the README, not a requirement.

---

## Phase 1 — Protocol Spec Cleanup ✅

- [x] **Merge `llmemos-protocol.md` + `llmemos-protocol.cand.md` → single file.**
  - Path C added as "advanced / platform-specific, not implemented in v1.x"
  - Chain of Provenance security model incorporated under Security section
  - All fingerprints remain as placeholders
  - `llmemos-protocol.cand.md` deleted

- [x] **Fix protocol spec: AGENTS.md frontmatter example.**
  Updated `protocol-version: "1.2.0"` → `"1.3.0"`.

- [x] **Fix protocol spec: Session Resume Path A.**
  Corrected stale script name `claude-memos` → `llmemos`.

- [x] **Update CHANGELOG.md with v1.3.0 entry (now v1.0.0).**
  *Note: `corpus-template/` entry is included in the changelog but the directory itself
  lands in Phase 4. That's fine — the changelog documents the release as a whole.*

- [x] **Update `.gitignore`:** `.env*` glob → specific `.env` and `.envrc` entries.

- [x] **Add `IMPLEMENTATION.md`** (this file).

---

## Phase 2 — Providers Directory ✅

- [x] **Create `providers/anthropic.claude-code/llmemos-bootstrap.instructions.md`.**
  Sourced from Peter's chezmoi copy; all real fingerprints, personal repo URL, and
  personal name references stripped. Default loading directive set to `--sticky`
  (not Peter's personal `--tags claude-code`) so new users get a safe, minimal default.
  Tmp dir changed from `/tmp/claude-memos-session` → `/tmp/llmemos-session`.

- [x] **Create `providers/anthropic.claude-ai/llmemos-project-instructions.md`.**
  Moved from root (git detected as 83% rename). "Peter" → "the user" throughout.
  Protocol version bumped to 1.3.0. Default directive set to `--sticky`.

- [x] **Add `providers/README.md`.** Explains the `company.product` convention and
  per-provider setup steps.

- [x] **Update `README.md`** — layout diagram and install steps updated to reflect new
  providers/ paths; provider instructions no longer say "coming soon".

---

## Phase 3 — MCP Server Merge ✅

- [x] **Create `mcp-server/` and copy gh-mcp source.**
  Files included: `src/`, `tests/` (excluding logs/), `pyproject.toml`, `uv.lock`,
  `deploy/`, `.gitignore`, `README.md`.
  Files excluded: `docs/` (personal refs), `logs/`, `__pycache__`, `.egg-info`.

- [x] **Review deploy/ and docs/ for personal references before committing.**
  `deploy/env.example`: ALLOWED_REPOS, TRUSTED_KEYS, ALLOWED_HOSTS all genericized;
  gopass usage pattern documented in comments.
  `deploy/gh-mcp.service`: paths changed to `/opt/gh-mcp`; dedicated `gh-mcp` system user.
  `docs/` discarded entirely (see Phase 0 note).

- [x] **Add `mcp-server/README.md`.** Cloudflare Tunnel as Plan A, nginx as Plan B;
  env var reference table; test instructions with GPG agent note.

- [x] **Run the test suite against the merged copy.**
  *Findings:*
  - 34 non-signing tests pass cleanly.
  - 14 signing tests require `TEST_SIGNING_KEY` env var + GPG agent unlocked (no TTY
    prompt). They skip automatically when `TEST_SIGNING_KEY` is unset.
  - `@pytest.mark.skipif` on fixtures is removed in pytest 9 — replaced with
    `_require_signing_key()` helper called at the top of each signing fixture.
  - The signing tests cannot run from within Claude Code (no TTY for pinentry).
    They pass in a normal terminal with the GPG agent unlocked.

- [x] **Side effect: fix `~/.gitleaks.toml` (chezmoi) for subdirectory `.venv/`.**
  The pre-commit gitleaks hook scans the full working directory. `^\\.venv/` only
  matched at the repo root; `mcp-server/.venv/` (created by `uv sync`) triggered false
  positives from test key material in the `cryptography` and `jwt` packages.
  Fixed pattern: `^(.*/)?\\.venv/`. Applied via chezmoi → will propagate to all
  project dirs on next pre-commit run.

---

## Phase 4 — Corpus Template

- [x] **Create `corpus-template/` with the HHGTTG-themed example corpus.**
  Minimum required files:
  - `AGENTS.md` — protocol frontmatter, example memo index with Zaphod/Arthur/Ford entries
  - `taxonomy.yml` — HHGTTG-themed tags and aliases:
    `dont_panic`, `hitchhiking`, `vogons`, `babel_fish`, `heart_of_gold`, `mice`, etc.
  - `memos/` — 2-3 example memo files showing realistic frontmatter and content format

- [x] **Add `corpus-template/README.md`.** Explains: fork/use this template, replace
  example memos with real ones, set up GPG signing, configure your bootstrap file.

---

## Phase 5 — README and Docs Cleanup

- [x] **Update `README.md` layout diagram and "coming soon" references.**
  Remaining items:
  - `mcp-server/` comment still says "(coming soon)" — update to reflect it's real
  - `corpus-template/` comment says "(coming soon)" — update after Phase 4 lands
  - "Full install script coming soon" — rewrite as honest "manual steps for now" or add
    a minimal install script

- [x] **Verify README layout matches actual `git ls-files` output.**

- [x] **`docs/` directory** — decided not to carry over the gh-mcp implementation doc
  (too personal). No action needed unless something else surfaces.

---

## Phase 6 — Final Checks and Release

- [x] **Scan for personal references.**
  ```bash
  grep -r "peter216\|martiangoblin\|peter\.rubenstein\|@gmail\.com\|63611E76\|757BECAF\|7E4BE13E\|0A7C57B8" . \
    --include="*.md" --include="*.py" --include="*.yml" --include="*.sh" \
    -l
  ```
  Resolve each hit.
  *Remaining hits are expected: `IMPLEMENTATION.md:178` is the grep command itself;
  `corpus-template/AGENTS.md:11` is a back-link to the public project repo.*

- [x] **Run gitleaks check.**
  ```bash
  gitleaks detect --source=. -v
  ```

  *Result: no leaks found (36 commits scanned).*

- [ ] **Confirm `bin/llmemos` runs cleanly with `--dry-run`.**
  ```bash
  ./bin/llmemos --dry-run --tags claude-code
  ```

- [ ] **Sign or amend the WIP commits before merge.**
  All WIP commits are currently unsigned (Claude Code has no TTY for GPG pinentry).
  Options: `git rebase -S` to re-sign all commits, or accept unsigned WIP history and
  sign the merge commit itself. The merge commit landing on `main` is what matters for
  the protocol's own integrity demonstration.

- [ ] **Merge `WIP` → `main`.** No squash.
  ```bash
  git checkout main && git merge WIP --no-ff -m "chore: release v1.0.0"
  ```

- [ ] **Tag `v1.0.0`.**
  ```bash
  git tag -s v1.0.0 -m "llmemos v1.0.0"
  git push origin main --tags
  ```

---

## Deferred (not blocking v1.0.0)

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
