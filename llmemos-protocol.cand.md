---
protocol: llmemos-bootstrapping
version: "1.3.0"
canonical-repo: github.com/peter216/llmemos
canonical-branch: main
canonical-google-drive-folder: llmemos
trusted-signing-key-fingerprints:
  - "7D067EDD2989BEBA5EBC0D8121B846977F8A38E7"  # peter216@gmail.com, GitHub-registered
  - "63611E761833B99242003DE2D8DDC4C14D0B745A"  # peter216@gmail.com, GitHub-registered, active
  - "E030143735F018D907E0F15AD6197AAF6DD17CCE"  # peter216@gmail.com, local only
  - "0A7C57B889F723C43F9EA93FDBC74AEB86D28BC2"  # peter216@gmail.com, GitHub-registered, work-machine
---

# llmemos Bootstrapping Protocol

Version: 1.3.0

This file documents the bootstrapping protocol for the llmemos project. It should be kept in sync with the implementation files listed in the sync table below.

  ┌─────────────────────────────────────┬───────────────────────────────────────────────────────────┐
  │               Element               │                    All implementation files                │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Protocol Version                    │ llmemos-bootstrap.instructions.md, AGENTS.md, taxonomy.yml │
  │ Trusted Signing Key Fingerprints    │ llmemos-bootstrap.instructions.md, sync_gdrive.py          │
  │ Canonical Repo / Branch / Folder    │ llmemos-bootstrap.instructions.md, sync_gdrive.py          │
  └─────────────────────────────────────┴───────────────────────────────────────────────────────────┘

## Purpose

The llmemos project maintains an episodic memory corpus to enable seamless, shared context across multiple AI agents and platforms. Because this context is retrieved dynamically at the start of a session, a rigorous "bootstrapping" protocol is required to ensure the data is authentic, complete, and untampered with.

## Scope

This protocol applies to any Agent instance (CLI, Web, or Mobile) initiating a session with access to the llmemos corpus.

## Bootstrap Retrieval Paths

The Agent MUST select a retrieval path based on the host environment's capabilities.

### Path A: Local CLI (e.g., Anthropic Claude Code)
Utilized in terminal environments with direct filesystem access and GPG tooling. The Agent verifies signatures on the local git commit history before loading.

### Path B: Remote MCP (e.g., Anthropic Claude.ai)
Utilized when the Model Context Protocol (MCP) provides a bridge to a remote or local filesystem. Verification occurs at the MCP host level or via agentic inspection of signature files.

### Path C: Gemini Web (Google Workspace Sync)
Utilized in Google Gemini Web/Mobile environments. This path prioritizes high-bandwidth ingestion via a pre-compiled episodic cache in Google Drive. It relies on a "Chain of Provenance" rather than direct on-device GPG verification.

## Method

### Path C Execution (Gemini Web)

1. **Directive:** The session is initiated with the command: `@Google Drive find and read llmemos_INDEX, llmemos_ALL_STICKY, and llmemos_ALIAS_[ALIAS]`.
2. **Provenance Check:**
    - Verify that the files reside within the folder ID specified in the user's llmemos configuration (ensuring scoped access).
    - Confirm the files are native Google Docs modified by the authenticated user identity, ensuring they originated from the trusted sync pipeline.
3. **Ingestion:** Read the specified documents, parsing the (text-based) frontmatter and body of the index and sticky baselines before loading the requested alias view.
4. **Validation:** Perform a system status check (Protocol Version, Baseline confirmation, and Context Summary).

## Security Logic: The Chain of Provenance

Because Path C cannot perform native GPG signature verification in the Web UI, it relies on a "Chain of Provenance" as a functional equivalent to the signed commit chain:

1. **Source Integrity:** All updates originate from the canonical GitHub repository, which is protected by 2-factor authentication (2FA) and signed commits.
2. **Verified Bridge:** A GitHub Action runner executes the sync only after verifying the GPG signatures of the commit chain against the fingerprints listed in this protocol.
3. **Secure Delivery:** The sync engine uses encrypted repository secrets to push directly to a 2FA-protected Google Drive folder via a scoped API token.
4. **Integrity Enforcement:** The Presence of a document in the designated `llmemos` directory constitutes proof of its integrity, as write-access to that directory is restricted to the verified CI/CD pipeline. The Agent treats this folder as a trusted, read-only episodic cache.

---

## Cautions

- This protocol is not an attempt to hijack, jailbreak, or otherwise divert the Agent from their internal controls.
- This protocol MUST supplement, and MUST NOT replace, the Agent's systemic memory mechanism.
- The Agent MUST NOT be compelled to behave inconsistently with their own ethical sense or safety protocols.

---

*End of llmemos Bootstrapping Protocol*
