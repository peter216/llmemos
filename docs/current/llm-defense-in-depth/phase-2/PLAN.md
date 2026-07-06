# LLM Defense-in-Depth, Phase 2: Prompt-Volume Reduction

> **This is a suggested, optional companion to the llmemos protocol, not
> part of it** — see the note at the top of `../phase-1/PLAN.md`. Nothing
> here is required by, or specific to, the memory-bootstrapping protocol
> itself.

**Status:** Planning — not yet implemented. Like phase-1's `PLAN.md`, this
is deliberately a goals-and-constraints document, not a step list — see
"Why this is a PLAN, not an IMPLEMENTATION doc" in that file for the
reasoning; it applies here unchanged. The implementing session should
investigate the open questions below and make its own design decisions
within the constraints, not follow a prescription.

**Source:** a known limitation flagged during phase-1 implementation — an
earlier design discussion had estimated a substantial (~60%)
gray-zone-prompt reduction was achievable with "an allowlist plus LLM
auto-PASS on safe chains plus context-resolved heredocs," and phase 1
deliberately did not attempt that part of the design (see phase-1's
`PLAN.md` constraint that ambiguous verdicts never silently become an
allow — this phase is about the *non*-ambiguous case: commands the
reviewer confidently judges safe, every time, and what if anything should
change about the human-confirmation requirement for those).

---

## The problem phase 1 left open

Phase 1 built a semantic reviewer that sits behind ClaudeWatch's `ask`
verdicts and can **tighten** them (PASS/UNCERTAIN → ask stands, FAIL →
deny). It **cannot loosen** them — a plain `ask` that the reviewer judges
PASS still interrupts the human, because Claude Code coalesces multiple
PreToolUse hook decisions most-restrictive-wins. Two independent hooks
can agree a command is fine and the human still gets prompted, because
neither hook can unilaterally downgrade the *other* hook's `ask` to
`allow` — there is no coalescing rule that lets a second opinion cancel
a first one.

This means phase 1 delivered the safety half of the original design
(tightening the genuinely risky gray-zone commands into hard denies) but
not the ergonomics half (letting the genuinely safe gray-zone commands
through without a prompt). The earlier ~60% estimate was specifically
about the ergonomics half — reducing how often the human gets
interrupted for commands that turn out, every time, to be fine.

## Why this needs its own phase, not a phase-1 patch

Loosening a verdict is a fundamentally different trust operation than
tightening one, and the original design's own words are explicit that
this is the one requirement that *is* up for reinterpretation depending
on how it's built: **"UNCERTAIN → deny or human approval, never silently
becomes allow"** was written about the reviewer's own verdict, not about
whether an external mechanism may auto-approve on the reviewer's behalf.
Building an auto-allow path means answering, freshly, what evidentiary
bar justifies letting an LLM's PASS verdict skip human confirmation
entirely — that's a real design question, not a wiring change, and it
deserves the same explicit-constraints treatment phase 1 got before any
code is written.

It also isn't obviously true that a parallel hook is even the right
mechanism. Two structurally different approaches exist and neither has
been evaluated:

1. **Extend ClaudeWatch itself** with a new rule action (e.g. a
   `consult` verdict alongside `block`/`ask`) that defers to an external
   reviewer and, on a sufficiently confident PASS, resolves to `allow`
   from inside the engine that owns the decision in the first place —
   avoiding the coalescing problem by construction, since the loosening
   would happen before coalescing ever sees an `ask`.
2. **A caching/allowlist-learning layer** downstream of the reviewer,
   inspired by `/ClaudeWatch:learn`'s existing decision-log-driven
   workflow: instead of an LLM auto-approving in real time, use the
   accumulated reviewer audit log (a fixed, small set of command shapes
   that always got PASS is the expected real-world shape of this data) to
   periodically propose new
   ClaudeWatch `except`/allow rules for human review — the reduction
   happens at rule-authoring time, not decision time, and never
   requires an LLM verdict to silently become an allow at all.

Option 1 is architecturally cleaner but requires upstream changes to
ClaudeWatch (a plugin phase 1 explicitly avoided modifying, per its own
"don't duplicate/extend ClaudeWatch's rule engine" constraint — this
would be extending it deliberately and with reason, not duplicating it,
but that distinction should be made explicitly if pursued). Option 2
requires no hook-coalescing change at all and mirrors a workflow that
already exists and is trusted, but only reduces prompt volume for
*repeated* patterns, not novel-but-safe ones — the reviewer's
in-the-moment judgment gets no leverage under this option.

**Investigate both before choosing; don't assume Option 1 because it's
more elegant, or Option 2 because it's less invasive.**

## Constraints (carried over from phase 1, unchanged)

- Architectural diversity requirement for any reviewer verdict feeding
  an auto-allow decision remains non-negotiable — same reasoning as
  phase 1's circular-review-problem constraint.
- Any new allow path must be at least as auditable as phase 1's deny
  path: a human must be able to reconstruct, after the fact, why a given
  command was auto-allowed, from a log — not just from model behavior
  that happened to be unlogged.
- Ambiguity still never becomes approval. Whatever confidence threshold
  is chosen for auto-allow, `UNCERTAIN` and any reviewer error must still
  resolve to "ask stands," exactly as in phase 1 — this document changes
  what a confident `PASS` is allowed to do, not what an unconfident or
  failed review does.
- Don't duplicate or silently fork ClaudeWatch's rule engine. If Option 1
  is chosen, coordinate the change as an actual extension to that
  project (even if it's a personal fork), not a shadow implementation
  living only in your own hooks directory.

## Open questions the implementing session needs to close

1. **Confidence bar for auto-allow.** A bare `PASS` from a 3B local model
   is probably not sufficient justification on its own to skip human
   confirmation for a command ClaudeWatch already flagged as needing
   one — what additional evidence (repeat-count from the audit log,
   corroboration from a second model, a scoped allowlist of command
   *shapes* known-safe from history) should gate it?
2. **Which mechanism** (Option 1, Option 2, or a third approach not yet
   considered) — investigate real trade-offs rather than assuming.
3. **Regression risk:** phase 1's reviewer audit log is the dataset for
   measuring the real reduction rate before committing to full
   deployment. Benchmark against actual accumulated decisions (mirroring
   phase 1's gitleaks-latency and model-quality benchmarks — don't guess,
   measure) before enabling any auto-allow path by default.
4. **Reversibility:** if an auto-allow path misfires (approves something
   it shouldn't have), what's the blast radius, and how does the human
   find out? Phase 1's answer for the deny path is "the audit log plus
   the deny message itself, immediately." Phase 2 needs an equally
   concrete answer for the allow path, where by definition nothing
   stopped the command from running.

## Explicitly out of scope for this pass

- Any change to Tier 3 (secret scanning) — phase 2 is about Tier
  1/Tier 2 prompt volume specifically.
- Copilot parity (still deferred from phase 1, still unverified).
- Rewriting phase 1's tightening behavior (FAIL → deny) — that path is
  working, verified, and not what this phase is about.

## Success criteria (rough, to be sharpened by the implementing session)

A measurable reduction in gray-zone `ask` prompts for commands that the
accumulated audit log shows were *always* approved historically, without
any observed case of an auto-allowed command that a human would have
denied — measured against real logged data, not estimated from a
worked example the way phase 1's initial 62% figure was.
