---
title: "Ergo Explorer REST API Reference"
category: reference
difficulty: intermediate
tags: [api, explorer, rest, blocks, transactions, boxes, tokens]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# Ergo Explorer REST API Reference

**Base URL:** `https://api.ergoplatform.com/api/v1`
**Method:** GET (all endpoints)
**Auth:** None required
**Rate Limits:** Undocumented — appears lenient but use 0.15s+ delays for bulk queries
**Docs:** Swagger at `https://api.ergoplatform.com/api/v1/docs/`

---

## Overview

The Explorer API is the standard REST interface for querying the Ergo blockchain. It provides indexed, structured access to blocks, transactions, addresses, boxes, and tokens. Unlike the GraphQL endpoint, it returns richer metadata (rendered register values, token names/decimals) but has less flexible filtering. Backed by a PostgreSQL indexer that polls the Ergo node.

---

## Key Endpoints

### Blocks

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /blocks?offset={n}&limit=1` | Get block by offset | **offset is 0-indexed from genesis**. To get block at height H, use `offset=H-1&limit=1` |
| `GET /blocks/{blockId}` | Get block by header ID | Returns full block with transactions |

**Key fields returned:** `id`, `height`, `timestamp` (millis), `transactionsCount`, `miner.address`, `difficulty`, `minerReward`

**Stumbling block:** The `?height=` parameter does NOT filter to that height — it returns recent blocks paginated. Use `?offset={height-1}&limit=1` instead. This wasted significant debugging time.

### Transactions

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /transactions/{txId}` | Full transaction details | Includes inputs, outputs, confirmation count |
| `GET /mempool/transactions/byId/{txId}` | Check if TX is in mempool | Returns 404 if not in mempool |
| `GET /addresses/{addr}/transactions?limit=N` | TX history for address | Paginated, newest first |

### Boxes

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /boxes/unspent/byAddress/{addr}?limit=N` | Current UTXOs for address | Primary wallet balance query |
| `GET /boxes/unspent/byTokenId/{tokenId}` | Boxes holding a specific token | Find pool boxes, NFT holders |
| `GET /boxes/unspent/byErgoTree/{ergoTree}` | Boxes at a contract address | For smart contract queries |
| `GET /boxes/{boxId}` | Specific box details | Includes spending info if spent |

**Key fields returned:** `boxId`, `transactionId`, `value`, `creationHeight`, `settlementHeight`, `address`, `ergoTree`, `assets[]` (with `name`, `decimals`), `additionalRegisters`, `spentTransactionId`, `mainChain`

### Tokens

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /tokens/{tokenId}` | Token metadata | Returns name, description, decimals, emissionAmount |

---

## Proven Working Patterns

### Height → Timestamp Conversion
```python
url = f"https://api.ergoplatform.com/api/v1/blocks?offset={height-1}&limit=1"
resp = requests.get(url)
block = resp.json()["items"][0]
timestamp_ms = block["timestamp"]  # milliseconds since epoch
```

**Win:** This works reliably. We used it for bulk conversion (built a CSV of all block heights to timestamps).

**Stumbling block:** Initially tried `?height={H}` which returns paginated recent blocks, not the block at that height. The correct parameter is `offset` (0-indexed).

### Find Current Pool Box by Pool NFT
```python
url = f"https://api.ergoplatform.com/api/v1/boxes/unspent/byTokenId/{pool_nft_id}"
resp = requests.get(url)
pool_box = resp.json()["items"][0]
reserves = pool_box["assets"]
```

### Check Transaction Confirmation
```python
url = f"https://api.ergoplatform.com/api/v1/transactions/{tx_id}"
resp = requests.get(url)
confirmations = resp.json()["summary"]["confirmationsCount"]
```

### NFT Metadata from Issuance Box
```python
url = f"https://api.ergoplatform.com/api/v1/tokens/{token_id}"
resp = requests.get(url)
name = resp.json().get("name")
decimals = resp.json().get("decimals")
```

---

## Wins

- **Rich metadata** — token names, decimals, and rendered register values come back automatically
- **No auth** — fully public API
- **Swagger docs** available at `/api/v1/docs/`
- **Reliable** — has been running for years with good uptime
- **`spentTransactionId`** is available as a direct field (unlike GQL where you need `spentBy`)

## Stumbling Blocks

- **`?height=` parameter on /blocks is NOT a filter** — it returns paginated recent blocks. Use `?offset={height-1}&limit=1` instead. This is the single biggest gotcha.
- **No register value filtering** — you can't query "boxes where R4 = X." Must fetch all boxes and filter locally.
- **No ErgoTree template hash filtering** — must use the exact ErgoTree hex (GQL is better for template-based queries)
- **No historical box state** — can't query "what did this box look like at height X." Only current state or spent state.
- **TX submission via Explorer is unreliable** — Explorer returns 200 but TX may never make it to mempool. Always verify confirmation separately. Node submission (`/transactions`) is more reliable.
- **Pagination** — some endpoints default to small page sizes. Always specify `?limit=100` or higher.
- **CORS** — may not be set for browser-based requests. Use server-side fetches.
