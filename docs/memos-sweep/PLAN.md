# Memos Sweep — Plan

**Status:** Deferred (Peter: "I don't think we need to sweep the existing corpus
yet, although I do want to do that later" — 2026-06-07). This doc exists so the
findings below aren't lost between now and whenever that sweep happens.

## Context

While building and smoke-testing `bin/llmemos-audit --report sections` against the
full corpus (`docs/accelerate/IMPLEMENTATION.md` Feature 2, Step 5 — section-tagging
work, 2026-06-07), the indexer's first full-corpus run surfaced four pre-existing
corpus-hygiene defects, all unrelated to section tagging itself. They were not fixed
in place — that's exactly the kind of "sweep the existing corpus" work Peter said to
defer — but they're recorded here so the audit tool's first real findings don't
evaporate before the sweep is scheduled.

(The tool was made tolerant of all four — logging a warning and skipping the
affected memo rather than crashing the whole index run — both because a single bad
memo shouldn't block indexing the rest of the corpus, and because surfacing defects
like these *is* the tool's job.)

## Findings

### 1. AGENTS.md path transposition: session-memo-009a / session-memo-009b

`AGENTS.md` lists these files at:

```
archive/memos/session-memo-009a-claude-code-todo-func.md
archive/memos/session-memo-009b-claude-ai-todo-func.md
```

But `git ls-tree -r HEAD` shows the actual tracked paths are:

```
memos/archive/session-memo-009a-claude-code-todo-func.md
memos/archive/session-memo-009b-claude-ai-todo-func.md
```

The `archive` and `memos` path segments are transposed in both `file:` entries.
This isn't a missing-file problem — the memos exist and are tracked in git; AGENTS.md
just points at the wrong path. **Fix:** swap the two segments in both `file:` fields.
Trivial, but currently makes both memos unreachable by any tooling that resolves
paths relative to the corpus root (including `llmemos-audit` itself, and presumably
anything else that reads `AGENTS.md` to locate memo files).

### 2. Malformed frontmatter: session-memo-015

```yaml
conversation: Centaur Project: Execution Phase Status
```

The colon inside the unquoted scalar value makes YAML parse `conversation:` as the
start of a nested mapping (`mapping values are not allowed here`), which breaks
frontmatter parsing for the whole memo. **Fix:** quote the value —
`conversation: "Centaur Project: Execution Phase Status"`.

### 3. Malformed frontmatter: session-memo-018

```yaml
conversation: "no therapy rule and send timestamps to claude"
topics: [personal, devops-pitch, ai-philosophy]
  - personal
  - devops-pitch
  - ai-philosophy
```

`topics:` is written in flow style (`[...]`) *and* immediately followed by three
orphaned block-list items at the same content — `expected <block end>, but found
'<block sequence start>'`. Reads like a leftover from an edit that converted the
list to flow style without deleting the original block-style lines. **Fix:** delete
the three orphaned `- personal` / `- devops-pitch` / `- ai-philosophy` lines; the
flow-style `topics:` line already carries the same three values.

## Why these matter beyond the indexer

All four defects make their respective memos partially or fully invisible to any
tooling that depends on `AGENTS.md` + frontmatter being well-formed — not just
`llmemos-audit`. Until fixed:

- session-memo-009a/009b can't be loaded by path from AGENTS.md at all
- session-memo-015/018 will fail frontmatter parsing in any tool that doesn't
  specifically guard against `yaml.YAMLError` the way `llmemos-audit` now does

## Relationship to In-Flight Work

Like the vendor-neutrality sweep, this is deliberately sequenced as its own pass
rather than folded into the section-tagging effort that surfaced it — fixing corpus
content is a different kind of work from building the tooling that found the
problems, and bundling them would muddy both the section-tagging PR and the eventual
sweep's scope. `llmemos-audit --report sections` is now the natural detection
mechanism for this class of defect going forward (it logs a warning and continues
rather than crashing), so the sweep can simply start by running it and triaging
whatever it reports — these four are just the first batch it found.
