# Frontmatter Schema & Document Templates

All markdown files in `content/` use YAML frontmatter for metadata. This schema
is the single source of truth — processing scripts, the MCP server, and the
embedding pipeline all rely on these fields.

---

## Field Reference

### Required Fields (all documents)

| Field | Type | Description |
|-------|------|-------------|
| `title` | `string` | Human-readable title. Contract docs: `"org/repo — filename.ext"`. Overviews: `"org/repo — Overview"`. Patterns: descriptive name. |
| `description` | `string` | One-sentence summary. Used in `llms.txt` entries and search result snippets. |
| `tags` | `list[string]` | Lowercase keywords for filtering and topic indexing. Include org slug, repo slug, and relevant domain terms. |
| `category` | `enum` | Document type: `concept`, `cookbook`, `reference`, `guide`, `ecosystem`, `pattern` |
| `difficulty` | `enum` | Target audience: `beginner`, `intermediate`, `advanced` |
| `sdk` | `list[string]` | Which SDK(s) the doc covers: `fleet-sdk`, `appkit`, `sigma-rust`, `python`, `none` |
| `updated` | `date` | ISO 8601 date (`YYYY-MM-DD`) of last generation or edit. |
| `source` | `enum` | Origin: `auto-generated` (pipeline output), `original` (human-written), `migrated` (from external docs) |

### Project Fields (ecosystem docs)

| Field | Type | Description |
|-------|------|-------------|
| `source_repo` | `string` | GitHub URL: `https://github.com/{org}/{repo}` |
| `project` | `string` | Slugified project ID: `{org}-{repo}` (e.g., `kushti-dexy-stable`) |

### Overview-Only Fields (one per project)

| Field | Type | Description |
|-------|------|-------------|
| `group` | `enum` | Ecosystem sector: `core-protocol`, `sdk`, `defi`, `infrastructure`, `dao`, `analytics`, `reference` |
| `priority` | `enum` | Processing priority: `high`, `medium`, `low` |
| `languages` | `list[string]` | Primary languages: `ergoscript`, `scala`, `typescript`, `rust`, `python`, `javascript`, `kotlin`, `svelte`, `vue`, `java`, `c`, `markdown` |
| `contract_count` | `integer` | Number of ErgoScript contracts found and analyzed. |
| `pattern_match_count` | `integer` | Number of cross-cutting pattern matches found. |

### Contract-Only Fields (one per ErgoScript file)

| Field | Type | Description |
|-------|------|-------------|
| `contract_file` | `string` | Repo-relative path to the source file (e.g., `contracts/bank/bank.es`) |

### Pattern Doc Fields (cross-cutting patterns)

| Field | Type | Description |
|-------|------|-------------|
| `source_repos` | `list[string]` | Repos this pattern was synthesized from: `["org/repo", ...]` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `author` | `string` | Original author (for human-written docs). |
| `ergo_version` | `string` | Ergo protocol version the doc targets (e.g., `"6.0"`). |
| `estimated_tokens` | `integer` | Pre-computed token count for large reference docs. |

---

## Enum Values

```yaml
category:
  - concept        # What things ARE (eUTXO, boxes, sigma protocols)
  - cookbook        # Short recipes (mint token, simple send)
  - reference      # API docs, language spec, EIPs
  - guide          # Long-form tutorials
  - ecosystem      # Per-project docs (overviews + contract analyses)
  - pattern        # Cross-cutting integration patterns

difficulty:
  - beginner       # No prior Ergo knowledge needed
  - intermediate   # Understands boxes, registers, basic ErgoScript
  - advanced       # Multi-stage contracts, protocol internals

source:
  - auto-generated # Output of clone_and_process_repos.py or other pipeline
  - original       # Human-written for the EKB
  - migrated       # Adapted from docs.ergoplatform.com or other sources

group:
  - core-protocol  # ergo node, sigmastate, sigma-rust, EIPs, oracle-core
  - sdk            # fleet-sdk, appkit, python appkit
  - defi           # DEX, stablecoins, lending, options, hodlcoin
  - infrastructure # wallets, bridges, mixers, names, MCP servers
  - dao            # paideia, governance tools
  - analytics      # indexers, explorers, ZMQ publishers
  - reference      # citadel (multi-protocol reference impl)

priority:
  - high           # Core protocol, major dApps, primary SDKs
  - medium         # Active ecosystem projects, secondary SDKs
  - low            # Niche tools, inactive projects
```

---

## Templates

### Concept Document

```yaml
---
title: "eUTXO Model"
description: "How Ergo extends the UTXO model with registers, scripts, and data inputs."
tags: [eutxo, boxes, registers, transactions, concepts]
category: concept
difficulty: beginner
sdk: [none]
updated: 2026-03-05
source: original
---
```

### Cookbook Recipe

```yaml
---
title: "Mint a Token"
description: "Step-by-step recipe to mint a fungible or NFT token on Ergo using Fleet SDK."
tags: [token, mint, eip-4, fleet-sdk, cookbook]
category: cookbook
difficulty: beginner
sdk: [fleet-sdk]
updated: 2026-03-05
source: original
---
```

### Reference Document

```yaml
---
title: "ErgoScript Language Specification"
description: "Complete reference for ErgoScript types, operations, context variables, and predefined functions."
tags: [ergoscript, language-spec, types, contracts, reference]
category: reference
difficulty: advanced
sdk: [none]
updated: 2026-03-02
source: original
author: ahrobe
ergo_version: "6.0"
estimated_tokens: 13250
---
```

### Ecosystem Overview (auto-generated)

```yaml
---
title: "kushti/dexy-stable — Overview"
description: "Dexy stablecoin — oracle-pegged minting, LP, cross-tracker, anti-drain mechanisms"
tags: [kushti, dexy-stable, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
project: kushti-dexy-stable
group: defi
priority: high
languages: [ergoscript, scala]
contract_count: 23
pattern_match_count: 0
---
```

### Contract Analysis (auto-generated)

```yaml
---
title: "kushti/dexy-stable — bank.es"
description: "ErgoScript contract analysis: contracts/bank/bank.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/bank.es
project: kushti-dexy-stable
---
```

### Cross-Cutting Pattern (auto-generated)

```yaml
---
title: "EIP-12 dApp Connector"
description: "EIP-12 dApp Connector — connection API, context API, multi-wallet detection, TypeScript types"
tags: [eip12-dapp-connector, pattern, integration]
category: pattern
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [nautls/nautilus-wallet, ThierryM1212/SAFEW, fleet-sdk/fleet]
---
```

### Guide (long-form tutorial)

```yaml
---
title: "Building Your First dApp on Ergo"
description: "End-to-end guide: ErgoScript contract, Fleet SDK frontend, Nautilus wallet connection."
tags: [tutorial, dapp, fleet-sdk, eip-12, ergoscript, guide]
category: guide
difficulty: intermediate
sdk: [fleet-sdk]
updated: 2026-03-05
source: original
---
```

---

## Conventions

1. **Tags are lowercase, hyphenated.** Use `fleet-sdk` not `Fleet SDK`. Use `eip-12` not `EIP-12`.
2. **One overview per project.** File: `content/ecosystem/{project}/overview.md`.
3. **Contract docs sit under `contracts/`.** File: `content/ecosystem/{project}/contracts/{slug}.md`.
4. **Patterns are top-level.** File: `content/patterns/{pattern-id}.md`.
5. **`source_repo` is singular** (one URL) for single-repo docs. **`source_repos` is plural** (list of `org/repo`) for multi-repo pattern docs. Never use both on the same document.
6. **Dates use ISO 8601** (`YYYY-MM-DD`), no quotes needed in YAML.
7. **Strings containing colons, quotes, or `#`** must be quoted in YAML frontmatter.
