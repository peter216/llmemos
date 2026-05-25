# llmemos Corpus Template

This directory is an example corpus you can fork to create your own llmemos memory
repository. The example content is themed around *The Hitchhiker's Guide to the Galaxy*
to keep it clearly fictional while demonstrating realistic memo format and taxonomy
structure.

---

## What's in here

| File / Dir | Purpose |
|---|---|
| `AGENTS.md` | Protocol metadata, validation anchor, and the memo index |
| `taxonomy.yml` | Canonical tag definitions and named aliases |
| `memos/` | Three example memo files showing realistic format and tone |

---

## How to use this template

**1. Create a new private GitHub repository** — e.g. `your-username/my-llmemos`.

**2. Copy or fork this template** into your new repo. Then:

- Replace the example memos with real ones from your own sessions.
- Update `AGENTS.md` frontmatter — set `canonical-repo` and `canonical-branch`
  to point at your new repo, and update `created`.
- Clear the `## Memo Index` — remove the example entries and add your own as your
  sessions accumulate. (Or start empty and add the first entry after your first
  real session.)
- Rewrite `taxonomy.yml` — replace the HHGTTG-themed tags with ones that reflect
  your actual topics. Keep the structure; change the content.

**3. Set up GPG signing** — all commits to your corpus must be GPG-signed with a key
listed in your bootstrap instructions file. Run:

```bash
gpg --list-secret-keys --keyid-format LONG
```

Copy your fingerprints into `llmemos-protocol.md` (in your llmemos checkout) and into
your bootstrap instructions file.

**4. Make your first signed commit:**

```bash
git commit -S -m "feat: initialize corpus"
git push
```

**5. Install the bootstrap path** — follow the setup steps in the main
[llmemos README](../README.md).

---

## Memo format

Each memo file needs frontmatter that matches the protocol spec. Required fields:

```yaml
---
id: session-memo-001
created: 2026-01-02T12:00:00Z
modified: 2026-01-02T12:00:00Z
conversation: "{{ CONVERSATION_TITLE }}"
topics: [tag-a, tag-b]
---
```

- `conversation` uses a `{{ CONVERSATION_TITLE }}` placeholder. Substitute the actual
  conversation name before committing.
- `sticky` is NOT set in the memo file — it belongs in the `AGENTS.md` index only.
- Use only tags defined in `taxonomy.yml`. Unknown tags generate a warning at load time.
- Write in a narrative, contextual tone — not imperative. If a memo starts reading like
  an instruction, it belongs in your instructions channel instead.

---

## Tone note

The example memos are intentionally written in a personal, reflective voice. This is
deliberate — memos that read like incident reports lose context quickly. The goal is
for the AI to pick up a memo six months later and understand not just what happened but
how you felt about it and what it meant to your working relationship.

The HHGTTG framing is fictional, but the memo structure and voice are exactly what a
real corpus should look like.
