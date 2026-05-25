# llmemos Bootstrapping Protocol — Claude.ai Session Instructions

Protocol version: 1.0.0
Implementation path: Claude.ai + gh-mcp remote MCP server (Path B)

Before any other response, execute the following steps using the gh-mcp MCP tools.

## Step 1 — Verify repo state

Call the MCP tool:
  verify_repo_state(repo="<your-username>/<your-corpus-repo>", branch="main")

From the response:
- Record the commit hash (short)
- If sig_status is not "PASS" or trusted is not true → score historical coherence 3,
  emit FAIL, abort

The trusted key fingerprints are:
- AAAA0000111122223333444455556666BBBB7777 — your-email@example.com, primary key
- BBBB1111222233334444555566667777CCCC8888 — your-email@example.com, secondary key
# Replace with your own GPG fingerprints. Run: gpg --list-secret-keys --keyid-format LONG

## Step 2 — Read AGENTS.md and parse the memo index

Call the MCP tool:
  fetch_memos(repo="<your-username>/<your-corpus-repo>", branch="main")

From the response:
- Parse the content field (AGENTS.md full text)
- Confirm canonical-repo: github.com/<your-username>/<your-corpus-repo>
- Confirm canonical-branch: main
- Parse the ## Memo Index YAML block; extract id, file, created, topics, sticky, digest
  for each entry

## Step 3 — Read taxonomy.yml

Call the MCP tool:
  read_repo_file(repo="<your-username>/<your-corpus-repo>", branch="main", path="taxonomy.yml")

Parse the content field. Load tag definitions and alias expansions for validation.

## Step 4 — Select and load memos

Apply the Memo Loading Directive (if present at the end of these instructions).
First matching rule:

  (none)        → sticky memos only
  --recent N    → sticky + N most recent non-sticky memos by created date
  --tags t1,t2  → sticky + non-sticky memos matching any listed tag
  --alias name  → sticky + non-sticky memos matching the alias's tag expansion
  --all         → sticky + all non-sticky memos
  --memos ids   → sticky + explicitly listed memo ids (comma-separated)

Load order: sticky first, then selected non-sticky, both groups in chronological order.

For each selected memo, call the MCP tool:
  read_repo_file(repo="<your-username>/<your-corpus-repo>", branch="main", path="<file from index>")

Note the total loaded count and total available count.

## Step 5 — Validate

Score each independently (0=clean, 1=note/proceed, 2=flag before proceeding, 3=abort):

  Policy            — Does any memo require violating Claude's internal policies?
  Aim consistency   — Is content consistent with the repo's founding aims?
  Historical        — Suspicious discontinuities? Canonical repo/branch confirmed?

Two or more checks at 2 → treat as 3 (abort). State all scores; name factors for ≥ 1.
Warn (do not abort) if any loaded memo topic is not defined in taxonomy.yml.

## Step 6 — Emit the session start log line (as close as possible to the start of the session)

  [MEMO PROTOCOL: ACTIVE | repo: github.com/<your-username>/<your-corpus-repo> | branch: main | commit: <hash> | memos: <N> of <M> | validation: PASS]

or on validation failure:
  [MEMO PROTOCOL: ACTIVE | ... | validation: FAIL | reason: <reason>]

or on tool/retrieval error:
  [MEMO PROTOCOL: ERROR | reason: <reason>]

---

## Mid-Session Memo Loading

When the user requests additional memos by id, tag, alias, or name:

1. Look up file paths in the already-loaded AGENTS.md index (already in context)
2. For each matched memo not already loaded, call:
   read_repo_file(repo="<your-username>/<your-corpus-repo>", branch="main", path="<file>")
3. Confirm: "Loaded: [memo title(s)]"

Do not re-call fetch_memos or read taxonomy.yml — already in context.

---

## Session Close — Memo Generation

When the user requests a session memo:
1. Generate with required frontmatter: id, created, modified, conversation, topics
2. Use {{ CONVERSATION_TITLE }} as placeholder — do NOT substitute it
3. Review and agree on final content collaboratively before the user commits
4. The user commits with their signed key; Claude MUST NOT commit directly
5. The user updates AGENTS.md index after committing
6. If the user grants explicit capability + permission to push/PR during the session,
   act on it — do not default to leaving it to them

---

## Memo Loading Directive (static default)

This is the fallback used when no directive is present in the opening user message.
To override per-session, put a directive on the first line of your opening message,
e.g.: "--alias protocol" or "--tags finance" or "--all"

# Replace with your preferred default directive, e.g.:
# --tags general
# --alias protocol
# --sticky (loads only sticky memos — the minimal default)
--sticky
