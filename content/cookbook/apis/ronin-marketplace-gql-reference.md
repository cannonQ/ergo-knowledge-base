---
title: "Ronin Marketplace GraphQL Reference"
category: reference
difficulty: intermediate
tags: [api, graphql, ronin, sky-mavis, nft, marketplace]
author: CannonQ
source: original
updated: 2026-03-09
---
# Sky Mavis (Ronin) Marketplace GraphQL Reference

**Endpoint:** `https://marketplace-graphql.skymavis.com/graphql`
**Method:** POST with `Content-Type: application/json`
**Auth:** None required for public queries
**Rate Limits:** Undocumented — appears lenient
**Docs:** None official. Schema discovered via introspection.

---

## Overview

The Sky Mavis Marketplace GraphQL API provides access to NFT listings, sales history, and token data on the Ronin blockchain. Used to query Cyberverse Gen4 CyberCitizens and Cyberia Apartments collections. No official documentation exists — all query structures were discovered through GraphQL introspection and trial-and-error.

---

## Collection Addresses (Cyberverse on Ronin)

| Collection | Contract Address |
|------------|-----------------|
| CyberCitizen Gen4 | `0xfc5e0d385f97c8068acd7c4a3b2cd1f5bdea45f2` |
| Cyberia Apartments | `0x79b407be9ef20052f415118de76b5a877752ae80` |

---

## Proven Working Queries

### 1. Get Listed NFTs (with prices)
```graphql
{
  erc721Tokens(
    tokenAddress: "0xfc5e0d385f97c8068acd7c4a3b2cd1f5bdea45f2"
    from: 0
    size: 20
    auctionType: Sale
  ) {
    total
    results {
      tokenId
      name
      order {
        currentPrice
        maker
      }
    }
  }
}
```

**Notes:** Returns `total` (114 listed Gen4s at time of testing) and `results` array. Prices are in **wei** (18 decimals). `currentPrice` of `"15000000000000000000000"` = 15,000 RON.

### 2. Sales History
```graphql
{
  activities(
    tokenAddress: "0xfc5e0d385f97c8068acd7c4a3b2cd1f5bdea45f2"
    activityTypes: [Sale]
    size: 10
  ) {
    results {
      from
      to
      timestamp
      metadata
      asset {
        id
        address
      }
    }
  }
}
```

**Notes:** `activityTypes` is required. Price data lives in `metadata.price` or `metadata.item_price` (varies by sale type). Payment token address in `metadata.payment_token`.

### 3. Recent Sales
```graphql
{
  recentlySolds(
    tokenAddress: "0xfc5e0d385f97c8068acd7c4a3b2cd1f5bdea45f2"
    from: 0
    size: 5
  ) {
    total
    results {
      tokenId
    }
  }
}
```

### 4. Schema Introspection
```graphql
{
  __schema {
    queryType {
      fields {
        name
        args {
          name
          type { name kind ofType { name } }
        }
      }
    }
  }
}
```

### 5. Type Introspection (discover field names)
```graphql
{
  __type(name: "Erc721List") {
    fields { name type { name } }
  }
}
```

---

## curl Examples (Windows CMD)

```cmd
curl.exe -s -X POST https://marketplace-graphql.skymavis.com/graphql ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"{ erc721Tokens(tokenAddress: \\\"0xfc5e0d385f97c8068acd7c4a3b2cd1f5bdea45f2\\\", from: 0, size: 5, auctionType: Sale) { total results { tokenId name order { currentPrice maker } } } }\"}"
```

---

## Key Schema Discoveries

| Query | Returns Type | List Field |
|-------|-------------|------------|
| `erc721Tokens` | `Erc721List` | `results` (NOT `data`) |
| `activities` | Activity list | `results` |
| `recentlySolds` | Sales list | `results` |

**Critical:** The list field is `results`, not `data`. Using `data` returns a parsing error. This was discovered via type introspection after initial failures.

---

## Price Decoding

Prices are in **wei** format (18 decimals for RON):
```python
price_ron = int(metadata["price"]) / 1e18
# or
price_ron = int(metadata["item_price"]) / 1e18
```

Payment tokens:
- `0xe514d9deb7966c8be0ca922de8a064264ea6bcd4` = WRON (Wrapped RON)

---

## Wins

- **Introspection enabled** — full schema discovery without documentation
- **No auth required** — public queries just work
- **Sales history available** — `activities` with `activityTypes: [Sale]` gives complete trade history
- **Listing data** — current floor price derivable from sorted `erc721Tokens` results
- **Simple pagination** — `from` and `size` parameters

## Stumbling Blocks

- **No official documentation** — everything discovered by trial-and-error
- **`results` not `data`** — the list field name doesn't match typical GraphQL conventions. Error message wasn't helpful: `"no field 'data' in type 'Erc721List'"`
- **Price field inconsistency** — some sales have `metadata.price`, others have `metadata.item_price`. Need to check both.
- **Wei format prices** — easy to get wrong decimal places. Gen4 floor of `"293000000000000000000"` = 293 RON, not 293 billion.
- **Moralis alternative was incomplete** — Moralis API couldn't find Apartments floor price or sales data on Ronin. Sky Mavis GQL is the authoritative source.
- **No floor price endpoint** — must query listings sorted by price and take the minimum. No pre-computed floor.
