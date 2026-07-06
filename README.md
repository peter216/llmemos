# llmemos

**Episodic memory protocol for human-AI working relationships.**

llmemos gives AI assistants genuine continuity across sessions: a cryptographically verified, curated memory system that persists context, reasoning, and relationship history between conversations.

---

## What it does

At the start of each session, the AI:

1. Clones or pulls your private memo corpus repository
2. Verifies that all recent commits are GPG-signed by a trusted key
3. Reads `AGENTS.md` (the memo index) and `taxonomy.yml` (the tag/alias map)
4. Loads the memos you've selected (sticky memos always, plus filtered non-sticky memos)
5. Validates memo content against the protocol's security checks
6. Emits a `[MEMO PROTOCOL: ACTIVE | ...]` log line as its first output

The result: the AI starts the session already knowing who you are, what you've built together, and what happened in past sessions — without re-explaining it.

---

## Two implementation paths

| | Path A — Claude Code | Path B — Claude.ai |
|---|---|---|
| **Entry point** | `~/bin/llmemos` | Claude.ai Project instructions |
| **Instructions file** | `providers/anthropic.claude-code/llmemos-bootstrap.instructions.md` | `providers/anthropic.claude-ai/llmemos-project-instructions.md` |
| **Repo access** | `git clone` / `git fetch` via Bash tool | `verify_repo_state`, `fetch_memos`, `read_repo_file` via gh-mcp |
| **Signature verification** | `git log --show-signature` (local GPG) | gh-mcp server (see `mcp-server/`) |
| **Loading directive** | Appended to system prompt by launcher, or first line of opening message | First line of opening user message, or static default in Project instructions |

---

## Repository layout

```
llmemos/
├── llmemos-protocol.md          ← Canonical protocol spec (source of truth)
├── providers/
│   ├── anthropic.claude-code/
│   │   └── llmemos-bootstrap.instructions.md  ← Path A: copy to ~/.claude/bootstrap/
│   └── anthropic.claude-ai/
│       └── llmemos-project-instructions.md    ← Path B: paste into Claude.ai Project
├── bin/
│   ├── llmemos                  ← Path A: launcher script
│   ├── llmemos-publish          ← Publish a new memo to your corpus (see below)
│   ├── llmemos_logger.py        ← Directive usage logger (called by launcher)
│   └── count-alias-usage.py    ← Utility: tally alias usage from git log
├── mcp-server/                  ← gh-mcp server for Path B (deploy from this directory)
├── docs/
│   └── llm-defense-in-depth/    ← Optional companion, not part of the protocol (see SECURITY.md)
└── corpus-template/             ← Example corpus to fork as a starting point
```

Your personal memo corpus lives in a **separate private repository** that you create and maintain. Fork `corpus-template/` as a starting point.

---

## Getting started

> No automated install script yet — manual steps:

**1. Create your corpus repository**

Fork or copy `corpus-template/` into a new private GitHub repo (e.g. `your-username/my-llmemos`).
It includes a ready-to-edit `AGENTS.md`, `taxonomy.yml`, and example memo files.
See `corpus-template/README.md` for step-by-step instructions.

All commits to your corpus must be GPG-signed.

**2. Install Path A (Claude Code)**

Copy `providers/anthropic.claude-code/llmemos-bootstrap.instructions.md` to `~/.claude/bootstrap/`. Edit to set your corpus repo URL and trusted GPG key fingerprints.

Symlink the launcher:

```bash
ln -s /path/to/llmemos/bin/llmemos ~/bin/llmemos
```

**3. Install Path B (Claude.ai)**

Deploy the gh-mcp server (see `mcp-server/`), register it as an MCP integration in Claude.ai, and paste the contents of `providers/anthropic.claude-ai/llmemos-project-instructions.md` into your Claude.ai Project instructions. Edit to set your corpus repo, trusted fingerprints, and your gh-mcp server URL.

---

## Optional companion: LLM defense-in-depth (command & content safety)

**Not part of the llmemos protocol** — skip this if you only want episodic
memory. Documented here because it emerged from the same working practice
and shares its defense-in-depth philosophy: a three-tiered Claude Code
safety architecture combining a deterministic rule engine (e.g.
ClaudeWatch), a local-LLM semantic reviewer for the gray zone that engine
can't judge, and content-based secret scanning on tool output and prompts.
See [`docs/llm-defense-in-depth/SECURITY.md`](docs/llm-defense-in-depth/SECURITY.md)
for the generic architecture and rationale; `docs/llm-defense-in-depth/phase-1/`
for a worked reference design and `phase-2/` for planned prompt-reduction
work. These docs describe the pattern generically — adapt paths, models,
and thresholds to your own environment.

---

## Trusted GPG keys

All commits to your corpus must be signed by a key listed in the protocol's
`trusted-signing-key-fingerprints`. Edit `llmemos-protocol.md` and your bootstrap
instructions file to list your own keys:

```bash
gpg --list-secret-keys --keyid-format LONG
```

---

## Memo lifecycle (brief)

1. At session close, ask the AI to generate a session memo
2. Review and agree on content collaboratively
3. The AI outputs the file to `memos/` in your corpus repo with `{{ CONVERSATION_TITLE }}`
   as a placeholder for the conversation title
4. Run `llmemos-publish` from your corpus root:

   ```bash
   /path/to/llmemos/bin/llmemos-publish
   # or symlink it: ln -s /path/to/llmemos/bin/llmemos-publish ~/bin/llmemos-publish
   ```

   The script prompts for title, digest, topics, and stickiness; substitutes the
   placeholder; updates the `AGENTS.md` index; shows a diff for review; commits and
   pushes with a GPG-signed commit; and injects `/rename <title>` into the active
   Claude session so the session name matches the memo title.
5. Done — the memo is in your corpus and will load in future sessions.

`llmemos-publish` requires Python 3.8+ and no external packages. Flags:
- `--dry-run` — preview changes without writing anything
- `--no-rename` — skip the session rename step

The AI does not commit to your corpus directly. If you set `agent-write-access:
pull-request` in your `AGENTS.md` frontmatter, the AI may push a branch and open a PR
for your review — but you must GPG-sign the merge commit.

---

## Versioning

This repo tracks **two independent version numbers**, on purpose:

| | Repo version | Protocol version |
|---|---|---|
| **Tracks** | Everything in this repo — tooling, docs, provider implementations, optional companions | Only the bootstrapping protocol's own contract (`llmemos-protocol.md`) |
| **Recorded in** | [`CHANGELOG.md`](CHANGELOG.md) | [`PROTOCOL-CHANGES.md`](PROTOCOL-CHANGES.md) + `llmemos-protocol.md`'s frontmatter `version:` field |
| **Git tags** | `vX.Y.Z`, one series | None — it's a versioned document, not a versioned release artifact |

They matched through `v1.5.0` because every past change happened to touch the
protocol itself. That's a coincidence of history, not a rule — a repo change
that doesn't touch the protocol's contract (e.g. a new optional companion
feature, a tooling fix, a doc improvement) bumps the repo version without
bumping the protocol version, and the two are expected to diverge from here.

If llmemos ever gets external consumers who need to pin against a protocol
version independently of this repo's own release cadence, a second tag series
would be the next step — not needed at the current scale.

---

## License

MIT — see [LICENSE](LICENSE).
