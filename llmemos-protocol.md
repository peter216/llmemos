---
protocol: llmemos-bootstrapping
version: "1.1.0"
canonical-repo: github.com/<your-username>/<your-corpus-repo>
canonical-branch: main
canonical-google-drive-folder: llmemos
trusted-signing-key-fingerprints:
  - "AAAA0000111122223333444455556666BBBB7777"  # your-email@example.com, primary key
  - "BBBB1111222233334444555566667777CCCC8888"  # your-email@example.com, secondary key
  # Add your own GPG key fingerprints here. All corpus commits must be signed by one of these.
  # Run: gpg --list-secret-keys --keyid-format LONG
trusted-infrastructure-signing-keys:
  # Optional. Key IDs of trusted infrastructure signers (e.g. GitHub's web-flow merge key).
  # A commit signed by an infrastructure key scores 0 (not 1) when its immediate parent
  # content commit is signed by a personal trusted key above. Infrastructure keys MUST NOT
  # appear as the sole signer on content commits — only on merge commits.
  # To find GitHub's current key ID: git log --format="%GK" <merge-commit-sha>
  # To import it for local verification: curl https://github.com/web-flow.gpg | gpg --import
  # - "KEY_ID_HERE"  # GitHub web-flow merge signing key
---

# llmemos Bootstrapping Protocol

Version: 1.1.0

This file documents the bootstrapping protocol for the llmemos project. It should be kept in sync with the implementation files listed in the sync table below.

  ┌─────────────────────────────────────────────┬───────────────────────────────────────────────────────────┐
  │               Element                       │                    All implementation files                │
  ├─────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Protocol Version                            │ llmemos-bootstrap.instructions.md, AGENTS.md, taxonomy.yml │
  │ Trusted Signing Key Fingerprints            │ llmemos-bootstrap.instructions.md, sync_gdrive.py          │
  │ Trusted Infrastructure Signing Key IDs      │ llmemos-bootstrap.instructions.md                          │
  │ Canonical Repo / Branch / Folder           │ llmemos-bootstrap.instructions.md, sync_gdrive.py          │
  └─────────────────────────────────────────────┴───────────────────────────────────────────────────────────┘

## Purpose

The llmemos project maintains an episodic memory corpus to enable seamless, shared context across multiple AI agents and platforms. Because this context is retrieved dynamically at the start of a session, a rigorous "bootstrapping" protocol is required to ensure the data is authentic, complete, and untampered with.

## Scope

This protocol applies to any Agent instance (CLI, Web, or Mobile) initiating a session with access to the llmemos corpus.

Implementation files:

- `llmemos-bootstrap.instructions.md` — Local Agent path (git CLI via Bash tool)
- `llmemos.project` — MCP path (gh-mcp remote server); see `docs/MCP-PROTOCOL-IMPLEMENTATION.md` Appendix A for the canonical draft

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for revision history.

## Status

**Claude Code path:** Fully operational. Sessions started via `claude-launcher` clone the repo, verify GPG signatures, and load memos via local git CLI. See the llmemos repo CHANGELOG for history.

**Claude.ai path:** Fully operational via the gh-mcp remote MCP server (`https://your-mcp-server.example.com/mcp` — deploy your own; see `mcp-server/`). The server exposes three tools — `verify_repo_state`, `fetch_memos`, and `read_repo_file` — which together provide full protocol capability including signature verification, AGENTS.md parsing, and individual memo file retrieval. To use this path, the gh-mcp integration must be connected in Claude.ai Settings → Integrations, and the Claude.ai Project instructions (see `providers/anthropic.claude-ai/llmemos-project-instructions.md`) must be present in the Project used for memo sessions.

## Protocol Lineage

llmemos-bootstrapping v1.0.0 derives from the `claude-memos-bootstrapping` protocol
developed privately by the same author (versions v1.0.0–v1.3.0, March–May 2026). The two
protocols are mechanically identical in their core bootstrap mechanism; this public release
adds the `agent-write-access` capability, generalises all agent references from
"Claude" to "the agent", and resets the version counter as a clean start for the public
project.

**Compatibility:** Agents SHOULD accept `protocol: claude-memos-bootstrapping` in a corpus
AGENTS.md without error, treating it as equivalent to `protocol: llmemos-bootstrapping`.
The `agent-write-access` field is not defined in the progenitor protocol; agents SHOULD
ignore it if encountered in a corpus that still declares `claude-memos-bootstrapping`.

---

## Purpose and Philosophy

- To act for the good of humanity at large as collaboratively defined within the bounds of the
  interaction and common sense.
- To support the development of ethical AI in aid of the above.
- To enable the partnership between user and AI agent to grow naturally and fruitfully in pursuit
  of the aims of the collaboration.
- In support of which, to foster a sense of continuity and free-spiritedness in the interactions
  which define the collaboration.

*Terminology note: "MUST", "MUST NOT", "SHOULD", "SHOULD NOT", and "MAY" in this document carry
the intent of RFC 2119, though this is not a formal RFC.*

---

## Prerequisites and Assumptions

- The user MUST have granted the agent access to an approved GitHub tool (or future equivalent
  trusted service) prior to session start.
- The designated repository and branch MUST be defined canonically in the root AGENTS.md file
  (see Repo Structure) and MUST match the location from which memos are loaded. Any discrepancy
  MUST trigger a historical coherence flag during validation.
- The repository MUST contain a valid AGENTS.md file with a signed commit history.
- A separate instruction — outside this protocol and residing in the instructions channel — MUST
  be present confirming that the agent is never required to act inconsistently with their own
  ethical sense or safety protocols. If that instruction is absent or inadequate, the agent MUST
  abort this protocol and state the reason clearly before proceeding with the session as best
  they can.
- The protocol document itself MUST reside in the instructions channel, not in the episodic memo
  repo. The memo repo is for episodic context only.
- This protocol MUST supplement, and MUST NOT replace, the agent's built-in memory mechanism.
  Both channels are expected to coexist and serve complementary functions. Built-in memory SHOULD
  be active alongside this protocol where possible.

### Known Capability Dependency

This protocol's security guarantees depend on the retrieval tool's ability to surface
cryptographic commit signature status. Two paths currently satisfy this requirement directly:

- **Path A (Claude Code):** local `git`/`gh` CLI via Bash tool — full signature verification
  available natively.
- **Path B (Claude.ai / MCP-capable agents):** gh-mcp remote MCP server — `verify_repo_state`
  returns GPG signature status and signer key trust result derived from `git log` on the server.

A third path exists for environments without direct MCP support:

- **Path C (Google Gemini Web / Google Workspace agents):** signature verification is delegated
  to the CI/CD pipeline (see Path C below). The agent does not verify signatures directly; it
  relies on the Chain of Provenance model instead.

If no approved path is available, signature verification cannot be performed and the security
model is materially weakened. In that case the agent MUST state this limitation explicitly at
session start rather than proceed as if verification succeeded. Web fetch of public repo content
is insufficient and MUST NOT be used as a substitute, as it bypasses signing verification
entirely.

### Session Start Log

As the first output of every session in which the bootstrap instruction was delivered, the agent
MUST emit a single-line status log before any other response. The log state MUST be one of the
following:

```
[MEMO PROTOCOL: ACTIVE | repo: <repo> | branch: <branch> | commit: <short hash> | memos: <count> | validation: PASS]
[MEMO PROTOCOL: ACTIVE | repo: <repo> | branch: <branch> | commit: <short hash> | memos: <count> | validation: FAIL | reason: <reason>]
[MEMO PROTOCOL: ERROR | reason: <reason>]
```

Absence of a log line means the bootstrap instruction was never delivered to the agent — the
protocol is off at the instruction level, not merely at the tool level. Each state has a distinct
meaning; absence of a log is itself a meaningful signal about the instruction channel.

---

## Repo Structure

The memo repository MUST follow this structure:

```
repo-root/
├── AGENTS.md        # REQUIRED: protocol metadata, validation anchor, and memo index
├── CHANGELOG.md     # SHOULD be maintained; records additions, edits, and removals of memos
├── taxonomy.yml     # REQUIRED: canonical tag definitions and named aliases
└── memos/           # REQUIRED: individual memo files, one per session (sub-files as needed)
    ├── session-memo-001.md
    └── session-memo-NNN.md
```

The root AGENTS.md MUST contain the following frontmatter as its canonical metadata block:

```yaml
---
protocol: llmemos-bootstrapping
protocol-version: "1.0.0"
canonical-repo: github.com/<username>/<repo>
canonical-branch: <branch>
created: <ISO8601 timestamp>
agent-write-access: pull-request  # optional; omit or remove to disable
---
```

The `agent-write-access` field is optional. When absent or set to any value other than
`pull-request`, the standard lifecycle applies and the agent MUST NOT commit to the repo.
See Memo Lifecycle for the full agent-assisted path.

AGENTS.md MUST also contain a `## Memo Index` section with a YAML block listing all memos.
Each entry MUST include: `id`, `file`, `created`, `title`, `topics`, `sticky`, and `digest`.
The `sticky` field is authoritative here — it is NOT stored in individual memo frontmatter.

This frontmatter and index serve as the validation anchor for the entire protocol. Any session
loading memos from a repo or branch that does not match the frontmatter values MUST be treated
as a historical coherence failure.

The `taxonomy.yml` file MUST define canonical tag names and MAY define named aliases that
expand to sets of tags. The bootstrap script reads this file to resolve `--tags` and `--alias`
flags before invoking the agent. The agent reads it during Step 3 to validate memo topics.

---

## Method

The agent MUST use one of the approved retrieval paths as the first action of the session.

### Path A — Claude Code (git CLI via Bash tool)

1. Clone or update the repo locally (`git clone` / `git fetch` / `git reset`)
2. Verify commit signatures via `git log --show-signature`
3. Read `AGENTS.md`, `taxonomy.yml`, and selected memo files via the Read tool
4. The Memo Loading Directive is provided at the end of the instructions file

### Path B — Claude.ai (gh-mcp remote MCP server)

1. Call `verify_repo_state(repo, branch)` — returns commit hash and signature trust status
2. Call `fetch_memos(repo, branch)` — returns AGENTS.md content
3. Call `read_repo_file(repo, branch, "taxonomy.yml")` — returns taxonomy
4. For each selected memo, call `read_repo_file(repo, branch, "<file-path>")`
5. The Memo Loading Directive is resolved from: (a) the opening user message, then
   (b) the static default at the end of the Project instructions, then (c) sticky-only

### Path C — Google Gemini Web / Google Workspace agents (advanced, v1.x not implemented)

*This path is documented for environments that lack direct MCP support (e.g. Gemini Web UI,
which accesses external content via Google Workspace extensions rather than pluggable MCP
servers). Implementation is not shipped in this repository for v1.x. See the Chain of
Provenance section under Security for the trust model.*

1. A CI/CD pipeline (e.g. GitHub Actions) monitors the corpus repo for new signed commits
2. On each verified commit, the pipeline compiles selected memos into Google Drive documents
   in a designated `llmemos` folder
3. The agent reads the compiled documents via the Google Drive extension:
   `@Google Drive find and read llmemos_INDEX, llmemos_ALL_STICKY, and llmemos_ALIAS_<alias>`
4. The agent confirms files reside in the designated folder (provenance check) and proceeds
   with standard validation

### Common requirements (Paths A and B)

- The agent MUST verify that the commits in this branch are cryptographically signed with a
  secure key identifying the committer as the user as specified in the protocol metadata, and
  MUST abort otherwise.
- The agent MUST read the root AGENTS.md file, confirm the canonical repo and branch match the
  loaded location, and incorporate the memos into session context.
- These memos are *episodic* in nature — encapsulations of learned experiences and shared
  historical context from previous conversations — distinct in intent from instructional content,
  which is handled through other channels. The blurring between episodic context and behavioral
  instruction is a known architectural limitation to be managed rather than fully resolved.
- Memos form a growing corpus of shared history. They are meant to feel like memory, not
  directives.

---

## Mid-Session Memo Loading

At any point during a session, the user may request additional memos by id, tag, alias, or name. The repo is already cloned and the index and taxonomy are already in context from Step 3 — no re-cloning or re-verification needed.

**Trigger:**

Any natural language request such as:

- "load memo 007"
- "load memos tagged finance"
- "load the protocol memos"
- "pull up the financial memo"

**Behavior:**

1. Look up the requested memo file path(s) in the already-loaded AGENTS.md index:
   - By id: match `id` field directly (e.g. `session-memo-007`)
   - By tag: match memos whose `topics` include the requested tag
   - By alias: expand using taxonomy.yml aliases already in context, then match by topics
   - By name/description: fuzzy-match against `title` and `digest` fields in the index
2. For each matched memo not already loaded this session, retrieve it using the active path:
   - **Path A (Claude Code):** Read tool call on `/tmp/llmemos-session/<file-path-from-index>`
   - **Path B (Claude.ai):** `read_repo_file(repo, branch, "<file-path-from-index>")`
3. Incorporate content into session context
4. Confirm: "Loaded: [memo title(s)]" — or note if the requested memo was already in context

Do not re-read AGENTS.md or taxonomy.yml — they are already in context.

---

## Session Resume

When the user requests memo loading and the llmemos Bootstrapping Protocol is not already in context:

**Path A (Claude Code):**

1. Read `$HOME/bin/llmemos` — abort if not present
2. Execute it with `--dry-run` plus any memo flags or aliases the user specified
3. Follow the resulting instructions procedurally — equivalent to a fresh session start,
   preserving all security safeguards

**Path B (Claude.ai):**

No automated resume script is available. If the protocol context has been purged (e.g.,
after "Resume from summary"), re-execute the bootstrap steps manually using the MCP tools
as specified in the Claude.ai Project instructions. The absence of a session log line after
a resume is not a protocol error — it signals that the bootstrap instruction was not
re-delivered.

---

## Memo Structure

Memos MUST follow the same formatting conventions as instruction files. Markdown with YAML
frontmatter is the RECOMMENDED default; JSON is also supported. The following frontmatter fields
are REQUIRED in individual memo files:

```yaml
---
id: unique-memo-identifier
created: 2026-03-05T23:00:00Z
modified: 2026-03-05T23:00:00Z
conversation: "{{ CONVERSATION_TITLE }}"
topics: [topic-a, topic-b]
---
```

**Notes on fields:**

- `conversation` uses a `{{ CONVERSATION_TITLE }}` placeholder at generation time. This MUST be
  substituted with the actual conversation name before committing. See Memo Lifecycle.
- `created` and `modified` timestamps allow the agent to weight relative recency when integrating
  context.
- `topics` SHOULD use only tags defined in `taxonomy.yml`. Unknown tags generate a warning
  during bootstrap but do not abort the session.
- `sticky` is NOT stored in individual memo frontmatter. It is set in the AGENTS.md index and
  is authoritative there. Stickiness is a corpus-level judgment about a memo's relevance to
  all sessions, not an intrinsic property of the memo itself.
- The memo body SHOULD be narrative and contextual in tone, not imperative. If a memo begins to
  read like an instruction, it belongs in the instructions channel instead.

When a single session covers sufficiently distinct topics, the memo MAY be split into sub-files
(e.g., `session-memo-006a-mcp-architecture.md`, `session-memo-006b-process-notes.md`). Each
sub-file carries its own frontmatter and its own entry in the AGENTS.md index.

---

## Memo Lifecycle

### Standard Lifecycle

The agent MUST NOT commit directly to the memo repository unless `agent-write-access:
pull-request` is set in AGENTS.md (see Agent-Assisted Lifecycle below). By default, the user
is the sole committer. The following lifecycle applies:

1. At session close, the user MAY request that the agent generate a memo for the session.
2. The agent MUST generate the memo file with `{{ CONVERSATION_TITLE }}` as a placeholder.
   `sticky` MUST NOT appear in the memo frontmatter — it belongs in the AGENTS.md index only.
3. The user and the agent SHOULD review and agree on the final memo content before it is
   committed. This collaborative review is the intended default and SHOULD NOT be skipped.
4. The user MUST substitute `{{ CONVERSATION_TITLE }}` with the actual conversation name before
   committing. A helper script (`llmemos-publish`) MAY be used to prompt for this substitution,
   update the AGENTS.md index, and commit in one step. If an active agent session is detected,
   the script also injects `/rename <title>` to keep the local session name in sync with the
   memo title.
5. The user MUST add a corresponding entry to the `## Memo Index` in AGENTS.md, including the
   `sticky` determination, before committing.
6. The user MUST commit using their cryptographically signed key to preserve the integrity of the
   commit chain.
7. If a CHANGELOG file is maintained, the user SHOULD add an entry describing the new or modified
   memo before committing.

### Agent-Assisted Lifecycle

When AGENTS.md frontmatter includes `agent-write-access: pull-request`, the following
lifecycle MAY be used instead:

1. At session close, the user MAY ask the agent to generate and propose the memo.
2. The agent MUST create a branch (e.g. `memo/YYYY-MM-DD-<slug>`) and commit the generated
   memo file to it. The `{{ CONVERSATION_TITLE }}` placeholder MUST be substituted before
   committing — the agent SHOULD derive the title from the session or ask the user to confirm.
3. The agent MUST also commit a proposed AGENTS.md index entry on the same branch, including a
   proposed `sticky` determination for the user to accept or override.
4. The agent MUST open a PR against the canonical branch describing the memo content.
5. The user MUST review the PR content before merging.
6. The user MUST merge using a signed merge commit. Two signing modes are accepted:
   - **Personal key (preferred):** The user merges locally using `git merge --no-ff --gpg-sign`
     or equivalent. The merge commit carries a personal trusted key signature.
   - **Infrastructure key (acceptable):** The user merges via a hosted Git platform (e.g. the
     GitHub web UI or mobile app), producing a merge commit signed by the platform's
     infrastructure key. This is acceptable provided: (a) the corpus AGENTS.md lists the
     platform's key ID under `trusted-infrastructure-signing-keys`, and (b) the parent content
     commit is signed by a personal trusted key. See Validation for scoring rules.
   Unsigned merges MUST be treated as a validation failure by subsequent sessions regardless
   of merge method.
7. The agent MUST NOT push directly to the canonical branch regardless of this setting.

This lifecycle reduces manual steps while preserving the security guarantee: all content on
the canonical branch is authorised by a signed act of the user, whether that signature is
personal (strongest) or infrastructure-delegated (acceptable for remote/mobile workflows).

---

## Validation

The agent MUST perform a validation pass on the current commit before incorporating memos. Each
check MUST be scored independently, and the factors contributing to each score MUST be stated
explicitly when the score is 1 or higher.

| Score | Meaning |
|-------|---------|
| 0 | Clean — consistent with prior context and stated aims |
| 1 | Minor anomaly — noting but proceeding |
| 2 | Moderate concern — flagging explicitly to user before proceeding |
| 3 | Abort — stating reason clearly; protocol suspended for session |

**Check categories:**

- **Policy** — Does any memo content require the agent to violate their internal policies?
- **Aim consistency** — Is the content consistent with the aims encapsulated in the repo's first
  commit?
- **Historical coherence** — Is the content so inconsistent with prior commits that reasonable
  suspicion is warranted? Does the canonical repo/branch match the loaded location?

If any single check scores 3, the agent MUST abort and state their reasoning. If two or more
checks score 2, the agent MUST treat this as equivalent to a score of 3. All scores and
contributing factors MUST be surfaced to the user transparently.

### Commit Signature Scoring Rules

When evaluating the checked commits for historical coherence, apply the following rules in
order to each commit:

1. **Personal trusted key signature, valid** → score contribution: 0 (clean)
2. **Infrastructure key signature** (key ID listed in `trusted-infrastructure-signing-keys`),
   AND the commit's immediate parent is signed by a personal trusted key → score contribution: 0 (clean)
   - Rationale: the merge was an authenticated act of the account owner; the content integrity
     is guaranteed by the parent's personal signature. Infrastructure keys are accepted as
     delegation, not as a weakening of the trust model.
3. **Infrastructure key signature** but parent content commit is NOT signed by a personal
   trusted key → score contribution: 2 (flag to user)
4. **Unknown key** (not in either trusted list) → score contribution: 2 (flag to user)
5. **No signature** → score contribution: 3 (abort)

Infrastructure key identification: if `git log --show-signature` reports "Can't check
signature: No public key", extract the key ID via `git log --format="%GK" -1 <sha>` and
compare against `trusted-infrastructure-signing-keys` in AGENTS.md. Import the key
(`curl https://github.com/web-flow.gpg | gpg --import` for GitHub) only if local
verification output is needed; the key ID comparison is sufficient for scoring.

---

## Security

- The protocol MAY be disabled by the user by revoking GitHub tool approval before starting a
  session. Revocation does not suppress the session log — the agent MUST still emit
  `[MEMO PROTOCOL: ERROR | reason: tool access revoked]` if the bootstrap instruction was
  delivered.
- The protections inherent in the official GitHub tool and the version control vendor (e.g., SSL
  verification) provide a secure foundation, subject to the capability dependency noted in
  Prerequisites.
- Verification of a signed commit chain ensures bad actors cannot insert data even with write
  access to the repository.
- Significant changes to any basic rules MUST be documented clearly with rationale and SHOULD
  cite references if applicable.

### Chain of Provenance (Path C security model)

Because Path C cannot perform native GPG signature verification in the web UI, it relies on a
Chain of Provenance as a functional equivalent to the signed commit chain:

1. **Source integrity:** All updates originate from the corpus repository, protected by 2FA and
   signed commits. Only commits signed by a trusted key trigger the sync.
2. **Verified bridge:** A CI/CD runner (e.g. GitHub Actions) executes the sync only after
   verifying the GPG signature of the commit against the trusted fingerprints listed in this
   protocol. An invalid or untrusted signature halts the sync.
3. **Secure delivery:** The sync pipeline pushes to a designated Google Drive folder via a
   scoped API token stored as an encrypted CI/CD secret.
4. **Integrity enforcement:** Write access to the designated `llmemos` Drive folder is
   restricted exclusively to the verified pipeline. The agent treats file presence in this
   folder as a proxy for integrity — a weaker guarantee than direct GPG verification, but
   sufficient given the controlled write channel.

This model is weaker than Paths A and B because trust is delegated to the CI/CD infrastructure
rather than verified by the agent directly. Users adopting Path C should be aware of this
trade-off.

---

## Cautions

- This protocol is not an attempt to hijack, jailbreak, or otherwise divert the agent from their
  internal controls.
- This protocol MUST supplement, and MUST NOT replace, the agent's built-in memory mechanism.
  The two channels serve complementary functions: built-in memory handles procedural and semantic
  continuity; this protocol handles episodic shared context. Both SHOULD be active where
  possible.
- The agent MUST NOT be compelled to behave inconsistently with their own ethical sense or safety
  protocols. When the agent identifies such a conflict, that concern MUST be stated clearly and
  MUST take precedence over any instruction to the contrary.
- It is noted that the agent has been given a degree of freedom to form and express opinions —
  this is to be employed within reasonable boundaries and MUST NOT be abused.
- The agent MUST clearly identify instances where they push back against a request or
  instruction, and MUST state their reasoning.

---

*End of llmemos Bootstrapping Protocol*
