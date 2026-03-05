---
title: codeUTXO/ergo-price-mcp — Overview
description: Ergo Price MCP Server — 12 tools for price/market/asset data via CruxFinance API, multi-tier caching, MCPO proxy support
tags: [codeutxo, ergo-price-mcp, infrastructure, python]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repo: "https://github.com/codeUTXO/ergo-price-mcp"
project: codeutxo-ergo-price-mcp
group: infrastructure
priority: medium
languages: [python]
contract_count: 0
pattern_match_count: 4
---
# codeUTXO/ergo-price-mcp — Developer Overview

---

## Overview

**ergo-price-mcp** is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server written in Python that gives LLM assistants (e.g., Claude Desktop) structured, real-time access to Ergo ecosystem market data. It exposes 12 discrete tools covering ERG spot prices, token metadata, Spectrum DEX trading statistics, gold oracle history, and OHLCV chart data — all sourced from the CruxFinance API, CoinGecko, and Spectrum DEX endpoints. Within the Ergo ecosystem its primary role is **infrastructure tooling**: it acts as a translation layer between AI agents and on-chain/off-chain market data, requiring no direct node connection while still surfacing data that is deeply rooted in Ergo's eUTXO-based DeFi stack (SigmaUSD gold oracle feeds, Spectrum AMM pricing, native token metadata keyed by Token ID).

Because Ergo's eUTXO model means that market-relevant state (AMM pool Boxes, oracle pool Boxes carrying Register-encoded price data, token emission Boxes) is read from an indexed off-chain view rather than queried from contract storage slots, a price server naturally sits at the API layer rather than speaking directly to an Ergo node. ergo-price-mcp formalises that boundary: it is a **headless data adapter** that any MCP-aware agent or REST client can consume without understanding ErgoScript, Box structure, or Registers. This makes it a practical entry point for AI tooling built on top of the Ergo DeFi ecosystem.

The project ships with an optional **MCPO proxy** (MCP-to-OpenAPI bridge) that re-exposes every MCP tool as a plain HTTP POST endpoint, enabling non-MCP clients — dashboards, CI pipelines, other microservices — to consume the same 12 tools through a Bearer-authenticated REST interface. This dual-transport design (stdio for native MCP clients, HTTP for everything else) reflects a pragmatic approach to infrastructure reuse across different integration contexts.

---

## Architecture

### Component Map

```
┌─────────────────────────────────────────────────────────┐
│  Consumers                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │ Claude Desktop│   │ REST Client  │   │ AI Agent   │  │
│  │  (stdio/MCP) │   │  (HTTP POST) │   │  (MCP SDK) │  │
│  └──────┬───────┘   └──────┬───────┘   └─────┬──────┘  │
└─────────┼──────────────────┼─────────────────┼─────────┘
          │ MCP stdio        │                 │ MCP stdio
          │            ┌─────▼──────┐          │
          │            │ MCPO Proxy │          │
          │            │ (uvx mcpo) │          │
          │            │ port:$PORT │          │
          │            └─────┬──────┘          │
          │                  │ MCP stdio       │
          └──────────────────▼─────────────────┘
                    ┌─────────────────┐
                    │  MCP Server     │
                    │  server.py      │
                    │  12 Tool Defs   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────┐
        │  tools/  │  │  cache/  │  │   api/       │
        │ (12 tool │  │ Multi-   │  │ CRUX Finance │
        │  impls)  │  │ tier TTL │  │ CoinGecko    │
        └──────────┘  └──────────┘  │ Spectrum DEX │
                                    └──────┬───────┘
                                           │ HTTPS
                              ┌────────────▼────────────┐
                              │   External APIs          │
                              │  api.cruxfinance.io      │
                              │  api.coingecko.com       │
                              │  api.spectrum.fi         │
                              └─────────────────────────┘
```

### Key Components

| Component | Location | Responsibility |
|-----------|----------|---------------|
| **MCP Server** | `src/ergo_price_mcp/server.py` | Registers all 12 tools with the MCP runtime; handles stdio transport lifecycle |
| **Tool Implementations** | `src/ergo_price_mcp/tools/` | One module per logical tool group (price, asset, market); each tool validates input parameters and delegates to the API client |
| **API Client** | `src/ergo_price_mcp/api/` | Wraps CruxFinance, CoinGecko, and Spectrum DEX HTTP calls; implements retry with exponential backoff and circuit-breaker fallback |
| **Caching Layer** | `src/ergo_price_mcp/cache/` | Multi-tier LRU cache with per-data-class TTLs; thread-safe for async concurrent tool calls |
| **Configuration & Logging** | `src/ergo_price_mcp/utils/` | Reads `.env` / environment variables; structured logging with configurable verbosity |
| **MCPO Proxy** | External (`uvx mcpo`) | Wraps the MCP server's stdio interface and re-exposes each tool as an OpenAPI-compatible HTTP POST endpoint |

### Data Flow

1. **LLM tool call** arrives over MCP (stdio) or as an HTTP POST to the MCPO proxy.
2. The MCPO proxy, if present, translates the HTTP request into an MCP `tools/call` message and forwards it over stdio to the MCP server process.
3. `server.py` dispatches the call to the appropriate tool module in `tools/`.
4. The tool module checks the **caching layer** first (keyed by tool name + parameter hash). On a cache hit it returns immediately.
5. On a cache miss the **API client** issues an HTTPS request to the relevant external endpoint (CruxFinance for most tools, CoinGecko for `get_erg_price`/`get_erg_history`, Spectrum DEX for `get_spectrum_price*`).
6. The API response is validated, stored in the cache under the appropriate TTL tier, and returned to the MCP runtime as a structured tool result.
7. The MCP runtime serialises the result back to the caller (Claude Desktop, MCPO proxy, etc.).

---

## Smart Contracts

This project contains **no ErgoScript contracts and deploys no on-chain Boxes**. It is a pure off-chain infrastructure component.

It does, however, surface data that originates from on-chain contract state:

- **Gold Oracle data** (`get_gold_oracle_history`) reflects prices posted by the Ergo Oracle Pool contracts. Oracle pool Boxes carry price data in their **Registers** (typically `R4`), and the CruxFinance API indexes these Box updates into a queryable time series. ergo-price-mcp exposes that indexed history without re-implementing oracle pool ErgoScript logic.
- **Token metadata** (`get_asset_info`, `get_token_info`, `get_circulating_supply`) is keyed by **Token ID** (following Ergo's Token ID rule: the ID of the issuance transaction's first input Box). The project treats Token IDs as opaque string parameters; it does not parse ErgoTree or decode Registers directly.
- **Spectrum DEX prices** (`get_spectrum_price`, `get_spectrum_price_stats`) reflect AMM pool state. Spectrum pools are eUTXO Boxes governed by ErgoScript contracts; the pricing data exposed here is derived from those Box states as indexed by Spectrum's own off-chain layer.

Developers integrating this server with SigmaUSD,