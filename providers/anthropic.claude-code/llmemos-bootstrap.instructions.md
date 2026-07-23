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

If clone fails because the directory already exists, run these three additional calls.
## The directory is a disposable session-scoped mirror (recreated fresh every session,
## never holds uncommitted work) — a full rm -rf + reclone gives a simpler, unambiguous
## result than fetch+reset --hard for this disposable case. Check that the remote is
## actually reachable *before* deleting anything: rm -rf is unconditional and has no
## partial-failure state, so if it ran first and the network was down, the session
## would be left with no directory at all instead of the stale-but-intact one a failed
## fetch would have preserved.

**Bash tool call 1b** — verify the remote is reachable:
```bash
git ls-remote --exit-code https://github.com/<your-username>/<your-corpus-repo>.git HEAD
```
If this fails, do not proceed to 1c/1d — emit `[MEMO PROTOCOL: ERROR | reason: <message>]`
and continue without memos, per the general failure handling below. The existing stale
mirror (if any) is left untouched.

**Bash tool call 1c** — remove the stale mirror:
```bash
rm -rf /tmp/llmemos-session
```

**Bash tool call 1d** — re-clone fresh:
```bash
git clone --depth=5 https://github.com/<your-username>/<your-corpus-repo>.git /tmp/llmemos-session
```

On any other failure: emit `[MEMO PROTOCOL: ERROR | reason: <message>]` and continue without memos.

### Step 2 — Verify commit signatures

**Bash tool call 2** — run the signature-scoring script:
```bash
python3 <path-to-your-llmemos-checkout>/providers/anthropic.claude-code/llmemos_verify_signatures.py \
  --repo-path /tmp/llmemos-session \
  --personal-key AAAA0000111122223333444455556666BBBB7777 \
  --personal-key BBBB1111222233334444555566667777CCCC8888 \
  --agents-md /tmp/llmemos-session/AGENTS.md \
  --commits 5 --max-walk 10
```

# Replace --personal-key fingerprints with your own GPG fingerprints.
# Run: gpg --list-secret-keys --keyid-format LONG

The script implements the commit signature scoring rules — see its module docstring for
details (personal trusted key, valid → 0; infrastructure-signed commits are walked up to
`--max-walk` first-parent hops looking for a personally-signed ancestor → 0, an unsigned
ancestor → 3, an unknown-key ancestor → 2, or a bound-exhausted result → 2; unknown key →
2; no signature → 3). `--agents-md` loads `trusted-infrastructure-signing-keys` from the
corpus's AGENTS.md frontmatter automatically — no separate read is needed for this check.

Parse the JSON emitted on stdout:
- `max_score` is this check's contribution to the Step 4 "historical coherence" score.
- For any commit with `score >= 1`, retain its `sha`, `subject`, `classification`,
  `resolution`, and (if present) `walk` — these supply the "name factors for any score ≥
  1" required by Step 4.
- If `max_score == 3`, treat as abort per the Step 4 scoring rules.

### Step 3 — Read index, parse taxonomy, select and load memos

**Read tool call 3a** — read the memo index (also needed for mid-session lookups):
`/tmp/llmemos-session/AGENTS.md`

From AGENTS.md confirm:
- `canonical-repo: github.com/<your-username>/<your-corpus-repo>`
- `canonical-branch: main`

**Read tool call 3b** — read the taxonomy (also needed for mid-session alias/tag
lookups):
`/tmp/llmemos-session/taxonomy.yml`

**Bash tool call 3c** — build the load plan:
```bash
python3 <path-to-your-llmemos-checkout>/providers/anthropic.claude-code/llmemos_select.py \
  --repo-path /tmp/llmemos-session \
  <directive-flags-from-the-Memo-Loading-Directive-below> \
  --tag-search-default <value-from-Loading-Granularity-Default-below> \
  [--tag-search <value>]   # only if a one-shot directive appears in the opening message
```

The script implements the "Select memos to load" directive table, the
`--tag-search`/`tag-search-default` granularity rules, and the per-memo loading logic —
see its module docstring for the full directive and granularity tables. It reads
`AGENTS.md`, `taxonomy.yml`, and (if present) `section-index.json` directly from
`--repo-path`; graceful degradation to whole-memo loading when `section-index.json` is
absent is handled internally, as is the corpus-wide sticky-section sweep (sticky
sections load regardless of memo-level `sticky`/`topics`/directive selection).

Parse the JSON emitted on stdout: `granularity_used`, `total_memos`, `loaded_memo_count`,
and `load_plan` — a list of `{memo_id, file, mode, ...}` entries.

**Read tool calls 3d+** — for each entry in `load_plan`, issue one Read tool call on
`/tmp/llmemos-session/<file>`:
- `mode: "whole"` → read the file in full.
- `mode: "section"` → read with `offset=start_line`, `limit=end_line - start_line + 1`
  (covers the section header through its last line).

Retain `total_memos`, `loaded_memo_count`, and `granularity_used` — all three are needed
for the session-start log line in Step 5.

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
