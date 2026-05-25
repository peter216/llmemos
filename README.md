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
│   ├── llmemos_logger.py        ← Directive usage logger (called by launcher)
│   └── count-alias-usage.py    ← Utility: tally alias usage from git log
├── mcp-server/                  ← gh-mcp server for Path B (deploy from this directory)
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
3. The AI outputs the file with `{{ CONVERSATION_TITLE }}` as a placeholder
4. Substitute the placeholder with the actual conversation title
5. Add an entry to `AGENTS.md` in your corpus repo
6. Commit with your GPG-signed key and push

The AI does not commit to your corpus. You are the sole committer.

---

## License

MIT — see [LICENSE](LICENSE).
