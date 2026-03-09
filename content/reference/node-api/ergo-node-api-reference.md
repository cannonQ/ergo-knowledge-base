---
title: "Ergo Node REST API Reference"
category: reference
difficulty: intermediate
tags: [api, node, rest, utxo, wallet, transactions]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# Ergo Node API Reference

**Base URL:** `http://localhost:9053` (or `http://{IP}:9053` for remote)
**Method:** GET (read endpoints), POST (tx submission)
**Auth:** Some endpoints require `api_key` header (wallet operations). Read-only blockchain endpoints typically don't.
**Docs:** Swagger at `http://localhost:9053/swagger`

---

## Overview

The Ergo full node exposes a REST API for direct chain queries, wallet operations, and transaction submission. With `extraIndex = true` in `ergo.conf`, it provides indexed access to historical transactions by global index — the foundation for building custom scanners. This is the most reliable data source and has zero external dependencies.

**Key distinction from Explorer:** The node has the raw UTXO set and full transaction history. It doesn't have the higher-level indexing (token names, address grouping) that the Explorer provides. But it's authoritative — if data comes from your node, it's truth.

---

## Key Endpoints

### Node Info

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /info` | Node status | Returns `fullHeight`, `headersHeight`, `peersCount`, `appVersion` |
| `GET /blockchain/indexedHeight` | Extra-index sync status | Returns `indexedHeight` and `fullHeight`. If equal, fully indexed. |

### Block Data

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /blocks/at/{height}` | Block header IDs at height | Returns array of block IDs |
| `GET /blocks/{blockId}` | Full block with transactions | Heavy response — includes all TX details |
| `GET /blocks/{blockId}/transactions` | Block transactions only | Lighter than full block |

### Transaction Data (requires extraIndex)

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /blockchain/transaction/byIndex/{globalIndex}` | TX by global index | Sequential scanning. Index 0 = genesis TX |
| `GET /blockchain/transaction/byId/{txId}` | TX by ID | Full TX with inputs/outputs |

### Box Data (requires extraIndex)

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /blockchain/box/byId/{boxId}` | Box by ID | Includes `spentTransactionId` if spent |
| `GET /blockchain/box/range?offset={n}&limit={m}` | Box IDs by global index range | Returns array of box ID strings |
| `GET /blockchain/box/unspent/byAddress/{addr}` | Current UTXOs for address | No auth needed |
| `GET /utxo/byId/{boxId}` | Unspent box only | Returns 404 if spent — useful for checking UTXO status |

### Mempool

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `GET /transactions/unconfirmed?limit=N` | Pending transactions | Competition detection for SR/oracle |
| `POST /transactions` | Submit signed transaction | **Most reliable submission method** |

### Wallet (requires api_key)

| Endpoint | Description | Notes |
|----------|-------------|-------|
| `POST /wallet/transaction/sign` | Sign a transaction | Used by oracle-core, swap tools |
| `GET /wallet/boxes` | Wallet UTXOs | Filtered view of wallet's boxes |

---

## Scanner Pattern (Storage Rent Example)

The storage rent scanner established the pattern used for all subsequent scanners:

```python
def scan_block(height):
    # 1. Get block header IDs
    block_ids = requests.get(f"{NODE}/blocks/at/{height}").json()
    
    # 2. Get transactions for each block
    for block_id in block_ids:
        txs = requests.get(f"{NODE}/blocks/{block_id}/transactions").json()
        
        # 3. Check each transaction
        for tx in txs["transactions"]:
            for inp in tx["inputs"]:
                # Check spendingProof, box age, etc.
                if is_sr_claim(inp, height):
                    record_claim(tx, inp)
```

**Key fields per input:**
- `boxId` — the box being spent
- `spendingProof.proofBytes` — empty string for SR claims
- `value` — nanoERG in the box
- `assets` — tokens in the box

**Key fields per output:**
- `boxId`, `value`, `ergoTree`, `address`
- `assets[]` — tokens
- `creationHeight`
- `additionalRegisters`

---

## Wins

- **Authoritative data** — direct from the chain, no intermediary
- **extraIndex** — sequential scanning by global index enables full-chain backfills
- **No external dependencies** — runs on your own hardware
- **TX submission is reliable** — `/transactions` POST is the most trustworthy submission path (Explorer submission returned 200 but TXs often vanished)
- **Box range queries** — `GET /blockchain/box/range` enables batch box ID lookups
- **UTXO check** — `GET /utxo/byId/{boxId}` returns 404 for spent boxes, making it a quick spent/unspent check
- **Full block data** — every transaction with all inputs/outputs, no pagination needed

## Stumbling Blocks

- **extraIndex must be enabled** — add `extraIndex = true` to `ergo.conf`. Without it, `/blockchain/transaction/byIndex/` returns 404. Node must re-sync after enabling.
- **No token metadata** — the node doesn't know token names/decimals. You need Explorer or Crux for that.
- **No address-based transaction history** — can't easily ask "all TXs involving address X" without scanning blocks
- **Wallet endpoints need API key** — set `apiKeyHash` in `ergo.conf`, pass key via `api_key` header
- **Large responses** — full block queries can return massive JSON for blocks with many TXs
- **Rate limiting** — when scanning thousands of blocks, add small delays (0.05-0.1s) to avoid overwhelming your own node
- **Remote access** — by default only listens on localhost. Need to bind to `0.0.0.0` for remote access, and consider firewall rules
- **No filtering in block TX queries** — you get ALL transactions in a block. Filtering by ErgoTree/token must be done locally.

---

## Configuration

**ergo.conf additions for scanner use:**
```
scorex.restApi.bindAddress = "0.0.0.0:9053"  # Remote access
ergo.node.extraIndex = true                   # Enable indexed queries
```

**Verify indexing:**
```bash
curl http://localhost:9053/blockchain/indexedHeight
# Should return: {"indexedHeight": N, "fullHeight": N}
```
