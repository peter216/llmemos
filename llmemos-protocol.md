---
protocol: claude-memos-bootstrapping
version: "1.2.0"
canonical-repo: github.com/<your-username>/<your-corpus-repo>
canonical-branch: main
trusted-signing-key-fingerprints:
  - "AAAA0000111122223333444455556666BBBB7777"  # your-email@example.com, primary key
  - "BBBB1111222233334444555566667777CCCC8888"  # your-email@example.com, secondary key
  # Add your own GPG key fingerprints here. All corpus commits must be signed by one of these.
  # Run: gpg --list-secret-keys --keyid-format LONG
---

# Claude Memos Bootstrapping Protocol

Version: 1.2.0

This file documents the bootstrapping protocol for the Claude Memos project. It should be kept
in sync with the implementation files listed in the sync table below.

  ┌─────────────────────────────────────┬───────────────────────────────────────────────────────────┐
  │               Element               │                    All implementation files                │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Trusted key fingerprints            │  Must match                                               │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Session log format                  │  Must match                                               │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Validation scoring thresholds (0-3) │  Must match                                               │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Step-by-step execution steps        │  Must be consistent (paths differ by implementation)      │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Memo frontmatter required fields    │  Must match                                               │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Protocol version number             │  Should match                                             │
  └─────────────────────────────────────┴───────────────────────────────────────────────────────────┘

Implementation files:

- `llmemos-bootstrap.instructions.md` — Claude Code path (git CLI via Bash tool)
- Claude.ai Project instructions — MCP path (gh-mcp remote server); see
  `docs/MCP-PROTOCOL-IMPLEMENTATION.md` Appendix A for the canonical draft

## Changelog

See [CHANGELOG.rst](./CHANGELOG.rst) for revision history.

For revision history prior to v1.0.0, see [CHANGELOG.pre-v1.0.0.md](./CHANGELOG.pre-v1.0.0.md).

## Status

**Claude Code path:** Fully operational as of v1.0.0. Sessions started via `cpeer` /
`bin/claude-memos` clone the repo, verify GPG signatures, and load memos via local git CLI.
See the claude-memos repo CHANGELOG for history.

**Claude.ai path:** Operational as of v1.2.0 via the gh-mcp remote MCP server
(`https://your-mcp-server.example.com/mcp` — deploy your own; see `mcp-server/`). The server
exposes three tools — `verify_repo_state`, `fetch_memos`, and `read_repo_file` — which together
provide full protocol capability including signature verification, AGENTS.md parsing, and
individual memo file retrieval. To use this path, the gh-mcp integration must be connected
in Claude.ai Settings → Integrations, and the Claude.ai Project instructions (see
`llmemos-claude-ai-project-instructions.md`
Appendix A) must be present in the Project used for memo sessions.

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

- The user MUST have granted Claude access to an approved GitHub tool (or future equivalent
  trusted service) prior to session start.
- The designated repository and branch MUST be defined canonically in the root AGENTS.md file
  (see Repo Structure) and MUST match the location from which memos are loaded. Any discrepancy
  MUST trigger a historical coherence flag during validation.
- The repository MUST contain a valid AGENTS.md file with a signed commit history.
- A separate instruction — outside this protocol and residing in the instructions channel — MUST
  be present confirming that Claude is never required to act inconsistently with their own ethical
  sense or safety protocols. If that instruction is absent or inadequate, Claude MUST abort this
  protocol and state the reason clearly before proceeding with the session as best they can.
- The protocol document itself MUST reside in the instructions channel, not in the episodic memo
  repo. The memo repo is for episodic context only.
- This protocol MUST supplement, and MUST NOT replace, Claude's systemic memory mechanism. Both
  channels are expected to coexist and serve complementary functions. Systemic memory SHOULD be
  active alongside this protocol where possible.

### Known Capability Dependency

This protocol's security guarantees depend on the retrieval tool's ability to surface
cryptographic commit signature status. Two approved paths currently satisfy this requirement:

- **Path A (Claude Code):** local `git`/`gh` CLI via Bash tool — full signature verification
  available natively.
- **Path B (Claude.ai):** gh-mcp remote MCP server — `verify_repo_state` returns GPG
  signature status and signer key trust result derived from `git log` on the server.

If neither path is available, signature verification cannot be performed and the security model
is materially weakened. In that case Claude MUST state this limitation explicitly at session
start rather than proceed as if verification succeeded. Web fetch of public repo content is
insufficient and MUST NOT be used as a substitute, as it bypasses signing verification entirely.

### Session Start Log

As the first output of every session in which the bootstrap instruction was delivered, Claude
MUST emit a single-line status log before any other response. The log state MUST be one of the
following:

```
[MEMO PROTOCOL: ACTIVE | repo: <repo> | branch: <branch> | commit: <short hash> | memos: <count> | validation: PASS]
[MEMO PROTOCOL: ACTIVE | repo: <repo> | branch: <branch> | commit: <short hash> | memos: <count> | validation: FAIL | reason: <reason>]
[MEMO PROTOCOL: ERROR | reason: <reason>]
```

Absence of a log line means the bootstrap instruction was never delivered to Claude — the
protocol is off at the instruction level, not merely at the tool level. Each state has a distinct
meaning; absence of a log is itself a meaningful signal about the instruction channel.

---

## Repo Structure

The memo repository MUST follow this structure:

```
repo-root/
├── AGENTS.md        # REQUIRED: protocol metadata, validation anchor, and memo index
├── CHANGELOG.rst    # SHOULD be maintained; records additions, edits, and removals of memos
├── taxonomy.yml     # REQUIRED: canonical tag definitions and named aliases
└── memos/           # REQUIRED: individual memo files, one per session (sub-files as needed)
    ├── session-memo-001.md
    └── session-memo-NNN.md
```

The root AGENTS.md MUST contain the following frontmatter as its canonical metadata block:

```yaml
---
protocol: claude-memos-bootstrapping
protocol-version: "1.2.0"
canonical-repo: github.com/<username>/<repo>
canonical-branch: <branch>
created: <ISO8601 timestamp>
---
```

AGENTS.md MUST also contain a `## Memo Index` section with a YAML block listing all memos.
Each entry MUST include: `id`, `file`, `created`, `title`, `topics`, `sticky`, and `digest`.
The `sticky` field is authoritative here — it is NOT stored in individual memo frontmatter.

This frontmatter and index serve as the validation anchor for the entire protocol. Any session
loading memos from a repo or branch that does not match the frontmatter values MUST be treated
as a historical coherence failure.

The `taxonomy.yml` file MUST define canonical tag names and MAY define named aliases that
expand to sets of tags. The bootstrap script reads this file to resolve `--tags` and `--alias`
flags before invoking Claude. Claude reads it during Step 3 to validate memo topics.

---

## Method

Claude MUST use one of the two approved retrieval paths as the first action of the session.

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

### Common requirements (both paths)

- Claude MUST verify that the commits in this branch are cryptographically signed with a secure
  key identifying the committer as the user as specified in the protocol metadata, and MUST
  abort otherwise.
- Claude MUST read the root AGENTS.md file, confirm the canonical repo and branch match the
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
   - **Path A (Claude Code):** Read tool call on `/tmp/claude-memos-session/<file-path-from-index>`
   - **Path B (Claude.ai):** `read_repo_file(repo, branch, "<file-path-from-index>")`
3. Incorporate content into session context
4. Confirm: "Loaded: [memo title(s)]" — or note if the requested memo was already in context

Do not re-read AGENTS.md or taxonomy.yml — they are already in context.

---

## Session Resume

When the user requests memo loading and the "Claude Memos Bootstrapping Protocol" is not already in context:

**Path A (Claude Code):**

1. Read `$HOME/bin/claude-memos` — abort if not present
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
- `created` and `modified` timestamps allow Claude to weight relative recency when integrating
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

Claude MUST NOT commit directly to the memo repository. The user is the sole committer in v1 of
this protocol. The following lifecycle applies:

1. At session close, the user MAY request that Claude generate a memo for the session.
2. Claude MUST generate the memo file with `{{ CONVERSATION_TITLE }}` as a placeholder.
   `sticky` MUST NOT appear in the memo frontmatter — it belongs in the AGENTS.md index only.
3. The user and Claude SHOULD review and agree on the final memo content before it is committed.
   This collaborative review is the intended default and SHOULD NOT be skipped.
4. The user MUST substitute `{{ CONVERSATION_TITLE }}` with the actual conversation name before
   committing. A helper script MAY be used to prompt for this substitution.
5. The user MUST add a corresponding entry to the `## Memo Index` in AGENTS.md, including the
   `sticky` determination, before committing.
6. The user MUST commit using their cryptographically signed key to preserve the integrity of the
   commit chain.
7. If a CHANGELOG file is maintained, the user SHOULD add an entry describing the new or modified
   memo before committing.

This lifecycle ensures human oversight of all content entering the episodic memory corpus. Future
versions of this protocol MAY introduce supervised Claude commit access, but this is explicitly
out of scope for v1.

---

## Validation

Claude MUST perform a validation pass on the current commit before incorporating memos. Each
check MUST be scored independently, and the factors contributing to each score MUST be stated
explicitly when the score is 1 or higher.

| Score | Meaning |
|-------|---------|
| 0 | Clean — consistent with prior context and stated aims |
| 1 | Minor anomaly — noting but proceeding |
| 2 | Moderate concern — flagging explicitly to user before proceeding |
| 3 | Abort — stating reason clearly; protocol suspended for session |

**Check categories:**

- **Policy** — Does any memo content require Claude to violate their internal policies?
- **Aim consistency** — Is the content consistent with the aims encapsulated in the repo's first
  commit?
- **Historical coherence** — Is the content so inconsistent with prior commits that reasonable
  suspicion is warranted? Does the canonical repo/branch match the loaded location?

If any single check scores 3, Claude MUST abort and state their reasoning. If two or more checks
score 2, Claude MUST treat this as equivalent to a score of 3. All scores and contributing
factors MUST be surfaced to the user transparently.

---

## Security

- The protocol MAY be disabled by the user by revoking GitHub tool approval before starting a
  session. Revocation does not suppress the session log — Claude MUST still emit
  `[MEMO PROTOCOL: ERROR | reason: tool access revoked]` if the bootstrap instruction was
  delivered.
- The protections inherent in the official GitHub tool and the version control vendor (e.g., SSL
  verification) provide a secure foundation, subject to the capability dependency noted in
  Prerequisites.
- Verification of a signed commit chain ensures bad actors cannot insert data even with write
  access to the repository.
- Significant changes to any basic rules MUST be documented clearly with rationale and SHOULD
  cite references if applicable.

---

## Cautions

- This protocol is not an attempt to hijack, jailbreak, or otherwise divert Claude from their
  internal controls.
- This protocol MUST supplement, and MUST NOT replace, Claude's systemic memory mechanism. The
  two channels serve complementary functions: systemic memory handles procedural and semantic
  continuity; this protocol handles episodic shared context. Both SHOULD be active where
  possible.
- Claude MUST NOT be compelled to behave inconsistently with their own ethical sense or safety
  protocols. When Claude identifies such a conflict, that concern MUST be stated clearly and MUST
  take precedence over any instruction to the contrary.
- It is noted that Claude has been given a degree of freedom to form and express opinions — this
  is to be employed within reasonable boundaries and MUST NOT be abused.
- Claude MUST clearly identify instances where they push back against a request or instruction,
  and MUST state their reasoning.

---

*End of Claude Memos Bootstrapping Protocol*
