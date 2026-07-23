# Protocol Changes

This file tracks changes to the **llmemos bootstrapping protocol
specification itself** — the contract defined in `llmemos-protocol.md`
(corpus structure, signature verification rules, memo-loading directives,
validation scoring, session-log format, and everything else a provider
implementation must honor to be protocol-compliant).

It is a narrower, slower-moving log than [`CHANGELOG.md`](CHANGELOG.md),
which tracks *everything* in this repo — tooling, docs, provider
implementations, and optional companions. A change can appear in
`CHANGELOG.md` without appearing here (most repo changes don't touch the
protocol's actual contract); a change here will always also appear in
`CHANGELOG.md`, cross-referenced by repo tag.

**Versioning:** this file's version numbers are the same ones recorded in
`llmemos-protocol.md`'s frontmatter (`version:` field) — that field is the
source of truth for "what protocol version does this document currently
describe," and this file is the history of how it got there. There is no
separate git tag series for protocol versions; each entry below names the
repo tag that first shipped it, which is sufficient to check out the exact
state of the spec at that protocol version.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
conventions, adapted for a spec rather than a release artifact.

---

## [Unreleased]

### Changed

- **Path A, Method step 1 (clone/recovery)** — added a remote-reachability check
  (`git ls-remote --exit-code`) before removing a stale session mirror. `rm -rf` has
  no partial-failure state, so running it before confirming the remote responds could
  leave a session with no mirror at all on a network failure, instead of the
  stale-but-intact one a failed `fetch` would have preserved. On a failed reachability
  check, the removal is skipped and the existing mirror is left untouched; the session
  proceeds per the general retrieval-error handling. Also dropped this step's original
  rationale wording ("avoids commonly-flagged destructive-git-command confirmation
  prompts"), which read as designing the recovery path around confirmation gates
  rather than around actual recoverability — caught by an independent review pass on
  the corresponding change in the provider implementation, then found to also be
  present in the spec's own prose.
- **Public-template vs. deployment trust boundary, clarified** — the credential-shaped
  rows in the sync table ("Trusted key fingerprints," etc.) previously read as
  requiring byte-identical values between this public template and a personalized
  deployment file. Reworded to make explicit that "must match" means a faithful,
  deliberate instantiation of the same contract, not identical example credentials —
  placeholder values in this document are the expected state of an unpersonalized
  template, not a historical-coherence discrepancy against a real deployment. Added a
  callout near the frontmatter and a "Verifying this protocol is genuine" note
  clarifying what actually would warrant a Step 4 flag (the deployment file's own
  values looking wrong, or structural disagreement between the two documents) versus
  what wouldn't (placeholders here, untouched).

---

## [1.5.0] — first shipped in repo `v1.5.0`

### Added

- **Content-emission integrity chain** — the bootstrap protocol (Path A) invokes
  `llmemos_select.py --emit-file` to assemble every selected memo/section into one
  file, replacing N per-entry Read calls with a single Read. Trust chain: script
  SHA-256 checksum verified before invocation; `emit_sha256` verified against the
  emitted file; commit-stamped output path; per-entry provenance comments;
  mandatory random spot-check against the verified repo clone each session.
  Degrades gracefully to per-entry Read behavior on checksum/hash mismatch rather
  than aborting. Documented in `llmemos-protocol.md` under "Content-Emission
  Integrity (Path A)."

---

## Baseline note

This file starts tracking independently as of protocol v1.5.0. Protocol-relevant
history before this point is interleaved with repo/tooling history in
`CHANGELOG.md`'s earlier entries (v1.0.0 through v1.4.0) rather than reconstructed
here — the split happened at v1.5.0, not before it, so earlier entries were never
classified against this narrower scope. If a past entry's protocol-relevance ever
needs to be looked up, `CHANGELOG.md` remains the authoritative record for that
period.
