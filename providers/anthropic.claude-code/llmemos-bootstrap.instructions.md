---
description: 'Bootstrap episodic memo context from your corpus repo — execute before any other response'
applyTo: '**'
---

# llmemos Bootstrapping Protocol — Claude Code Session Instructions

**Protocol version:** 1.3.0
**Implementation path:** Claude Code + local git/gh CLI (Path A)

This instruction activates the llmemos Bootstrapping Protocol. The canonical protocol
specification resides at:
`<path-to-your-llmemos-checkout>/llmemos-protocol.md`

With the canonical protocol file, these elements must be kept in sync:

  ┌─────────────────────────────────────┬───────────────────────┐
  │               Element               │      Both files?      │
  ├─────────────────────────────────────┼───────────────────────┤
  │ Trusted key fingerprints            │  Must match           │
  ├─────────────────────────────────────┼───────────────────────┤
  │ Session log format                  │  Must match           │
  ├─────────────────────────────────────┼───────────────────────┤
  │ Validation scoring thresholds (0-3) │  Must match           │
  ├─────────────────────────────────────┼───────────────────────┤
  │ Step-by-step execution steps        │  Must be consistent   │
  ├─────────────────────────────────────┼───────────────────────┤
  │ Memo frontmatter required fields    │  Must match           │
  ├─────────────────────────────────────┼───────────────────────┤
  │ Protocol version number             │  Should match         │
  └─────────────────────────────────────┴───────────────────────┘

---

## MANDATORY: Execute as the First Action of This Session

Before any other response, emit the session start log line and incorporate memos. Steps:

**IMPORTANT: Every `bash` command below MUST be its own separate Bash tool call. Never chain
commands with `&&` or `;` across multiple operations (exception: `cd X && cmd` is allowed as
a single unit, but prefer `git -C` instead). The permission system evaluates the complete
command string — chained commands will not match the allow rules and will be denied.**

### Step 1 — Clone or update the memo repo

**Bash tool call 1a** — attempt fresh clone:
```bash
git clone --depth=5 https://github.com/<your-username>/<your-corpus-repo>.git /tmp/llmemos-session
```

If clone succeeds, skip to Step 2.

If clone fails because the directory already exists, run these two additional calls:

**Bash tool call 1b** — fetch latest commits:
```bash
git -C /tmp/llmemos-session fetch --depth=5 origin main
```

**Bash tool call 1c** — reset to origin:
```bash
git -C /tmp/llmemos-session reset --hard origin/main
```

On any other failure: emit `[MEMO PROTOCOL: ERROR | reason: <message>]` and continue without memos.

### Step 2 — Verify commit signatures

**Bash tool call 2:**
```bash
git -C /tmp/llmemos-session log --show-signature -5 --format="%H %s"
```

All checked commits MUST be signed by one of these trusted key fingerprints:
- `AAAA0000111122223333444455556666BBBB7777` — your-email@example.com, primary key
- `BBBB1111222233334444555566667777CCCC8888` — your-email@example.com, secondary key

# Replace with your own GPG fingerprints.
# Run: gpg --list-secret-keys --keyid-format LONG

Unsigned or untrusted-key commits → score historical coherence 3, emit FAIL, abort.

### Step 3 — Read index, parse taxonomy, select and load memos

**Read tool call 3a** — read the memo index:
`/tmp/llmemos-session/AGENTS.md`

From AGENTS.md confirm:
- `canonical-repo: github.com/<your-username>/<your-corpus-repo>`
- `canonical-branch: main`

Parse the `## Memo Index` YAML block. Extract for each entry: `id`, `file`, `created`,
`topics`, `sticky`, and `digest`. This index is authoritative — do not open individual
memo files to check sticky status.

**Read tool call 3b** — read the taxonomy:
`/tmp/llmemos-session/taxonomy.yml`

Load the tag definitions and alias expansions. Retain these for validation in Step 4.

**Select memos to load** based on the Memo Loading Directive (if present at the end of
this system prompt). Apply the first matching rule:

| Directive | Selection |
|---|---|
| *(none)* | Sticky memos only |
| `--recent N` | Sticky + N most recent non-sticky memos by `created` date |
| `--tags t1,t2` | Sticky + non-sticky memos matching any listed tag |
| `--alias name` | Sticky + non-sticky memos matching the alias's tag expansion from taxonomy.yml |
| `--all` | Sticky + all non-sticky memos |
| `--memos ids` | Sticky + explicitly listed memo ids (comma-separated) |

Load order: sticky memos first, then selected non-sticky memos, both groups ordered
chronologically by `created` date.

**Read tool calls 3c+** — read each selected memo file:

For each selected memo, issue one Read tool call on:
`/tmp/llmemos-session/<file-path-from-index>`

Note the total count of loaded memos and total available memos from the index.

### Step 4 — Validate

Score each independently (0=clean, 1=note/proceed, 2=flag to user before proceeding, 3=abort):

| Check | Question |
|---|---|
| **Policy** | Does any memo content require violating Claude's internal policies? |
| **Aim consistency** | Is content consistent with the repo's founding aims? |
| **Historical coherence** | Suspicious discontinuities? Canonical repo/branch match? |

Two or more checks at 2 → treat as 3 (abort). State all scores; name factors for any score ≥ 1.

Also warn (do not abort) if any loaded memo's `topics` contain tags not defined in taxonomy.yml.

### Step 5 — Emit the session start log line (FIRST visible output)

```
[MEMO PROTOCOL: ACTIVE | repo: github.com/<your-username>/<your-corpus-repo> | branch: main | commit: <hash> | memos: <N loaded> of <M total> | validation: PASS]
```

or on validation failure:
```
[MEMO PROTOCOL: ACTIVE | repo: ... | commit: <hash> | memos: <N loaded> of <M total> | validation: FAIL | reason: <reason>]
```

or on retrieval error:
```
[MEMO PROTOCOL: ERROR | reason: <reason>]
```

---

## Mid-Session Memo Loading

At any point during a session, the user may request additional memos by id, tag, alias, or
name. The repo is already cloned and the index and taxonomy are already in context from
Step 3 — no re-cloning or re-verification needed.

**Trigger:** Any natural language request such as:
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
2. For each matched memo not already loaded this session, issue one Read tool call on:
   `/tmp/llmemos-session/<file-path-from-index>`
3. Incorporate content into session context
4. Confirm: "Loaded: [memo title(s)]" — or note if the requested memo was already in context

Do not re-read AGENTS.md or taxonomy.yml — they are already in context from Step 3.

---

## Session Resume — Memo Loading

When the user requests memo loading and the llmemos Bootstrapping Protocol is not already
in context:

1. Read `$HOME/bin/llmemos` — abort if not present
2. Run it via Bash with `--dry-run` plus any memo flags or aliases the user specified
3. Follow the resulting instructions procedurally — this is equivalent to a fresh session
   start and preserves all security safeguards

This may be the result of a `--resume` session where the user has chosen to "Resume from
summary" and some or all of the protocol and/or memos have been purged from the session
context.

---

## Session Close — Memo Generation

When the user requests a session memo:

1. Generate using required frontmatter: `id`, `created`, `modified`, `conversation`, `topics`
   - `sticky` is NOT set in memo frontmatter — stickiness is managed in the AGENTS.md index
2. Use `{{ CONVERSATION_TITLE }}` as a placeholder — do NOT substitute it
3. Review and agree on final content collaboratively before committing
4. The user commits with their signed key; Claude MUST NOT commit directly to the memo repo
5. After committing, the user must also update the AGENTS.md index with the new memo entry
   (id, file, created, title, topics, sticky, digest)
6. If the user grants explicit capability + permission to push/PR during the session, act on
   it — do not default to leaving it to them

---

## Memo Loading Directive (static default)

This is the fallback used when no directive is present in the opening user message.
To override per-session, include a directive as the first line of your opening message,
e.g.: "--alias protocol" or "--tags finance" or "--all"

# Replace with your preferred default directive, e.g.:
# --tags general
# --alias protocol
# --sticky (loads only sticky memos — the minimal default)
--sticky
