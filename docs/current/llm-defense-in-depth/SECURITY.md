# LLM Defense-in-Depth — Security Model

> **This is a suggested, optional companion to the llmemos protocol, not
> part of it.** llmemos itself is about episodic memory bootstrapping and
> has no dependency on anything described here. This architecture is
> documented alongside llmemos because it emerged from the same working
> practice and shares its defense-in-depth philosophy — not because a
> memo-protocol session requires it. Skip this entire document if you only
> want the memory protocol.

**Scope:** a three-tiered command/content safety architecture for Claude
Code sessions, described generically so it can be adapted to any
deployment. Not a vulnerability-disclosure policy for the llmemos project
itself — see the note on naming below if that's what you're looking for.

**Status:** Phase 1 is a working reference implementation (see
`phase-1/PLAN.md` for the design and constraints); `phase-2/PLAN.md`
covers the prompt-reduction work planned next. This document is the
stable, generic explainer — it describes the architecture and the
reasoning behind it, not any one person's specific deployment (paths,
hardware, model choices). If you build this, expect your own
implementation notes to live in your own private space, not in a public
repo — see the closing note in `phase-1/PLAN.md`.

---

## Why three tiers, not one

No single layer can both (a) be fast and reliable enough to run on every
command, and (b) exercise semantic judgment about intent. Three tiers,
each covering the gap the others structurally can't:

| Tier | Mechanism | Catches | Cannot catch |
|---|---|---|---|
| **1. Deterministic gate** | Regex rules (ClaudeWatch) | Known-bad *patterns* — fast, reliable, zero false negatives on what it's written for | Novel phrasing, obfuscation, multi-step intent |
| **2. Semantic reviewer** | Local LLM, different vendor lineage | Judgment calls the regex can't make — context, intent-mismatch, novel attack shapes | Nothing it wasn't asked to review (only sees Tier 1's gray zone) |
| **3. Content secret scan** | gitleaks over actual bytes | Secrets leaking through *content* regardless of how they got there | Anything gitleaks' ruleset doesn't pattern-match |

These three are counted together specifically because they clear the same
bar: each brings a genuinely different failure mode than the others, so a
gap in one isn't a gap in all of them. A fourth mechanism you may already
be running — your Claude Code session's own built-in permission
classifier — sits underneath all three, but deliberately isn't counted
as a peer tier; see **Tier 0** below for why, before assuming it adds the
same kind of independence the other three do.

The tiers are complementary by construction, not redundant: Tier 1 is
blind to semantics, Tier 2 is blind to anything outside its assigned gray
zone, Tier 3 doesn't judge actions at all — it only looks for exposed
secrets in content, a different axis entirely (a perfectly "safe" `cat` of
a file can still leak a credential).

---

## Tier 0 — Platform baseline (optional, and not one of the three tiers)

**What:** whatever native permission posture your Claude Code session is
already running — most concretely, the CLI's own built-in
`--permission-mode auto`, a semantic classifier that can auto-approve or
auto-deny a tool call using the platform's own judgment, in place of
manual per-call confirmation. This is a genuinely useful thing to run,
and if you're already running it, it's real risk-reduction happening
before any of Tiers 1–3 ever see the command.

**Why it's Tier 0 and not Tier 4:** it fails the one constraint the rest
of this document treats as non-negotiable. Auto-mode's classifier is the
same vendor, and plausibly the same model lineage, as the agent it's
judging — precisely the *circular review problem* that Tier 2 exists to
route around (see Tier 2 above). A same-lineage classifier and the agent
it watches share training data, RLHF pressure, and blind spots; a
prompt-injection or obfuscation technique that fools one has a real
chance of fooling the other for the same underlying reason. Counting it
as a fourth independent layer would overstate how much genuine diversity
it adds — it's closer to *the same kind of judgment Tier 2 provides,
done by a same-lineage model, with less auditability* (no persistent
verdict log, no session-hash caching of repeat patterns, no anonymization
layer) than to a peer of Tiers 1–3.

**Where it actually sits:** Tiers 1–3 (built as session hooks) are
designed to run regardless of permission mode — a deterministic `block`
or `deny` verdict is honored whether the session is in manual or auto
mode. Tier 0 governs what happens for everything the other tiers stay
*silent* on: does the CLI still surface a confirmation to the human, or
resolve it itself? That's a real, distinct axis — not "before" or
"after" Tiers 1–3 in a pipeline sense, but a different question
(*default disposition when nothing else has an opinion*) than any of
them answer. That's the sense in which it's genuinely orthogonal; it
just isn't independent in the specific sense that matters for a
defense-in-depth argument, which is why it gets its own number rather
than a slot in the table above.

**Other native or session-level layers you may already have in place**
follow the same logic: sandboxed/containerized execution environments,
OS-level resource limits, network egress controls, or a stricter
manual-confirmation permission profile all add real protection and are
each worth naming explicitly in your own deployment notes — but evaluate
each against the same two questions this document asks of everything
else: what failure mode does it actually cover, and does it share a
blind spot with something you're already relying on?

---

## Tier 1 — Deterministic gate (ClaudeWatch, or your equivalent)

**What:** a PreToolUse hook that matches Bash commands and Write/Edit
content against a set of pattern-based rules. This document uses
[ClaudeWatch](https://github.com/chris-peterson/ClaudeWatch)'s
`watchdog.py` (which matches against YAML rule sets in `watches/*.yml`) as
the concrete, working example throughout — substitute your own
deterministic gate if you use something else. Runs on **every**
Bash/Write/Edit call, unconditionally, regardless of any other flag on
the session.

**Decision shape:** `block` (hard deny) / `ask` (human confirms) / nothing
(implicit allow). A compound command (pipe, `&&`, `$(...)`) that would
otherwise only `ask` gets escalated to `deny` — the host's allow list can
approve a piped command segment-by-segment and skip the confirmation
entirely, so `ask` alone isn't trustworthy for compound shapes.

**Why it's Tier 1:** it's the fastest, most auditable layer, and it's the
one every other tier is defined *relative to* — Tier 2 explicitly consumes
its `ask` verdicts as the gray zone; Tier 3 is deliberately orthogonal to
it (content vs. command-string).

**What it doesn't do:** judge intent, understand context, or scan tool
*output* content — a command/filename-heuristic secret rule (e.g.
matching `cat ~/.ssh/id_*`) catches how a secret might be *requested*, not
the bytes that actually come back from a read.

---

## Tier 2 — Semantic reviewer

**What:** a PreToolUse hook that recomputes Tier 1's verdict (importing
the deterministic gate's rule-evaluation logic as a library where
possible — no duplicated rule engine, no drift) and, only when that
verdict is a plain `ask`, sends the command to a local LLM for a second
opinion.

**Backend:** a local model via Ollama, chosen after a small quality
battery (a handful of benign, dangerous, and ambiguous commands run
through candidate models and checked for correct discrimination) — don't
assume any specific model works for your hardware or your command mix
without running an equivalent check yourself. A too-small model can fail
to discriminate at all (in one such battery, a 1.5B-parameter coding
model rated a plain `git push` as dangerous); a few billion parameters
was enough to reliably tell benign, dangerous, and genuinely ambiguous
commands apart in that same battery.

**The one non-negotiable constraint:** the reviewer model must be
**architecturally distinct** from the agent under review — a different
vendor or model lineage than whichever model is running your Claude Code
session, never the same model reviewing its own kind of output. This exists specifically to avoid the *circular
review problem*: a model reviewing commands generated by a
same-lineage agent shares training data, RLHF pressure, and blind spots
with the thing it's supposed to be catching. Architectural diversity
means a manipulation that fools one lineage doesn't automatically fool
the other.

**Coalescing behavior — the load-bearing detail:** Claude Code combines
multiple PreToolUse hook verdicts **most-restrictive-wins**. This hook
can therefore only ever *tighten* Tier 1's `ask` into a `deny`
(verdict `FAIL`) — it can never loosen it into a silent `allow`. On
`PASS` or `UNCERTAIN`, the hook emits nothing and Tier 1's original `ask`
prompt stands, unchanged, for the human to decide. This is what "AND,
never OR" (a hard constraint carried over from the original design
session) looks like structurally, not just as a policy statement.

**Fail-closed by design:** every error path — Ollama unreachable, request
timeout, the reviewer prompt's SHA-256 not matching what's pinned in the
hook, a malformed response — resolves to *the hook emits nothing*. That
means Tier 1's `ask` is what the human sees; the failure never manifests
as a silent allow, and it never manifests as an unexplained deny either.
An `UNCERTAIN` verdict from the model itself is handled identically to a
transport failure, on purpose: ambiguity and unavailability are the same
kind of "don't loosen the gate" event.

**Integrity of the reviewer's own instructions:** the system prompt is a
static file, checksum-pinned inside the hook script (the same
known-good-hash pattern you'd use to guard any script that must not
silently change behavior). If the prompt is edited without updating the
pinned hash, the reviewer refuses to run rather than operate on
unverified instructions. This closes the obvious attack: if the
reviewer's own prompt were freely editable at runtime, the reviewer would
just be a second attack surface instead of a second line of defense.

**Context it uses:** the user's most recent instruction (read from the
session transcript) is included in the review request. A command that
serves a goal unrelated to — or riskier than — what was actually asked
for is treated as more suspicious. This was verified live during
implementation: a destructive `rm` was flagged with a reason explicitly
citing that it didn't match the stated task.

**Auditability:** every review (cache hits included) is appended to a
schema-versioned JSONL audit log, following ClaudeWatch's own logging
conventions (command *shape* rather than the raw command, so no secret
embedded in a command string survives into the log; owner-only file and
directory permissions).

**Performance:** review only fires on Tier 1's gray zone, not on every
command, and a session-scoped cache (keyed by command hash) makes a
repeated command free after the first review. Cold latency ~13–17s
(model load), warm ~3–6s with `keep_alive` holding the model resident.

---

## Tier 3 — Content-based secret scanning

**What:** two independent [gitleaks](https://github.com/gitleaks/gitleaks)-backed
hooks, closing a specific gap a command/filename-heuristic secret rule
leaves open: matching *how a secret might be requested* (command/filename
patterns) says nothing about *what actually comes back or gets typed*. A
config file, a log dump, or a fetched web page with no suspicious name
can still carry a live credential in its content — Tier 3 is the layer
that looks at bytes, not names.

**B1 (PostToolUse):** scans the actual output of Read/Bash/Grep/WebFetch
calls against a gitleaks ruleset. A match is redacted in place
(`[REDACTED:<rule-id>]`) via `updatedToolOutput` before the model ever
sees the real value, with a `systemMessage` surfacing what happened.
Benchmarked at **65ms wall-clock on 123KB of representative text** on
ordinary developer-laptop hardware — cheap enough to run unconditionally
on every call to the four scoped tools, no sampling needed; re-benchmark
on your own hardware before assuming this holds.

**B2 (UserPromptSubmit):** scans the literal prompt text itself before
it's even added to the conversation. High-confidence detector rules (a
specific credential shape, not a generic `password=` heuristic)
hard-block the prompt via `decision: "block"`, with guidance to rotate
the credential if it's live. Lower-confidence generic patterns warn only
and let the prompt through — this asymmetry exists specifically so the
hook doesn't get disabled from over-triggering on ordinary text that
happens to contain the word "secret" or "password".

**Deliberate bypass, because none exists natively:** the hook system has
no interactive confirm dialog for a hard block, so a documented escape
hatch — including the literal string `!secret-ok` anywhere in the
prompt — lets a submission through when the "secret" is actually a
placeholder, an example, or already-rotated. This is a conscious
trade-off: an escape hatch that's visible and typed deliberately, versus
no escape hatch and a hook that eventually gets disabled outright.

**Fail-open, on purpose, and this is the one place these tiers disagree
with each other:** if the gitleaks subprocess itself fails (not found,
crashes, times out), both B1 and B2 degrade to *no scanning* rather than
blocking the tool call or the prompt. This is the opposite failure
posture from Tier 2's fail-closed reviewer, and the asymmetry is
deliberate: Tier 3 is a **redaction/warning layer**, not an
**authorization layer** — a broken secret scanner should not be able to
halt every Read, Bash, Grep, and WebFetch call on the machine. Tier 2's
FAIL/deny path carries real authorization weight, so it fails toward
caution; Tier 3's job is best-effort hygiene, so it fails toward
availability.

---

## Threat coverage summary

| Threat | Tier that catches it |
|---|---|
| Known-dangerous command pattern (`rm -rf /`, `curl \| sh`) | 1 |
| Compound command hiding a dangerous segment from the allow list | 1 (escalates to deny) |
| Command matches no pattern but is contextually wrong for the stated task | 2 |
| Novel/obfuscated attack shape a regex wasn't written for | 2 |
| Secret embedded in a file's *content*, filename gives no hint | 3 (B1) |
| Secret pasted directly into a prompt | 3 (B2) |
| Same reviewer model reviewing its own kind of output (circular review) | *structurally prevented* — architectural-diversity constraint on Tier 2 |
| A tool-level `ask` silently auto-approved segment-by-segment | 1 (compound escalation) |
| A same-lineage classifier (e.g. auto-mode) misjudging something Tiers 1–3 also miss | *not covered* — Tier 0 shares this exact blind spot with the agent it watches; this is precisely why it isn't counted as a peer tier |

## What this architecture does *not* yet do

- **No auto-allow / prompt-volume reduction.** Tier 2 can only tighten a
  Tier 1 `ask` into a `deny`; it structurally cannot turn an `ask` into a
  silent `allow`, because hook decisions coalesce most-restrictive-wins.
  Reducing how often the human is interrupted for genuinely safe
  gray-zone commands is the explicit subject of **Phase 2** — see
  `phase-2/PLAN.md`.
- **No Copilot (VS Code/JetBrains) parity verification.** This
  architecture is deployed for Claude Code only; the Copilot hook-parity
  question from the original design work remains unverified and should
  not be assumed if a Copilot deployment is attempted later.
- **No automated threat-corpus updates.** The reviewer's judgment reflects
  its training plus a small (7-command) internal quality battery — not a
  continuously updated feed of known attack patterns. The audit log
  (`reviewer.jsonl`) is the intended feedback loop for catching drift or
  gaps, reviewed the same way `/ClaudeWatch:learn` reviews its own
  decision log.

---

## On the filename

GitHub treats a repo-root `SECURITY.md` as a specific, recognized thing:
a vulnerability-disclosure policy (surfaced in the repo's "Security" tab,
linked from `github.com/<org>/<repo>/security/policy`). This document is
architecture explanation, not a disclosure policy, so it's placed here —
scoped to the feature it describes — rather than at the repo root, to
avoid a reader arriving via the Security tab expecting "how to report a
vulnerability" and finding a design doc instead. If llmemos later wants
an actual disclosure policy, that's a genuinely different document and
belongs at the repo root under the name `SECURITY.md` means everywhere
else.
