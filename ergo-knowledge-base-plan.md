# Ergo Developer Knowledge Base: Consolidated Architecture & Implementation Plan

## The Core Question: What Do Humans Build vs. What Do Machines Process?

The short answer: **humans build the scaffolding and babysit the video pipeline (~30% of effort), machines fill in the building (~70%).** The human work splits into two tracks: (1) upfront scaffolding — repo structure, Telegram processing script, ecosystem code extraction pipeline, templates, glossary — and (2) the semi-automated video pipeline that requires 3-4 hours of human attention per batch of 50 videos (speaker assignment review, spot audits) across 9 batches. Once scaffolding is in place, LLM pipelines and GitHub Actions handle the Telegram summarization, ecosystem contract documentation, embedding generation, topic extraction, and ongoing indexing.

The critical insight is that every hour spent on scaffolding saves 50+ hours of manual documentation work. A well-designed template means an LLM can process 100 Telegram months in the time it would take a human to manually summarize 2. The video pipeline — already built — handles the transcription and summarization, though speaker verification keeps humans in the loop at ~3-4 hours per 50-video batch. An existing ErgoScript language spec (Ahrobe's LangSpec.md, ~1,350 lines) gives the reference section a significant head start. And the ecosystem code catalog — 51 open source repos covering every major Ergo dApp — has been automatically processed into 242 documented contract analyses, 14 cross-cutting pattern guides, and integration references for ~$5 in LLM costs.

---

## Human Work (One-Time Setup, ~2 Weeks of Active Work)

*Video processing pipeline already exists. Telegram pipeline already complete (102 general months + 51 dev months, 2017–2026). The remaining human work focuses on repo scaffolding, ecosystem repo processing, seed content, and the MCP server.*

### 1. Repository Structure & Templates

**Why humans:** The directory structure IS the retrieval architecture. Bad structure = bad search results forever. An LLM can't decide whether ErgoScript contracts should live under `sdk/` or `smart-contracts/` — that requires ecosystem knowledge.

**What to build:**

```
ergo-knowledge-base/
├── llms.txt                          # AI discovery index
├── llms-full.txt                     # Auto-generated full context dump
├── manifest.yaml                     # Machine-readable structure map
├── README.md
│
├── glossary/                         # ── GLOSSARY (three-tier, single source of truth) ──
│   ├── ergo_glossary.yaml            # MASTER — 126 terms, 17 categories, 544 aliases
│   │                                 #   ~15K tokens. Hand-curated. Edit only this file.
│   │                                 #   Sources: docs.ergoplatform.com, ergonaut.space,
│   │                                 #            awesome-ergo (glasgowm148), ergodocs chat
│   ├── ergo_glossary_compact.yaml    # GENERATED — term + 6 aliases + 1-sentence def + category
│   │                                 #   ~7K tokens. Inject into Telegram/video pipelines.
│   ├── ergo_aliases.yaml             # GENERATED — 544 lowercase alias→canonical pairs
│   │                                 #   ~4K tokens. For term normalization & query expansion.
│   └── ergo_aliases.json             # GENERATED — same map as JSON (Fleet SDK / JS consumers)
│
├── content/
│   ├── concepts/                     # What things ARE
│   │   ├── _index.md                 # Section overview
│   │   ├── eutxo-model.md
│   │   ├── boxes-and-registers.md
│   │   ├── sigma-protocols.md
│   │   ├── storage-rent.md
│   │   ├── nipopows.md
│   │   ├── autolykos.md
│   │   ├── avl-trees.md
│   │   └── transaction-model.md
│   ├── cookbook/                     # How to DO things (short recipes)
│   │   ├── tokens/
│   │   │   ├── mint-token.md
│   │   │   ├── transfer-token.md
│   │   │   └── burn-token.md
│   │   ├── contracts/
│   │   │   ├── simple-send.md
│   │   │   ├── multi-sig.md
│   │   │   ├── timelock.md
│   │   │   └── state-machine.md
│   │   └── apis/
│   │       ├── node-rest-basics.md
│   │       ├── graphql-queries.md
│   │       └── explorer-api.md
│   ├── guides/                       # Long-form tutorials
│   │   ├── ergoscript-fundamentals/  # ✅ DeCo Education adapted series (MIT, attributed)
│   │   │   ├── 01-boxes-registers-context.md   # Syntax, types, SigmaProp, SELF/INPUTS/OUTPUTS
│   │   │   ├── 02-guard-script-framework.md    # Box-focused contract design methodology
│   │   │   └── 03-offchain-appkit.md           # Transaction building with Ergo AppKit
│   │   ├── first-dapp/
│   │   ├── building-a-dex/
│   │   └── writing-an-offchain-bot/
│   ├── reference/                    # API docs, built-ins, EIPs
│   │   ├── node-api/
│   │   │   └── endpoints/            # One file per endpoint
│   │   ├── explorer-api/
│   │   ├── graphql-schema/
│   │   ├── avl-tree-rust/             # Rust AVL+ tree implementation
│   │   ├── ergoscript-by-example/     # 13 annotated ErgoScript contract examples
│   │   ├── eips/                     # One file per EIP (auto-generated from ergoplatform/eips)
│   │   │   ├── eip-0004.md           # Asset standard
│   │   │   ├── eip-0012.md           # dApp connector
│   │   │   ├── eip-0020.md           # ErgoPay
│   │   │   ├── eip-0022.md           # Auction standard
│   │   │   ├── eip-0023.md           # Oracle pool v2
│   │   │   ├── eip-0024.md           # Artwork standard (NOT Babel Fees — that's EIP-31)
│   │   │   ├── eip-0027.md           # Re-emission
│   │   │   ├── eip-0028.md           # ErgoAuth
│   │   │   ├── eip-0031.md           # Babel fees
│   │   │   ├── eip-0034.md           # NFT collections
│   │   │   └── eip-0041.md           # Stealth addresses
│   │   └── ergoscript/
│   │       ├── language-spec.md      # Ahrobe's LangSpec — already exists
│   │       ├── built-in-functions.md
│   │       ├── types.md
│   │       └── context-variables.md  # SELF, INPUTS, OUTPUTS, HEIGHT, getVar
│   ├── node/                         # Node operation (new section — discovered in research)
│   │   ├── modes.md                  # Archival, Pruned, Digest, Light SPV
│   │   ├── bootstrapping.md          # utxoBootstrap, nipopowBootstrap, UTXO snapshots
│   │   ├── configuration.md
│   │   └── api-overview.md
│   ├── privacy/                      # Privacy section (new — significant ecosystem area)
│   │   ├── ergomixer.md              # ZeroJoin, non-interactive mixing
│   │   ├── stealth-addresses.md      # EIP-41
│   │   ├── covert-addresses.md
│   │   └── sigma-protocols-zkp.md
│   ├── sdks/                         # Per-SDK docs + examples, nested by SDK
│   │   ├── fleet-sdk/                # TypeScript/JS — primary web SDK
│   │   │   └── examples/             # Runnable code snippets
│   │   ├── appkit/                   # JVM (Java/Scala/Kotlin/Android)
│   │   │   └── examples/
│   │   ├── sigma-rust/               # Rust + WASM
│   │   ├── fleetsharp/               # C#/.NET
│   │   ├── rustkit/                  # Community Rust SDK
│   │   ├── python/
│   │   │   ├── ergo-lib-python.md    # Recommended: direct sigma-rust bindings
│   │   │   └── ergpy.md              # Older JPype-based wrapper
│   │   ├── ergo-node-interface-rust/  # Rust node interaction library
│   │   ├── ergo-utilities-rust/      # Off-chain Rust utilities
│   │   ├── mosaik/                   # UI framework for mobile dApps
│   │   └── sigma-js/                 # ErgoScript compiler (JS/WASM via Scala.js)
│   └── ecosystem/                   # dApp docs (auto-generated from repos)
│       ├── _index.md                 # Ecosystem overview
│       ├── spectrum-dex/             # AMM DEX (formerly ErgoDEX)
│       │   ├── overview.md
│       │   ├── contracts/
│       │   └── backend-bots.md
│       ├── dexy/                     # Oracle-pegged stablecoin
│       ├── sigmausd/                 # AgeUSD stablecoin
│       ├── duckpools/                # Pool-based lending
│       ├── sigmafi/                  # P2P bonds / yield
│       ├── sigma-o/                  # Options trading
│       ├── phoenix-hodlcoin/         # Proof-of-hodl
│       ├── chaincash/                # Note-based monetary system
│       ├── mew-finance/              # DeFi suite
│       ├── gluon/                    # Djed-style cross-chain stablecoin
│       ├── exle/                     # Decentralized lending
│       ├── ergo-raffle/              # Crowdfunding / raffle
│       ├── off-the-grid/             # Grid trading dApp
│       ├── ergomixer/                # Privacy mixer (ZeroJoin)
│       ├── rosen-bridge/             # Cross-chain bridge
│       ├── oracle-pools/             # Price feed infrastructure
│       ├── paideia/                  # DAO platform
│       ├── ergopad/                  # IDO launchpad
│       ├── skyharbor/                # NFT marketplace
│       ├── auction-house/            # NFT auctions (EIP-22/24/34)
│       ├── lilium/                   # NFT minting suite
│       ├── ergo-names/               # Decentralized domain names
│       ├── crux-finance/             # Portfolio analytics
│       ├── danaides/                 # Blockchain indexer
│       ├── machina-finance/          # Off-chain bot platform
│       └── citadel/                  # Multi-protocol reference client
│
│   └── patterns/                    # Cross-cutting frontend/backend patterns
│       ├── eip12-dapp-connector.md
│       ├── ergopay-signing.md
│       ├── ergoauth-authentication.md
│       ├── transaction-building.md
│       ├── box-selection.md
│       ├── offchain-bots.md
│       ├── headless-dapp.md
│       ├── onchain-state-tracking.md
│       ├── constant-segregation.md   # substConstants pattern for contract templates
│       ├── state-machine.md          # Box replacement / singleton NFT pattern
│       ├── babel-fees.md             # EIP-31 — pay tx fees in non-ERG tokens
│       └── grid-trading.md           # On-chain grid order contracts
│
├── forum/                           # ✅ ErgoForum archive (Discourse scrape, curated 677 topics)
│   ├── .gitignore                    # Excludes raw/ JSON cache
│   ├── forum-index.md                # Category + glossary-tag clustered index (top 25/category)
│   └── topics/                       # Markdown per topic, organized by category
│       ├── announcements/
│       ├── dev/
│       ├── community/
│       ├── mining/
│       └── uncategorized/
│
├── blog/                            # ✅ Ergo Platform blog archive (Strapi CMS, 695 posts)
│   ├── .gitignore                    # Excludes raw/ JSON cache
│   ├── blog-index.md                 # Tag + year + glossary-tag clustered index (top 10/tag)
│   ├── posts/                        # Full-content posts by blog tag
│   │   ├── core/
│   │   ├── tooling/
│   │   ├── ecosystem/
│   │   ├── events/
│   │   ├── mining/
│   │   └── ...                       # 20 tag-based subdirectories
│   └── stubs/                        # External-URL-only posts (mostly Medium)
│       ├── announcements/
│       ├── events/
│       └── ...
│
├── telegram/                         # LLM-processed chat archives
│   ├── summaries/
│   │   ├── main-chat/                # 2017-01.md through 2026-02.md (102 months)
│   │   └── dev-chat/                 # 2021-01.md through 2026-02.md (51 months)
│   ├── topics/
│   │   └── topic-index.md            # Cross-month topic map
│   └── segments/                     # Weekly conversation chunks (Tier 2)
│
├── video-content/                    # LLM-processed transcripts
│   ├── amas/
│   ├── dev-updates/
│   ├── presentations/
│   └── index.md
│
├── mcp-server/                       # MCP server source
│   ├── server.py
│   ├── tools/
│   └── config.yaml
│
├── scripts/                          # Processing pipelines
│   ├── generate_glossary_tiers.py    # ✅ BUILT — derives compact + alias tiers from master
│   ├── telegram-pipeline/            # ✅ BUILT — 5 scripts, copied from ~/ergo-telegram/pipeline
│   │   ├── process_telegram.py       #   Weekly segment processor
│   │   ├── generate_monthly.py       #   Rolls weekly → monthly summaries
│   │   ├── batch_api.py              #   Anthropic batch API client
│   │   ├── claude_prompts.py         #   Prompt templates
│   │   └── generate_index.py         #   Topic index builder
│   ├── adapt_video_output.py         # Adapter for existing video pipeline
│   ├── clone_and_process_repos.py    # Ecosystem code extraction + LLM docs
│   ├── scrape_ergoforum.py           # ✅ BUILT — Discourse API scraper (350 lines)
│   ├── scrape_ergo_blog.py           # ✅ BUILT — Strapi CMS API scraper (290 lines)
│   ├── build_topic_index.py          # ✅ BUILT — cross-month topic map
│   ├── generate_embeddings.py
│   ├── generate_llms_txt.py
│   └── ecosystem_repos.yaml          # Catalog of 55 repos to process
│
├── vectordb/                         # LanceDB data (file-based, lives in repo)
│   └── .gitkeep
│
└── .github/
    └── workflows/
        ├── update-embeddings.yml
        ├── generate-llms-txt.yml
        └── process-new-content.yml
```

**Glossary tier decision guide:**

| Use case | File to inject |
|---|---|
| Telegram / video LLM summarization | `ergo_glossary_compact.yaml` (~7K tokens) |
| Search query expansion | `ergo_aliases.yaml` or `.json` (~4K tokens) |
| Topic extraction / tagging | `ergo_glossary_compact.yaml` — includes category field |
| MCP agent deep reasoning | `ergo_glossary.yaml` master (~15K tokens) |
| WhisperX transcription prompt | Extracted `whisper_prompt` field (see Section 3) |
| JS/TS runtime normalization | `ergo_aliases.json` |

**Regenerate derived tiers any time master changes:**
```bash
python3 scripts/generate_glossary_tiers.py
# Validates for alias collisions, prints token counts per tier
```

### 2. Document Templates & Frontmatter Schema

**Why humans:** The frontmatter schema determines what metadata is available for filtering during retrieval. Get this wrong and your RAG system can't distinguish a beginner tutorial from an advanced API reference.

**Standard frontmatter for every document:**

```yaml
---
title: "Minting tokens with Fleet SDK"
description: "Step-by-step guide to minting custom tokens on Ergo using Fleet SDK"
tags: [tokens, minting, fleet-sdk, typescript]
category: cookbook          # concept | cookbook | reference | guide | ecosystem
difficulty: beginner       # beginner | intermediate | advanced
sdk: [fleet-sdk]           # fleet-sdk | appkit | sigma-rust | python | none
updated: 2026-02-01
estimated_tokens: 680      # LLM agents budget context windows with this
prerequisites:
  - concepts/boxes-and-registers
  - sdks/fleet-sdk/getting-started
ergo_version: "5.0"
source: original           # original | migrated-from-docs | telegram-derived | video-derived
---
```

**Telegram summary frontmatter:**

```yaml
---
title: "Ergo Main Chat Summary — March 2023"
type: monthly_summary
chat: main                 # main | dev
date_range: [2023-03-01, 2023-03-31]
message_count: 4287
active_participants: [kushti, morphic, scalahub, greenhat, ...]
key_topics:
  - sub-blocks discussion
  - sigma-rust v0.24 release
  - oracle pool v2 design
  - storage rent optimization
unresolved_questions:
  - "How should sub-block ordering handle conflicting transactions?"
important_links:
  - url: https://github.com/ergoplatform/eips/pull/47
    context: "Sub-blocks EIP draft"
segment_files:             # Links to Tier 2 weekly detail
  - segments/main-chat/2023-W09.md
  - segments/main-chat/2023-W10.md
  - segments/main-chat/2023-W11.md
  - segments/main-chat/2023-W12.md
  - segments/main-chat/2023-W13.md
estimated_tokens: 1200
---
```

**Video transcript frontmatter:**

```yaml
---
title: "Ergo Summit 2023 — kushti on Sigma Protocols"
type: video_transcript
date: 2023-09-15
speakers: [kushti, morphic]
duration_minutes: 47
source_url: https://youtube.com/watch?v=XXXXX
topics: [sigma-protocols, zero-knowledge-proofs, privacy]
category: presentation
has_full_transcript: true
summary_tokens: 450
full_transcript_tokens: 8200
---
```

### 3. The Ergo Glossary / Terminology File

**Why humans:** This is THE most leveraged artifact in the entire project. Every LLM pipeline — Telegram summarization, video transcription, topic extraction, even search query expansion — uses it. It must be hand-curated by someone who knows the ecosystem.

**Status: ✅ COMPLETE.** The glossary has been built and lives at `glossary/` in the EKB folder alongside the derived tier files. Do not edit the generated files directly — only edit the master and regenerate.

**Files:**
- `glossary/ergo_glossary.yaml` — master, 126 terms, 17 categories, 544 alias→canonical pairs, ~15K tokens. Sources: docs.ergoplatform.com, ergonaut.space, awesome-ergo (glasgowm148).
- `glossary/ergo_glossary_compact.yaml` — generated, ~7K tokens, for pipeline injection
- `glossary/ergo_aliases.yaml` / `ergo_aliases.json` — generated, ~4K tokens, for term normalization
- `scripts/generate_glossary_tiers.py` — regenerates compact + alias tiers, validates collisions

**Entry structure** (master format):
```yaml
  - term: Storage rent
    aliases:
      - demurrage
      - storage fee
      - storage rent fee
      - box rent
    definition: >
      A fee mechanism charging for long-term UTXO storage on the blockchain,
      unique to Ergo among major chains. After 4 years without being spent,
      a box can be garbage-collected by miners. Prevents state bloat and
      ensures long-term economic sustainability.
    category: protocol
    docs_url: https://docs.ergoplatform.com/mining/rent/
```

**Categories in use:** `protocol`, `development`, `cryptography`, `mining`, `defi`, `infrastructure`, `sdk`, `standard`, `pattern`, `governance`, `nft`, `token`, `analytics`, `node`, `wallet`, `privacy`, `tool`

**Notable corrections from original stub:** EIP-24 is the NFT Artwork Standard — Babel Fees is EIP-31. The original plan had this backwards; the master glossary is correct.

**Whisper initial_prompt** (feed into existing video pipeline — extract from master or use this):
```
Discussion about Ergo blockchain, ErgoScript smart contracts, eUTXO model,
Sigma protocols, SigmaProp, proveDlog, ZeroJoin, ErgoMixer, SigmaUSD, AgeUSD,
SigRSV, Dexy, GORT, Spectrum DEX, Duckpools, SigmaFi, SigmaO, Phoenix Finance,
HodlCoin, Rosen Bridge, RWT, oracle pools, NiPoPoWs, Autolykos, storage rent,
sub-blocks, Sigma Chains, AVL trees, boxes and registers, ErgoTree, ErgoScript,
Fleet SDK, AppKit, sigma-rust, FleetSharp, Mosaik, GetBlok Plasma, Kiosk,
EIP-12 dApp connector, ErgoPay, ErgoAuth, Babel fees, Paideia, ErgoPad, Sigmanauts,
ERGOHACK, DeCo Education, Nautilus wallet, Satergo, Minotaur, SAFEW,
Ergo Explorer, ErgoWatch, Danaides, Machina Finance, Citadel, Lilium,
CruxFinance, ErgoRaffle, Off the Grid, grid trading, stealth addresses,
Schnorr signatures, Sigmajoin, constant segregation, headless dApp, off-chain bot.
Speakers include kushti (Alexander Chepurnoy), morphic, scalahub, greenhat,
anon_real, Mark Glasgow (glasgowm148), Bruno Woltzenlogel Paleo.
```

**This file is referenced by every processing script.** The Telegram pipeline uses it for topic tagging, the video pipeline feeds `whisper_prompt` to WhisperX, the LLM post-correction pass uses it for fixing misrecognitions, and the search pipeline uses `ergo_aliases.yaml` for query expansion.

### 4. Processing Scripts (Write Once, Run Forever)

**Why humans:** Someone needs to write the Python scripts. But they're write-once — after testing on a sample month of Telegram data, they process everything else autonomously. The video pipeline already exists, so only a thin adapter is needed.

**Scripts to write:**

| Script | Purpose | Lines of Code | Status |
|--------|---------|--------------|--------|
| `generate_glossary_tiers.py` | Master glossary → compact tier + alias map (YAML + JSON). Validates alias collisions, prints token counts. | ~130 | ✅ Done |
| `process_telegram.py` | Parse TG JSON → thread reconstruction → weekly segments → LLM summarization → monthly summaries | ~400 | ✅ Done (102 general + 51 dev months) |
| `adapt_video_output.py` | Lightweight adapter to add repo-standard frontmatter to existing video pipeline output | ~80 | — |
| `clone_and_process_repos.py` | GitHub API → extract contracts + patterns → LLM documentation generation → structured output | ~715 | ✅ Done (51 repos, 242 docs, 14 patterns) |
| `generate_embeddings.py` | Parse all Markdown → chunk by headers → attach metadata → embed with BGE-M3 → upsert to LanceDB | ~314 | ✅ Done (dry-run verified: 1,566 chunks, ~416K tokens; needs `ollama pull bge-m3` for actual run) |
| `generate_llms_txt.py` | Walk repo → collect frontmatter → generate llms.txt and llms-full.txt | ~219 | ✅ Done (242 docs, llms.txt + llms-full.txt ~400K tokens) |
| `build_topic_index.py` | Tag-based topic index + Telegram topic aggregation → cross-document topic index | ~248 | ✅ Done (111 tags, 4,587 Telegram topics indexed) |
| `scrape_ergoforum.py` | Discourse API scrape → cached JSON → markdown per topic → category + glossary-tag clustered index | ~350 | ✅ Done (1,008 topics, 10K+ posts, auto-tagged against 544 glossary aliases) |
| `scrape_ergo_blog.py` | Strapi CMS API scrape → cached JSON → markdown per post → tag + year + glossary-tag clustered index | ~290 | ✅ Done (701 posts: 397 full-content + 304 external stubs, auto-tagged against 544 glossary aliases) |

**Total: ~2,746 lines of Python** (~2,536 written, ~80 remaining for video adapter). Video processing is already handled by existing scripts. Telegram pipeline is complete. Ecosystem pipeline is complete. Forum archive is complete. Blog archive is complete. Embedding pipeline is ready to run once Ollama/BGE-M3 is set up.

### 5. MCP Server

**Why humans:** The tool definitions, descriptions, and routing logic require understanding what developers actually ask. But the implementation is a thin wrapper around LanceDB search.

**Core structure (Python + FastMCP):**

```python
from mcp.server.fastmcp import FastMCP

app = FastMCP("ergo-knowledge-base")

@app.tool()
async def search_docs(query: str, category: str = None,
                      sdk: str = None, limit: int = 5) -> list:
    """Search Ergo developer documentation, guides, and API references.
    Filter by category (concept/cookbook/reference/guide) and SDK
    (fleet-sdk/appkit/sigma-rust/python)."""

@app.tool()
async def search_code(query: str, language: str = "ergoscript",
                      project: str = None, limit: int = 5) -> list:
    """Search ErgoScript contracts, SDK code examples, and dApp integration
    patterns. Filter by language (ergoscript/typescript/scala/rust/python)
    and project (spectrum/dexy/duckpools/rosen/paideia/sigmausd/citadel)."""

@app.tool()
async def explore_api(endpoint_pattern: str = None,
                      api: str = "node") -> list:
    """Browse and search API endpoints for the Ergo Node REST API,
    Explorer API, or GraphQL schema. Returns parameters, response
    schemas, and usage examples."""

@app.tool()
async def search_community(query: str, date_range: str = None,
                           chat: str = None) -> list:
    """Search community knowledge from Telegram discussions (2017-present)
    and video transcripts. Returns context with timestamps and speaker
    attribution. Use date_range as 'YYYY-MM' or 'YYYY-MM:YYYY-MM'."""

@app.tool()
async def get_contract_template(type: str) -> str:
    """Get a ready-to-use ErgoScript contract template with deployment
    instructions. Types: token-mint, multi-sig, oracle-pool, dex-swap,
    auction, timelock, lending-pool, dao-voting, bridge-commitment."""

@app.tool()
async def get_integration_pattern(pattern: str) -> str:
    """Get frontend/backend integration patterns with working code examples.
    Patterns: eip12-connector, ergopay-signing, ergoauth, transaction-building,
    box-selection, offchain-bot, headless-dapp, state-tracking."""

@app.tool()
async def get_project_architecture(project: str) -> str:
    """Get complete architecture overview of an Ergo ecosystem project,
    including contract relationships, off-chain components, and frontend
    integration points. Projects: spectrum, dexy, duckpools, rosen-bridge,
    paideia, sigmausd, sigmafi, phoenix, citadel."""

@app.resource("ergo://llms-full")
async def llms_full() -> str:
    """Complete Ergo developer documentation for full-context ingestion."""

@app.resource("ergo://glossary")
async def glossary() -> str:
    """Ergo blockchain terminology and definitions."""
```

### 6. GitHub Actions Workflows

**Why humans:** CI/CD configuration, but it's boilerplate. Three workflows:

**`update-embeddings.yml`** — Triggers on push to `main` when content files change. Detects modified files via `git diff`, re-chunks and re-embeds only changed files, upserts to LanceDB. Runs in <2 minutes for typical PRs.

**`generate-llms-txt.yml`** — Triggers on any content change. Regenerates `llms.txt` and `llms-full.txt` from the repo's current state. Auto-commits the updated files.

**`process-new-content.yml`** — Manual trigger for bulk processing. Processes new Telegram export drops. Video processing runs through the existing pipeline outside of Actions.

### 7. Seed Content (Quality Gates)

**Why humans:** You need ~5-10 "gold standard" documents written by hand to serve as examples for the LLM processing pipeline and to validate the frontmatter schema actually works. Write these yourself:

- `reference/ergoscript/language-spec.md` — **Already exists.** Ahrobe's LangSpec.md (~1,350 lines) covers all ErgoScript types, methods, predefined functions, and known limitations. This is comprehensive and close to the right format — needs frontmatter added and possibly splitting into per-type files for granular retrieval (e.g. `types/box.md`, `types/coll.md`, `global-functions.md`). Can serve as-is for `llms-full.txt` ingestion.
- `concepts/eutxo-model.md` — ✅ Done. The definitive eUTXO explanation (~2,500 tokens). Covers UTXO vs accounts, boxes, data inputs, context variables, multi-stage protocols, Ergo vs Cardano.
- `concepts/boxes-and-registers.md` — ✅ Done. Box structure, R0-R9, type system, token mechanics, EIP-4 conventions, box identity, minimum box value (~2,200 tokens).
- `concepts/sigma-protocols.md` — ✅ Done. SigmaProp, Schnorr/DH tuples, AND/OR/threshold composition, zero-knowledge proofs, ring signatures, vs Ethereum (~2,300 tokens).
- `concepts/storage-rent.md` — ✅ Done. 4-year rule, fee calculation, token protection, dApp implications, miner economics, activation history (~2,000 tokens).
- `cookbook/tokens/mint-token.md` — Token minting with Fleet SDK
- `cookbook/apis/node-rest-basics.md` — The "grab this and go" API doc
- `sdks/fleet-sdk/getting-started.md` — SDK quickstart
- `reference/node-api/endpoints/utxo-by-id.md` — One API endpoint as template

These become the style guide. Every LLM-generated document gets compared against them.

**DeCo Education Adapted Guides** (✅ Complete):

Adapted from [DeCo Education's ErgoScript Developer Course](https://github.com/DeCo-Education/ErgoScript-Developer-Course) (MIT License, by lgd and kii) with full attribution. These guides bridge the gap between concept docs and production code:

- `guides/ergoscript-fundamentals/01-boxes-registers-context.md` — ✅ Done. Syntax, types, SigmaProp, blockchain context, global functions, pin-lock exercise. Adapted from DeCo Week 1.
- `guides/ergoscript-fundamentals/02-guard-script-framework.md` — ✅ Done. Box-focused contract design methodology (unique to DeCo), worked example with personal record box, blank template. Adapted from DeCo Week 2.
- `guides/ergoscript-fundamentals/03-offchain-appkit.md` — ✅ Done. 10-step AppKit transaction recipe, alcohol sale walkthrough, context variables, real-world considerations. Adapted from DeCo Week 3.

All concept docs cross-reference these guides, and guides cross-reference each other and the concept docs.

**Decision point on LangSpec.md:** It works well as a single monolithic reference (easy for an LLM to ingest whole), but RAG retrieval benefits from smaller chunks. The recommended approach is to keep the full file AND generate per-type split files — the embedding pipeline handles both, and the `llms.txt` index can link to whichever granularity the agent needs. The LLM can do the splitting automatically using the existing file as input.

### 8. Ecosystem Code Repository Catalog

**Why this matters:** The real value of this knowledge base isn't just documenting ErgoScript syntax — it's capturing production patterns from live dApps. A developer asking "how do I build a lending protocol on Ergo?" should get actual Duckpools contract patterns, not generic ErgoScript docs. The ecosystem catalog is what makes this knowledge base unique rather than a prettier version of docs.ergoplatform.com.

**What the LLM pipeline processes:** For each repo below, the pipeline clones, extracts ErgoScript contracts (`.es` files), scans for key patterns (EIP-12 connector usage, transaction building, box selection), generates per-contract documentation with frontmatter, and indexes code + README content.

**Human work:** Curate this list (below), write a `clone_and_process_repos.py` script, and decide which repos are high enough quality to include. The LLM does the extraction, summarization, and documentation generation.

#### Core Protocol & SDKs

| Repository | Language | What to Extract | Priority |
|-----------|----------|----------------|----------|
| `ergoplatform/ergo` | Scala | Node API endpoints (Swagger), config options, mining | High |
| `ergoplatform/sigmastate-interpreter` | Scala | ErgoScript compiler internals, ErgoTree spec, test cases as examples | High |
| `ergoplatform/sigma-rust` | Rust | WASM bindings, wallet features, ErgoTree interpreter | High |
| `ergoplatform/eips` | Markdown | All EIPs as structured reference docs | High |
| `ergoplatform/oracle-core` | Rust | Oracle pool v2 architecture, connector patterns | High |
| `ergoplatform/ergo-appkit` | Java/Scala | SDK patterns, transaction building, contract compilation | High |
| `fleet-sdk/fleet` | TypeScript | Core library, transaction builder, wallet integration, serialization | High |
| `fleet-sdk/fleet-by-example` | TypeScript | Worked examples — direct cookbook material | High |
| `fleet-sdk/docs` | Markdown | VitePress docs — migrate/cross-reference | High |
| `ergo-pad/ergo-python-appkit` | Python | Python SDK patterns, JPype bridge | Medium |
| `ergoplatform/ergo-wallet-app` | Kotlin | Mobile wallet patterns, key management | Medium |
| `ergoplatform/ledger-app-ergo` | C | Hardware wallet integration | Low |

#### DeFi Protocols — Smart Contracts + Off-chain Code

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| **Spectrum/ErgoDEX** | | | |
| `spectrum-finance/ergo-dex` | DEX contracts | ErgoScript | AMM pools, order-book, atomic swaps, partial fills, LP mechanics |
| `spectrum-finance/ergo-dex-backend` | Off-chain bots | Scala | Order matching, execution bots, state tracking |
| **Dexy Stablecoin** | | | |
| `kushti/dexy-stable` | Stablecoin | ErgoScript/Scala | Oracle-pegged minting, LP with oracle rate modification, cross-tracker, top-up swaps, anti-drain mechanisms |
| `ergoplatform/ergo-jde` (Dexy specs) | Spec | Markdown/Scala | Dexy design docs and test specifications |
| **SigmaUSD / AgeUSD** | | | |
| `DjedAlliance/Djed-Ergo` | Stablecoin | ErgoScript/Scala | AgeUSD protocol, headless dApp pattern, reserve management, CLI implementation |
| **Duckpools** | | | |
| `duckpools` org — contracts repo | Lending | ErgoScript | Lending pools, collateralized borrowing, interest rate algorithms, liquidation |
| `duckpools` — option pools | Options | ErgoScript | Option contract patterns |
| **SigmaFi** | | | |
| SigmaFi contracts | Bonds/Yield | ErgoScript | P2P bond contracts, yield strategies |
| SigmaFi UI | Frontend | JS/TS | dApp connector integration with DeFi |
| **Phoenix / HodlCoin** | | | |
| HodlCoin contracts | Proof-of-hodl | ErgoScript | Time-locked value accrual, proof-of-hodl mechanics |
| **SigmaO** | | | |
| SigmaO contracts | Options trading | ErgoScript | Decentralized options on Ergo tokens |

#### Infrastructure & Bridges

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| **Rosen Bridge** (34 repos) | | | |
| `rosen-bridge/contract` | Bridge contracts | ErgoScript | Guard/watcher architecture, multi-sig consensus on-chain, RWT staking, fraud detection, event lifecycle |
| `rosen-bridge/watcher` | Watcher node | TypeScript | Chain scanning, commitment creation, event trigger assembly |
| `rosen-bridge/scanner` | Block scanner | TypeScript | Abstract scanner pattern, address/token extractors, observation extraction |
| `rosen-bridge/guard` (if public) | Guard node | TypeScript | Event verification, cross-chain tx signing, payment distribution |
| `rosen-bridge/ui` | Frontend | TypeScript | Bridge UI patterns, cross-chain status tracking |
| **Wallets** | | | |
| `nautls/nautilus-wallet` | Browser wallet | TypeScript/Vue | EIP-12 dApp connector implementation (reference), wallet architecture, Ledger integration |
| `ThierryM1212/SAFEW` | Browser wallet | JavaScript | Alternative EIP-12 implementation, ErgoMixer integration |
| `ErgoWallet/ergowallet-desktop` | Desktop wallet | TypeScript | Desktop wallet patterns, multi-wallet management |

#### DAOs & Governance

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| **Paideia** (11 repos) | | | |
| `paideiadao/paideia-contracts` | DAO contracts | ErgoScript/Python | Staking, voting, proposal lifecycle, treasury management, config boxes as on-chain oracles, EIP-6 protocol specs |
| `paideiadao/paideia-app` | Frontend | TypeScript/Next.js | Full dApp frontend with wallet connection, proposal UI, staking interface |
| `paideiadao/paideia-state` | State management | Scala | On-chain state tracking, box scanning |
| `paideiadao/paideia-offchain` | Off-chain logic | Python | Transaction assembly, bot operations |
| `paideiadao/paideia-sdk` | SDK | Scala | Optimized Scala function calls for contract interaction |
| `paideiadao/paideia-data` | Backend | Python/SQL/Redis | Database patterns for dApp state, caching |

#### Analytics & Portfolio

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| **CruxFinance** | Portfolio/Analytics | Scala/Rust/JS/TS | Cross-chain liquidity, portfolio tracking, charting, EXLE lending integration |
| **ErgoPad / Danaides** | Indexing | Python | High-performance blockchain indexing, dApp backend patterns |
| `ergo-pad/nft-market` | NFT Marketplace | TypeScript/Next.js | NFT marketplace frontend patterns, MUI + Next.js template |

#### Multi-Protocol Reference Implementation

| Repository | Type | Language | Key Patterns to Extract |
|-----------|------|----------|------------------------|
| `arkadianet/citadel` | DeFi desktop client | Rust/React/Tauri | **Gold mine.** One crate per protocol (AMM, Dexy, HodlCoin, Duckpools, Rosen, SigmaFi, SigmaUSD). Shows EIP-12 tx building, box selection, sigma encoding, ErgoPay signing flow, node API client with capability detection. This single repo demonstrates how to interact with nearly every major Ergo protocol from a unified codebase. |

#### Frontend Connector Patterns (Cross-Cutting)

These aren't separate repos but patterns to extract FROM the repos above. The knowledge base needs dedicated docs on each:

| Pattern | Key Source Repos | What to Document |
|---------|-----------------|-----------------|
| **EIP-12 dApp Connector** | Nautilus, SAFEW, Fleet SDK docs | Connection API (`ergoConnector.{wallet}.connect()`), Context API (`ergo.get_utxos()`, `ergo.sign_tx()`, `ergo.submit_tx()`), multi-wallet detection, TypeScript types (`@nautilus-js/eip12-types`) |
| **ErgoPay (EIP-20)** | Nautilus, SAFEW, Citadel (`ergopay-core`, `ergopay-server`) | Transaction reduction for mobile signing, URI scheme, dynamic vs static requests, local HTTP server pattern for desktop↔mobile flow |
| **ErgoAuth (EIP-28)** | ErgoPad API, Paideia | User authentication via SigmaProp signature, challenge-response flow, no-funds-moved guarantee |
| **Transaction Building** | Fleet SDK, Citadel (`ergo-tx`), AppKit | `TransactionBuilder` pattern, `OutputBuilder`, box selection strategies, change handling, fee calculation, token operations (mint/transfer/burn) |
| **Box Selection** | Fleet SDK (`configureSelector`), Citadel, Nautilus | UTXO selection algorithms, `ensureInclusion`, token filtering, target amount matching |
| **Off-chain Bots** | Spectrum backend, Machina Finance, Duckpools | Bot architecture: chain scanning → state detection → tx assembly → submission, execution fee economics |
| **Headless dApp Pattern** | Djed-Ergo (AgeUSD), SigmaFi | Pure logic layer separating protocol state reading + action execution from any UI, making dApps composable and testable |
| **On-chain State Tracking** | Rosen Bridge scanner, Paideia state, Danaides | Scanning frameworks, box tracking by token/address, state reconstruction from UTXO set |

#### Processing Pipeline for Ecosystem Code

**`clone_and_process_repos.py`** — ✅ Complete (715 lines). Uses GitHub API (no git clone). For each repo in the catalog:

1. Clone or pull latest from GitHub
2. Find all `.es` (ErgoScript), `.ergo` files — extract with full file path context
3. Find all transaction-building patterns (regex for `TransactionBuilder`, `OutputBuilder`, `ctx.newTxBuilder`, `ergo.sign_tx`, etc.)
4. Extract README.md and any `/docs` or `/spec` directories
5. Send each contract file to LLM with prompt:

```
Analyze this ErgoScript contract from the {project_name} project.
Produce a structured document with:
- Purpose: What this contract does in 2-3 sentences
- Inputs/Outputs: What boxes it expects and produces
- Key Logic: The core validation conditions, explained
- Registers Used: Which R4-R9 registers and their types/purposes
- Tokens: Any NFTs or tokens used for authentication/tracking
- Integration Pattern: How off-chain code interacts with this contract
- Related Contracts: Which other contracts in this project it composes with

Use exact Ergo terminology from the glossary.
Tag with: project, contract_type (stablecoin/dex/lending/bridge/dao/utility),
complexity (beginner/intermediate/advanced)
```

6. Generate per-project overview doc summarizing architecture
7. Output to `content/ecosystem/{project}/` with proper frontmatter

**Scale:** 51 repos, 242 generated docs, 14 cross-cutting patterns, ~400K tokens. LLM processing cost: **~$5.** Human review of generated docs: ~5-8 hours (focus on verifying contract descriptions are accurate).

---


Once the scaffolding is in place, the machines take over. Here's what runs automatically:

### Phase A: Telegram Processing ✅ COMPLETE

**Human input:** Drop the Telegram JSON exports into a staging directory. Run one command.

**What the pipeline does automatically:**
1. Parses all JSON, handles the dual text format (string vs. entity array)
2. Filters noise (bot commands, emoji-only, messages <5 chars)
3. Reconstructs reply chains using `reply_to_message_id`
4. Groups messages into weekly segments using conversation gaps
5. Sends each week's segment to an LLM (Claude or GPT-4o-mini) with the prompt:

```
You are processing Ergo blockchain Telegram chat archives.

Given the following week of conversation, produce a structured summary:

## Key Topics Discussed
- List each distinct technical topic with 2-3 sentence summary

## Important Decisions or Announcements
- Any decisions made, releases announced, or proposals introduced

## Technical Q&A Worth Preserving
- Questions asked and answers given that a future developer would find useful

## Links Shared
- URLs with context about what they contain

## Unresolved Questions
- Topics raised but not resolved

Use the exact technical terms from the Ergo glossary:
{glossary_terms}

Preserve exact usernames, message IDs, and timestamps for citation.
Format: [YYYY-MM-DDThh:mm] @username (msg#ID): key quote
```

6. Reduces weekly summaries into monthly summaries
7. Runs BERTopic across all segments to build topic index
8. Generates Markdown files with full frontmatter
9. Outputs everything to `telegram/summaries/` and `telegram/segments/`

**Scale:** ~100 monthly summaries across both chats. At ~$0.01-0.03 per monthly summary with GPT-4o-mini, total cost: **$2-5.**

**Human review needed:** Spot-check 5-10 summaries for accuracy, especially early months where the LLM has less context. Fix any systematic errors in the prompt. After that, the pipeline is trusted.

### Phase A2: ErgoForum Archive ✅ COMPLETE

**Source:** [ergoforum.org](https://ergoforum.org) — Discourse-based community forum, running since July 2019. 1,230 topics, 10,104 posts, 1,277 users. Low recent activity (~2 topics/month) — primarily a historical archive of protocol design discussions, EIP proposals, and technical Q&A.

**What the pipeline does:**
1. Paginates `/latest.json` to collect all topic IDs and metadata
2. Fetches each topic's full content via `/t/{id}.json` (HTML posts, authors, timestamps, likes)
3. Caches raw JSON in `forum/raw/` (gitignored) for offline re-processing
4. Converts HTML to clean markdown via `markdownify`
5. Auto-tags each topic against the 544-alias glossary using word-boundary regex
6. Writes markdown files to `forum/topics/{category}/` with full frontmatter
7. Generates `forum/forum-index.md` (category-clustered + glossary-tag-clustered) and `forum/forum-index.json`

**Why this matters:** ErgoForum contains kushti's original protocol design discussions, EIP proposal debates, and technical deep-dives that don't exist anywhere else. Many design decisions (Dexy mechanics, oracle pool v2 architecture, storage rent parameters) were first discussed and debated on the forum before becoming code. The auto-tagging against the glossary creates semantic cross-references to concept docs, ecosystem docs, and Telegram summaries.

**Scale:** 1,230 topics, ~10 minutes to scrape (rate-limited at 0.5s/call). **Cost: $0** (no LLM needed — Discourse API provides full HTML content). Glossary auto-tagging is pure regex, no API calls.

### Phase A3: Ergo Platform Blog Archive ✅ COMPLETE

**Source:** [ergoplatform.org/en/blog/](https://ergoplatform.org/en/blog/) — Official Ergo Platform blog hosted on Strapi CMS. 701 posts spanning October 2018 to January 2026. Mix of original content (397 full-text posts) and external URL references (304 stubs pointing to Medium articles, especially 2019-2021 era).

**What the pipeline does:**
1. Fetches all posts from Strapi CMS API (`/api/posts`) with pagination (8 pages of 100)
2. Caches raw JSON in `blog/raw/` (gitignored) for offline re-processing
3. Separates full-content posts (written to `blog/posts/{tag}/`) from external-URL stubs (`blog/stubs/{tag}/`)
4. Cleans up content (HTML comments, StartFragment markers, excessive whitespace)
5. Auto-tags each post against the 544-alias glossary using word-boundary regex
6. Generates full frontmatter including blog tag, type, glossary hits, and source URL
7. Generates `blog/blog-index.md` (by blog tag, by year, by glossary concept) and `blog/blog-index.json`

**Why this matters:** The Ergo Platform blog is the primary official communication channel — protocol announcements, technical explainers, ecosystem updates, ErgoHack results, and community education. Many posts cover topics not discussed elsewhere (ErgoScript design patterns, DeFi explainers, privacy features). The current website has rendering issues (many news items return blank pages), making this archive a valuable preservation effort. Blog tag distribution provides natural topic clustering: Tooling, Events, Ecosystem, Core, Mining, Privacy, etc.

**Scale:** 701 posts fetched in ~3 seconds (Strapi API returns full content inline). Processing (glossary tagging + markdown generation) takes ~5 seconds for all 701 posts. **Cost: $0** (no LLM needed — Strapi provides full content). Glossary auto-tagging is pure regex.

### Phase B: Video Transcription (Pipeline Already Exists ✅)

**Status:** Video processing scripts are already built and tested. ~450 videos to process at ~$0.17/hour, covering AMAs, dev updates, ergoversary events, and key presentations.

**The pipeline is semi-automated, not hands-off.** Each batch of ~50 videos takes 3-4 hours of human time due to the start/stop/wait nature of the process plus manual review of speaker assignments and spot audits. This is the single largest block of human time in the project.

**Remaining work:**
1. Ensure output format includes YAML frontmatter matching the repo's schema (may need a lightweight adapter script)
2. Feed `whisper_prompt` from `ergo_glossary.yaml` into the existing pipeline if not already using domain-specific prompting
3. Batch process the full 450-video archive across 9 batches
4. Manual speaker assignment review per batch
5. Drop outputs into `video-content/{category}/`

**Scale:** ~450 videos across ~9 batches. **~27-36 hours of human processing time.** API cost: ~$50-70 at $0.17/hr. This is a parallel workstream — batches can run alongside other development work but require attention during processing windows.

**Key implication for timeline:** Video processing stretches across the entire project timeline rather than being a fire-and-forget batch job. Plan to run 2-3 batches per week alongside other work.

### Phase C: Ecosystem Code Processing (LLM Does 85% of the Work)

**Human input:** Curate `ecosystem_repos.yaml` listing all repos to process (the catalog from Section 8 above). Run one command.

**What the pipeline does automatically:**
1. Clones each repo (or pulls latest if already cloned)
2. Scans for `.es` (ErgoScript), `.scala`, `.ts`, `.rs`, `.py` files matching contract/integration patterns
3. Extracts README.md, `/docs`, `/spec` directories, and any EIP references
4. Sends each contract to LLM with structured analysis prompt + glossary context
5. Generates per-project overview documents from README + contract summaries
6. Extracts cross-cutting patterns (EIP-12 connector usage, TransactionBuilder patterns, box selection, ErgoPay flows) into dedicated `content/patterns/` docs
7. Writes all output with proper frontmatter to `content/ecosystem/{project}/`
8. The Citadel repo gets special treatment — its one-crate-per-protocol architecture becomes the canonical reference for multi-protocol integration

**Scale:** 51 repos processed, 242 docs generated, 14 cross-cutting pattern guides. **LLM cost: ~$5.** The contracts are short (most ErgoScript files are 50-300 lines), so token costs are modest.

**Human review needed:** ~5-8 hours. Focus on:
- Verifying contract descriptions are technically accurate (the LLM can misread ErgoScript validation logic)
- Ensuring the "Integration Pattern" sections actually describe how off-chain code calls the contract
- Checking that cross-cutting pattern docs (EIP-12, ErgoPay, etc.) are consistent across examples from different projects
- Flagging any repos that have been deprecated or superseded (e.g., ErgoDEX → Spectrum Finance rename)

### Phase D: Existing Docs Migration (LLM Does 70% of the Work)

**Human input:** Provide a list of source URLs (docs.ergoplatform.com pages, GitHub READMEs, wiki pages).

**What the pipeline does:**
1. Scrapes/fetches the source content
2. LLM restructures into the repo's template format with proper frontmatter
3. LLM identifies cross-references and populates `prerequisites` and `related` fields
4. LLM fills in `estimated_tokens` and `difficulty` metadata
5. Outputs draft Markdown files

**Human review needed:** More here than other phases (~30% of effort). The LLM can restructure content but can't verify that code examples still work, that API endpoints are current, or that SDK version numbers are right. **This is where domain expertise matters.** Best approach: LLM generates drafts, human reviews in PR before merge.

### Phase E: Embedding Generation & Indexing (Fully Automated)

**Human input:** None after initial setup. GitHub Actions handles everything.

**What runs automatically on every push to `main`:**
1. Detects changed files via `git diff`
2. Parses Markdown using header-based recursive chunking
3. Prepends header breadcrumb to each chunk for context preservation
4. Never splits within fenced code blocks
5. Targets 512-1024 tokens per chunk with 15% overlap
6. Generates embeddings via BGE-M3 (self-hosted via Ollama)
7. Attaches all frontmatter metadata to each chunk
8. Upserts to LanceDB with content-hash-based deduplication
9. Unchanged content is skipped automatically

**Cost: $0.** BGE-M3 runs locally. LanceDB is file-based. GitHub Actions is free for public repos.

### Phase F: llms.txt Generation (Fully Automated)

Auto-regenerated on every content change. Walks the repo, collects frontmatter, builds the structured index with token counts and descriptions. Auto-committed back to the repo.

### Phase G: Ongoing Content (Mixed, Tilts Toward Automated Over Time)

| Activity | Human % | LLM % | Frequency |
|----------|---------|-------|-----------|
| New Telegram months | 5% (spot-check) | 95% | Monthly |
| New video transcripts | 40% (speaker review, spot audit) | 60% | Per batch, 3-4 hrs per 50 videos |
| Ecosystem repo updates | 15% (verify contract accuracy) | 85% | Per major release or new project |
| New SDK version docs | 30% (verify code) | 70% | Per release |
| New EIP documentation | 40% (technical review) | 60% | Per EIP |
| Community-contributed guides | 20% (editorial review) | 80% | Ad hoc |
| API endpoint changes | 30% (verify accuracy) | 70% | Per node release |
| Re-embedding after schema change | 0% | 100% | Rare |

---

## The RAG Stack (All Open Source, All Zero Cost)

### Vector Database: LanceDB

- **Why:** Embedded, file-based (like SQLite for vectors). No Docker, no server, no infrastructure. The `.lance` files live right in the repo or alongside it. Contributors can clone and run locally with zero setup.
- **Hybrid search:** Pair with `rank-bm25` Python library for keyword search. Merge results via Reciprocal Rank Fusion (RRF).
- **Versioning:** LanceDB supports automatic versioning with time-travel — you can query the knowledge base as it existed at any point in time.

### Embeddings: BGE-M3

- **Why:** MIT license, self-hosted via Ollama (`ollama pull bge-m3`), supports 100+ languages, native dense + sparse + multi-vector output. Handles both documentation prose and code.
- **Dimensions:** 1024 dense vectors. The sparse output enables keyword-aware retrieval without a separate BM25 index.
- **Alternative for code-heavy content:** If retrieval quality for pure ErgoScript code is insufficient, add Nomic Embed Code (Apache 2.0) as a second embedding model with routing — code files go through Nomic, prose goes through BGE-M3.

### Reranker: BGE-reranker-v2-m3

- **Why:** Open-source cross-encoder that runs locally. Takes the top 20 hybrid search results and re-scores them for the final top 5 passed to the LLM.
- **Impact:** Studies consistently show 20-30% precision improvement from reranking on top of hybrid search.

### Topic Modeling: BERTopic + KeyBERT

- **Why:** BERTopic's `topics_over_time()` tracks when concepts entered Ergo discourse. KeyBERT extracts multi-word phrases ("oracle pool v2", "sub-block ordering") that single-word keyword extractors miss.
- **Used for:** Telegram topic index, auto-tagging documents, search query expansion.

### Framework: LlamaIndex or Direct

- **LlamaIndex** if you want hierarchical retrieval (Tier 1 summaries → Tier 2 detail) out of the box via `RecursiveRetriever`.
- **Direct LanceDB + custom code** if you prefer minimal dependencies. The search logic is ~100 lines of Python.

### Full Stack Cost

| Component | Tool | Monthly Cost |
|-----------|------|-------------|
| Vector database | LanceDB (embedded) | $0 |
| Embeddings | BGE-M3 via Ollama | $0 |
| Reranker | BGE-reranker-v2-m3 | $0 |
| Keyword search | rank-bm25 | $0 |
| Topic modeling | BERTopic + KeyBERT | $0 |
| MCP server | FastMCP (self-hosted) | $0 |
| CI/CD | GitHub Actions (public repo) | $0 |
| **Total** | | **$0/month** |

One-time processing costs: Telegram ~$2-5, video ~$50-70 (pipeline exists, semi-automated batches), ecosystem code ~$3-8, docs migration ~$1-3. **Total: ~$58-88.** Video is the dominant cost, ecosystem code processing is surprisingly cheap because ErgoScript contracts are compact.

---

## Chunking Strategy by Content Type

| Content Type | Chunking Method | Target Size | Special Rules |
|-------------|----------------|-------------|---------------|
| Markdown docs | Header-based recursive (split on H2) | 512-1024 tokens | Prepend header breadcrumb; never split code blocks |
| ErgoScript contracts (.es) | Whole file or AST-based | Function/contract level | Prepend file path + project name + purpose comment |
| Scala/Rust SDK code | AST-based via tree-sitter | Function/class level | Include docstrings, imports, and module context |
| TypeScript (Fleet/frontend) | AST-based via tree-sitter | Function/component level | Include imports; flag EIP-12 connector patterns |
| Python scripts | AST-based via tree-sitter | Function level | Include docstrings and imports |
| API endpoint docs | One chunk per endpoint | Entire endpoint doc | Include URL, method, params, response schema |
| GraphQL schema | One chunk per type/query | Type definition level | Include field descriptions |
| Telegram segments | Thread-based or time-window | 512-1024 tokens | Prepend metadata header with date/participants/topic |
| Video transcripts | Topic-segmented | 512-1024 tokens | Include timestamp ranges and speaker labels |
| Ecosystem contract docs | One chunk per contract | Entire contract doc | Include project, contract_type, integration pattern |
| Cross-cutting pattern docs | Section-based | 512-1024 tokens | Prepend pattern name; include code examples inline |

**Every chunk gets a metadata header prepended before embedding:**

```
# Ergo Concepts > Boxes and Registers > Register Types
# Tags: registers, boxes, data-types, eutxo
# SDK: none | Difficulty: beginner
```

This ensures chunks carry their full context when retrieved in isolation — the #1 RAG failure mode is contextless chunks.

---

## The llms.txt Standard

The `/llms.txt` file at the repo root serves as an AI-readable sitemap. LLM agents, Cursor's `@Docs`, and tools like Context7 parse it to understand what the repo contains.

**Example for this repo:**

```markdown
# Ergo Developer Knowledge Base

> Comprehensive developer documentation for the Ergo blockchain ecosystem,
> including SDKs, ErgoScript smart contracts, node APIs, GraphQL schemas,
> community knowledge from 8 years of Telegram history, and video transcripts.

## Concepts
- [eUTXO Model](content/concepts/eutxo-model.md): How Ergo extends the UTXO model with registers and scripts (~800 tokens)
- [Boxes and Registers](content/concepts/boxes-and-registers.md): Ergo's data model for UTXOs (~650 tokens)
- [Sigma Protocols](content/concepts/sigma-protocols.md): Zero-knowledge proof system (~900 tokens)

## SDK Documentation
- [Fleet SDK Getting Started](content/sdks/fleet-sdk/getting-started.md): TypeScript SDK quickstart (~500 tokens)
- [AppKit Setup](content/sdks/appkit/setup.md): Java/Scala SDK with Maven/Gradle (~600 tokens)

## API Reference
- [Node REST API](content/reference/node-api/): Complete endpoint documentation
- [GraphQL Schema](content/reference/graphql-schema/): Explorer GraphQL types and queries

## Smart Contracts
- [ErgoScript Guide](content/reference/ergoscript/): Language reference and built-in functions
- [Contract Templates](examples/ergoscript/): Ready-to-use contract patterns

## Cookbook
- [Mint Token](content/cookbook/tokens/mint-token.md): Token minting recipe (~400 tokens)
- [Node API Basics](content/cookbook/apis/node-rest-basics.md): Essential REST endpoints (~350 tokens)

## Ecosystem dApps
- [Spectrum DEX](content/ecosystem/spectrum-dex/overview.md): AMM contracts, order-book, execution bots (~1200 tokens)
- [Dexy Stablecoin](content/ecosystem/dexy/overview.md): Oracle-pegged minting, LP mechanics, anti-drain (~1500 tokens)
- [Rosen Bridge](content/ecosystem/rosen-bridge/overview.md): Guard/watcher architecture, cross-chain consensus (~1800 tokens)
- [Paideia DAO](content/ecosystem/paideia/overview.md): Staking, voting, proposals, treasury management (~1400 tokens)
- [Duckpools Lending](content/ecosystem/duckpools/overview.md): Lending pools, collateralized borrowing (~1000 tokens)
- [SigmaUSD](content/ecosystem/sigmausd/overview.md): AgeUSD protocol, reserve management (~900 tokens)
- [Citadel](content/ecosystem/citadel/overview.md): Multi-protocol Rust reference implementation (~1100 tokens)

## Frontend & Backend Patterns
- [EIP-12 dApp Connector](content/patterns/eip12-dapp-connector.md): Wallet connection, tx signing, multi-wallet support (~800 tokens)
- [ErgoPay Signing](content/patterns/ergopay-signing.md): Mobile wallet integration, URI scheme, QR codes (~600 tokens)
- [Transaction Building](content/patterns/transaction-building.md): Fleet SDK + AppKit patterns, box selection, fees (~900 tokens)
- [Off-chain Bots](content/patterns/offchain-bots.md): Execution bot architecture, state scanning, tx assembly (~700 tokens)
- [Headless dApp Pattern](content/patterns/headless-dapp.md): Pure logic layer for protocol interactions (~500 tokens)

## Community Knowledge
- [Telegram Topic Index](telegram/topics/topic-index.md): Searchable index of 8 years of community discussions
- [Monthly Summaries](telegram/summaries/): Per-month discussion summaries with citations

## Video Archive
- [Video Index](video-content/index.md): Transcripts of AMAs, dev updates, and presentations
```

The companion `llms-full.txt` concatenates all docs into a single file for direct context-window ingestion. Auto-generated by CI on every merge.

---

## MCP Server: The Agent Interface

The MCP server is what makes this a true "AI-native" knowledge base rather than just a docs site. When a developer's LLM agent (Claude, Cursor, Windsurf) needs to know how to mint a token on Ergo, it calls the MCP server's `search_docs` tool instead of hallucinating.

**Eight tools covering all use cases:**

1. **`search_docs`** — Semantic search across all documentation. Filters by category, SDK, difficulty. Returns ranked chunks with source file paths.

2. **`search_code`** — Dedicated code search with project filtering. "Show me how Duckpools handles liquidation" returns the actual contract with explanation. Filter by language and project.

3. **`explore_api`** — Structured API endpoint lookup. "Show me how to get a box by ID from the node" returns the exact endpoint, parameters, and example response.

4. **`search_community`** — Two-tier Telegram retrieval. Scans monthly summaries first, then drills into weekly segments. Returns context with timestamps and `t.me` citation links.

5. **`get_contract_template`** — Returns complete, deployable ErgoScript templates. "Give me a timelock contract" returns working code plus deployment instructions. Includes templates derived from production contracts.

6. **`get_integration_pattern`** — Returns frontend/backend patterns with working code. "How do I connect a React app to Nautilus?" returns the full EIP-12 flow with TypeScript examples from real dApps.

7. **`get_project_architecture`** — Returns complete architecture overview of any major Ergo project. Shows how contracts relate to each other, what off-chain components exist, and how the frontend integrates.

8. **`search_telegram`** — Alias for community search focused on historical discussions.

**Deployment:** stdio transport for local development (works directly with Claude Desktop/Cursor), Cloudflare Workers or Vercel for remote access. Both transports from the same codebase.

---

## Implementation Timeline

*Video processing runs as a parallel workstream across the entire timeline: ~9 batches of 50, each taking 3-4 hours of human attention. Plan 2-3 batches per week alongside other work.*

### Week 1: Scaffolding + Start Video Batches (Human, ~20 hours)
- [x] Create repo with directory structure — ✅ Done. Full content/ tree: ecosystem/, patterns/, reference/, sdks/, examples/, topics/
- [x] Write frontmatter schema and document templates — ✅ Done. `FRONTMATTER.md`: 20-field schema, 7 templates (concept, cookbook, reference, overview, contract, pattern, guide), enum values, conventions
- [x] Curate `ergo_glossary.yaml` — ✅ Done (126 terms, 17 categories, 544 aliases)
- [x] Integrate LangSpec.md — ✅ Done. Kept monolithic at `content/reference/ergoscript/language-spec.md` (~13K tokens) with frontmatter
- [x] Write 4 gold-standard seed documents — ✅ Done. `eutxo-model.md` (~2,500 tokens), `boxes-and-registers.md` (~2,200 tokens), `sigma-protocols.md` (~2,300 tokens), `storage-rent.md` (~2,000 tokens). All cross-referenced with each other and DeCo guides.
- [x] Adapt DeCo Education ErgoScript Developer Course into 3-part guide series — ✅ Done. MIT license, full attribution. `01-boxes-registers-context.md`, `02-guard-script-framework.md`, `03-offchain-appkit.md` in `content/guides/ergoscript-fundamentals/`.
- [ ] Set up LanceDB locally, test basic embedding + retrieval — `generate_embeddings.py` written and dry-run verified (1,566 chunks). Needs `ollama pull bge-m3`
- [ ] Write thin adapter script if needed to conform video output to repo frontmatter
- [ ] **Video: process batches 1-2** (~6-8 hrs human time)

### Week 2: Telegram Pipeline + Ecosystem Script (Human + LLM pair programming, ~15 hours)
- [x] ~~Write `process_telegram.py`~~ — ✅ Complete (102 general + 51 dev months processed)
- [x] Write `clone_and_process_repos.py` — ✅ Done. GitHub API-based (no git clone), tested on all 51 repos. 715 lines. Features: contract_extensions for .md/.txt contracts, branch overrides, multi-repo CLI flag, cross-cutting pattern synthesis
- [x] Curate `ecosystem_repos.yaml` — ✅ Done. 51 repos (exceeded ~30-40 target), 14 cross-cutting patterns, covering DeFi, DAOs, wallets, bridges, NFTs, MCP servers
- [x] Write `generate_embeddings.py` and `generate_llms_txt.py` — ✅ Done. llms.txt (242 docs, ~400K tokens), embeddings pipeline dry-run verified (1,566 chunks)
- [x] Write `build_topic_index.py` — ✅ Done. 111 tags, 93 co-occurrence pairs, 4,587 Telegram topics indexed
- [ ] Validate output quality, iterate prompts — Spot-checks during dev, no formal pass yet
- [ ] **Video: process batches 3-5** (~9-12 hrs human time)

### Week 3: Let the Machines Rip (Human: ~8 hours monitoring + video)
- [x] ~~**Run Telegram pipeline on full corpus**~~ — ✅ Complete
- [x] **Run ecosystem code pipeline on all 51 repos** — ✅ Done. 242 markdown docs, 14 pattern docs, ~400K tokens total. Pushed to cannonQ/ergo-knowledge-base
- [ ] Spot-check outputs, fix any systematic prompt issues
- [ ] Ingest completed video transcripts as they finish
- [ ] Run full embedding generation across all content — script ready, needs Ollama + BGE-M3 setup
- [ ] Human review: scan 10-15 Telegram summaries, 5 video transcripts, 10 ecosystem contract docs
- [x] Generate all 14 cross-cutting pattern docs (EIP-12, ErgoPay, tx building, headless dApp, singleton NFT, proxy contracts, oracle data, token minting, AMM/LP, Plasma/AVL, etc.) — ✅ Done
- [x] Scrape ErgoForum archive — ✅ Done. `scrape_ergoforum.py` (350 lines). 1,008 topics scraped via Discourse API → curated to 677 (dropped 331 support + zero-glossary-hit topics, kept all kushti/armeanio). Auto-tagged against 544 glossary aliases. Output: `forum/topics/{category}/`, `forum/forum-index.md` (top 25/category, lean).
- [x] Scrape Ergo Platform blog archive — ✅ Done. `scrape_ergo_blog.py` (290 lines). 701 posts from Strapi CMS API (397 full-content + 304 external stubs). Auto-tagged against 544 glossary aliases. Output: `blog/posts/{tag}/`, `blog/stubs/{tag}/`, `blog/blog-index.md` (top 10/tag, lean).
- [x] Add 4 ergoplatform repos — ✅ Done. ergo-node-interface-rust (sdk), ergo_avltree_rust (reference), ergo-utilities-rust (sdk), ergoscript-by-example (reference). Total repos: 55.
- [x] Curate indexes for LLM context — ✅ Done. Deleted JSON indexes (forum + blog). Shrunk markdown indexes to fit context windows.
- [ ] **Video: process batches 6-7** (~6-8 hrs human time)

### Week 4: Migration + MCP (Human: ~15 hours + video)
- [ ] Migrate highest-value existing docs from docs.ergoplatform.com
- [ ] LLM generates drafts, human reviews in PRs
- [ ] Write the missing SDK comparison guide (human + LLM)
- [ ] Build MCP server, test with Claude Desktop
- [ ] Set up GitHub Actions workflows
- [ ] Fork all 55 ecosystem repos for preservation (strategy TBD: personal account vs dedicated org)
- [ ] **Video: process batches 8-9** (~6-8 hrs human time)

### Week 5: Polish + Launch (Human: ~10 hours)
- [ ] Ingest final video batch outputs
- [ ] Write README and contribution guidelines
- [ ] Test end-to-end: developer asks question → MCP server → relevant answer with citations
- [ ] Deploy MCP server (Cloudflare Workers or Vercel)
- [ ] Announce to Ergo community, collect feedback
- [ ] Document the processing pipeline so others can contribute

### Ongoing: ~3-5 hours/month (plus video as new content drops)
- Monthly Telegram processing: automated, spot-check
- New video transcripts: 3-4 hrs per batch of 50 via existing pipeline
- Ecosystem repo updates: re-run pipeline on updated repos quarterly or on major releases
- Community PRs: review and merge
- Prompt tuning based on retrieval quality feedback

---

## Summary: The Effort Split

| Phase | Human Hours | LLM Processing | Cost |
|-------|-------------|-----------------|------|
| Repo structure + templates | 8-10 | 0 | $0 |
| Glossary + ecosystem catalog curation | 4-6 | 0 | $0 |
| Seed documents (4 concepts + 3 DeCo guides + LangSpec) | 4-6 | LangSpec split (if desired) | $0 — ✅ 4 concepts + 3 guides done |
| Processing scripts (TG + ecosystem + utilities) | 10-13 | 0 | $0 |
| Video adapter script | 1-2 | 0 | $0 |
| Telegram processing (8 years) | 3-5 (review) | ~100 monthly summaries | $2-5 |
| Video processing (450 videos, 9 batches) | **27-36** (speaker review, spot audit) | ~450 transcripts | ~$50-70 |
| Ecosystem code processing (55 repos) | 5-8 (review contract docs + patterns) | 246+ contract/overview docs + 14 pattern guides | ~$5 |
| ErgoForum archive (677 curated topics) | 0 | 677 topic docs + lean index | $0 — ✅ Done |
| Ergo Blog archive (701 posts) | 0 | 397 full-content posts + 304 stubs + clustered index | $0 — ✅ Done |
| Docs migration | 6-8 (review) | ~50-100 migrated docs | $1-3 |
| MCP server | 6-8 | 0 | $0 |
| GitHub Actions | 2-3 | 0 | $0 |
| Embeddings + indexing | 0 | Entire corpus | $0 |
| **Total** | **~76-105 hours** | **Bulk of content** | **~$58-88** |

Video processing remains the single largest human time commitment (~27-36 hours across 5 weeks). Ecosystem code processing adds ~5-8 hours of review but produces the most differentiated content in the entire knowledge base — production contract patterns from live dApps that no other Ergo resource consolidates.

The machines process the vast majority of content by volume: 450 video transcripts + 153 Telegram summaries (102 general + 51 dev) + 246+ ecosystem contract/overview docs + 14 cross-cutting pattern guides + 677 curated forum topics + 701 blog posts + full corpus embedding. Human-authored content so far: 4 concept docs + 3 DeCo-adapted guides (1,712 lines) + LangSpec integration + FRONTMATTER.md schema. The human work breaks down as: ~30% video processing (semi-automated), ~30% scaffolding and scripting (one-time, mostly complete), ~25% review and migration (diminishing over time), ~15% ecosystem code review (highest value per hour).
