# LLM Defense-in-Depth: Hybrid Command Security Reviewer + Content-Based Secret Scanning

> **This is a suggested, optional companion to the llmemos protocol, not
> part of it.** llmemos itself only concerns episodic memory bootstrapping;
> nothing in the protocol requires or depends on this feature. It's
> included here because it grew out of the same working relationship and
> the same defense-in-depth philosophy, and because llmemos adopters running
> Claude Code sessions may find the pattern useful — but it stands
> independently and you should feel free to ignore, adapt, or replace any
> part of it. Personal implementation notes (real paths, hardware, specific
> tool choices) are deliberately kept out of this document — see
> `phase-1/IMPLEMENTATION.md`-shaped local notes in your own environment if
> you build a variant of this.

**Status:** Planning — not yet implemented. This is a goals-and-constraints
document, deliberately left high-level. The implementing session should make
its own design decisions within these constraints rather than follow a
prescribed step list — see "Why this is a PLAN, not an IMPLEMENTATION doc"
below.

**Source:** Consolidated from two prior design discussions — one reviewing
shell-permission escape hatches, one comparing this proposal against Claude
Code's then-new auto-mode classifier and researching GitHub Copilot hook
parity. Reproduced and reconciled below rather than treated as a separate
thing to re-ingest.

---

## Why this is a PLAN, not an IMPLEMENTATION doc

Two reasons, not just one:

1. **Real open decisions remain that no one has done the legwork to close** —
   gitleaks subprocess latency at realistic call frequency hasn't been
   benchmarked, and GitHub Copilot's hook parity (real for CLI/cloud-agent
   surfaces, unconfirmed for IDE-integrated agent modes) hasn't been
   verified. A prescriptive implementation doc would have to either guess at
   these or leave placeholder TODOs — better to let the implementing session
   investigate and decide, with the reasoning visible in its own output.
2. **The proposal may be stale relative to whatever deterministic gate you
   already run.** It was drafted assuming a rule-engine plugin exists and
   handles allow/ask/deny classification (this doc uses
   [ClaudeWatch](https://github.com/chris-peterson/ClaudeWatch) as a
   concrete example throughout — substitute your own if you use something
   else, or skip the reconciliation section if you're starting from
   nothing). Freezing this design into an IMPLEMENTATION doc risks building
   something that duplicates your existing gate rather than extending it.
   The Reconciliation section below exists so the implementing session
   starts from current reality, not from a stale snapshot.

---

## Original design

### A. PreToolUse hybrid reviewer (the original core idea)

```
Command → Deterministic gate (DENY / ALLOW / GRAY ZONE)
                                        │ gray zone only
                                        ▼
                              LLM security reviewer
                              (PASS / FAIL / UNCERTAIN)
                                        │
                              UNCERTAIN → deny or prompt the human
```

- Both gates must pass (AND, never OR).
- LLM reviewer sees only the gray zone — commands neither explicitly allowed
  nor denied by the deterministic layer.
- Architectural diversity requirement: the reviewer must be a **different
  model or provider** than the agent being reviewed (Claude reviewing
  Claude's own commands shares training and blind spots — this is the
  "circular review problem," and it's the one requirement in this whole doc
  that isn't up for reinterpretation).
- Static, signed reviewer system prompt — version-controlled like llmemos;
  if the reviewer's prompt is itself dynamically injectable, the reviewer
  becomes another attack surface.
- Conservative default: UNCERTAIN → deny or human approval, never silently
  becomes allow.
- Compared against Claude Code's auto-mode classifier (deterministic +
  classifier hybrid, same general shape). Conclusion: still worth building
  *alongside* auto mode, not instead of it — auto-mode's classifier is
  same-vendor/same-lineage as the agent (exactly the circular-review problem
  above), has no anonymization layer, no persistent audit log of allow/deny
  verdicts, and no session-hash caching of repeat patterns. This conclusion
  should be re-examined against whatever your deterministic gate has since
  shipped (see Reconciliation).

### B. Two additional, separate hooks (content-based secret scanning)

These are a distinct concern from command-safety review — they scan for
*secrets*, not for dangerous *actions*.

- **B1. PostToolUse hook (primary priority).** Write tool output to a temp
  file, run `gitleaks detect --no-git -s <tmpdir>` against the canonical
  `~/.gitleaks.toml` ruleset, redact matches, return via `updatedToolOutput`.
  Scope to Read/Bash/Grep/WebFetch (not all tools) to bound subprocess
  overhead. Rationale for PRIMARY priority: this catches secrets entering
  context via file reads/@-mentions/attachments — the realistic accidental-
  exposure case — which a prompt-only scanner would miss entirely.
- **B2. UserPromptSubmit hook (secondary priority).** Same temp-file +
  gitleaks approach, applied to the literal `prompt` field. Exit 2 to hard-
  block high-confidence matches (real key/credential patterns); warn-only via
  `systemMessage` for lower-confidence generic patterns (`password=`,
  `secret=`) to avoid the hook getting disabled from over-triggering. Needs a
  deliberate bypass convention (no interactive confirm dialog exists in the
  hook system for a hard block).

### GitHub Copilot parity (needs re-verification at implementation time, not reuse)

- Copilot has its own preToolUse/postToolUse hooks (`.github/hooks/*.json`),
  close to field-equivalent to Claude Code's — B1 above should port with
  minimal changes.
- **Confirmed gap at the time this was drafted:** documented only for
  Copilot CLI and cloud agent surfaces, **not confirmed for IDE-integrated
  agent modes** (VS Code, JetBrains). This needs direct verification before
  relying on it there; don't assume it now just because CLI parity looked
  good at drafting time.
- Copilot's `userPromptSubmitted` (CLI/cloud agent) is non-blocking with no
  output mechanism — B2 does not port to that surface as designed.
- A genuinely blocking/modifiable `userPromptSubmitted` exists only in the
  Copilot SDK (custom-agent territory, not the CLI or any off-the-shelf
  surface) — a separate future project if pursued at all.

### Open item carried over verbatim (unresolved, needs investigation not a guess)

Benchmark gitleaks subprocess latency at realistic call frequency (per
Bash/Read/Grep/WebFetch call) and weigh against actual security benefit
before committing to B1/B2 across the board. For calibration: Claude Code's
own auto-mode classifier calls add a round-trip and count toward token usage;
the local gitleaks call should be cheaper but this was never verified.

---

## Reconciliation: what's changed since this was drafted

The proposal predates the current state of whatever deterministic gate you
run (this doc uses ClaudeWatch as the running example — substitute your
own plugin/tooling if different). If your deterministic gate already
covers allow/ask/deny classification with decision logging, this changes
the shape of what's left to build:

- **The "Deterministic gate" box in section A already exists and is running
  in production.** ClaudeWatch's rule engine (`scripts/watchdog.py` +
  `watches/*.yml`) does allow/ask/deny classification with decision logging,
  ask→deny escalation on compound commands, and a documented rule-authoring
  workflow (`/ClaudeWatch:rules`). **Do not re-implement a deterministic
  allowlist from scratch.** The LLM reviewer in section A should sit
  downstream of ClaudeWatch's own `ask` verdicts (i.e., ClaudeWatch's "ask"
  *is* the gray zone), not behind a second, parallel deterministic layer.
- **`watches/watch-secrets.yml` already exists but does not overlap with
  B1/B2.** It catches secret exposure via **command-string and filename
  heuristics** — `cat ~/.ssh/id_*`, `cat *.env`, `echo $SECRET_*`, etc. It
  does **not** scan actual tool *output content* for embedded
  secrets/tokens that leak incidentally through a file whose name gives no
  hint (a config file, a log dump, a web-fetched page). B1's content-based
  gitleaks scan of tool output is still a real, unfilled gap — this part of
  the original proposal holds up. B2 (prompt-content scanning) is likewise
  still unfilled.
- **The circular-review problem (architectural diversity requirement) is
  unaffected and still fully applies** — Claude Code's own auto-mode
  classifier is same-vendor/same-lineage as the agent it's watching, which
  is exactly the failure mode this design exists to avoid. This is the one
  part of the original conclusion that gets *stronger* with time, not
  weaker: don't use "auto mode already exists" as a reason to skip the LLM
  reviewer.
- **A live example of the gap the LLM reviewer would fill** occurred during
  the drafting of this document: ClaudeWatch's ambient rules correctly
  escalated a compound
  command (`gh issue create --body "$(cat <<'EOF' ... )"`) to a hard block
  because the guarded command (`gh issue create`) was piped/composed rather
  than issued bare — a deterministic, syntactic rule, not a semantic
  judgment about whether the *content* being posted was safe. That's a
  concrete, current instance of "deterministic gate handles the syntactic
  case; a semantic reviewer would be needed for judgment the regex can't
  make."
- **Decision logging already exists** (`CLAUDEWATCH_LOG`, schema-versioned,
  owner-only permissions) — the LLM reviewer's own audit log (verdict,
  model, reason, command hash) should probably follow the same convention
  rather than invent a second logging format.

## Scope for the implementing session

Given the reconciliation above, the actual remaining build is narrower than
the original doc implies:

1. An LLM semantic reviewer that receives ClaudeWatch's `ask` verdicts (not
   a new deterministic layer), from an architecturally distinct model —
   investigate real options (local Ollama vs. a different vendor's hosted
   API) and choose, don't assume the answer from context that may be stale
   by the time this is implemented.
2. B1 — PostToolUse content-based gitleaks scan of Read/Bash/Grep/WebFetch
   output.
3. B2 — UserPromptSubmit content-based gitleaks scan of the literal prompt.
4. Re-verify (don't reuse) the Copilot VS Code/JetBrains hook-parity
   question if that surface is in scope for this pass.
5. Do the gitleaks latency benchmark before committing to always-on
   B1/B2 — this was an open item before and still is.

## Constraints (non-negotiable regardless of implementation approach)

- Reviewer model must be architecturally distinct from the agent under
  review (different provider or a genuinely different model lineage).
- Reviewer system prompt must be static and signed/version-controlled.
- UNCERTAIN/ambiguous verdicts default to deny or human approval — never
  silent allow.
- Don't duplicate ClaudeWatch's deterministic allow/ask/deny gate.
- Follow the existing decision-logging convention rather than inventing a
  new one, unless there's a concrete reason the existing schema doesn't fit.

## Explicitly out of scope for this pass

- Rebuilding or extending ClaudeWatch's rule engine itself.
- The Copilot SDK custom-agent path for a genuinely blocking
  `userPromptSubmitted` — noted as a possible separate future project, not
  part of this build.
