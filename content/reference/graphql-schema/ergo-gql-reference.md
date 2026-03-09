---
title: "Ergo GraphQL API Reference"
category: reference
difficulty: intermediate
tags: [api, graphql, gql, boxes, queries]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# Ergo GraphQL API Reference

**Endpoint:** `https://gql.ergoplatform.com/`
**Alt Endpoint:** `https://explore.sigmaspace.io/api/graphql`
**Method:** POST with `Content-Type: application/json`
**Auth:** None required
**Rate Limits:** Unknown — no documented limits, but be reasonable

---

## Overview

The Ergo GraphQL API provides flexible querying of on-chain box, transaction, and token data. It is the single best tool for bulk data extraction on Ergo — far more flexible than the Explorer REST API for filtering by ErgoTree, token ID, registers, and spent/unspent status. No official documentation exists; everything below was discovered through introspection and trial-and-error.

---

## How to Use

**Browser:** Paste queries directly into `https://gql.ergoplatform.com/` — it has a built-in GraphQL Playground UI.

**curl:**
```bash
curl -s -X POST https://gql.ergoplatform.com/ \
  -H "Content-Type: application/json" \
  -d '{"query": "{ boxes(tokenId: \"YOUR_TOKEN_ID\", spent: false) { boxId value assets { tokenId amount } } }"}'
```

**Python:**
```python
import requests
resp = requests.post("https://gql.ergoplatform.com/",
    json={"query": query_string, "variables": {}},
    headers={"Content-Type": "application/json"},
    timeout=15)
data = resp.json().get("data", {})
```

---

## Box Schema (discovered via introspection)

Available fields on the `Box` type:

| Field | Type | Description |
|-------|------|-------------|
| `boxId` | String! | Unique box identifier |
| `transactionId` | String! | TX that created this box |
| `value` | String! | nanoERG value |
| `creationHeight` | Int! | Block height when created |
| `index` | Int! | Output index in transaction |
| `ergoTree` | String! | Contract script (hex) |
| `ergoTreeTemplateHash` | String! | Hash of contract template |
| `address` | String! | Encoded address |
| `additionalRegisters` | JSON! | R4-R9 register values |
| `assets` | [Asset!]! | Tokens in this box |
| `settlementHeight` | Int! | Block height when settled |
| `globalIndex` | Int! | Global box index |
| `mainChain` | Boolean! | Whether on main chain |
| `headerId` | String! | Block header ID |
| `spentBy` | Input | Spending input (null if unspent) |
| `beingSpent` | Boolean! | Mempool spending status |
| `transaction` | Transaction! | Parent transaction |

**Fields that DO NOT exist** (common mistakes):
- ~~`spentTransactionId`~~ → Use `spentBy { transactionId }` instead
- ~~`spentHeight`~~ → Use `spentBy` to get spending TX, then query that TX for height

---

## Box Query Parameters

```graphql
boxes(
  address: String        # Filter by encoded address
  ergoTree: String       # Filter by ErgoTree hex (exact match)
  ergoTreeTemplateHash: String  # Filter by template hash
  tokenId: String        # Filter by token ID in box
  boxId: String          # Filter by specific box ID
  spent: Boolean         # true = spent only, false = unspent only
  minHeight: Int         # Minimum creation height
  maxHeight: Int         # Maximum creation height
  take: Int              # Pagination limit (default ~20)
  skip: Int              # Pagination offset
)
```

---

## Proven Working Queries

### 1. Find current holder of a token
```graphql
{
  boxes(tokenId: "YOUR_TOKEN_ID", spent: false) {
    boxId
    address
    value
    assets { tokenId amount }
    creationHeight
  }
}
```

### 2. All spent boxes from a contract (for marketplace sales extraction)
```graphql
{
  boxes(
    ergoTree: "PASTE_ERGOTREE_HEX"
    spent: true
    take: 200
    skip: 0
  ) {
    boxId
    transactionId
    value
    creationHeight
    settlementHeight
    assets {
      tokenId
      amount
    }
    additionalRegisters
    spentBy { transactionId }
  }
}
```
Paginate by incrementing `skip` by 200 until results are empty.

### 3. Boxes by address with height filter
```graphql
{
  boxes(
    address: "9f4QF8jQSBpGULoi2hHCErnpMgqHJuqsXqGGF3UFHGUZQY8RMCH"
    minHeight: 1690000
  ) {
    boxId
    transactionId
    creationHeight
    value
    additionalRegisters
  }
}
```

### 4. Find all LP pool boxes by template hash
```graphql
{
  boxes(
    ergoTreeTemplateHash: "d19e23d1f7a101fef63861cd303ec5e1c1db93e9e1c244178e83556c4d082a49"
    spent: false
    take: 200
    skip: 0
  ) {
    boxId
    address
    value
    creationHeight
    assets { tokenId amount }
    additionalRegisters
  }
}
```
N2T pool template: `d19e23d1f7a101fef63861cd303ec5e1c1db93e9e1c244178e83556c4d082a49`
T2T pool template: `8b159b63f668c5782400b6b0a0a11db995888c0153a29e30594c8d88d5b9430c`

### 5. Token metadata lookup
```graphql
{
  tokens(tokenId: "YOUR_TOKEN_ID") {
    boxId
    name
    decimals
  }
}
```

### 6. Transaction outputs
```graphql
{
  transactions(transactionId: "TX_ID") {
    transactionId
    inclusionHeight
    outputs {
      boxId
      value
      address
      assets { tokenId amount name decimals }
      additionalRegisters
    }
  }
}
```

### 7. Schema introspection (discover available fields)
```graphql
{
  __type(name: "Box") {
    fields { name type { name kind } }
  }
}
```

```graphql
{
  __type(name: "Query") {
    fields { name args { name type { name } } }
  }
}
```

---

## Wins

- **ErgoTree filtering** is the killer feature — lets you query all boxes from a smart contract (MewMart, SkyHarbor, LP pools) without knowing individual addresses
- **ergoTreeTemplateHash** filtering lets you find all pools of a given type (N2T vs T2T) in one query
- **spent: true/false** combined with ErgoTree = complete marketplace history extraction
- **Pagination** via `take`/`skip` works reliably up to ~200 per page
- **No auth** required — fully public
- **Introspection** is enabled — you can discover the schema dynamically

## Stumbling Blocks

- **No official documentation** — everything discovered via introspection and trial-and-error
- **`spentTransactionId` doesn't exist** — this is the #1 gotcha. Use `spentBy { transactionId }` instead
- **`maxHeight` doesn't reliably filter historical state** — for spent boxes, it doesn't show you "what existed at height X." You need to query all boxes (spent+unspent) and filter by `creationHeight` yourself
- **`data` vs `results`** field naming varies by type — always introspect first
- **Large result sets** can timeout — keep `take` at 200 or less
- **Register values are raw hex** — you need a decoder (zigzag VLQ for integers, Coll[Byte] for strings)
- **The `height` parameter on the Explorer REST API is NOT the same as GQL's `minHeight`/`maxHeight`**
- **Address vs ErgoTree** — some contracts embed constants (like seller PK) into the ErgoTree, making each listing have a unique ErgoTree. In those cases, query by the factory/proxy address instead
