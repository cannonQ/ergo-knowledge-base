# Ergo Knowledge Base (EKB)

MCP server for Ergo blockchain development. Semantic search across 550+ documents, 65 ecosystem projects, EIPs, ErgoScript reference, API references, and cookbook recipes.

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

## What's Inside

```
content/
  concepts/        # eUTXO, boxes, sigma protocols, storage rent
  patterns/        # Transaction building, headless dApp, ErgoPay, etc.
  ecosystem/       # 65 projects (Paideia, Spectrum, Rosen Bridge, ...)
  cookbook/
    tokens/        # Mint, transfer, burn (Fleet SDK)
    contracts/     # Simple send, timelock, multi-sig, state machine
    apis/          # Crux, ErgoWatch, Spectrum, Ronin API references
    queries/       # Python scripts: LP supply, price history, SR scanner
  reference/
    eips/          # 22 Ergo Improvement Proposals
    ergoscript/    # Built-in functions, types, context variables
    data-model/    # Box structure, registers, register decoding
    node-api/      # Ergo node REST API reference
    explorer-api/  # Explorer REST API reference
    graphql/       # Ergo GraphQL API reference
    p2p/           # Network protocol
  guides/          # Wallet setup, ErgoScript tutorials
  node/            # Node config, install, testnet, Swagger API
  sdks/            # Fleet SDK, AppKit, ergo-lib, Sigma.js, etc.
```

3,390+ chunks embedded with OpenAI `text-embedding-3-small` (1024 dims). Pure-JS cosine similarity search — no native dependencies.

## Local Development

```bash
git clone https://github.com/cannonQ/ergo-knowledge-base.git
cd ergo-knowledge-base/mcp-server
cp .env.local.example .env.local  # add your OPENAI_API_KEY
npm install && npm run dev
```

## License

[AGPL-3.0](LICENSE)
