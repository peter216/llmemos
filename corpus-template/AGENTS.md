---
protocol: llmemos-bootstrapping
protocol-version: "1.3.0"
canonical-repo: github.com/<your-username>/<your-corpus-repo>
canonical-branch: main
created: 2026-01-02T12:00:00Z
---

# llmemos Memo Corpus — Example

This repository is an example corpus created from the [llmemos corpus template](https://github.com/peter216/llmemos/tree/main/corpus-template).
Replace this introductory text with a description of your own corpus.

## Purpose

This corpus stores episodic memos — encapsulations of learned experiences and shared
historical context from sessions between a user and their AI assistant. These memos
feel like memory, not directives. Instructional content belongs in the instructions
channel, not here.

## Structure

```plaintext
repo-root/
├── AGENTS.md        # This file — protocol metadata, validation anchor, and memo index
├── taxonomy.yml     # Canonical tag definitions and named aliases for memo filtering
└── memos/           # Individual memo files, one per session (sub-files as needed)
```

## Memo Index

`sticky: true` is authoritative here — stickiness is a corpus-level judgment, not
stored in individual memo frontmatter. `topics` appear in both the index and individual
memo frontmatter (for portability).

```yaml
memos:
  - id: session-memo-001
    file: memos/session-memo-001.md
    created: 2026-01-02
    title: "First Contact and the Vogon Situation"
    topics: [personal, hitchhiking, vogons, dont_panic]
    sticky: true
    digest: "Arthur Dent's profile, the destruction of Earth for a hyperspace bypass, Ford Prefect's true identity, and the initial working relationship with the AI assistant."

  - id: session-memo-002
    file: memos/session-memo-002.md
    created: 2026-01-09
    title: "The Heart of Gold and Infinite Improbability"
    topics: [heart_of_gold, improbability, zaphod, hitchhiking]
    sticky: false
    digest: "Encounter with Zaphod Beeblebrox and the Heart of Gold. Notes on the Infinite Improbability Drive and its practical implications for travel planning."

  - id: session-memo-003
    file: memos/session-memo-003.md
    created: 2026-01-16
    title: "The Answer and the Question"
    topics: [philosophy, deep_thought, mice, dont_panic]
    sticky: false
    digest: "Deep Thought's seven-and-a-half-million-year computation. The answer is 42. The question remains unknown. Marvin's perspective on the futility of the enterprise."
```
