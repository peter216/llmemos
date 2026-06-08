---
description: 'Bootstrap episodic memo context from your corpus repo — execute before any other response'
applyTo: '**'
---

# llmemos Bootstrapping Protocol — Claude Code Session Instructions

**Protocol version:** 1.2.0
**Implementation path:** Claude Code + local git/gh CLI (Path A)

This instruction activates the llmemos Bootstrapping Protocol. The canonical protocol
specification resides at:
`<path-to-your-llmemos-checkout>/llmemos-protocol.md`

With the canonical protocol file, these elements must be kept in sync:

  ┌──────────────────────────────────────────────┬───────────────────────┐
  │               Element                        │      Both files?      │
  ├──────────────────────────────────────────────┼───────────────────────┤
  │ Trusted key fingerprints                     │  Must match           │
  ├──────────────────────────────────────────────┼───────────────────────┤
  │ Trusted infrastructure signing key IDs       │  Must match           │
  ├──────────────────────────────────────────────┼───────────────────────┤
  │ Session log format                           │  Must match           │
  ├──────────────────────────────────────────────┼───────────────────────┤
  │ Validation scoring thresholds (0-3)          │  Must match           │
  ├──────────────────────────────────────────────┼───────────────────────┤
  │ Step-by-step execution steps                 │  Must be consistent   │
  ├──────────────────────────────────────────────┼───────────────────────┤
  │ Memo frontmatter required fields             │  Must match           │
  ├──────────────────────────────────────────────┼───────────────────────┤
  │ Protocol version number                      │  Should match         │
  └──────────────────────────────────────────────┴───────────────────────┘

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

Additionally, read `trusted-infrastructure-signing-keys` from AGENTS.md (if present).
These are key IDs (short form, e.g. `B5690EEEBB952194`) for platform infrastructure signers
such as GitHub's web-flow merge key.

Apply these scoring rules to each commit:

1. **Personal trusted key, valid** → historical coherence contribution: 0
2. **Infrastructure key** (ID in `trusted-infrastructure-signing-keys`) AND parent commit
   signed by a personal trusted key → historical coherence contribution: 0
   - If `git log --show-signature` reports "Can't check signature: No public key", extract
     the key ID via `git log --format="%GK" -1 <sha>` and compare to the infrastructure list.
3. **Infrastructure key** but parent is NOT signed by a personal trusted key → score 2
4. **Unknown key** (not in either list) → score 2
5. **No signature** → score 3 (abort)

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

**Read tool call 3c (optional)** — if `section-index.json` exists at the corpus root,
read it:
`/tmp/llmemos-session/section-index.json`

Because the index ships inside the same signed commit as the rest of the corpus, no
separate currency/staleness check is performed — it is trusted exactly as the rest of
the corpus content is. If present, use it for section-level loading per "Loading
granularity" below. If absent, fall back to whole-memo loading (today's behavior) —
this is graceful degradation, not an error condition.

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

**Loading granularity** — if `section-index.json` was loaded in 3c, resolve the
*initial bootstrap load's* granularity via `--tag-search <all | sections | memos>`
(a one-shot directive, consumed here and discarded):

| `--tag-search` value | Behavior |
|---|---|
| `all` (protocol default) | Union of memo-level and section-level matches, deduplicated — a memo already loaded in full is not redundantly re-loaded at section level. On a corpus with no section tagging adopted, this collapses to today's whole-memo behavior (graceful degradation) |
| `sections` | Load matching content at section granularity wherever the index allows it |
| `memos` | Load matching content at whole-memo granularity only (today's behavior, regardless of index presence) |

**Distinguishing `--tag-search` from `tag-search-default`:** `--tag-search` is
consumed once, here, to select the *initial* load's granularity, then discarded. A
separate, persistent setting — `tag-search-default` — may also be present, supplied
via the altpath mechanism (the same channel that carries trusted-key overrides and
taxonomy extensions) and retained in ambient session context for the rest of the
session. Look for a `tag-search-default: <all|sections|memos>` line under the
"Loading Granularity Default" heading near the end of this file — read it during
bootstrap alongside the static memo-loading directive footer, and retain its value
for the rest of the session. Unlike `--tag-search`, it remains available to inform
*any* loading decision the agent makes on its own initiative after bootstrap
completes — see "Mid-Session Memo Loading" below for how it governs agent-initiated
loads. The altpath mechanism is the right carrier for it precisely because it is
read once at session start and folded into ambient context, rather than consumed
and discarded like a CLI argument.

For each memo in the selection set, apply this loading logic (uniform — every indexed
memo has at least one section entry by construction, so there is no "memo has no
sections" special case to handle):

1. **Sticky memo** → load the whole memo in one Read call (a read-efficiency
   optimization: a sticky memo's sections collectively span its entire body, so
   reading them individually would cost more round-trips than reading the file once)
2. **Non-sticky memo**, when operating at section granularity:
   - Load sections where `sticky=true` unconditionally
   - Load sections whose `tags` intersect the active loading directive — for an
     untagged memo this naturally means loading its single synthetic section (whose
     `tags` are the memo's `topics`), reproducing today's whole-memo behavior exactly
   - Skip sections with no matching tags and `sticky=false`

When loading a section rather than a whole memo, read the memo file and request only
the lines spanning the index's `start_line`/`end_line` for that section — these align
directly with a targeted Read call's `offset`/`limit` parameters, so no re-parsing of
the memo file is needed. Include the section header in the read range.

**Read tool calls 3d+** — read each selected memo or section:

For each selected memo (whole-memo path) or section (section-granularity path), issue
one Read tool call on:
`/tmp/llmemos-session/<file-path-from-index>`
— passing `offset`/`limit` derived from the index's `start_line`/`end_line` for
section-level reads.

Note the total count of loaded memos/sections, the total available memos from the
index, and which granularity was actually used — all three are needed for the
session-start log line in Step 5.

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
[MEMO PROTOCOL: ACTIVE | repo: github.com/<your-username>/<your-corpus-repo> | branch: main | commit: <hash> | memos: <N loaded> of <M total> | granularity: <whole-memo|sections|mixed> | validation: PASS]
```

or on validation failure:
```
[MEMO PROTOCOL: ACTIVE | repo: ... | commit: <hash> | memos: <N loaded> of <M total> | granularity: <whole-memo|sections|mixed> | validation: FAIL | reason: <reason>]
```

or on retrieval error:
```
[MEMO PROTOCOL: ERROR | reason: <reason>]
```

**`granularity` field values:**

| Value | When to use |
|---|---|
| `whole-memo` | No `section-index.json` was present (graceful degradation), or every loaded memo was loaded in full (e.g. all selections were sticky, or `--tag-search memos` was in effect) |
| `sections` | At least one memo was loaded at section granularity and none were loaded as a whole-memo *match* (sticky whole-memo loads don't count against this — they're the read-efficiency optimization, not a granularity choice) |
| `mixed` | The selection set combined whole-memo loads (sticky memos, or non-sticky memos matched as a whole under `--tag-search all`'s union/dedup) with section-level loads of other memos |

> **Sync note:** This field is new in protocol v1.2.0 and not yet reflected in the
> canonical `llmemos-protocol.md` Step 5 template — that file's matching template
> needs a corresponding update to satisfy the "Session log format — Must match"
> sync-table requirement. Flagged here as a known follow-up, not yet applied.

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

**Loading granularity for agent-initiated loads**

> When an agent independently decides to load additional memo content mid-session
> (i.e., not in direct response to an explicit user directive specifying
> granularity), it SHOULD honor the session's configured `tag-search` preference.
> If the agent judges that an alternate granularity better serves the immediate
> need — e.g., pulling a whole memo despite a `sections` preference because the
> surrounding context made the full memo clearly relevant, or vice versa — it MAY
> do so without seeking permission first. However, it MUST note the deviation to
> the user afterward (e.g., "loaded memo-030 in full rather than just the tagged
> section, because X"), so the user can decide whether their configured default
> should change based on the pattern the agent is observing.

This mirrors the protocol's existing "warn but don't abort" posture (cf. the
taxonomy-tag-mismatch check in Step 4 validation): trust the agent's in-the-moment
judgment, but surface deviations transparently so the human stays in the loop on
tuning their own defaults.

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
7. `llmemos-publish` automatically injects `/rename <title>` into the active Claude session
   after publishing, keeping the local session name in sync with the memo title. Pass
   `--no-rename` to skip this step.

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

---

## Loading Granularity Default (tag-search-default)

This is the persistent session-level preference for loading granularity, carried
via the altpath mechanism — read once at bootstrap (Step 3) and retained in
ambient session context for the rest of the session. It governs granularity for
*agent-initiated* mid-session loads (see "Loading granularity for agent-initiated
loads" under Mid-Session Memo Loading) and, when no `--tag-search` directive is
supplied for the initial bootstrap, also serves as that load's granularity.

Distinct from `--tag-search`: that flag is one-shot (consumed at Step 3, governs
only the initial load); this setting persists for the whole session.

# Replace with your preferred default granularity: all | sections | memos
tag-search-default: all
