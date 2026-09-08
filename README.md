# Ergo Knowledge Base (EKB)

MCP server for Ergo blockchain development. Semantic search across 570+ documents, 65 ecosystem projects, EIPs, ErgoScript reference, API references, and cookbook recipes.

**Setup instructions:** [ergo-knowledge-base.vercel.app](https://ergo-knowledge-base.vercel.app/)

## Quick Start

Add to your MCP config (Claude Code, Gemini CLI, Codex CLI, Cursor, VS Code, Windsurf, Cline):

```json
{
  "mcpServers": {
    "ergo-code": {
      "url": "https://ergo-knowledge-base.vercel.app/api/mcp"
    }
  }
}
```

## Tools

| Tool | Description | Example input |
|------|-------------|---------------|
| `search_docs` | Semantic vector search across all content | `"how do oracle pools work?"` |
| `get_concept` | Core Ergo concepts | `"sigma-protocols"`, `"eutxo-model"` |
| `get_contract` | Project overview + contract deep-dives. Ask for a project to get its overview and contract list, then drill into a specific contract to learn how it works | `"dexy"`, `"sigmausd"`, `"rosen-bridge"` |
| `get_pattern` | Cross-cutting dev patterns | `"transaction-building"`, `"headless-dapp"` |
| `get_cookbook` | Code recipes (ErgoScript + Fleet SDK) | `"mint-token"`, `"timelock"`, `"multi-sig"` |
| `get_eip` | Ergo Improvement Proposals by number | `"4"`, `"20"`, `"eip-6"` |
| `get_ergoscript_ref` | ErgoScript language reference | `"built-in-functions"`, `"types"`, `"context-variables"` |
| `list_projects` | Retrieves the master list of all 65 ecosystem projects | *(no input)* |
| `get_skill` | Complete actionable skill docs (returned in full, not chunked) | `"nautilus"`, `"babel-fees"`, `"plasma-avl"`, `"list"` |
| `audit_contract` | Pass 1: Initial ErgoScript security audit with full EKB context | ErgoScript code + optional description |
| `audit_verify` | Pass 2: Independent verification of Pass 1 findings — catches false positives and missed issues | ErgoScript code + Pass 1 findings |

## Skills

Skills are complete, step-by-step instruction documents returned in full (not chunked). Unlike `search_docs` which returns the most relevant fragments, `get_skill` returns the entire document so instructions can be followed end-to-end.

Available skills:
- **nautilus** — Nautilus wallet dApp connector integration (EIP-12)
- **babel-fees** — Babel fee implementation (pay tx fees in tokens instead of ERG)
- **fleet-sdk** — Transaction building with Fleet SDK
- **appkit** — AppKit code generation patterns
- **ergo-wasm** — ergo-lib-wasm toolkit usage
- **node-deployment** — Ergo node setup and configuration
- **eip004** — EIP-4 NFT/token operations
- **plasma-avl** — AVL tree operations with Plasma-Toolkit (mainnet patterns)
- **scala-test-harness** — Scala/AppKit test harness patterns (GroupElement vs SigmaProp, HEIGHT off-by-one, error→fix reference)
- **contract-audit-engagement** — Financial-audit method for contract sets: value ledger of every spend path, fixed procedure checklist, two independent passes with burden-on-safe adjudication, severity matrix, workpapers, retest, sign-off

Pass `"list"` to `get_skill` to see all available skills at any time.

## Contract Auditing

Two independent tools implement a two-pass audit framework:

1. **`audit_contract`** (Pass 1) — Returns security context (9 known vulnerability categories, secure design patterns, LLM pitfall calibration, and the Audit Program: debit-side procedure checklist, pre-named trap register T1–T19 from real findings, severity matrix) plus EKB documentation dynamically matched to your contract's patterns. The LLM performs the initial audit using this grounding data.

2. **`audit_verify`** (Pass 2) — Takes the original code and your Pass 1 findings. Returns the same security context but with **independent reviewer framing**: *"Another auditor produced these findings. Assume they made mistakes."* This eliminates confirmation bias and catches false positives and missed issues.

The two-tool split means Pass 2 approaches the contract fresh — or in Claude Code, you can spawn a subagent for Pass 2 (literally separate context window). Works with any LLM: Claude, Gemini, GPT, etc.

For any contract that holds or moves funds, run Pass 1 **twice in independent contexts** before Pass 2, and adjudicate every disagreement with the burden on the side that said safe. A single Pass 1 declared the Dexy LP cluster clean while the pool was being drained. See the `contract-audit-engagement` skill for the full method.

## What to Ask

**Beginner questions:**
- "How does the eUTXO model work on Ergo?"
- "How do I mint an NFT with Fleet SDK?"
- "What is EIP-4?"

**Building contracts:**
- "Show me a timelock contract with refund"
- "How do I build a multi-sig guard in ErgoScript?"
- "What are the ErgoScript built-in functions?"

**Ecosystem research:**
- "How does SigmaUSD maintain its peg?"
- "What contracts does Rosen Bridge use?"
- "List all ecosystem projects"

**Pattern lookups:**
- "How does EIP-12 dApp connector work?"
- "What's the singleton NFT state machine pattern?"

**Skills (full step-by-step docs):**
- "Get the nautilus skill" → complete Nautilus wallet integration guide
- "Get the babel-fees skill" → Babel fee implementation from scratch
- "Get the plasma-avl skill" → AVL tree operations on mainnet

**Contract auditing (two-pass):**
- Call `audit_contract` with ErgoScript code + optional description → LLM performs Pass 1 audit
- Call `audit_verify` with the code + Pass 1 findings → independent verification catches false positives and missed issues

## What's Inside

```
content/
  concepts/        # eUTXO, boxes, sigma protocols, storage rent
  patterns/        # Transaction building, headless dApp, ErgoPay, etc.
  ecosystem/       # 65 projects (Paideia, Spectrum, Rosen Bridge, ...)
  cookbook/
    tokens/        # Mint, transfer, burn (Fleet SDK)
    contracts/     # Simple send, timelock, multi-sig, state machine
    apis/          # Crux, ErgoWatch, Spectrum API references
    queries/       # Python/JS: LP supply, NFT scraper, buyback bot, SR scanner
  reference/
    eips/          # 22 Ergo Improvement Proposals
    ergoscript/    # Built-in functions, types, context variables, audit context
    data-model/    # Box structure, registers, register decoding
    node-api/      # Ergo node REST API reference
    explorer-api/  # Explorer REST API reference
    graphql/       # Ergo GraphQL API reference
    p2p/           # Network protocol
  skills/          # Babel fees, Nautilus, Fleet SDK, AppKit, WASM, AVL, node deployment
  guides/          # Wallet setup, ErgoScript tutorials, toolchain guides
  node/            # Node config, install, testnet, Swagger API
  sdks/            # Fleet SDK, AppKit, ergo-lib, Sigma.js, etc.
```

3,580+ chunks embedded with OpenAI `text-embedding-3-small` (1024 dims). Pure-JS cosine similarity search — no native dependencies.

## Sources & Attribution

This knowledge base curates, extends, and enriches content from across the Ergo ecosystem:

| Source | Content | Notes |
|--------|---------|-------|
| [ergoplatform/ergodocs](https://github.com/ergoplatform/ergodocs) | Node docs, data model, ErgoScript tutorials, wallet guides | Community documentation |
| [ergoplatform/eips](https://github.com/ergoplatform/eips) | Ergo Improvement Proposals (EIP-1 through EIP-44) | Public standards |
| 65 ecosystem project repos | Contract analyses auto-generated from source code | Links to each source repo in file frontmatter |
| [Degens-World/Ergo-Skills](https://github.com/Degens-World/Ergo-Skills) | 7 actionable skill documents (Nautilus, Fleet SDK, Babel fees, AppKit, WASM, EIP-4, node deployment) | MIT |
| [Degens-World/Ergo-Context](https://github.com/Degens-World/Ergo-Context) | ErgoScript audit calibration data (known issues, LLM pitfalls, secure patterns) | MIT |
| Original contributions | Concepts, patterns, cookbook recipes, query scripts, toolchain guides, Plasma-AVL skill, two-pass audit methodology | AGPL-3.0 |

Every file includes `source` and `source_url` frontmatter fields tracing back to its origin.


## Local Development

```bash
git clone https://github.com/cannonQ/ergo-knowledge-base.git
cd ergo-knowledge-base/mcp-server
cp .env.local.example .env.local  # add your OPENAI_API_KEY
npm install && npm run dev
```

## License

[AGPL-3.0](LICENSE)
