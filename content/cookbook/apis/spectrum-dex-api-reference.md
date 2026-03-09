---
title: "Spectrum DEX API Reference"
category: reference
difficulty: intermediate
tags: [api, spectrum, dex, lp-pools, amm, defi]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# Spectrum DEX API Reference

**Base URL:** `https://api.spectrum.fi/v1`
**Method:** GET
**Auth:** None required
**Rate Limits:** Undocumented
**Docs:** Partial Swagger at `https://api.spectrum.fi/docs`

---

## Overview

The Spectrum (formerly ErgoDEX) API provides current pool state, market prices, and trading volume data for the Spectrum AMM on Ergo. It was the primary DEX API but has become unreliable — the API went down multiple times in 2025 and its historical data capabilities are limited. We used it for pool discovery and current price snapshots, but ultimately moved to Crux for historical prices and direct on-chain queries for pool state.

**Status: Partially deprecated.** Some endpoints work, some don't. Use Crux or on-chain queries as primary data sources.

---

## Key Endpoints

### Pool Stats (Current State)

```
GET /v1/amm/pools/stats
```

**Returns:** Array of all pools with current reserves, TVL, volume.

**WARNING:** Despite accepting `from` and `to` timestamp parameters, this endpoint **always returns current pool state regardless of timestamps**. We discovered this the hard way — a pool created in August 2024 showed data for January 2022 queries. The timestamps are ignored.

### Market Prices (Historical — WORKS)

```
GET /v1/price-tracking/markets?from={ms}&to={ms}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `from` | integer | Start of window (UNIX ms) |
| `to` | integer | End of window (UNIX ms) |

**Returns:**
```json
[
  {
    "id": "xId_yId",
    "baseId": "...",
    "baseSymbol": "ERG",
    "quoteId": "...",
    "quoteSymbol": "SigUSD",
    "lastPrice": 0.467111,
    "baseVolume": { ... },
    "quoteVolume": { ... }
  }
]
```

**This endpoint actually returns historical data.** January 2022 returns 8 pools. December 2024 returns 100+ pools with different prices. Confirmed working by comparing `lastPrice` across dates.

### AMM Pool List

```
GET /v1/amm/pools
```

Returns all LP pools with current state.

---

## Pool Box Anatomy (On-Chain)

Since the API is unreliable, direct on-chain pool queries became essential. Here's the pool box structure:

### N2T (Native-to-Token) Pool Box
```
ErgoTree Template Hash: d19e23d1f7a101fef63861cd303ec5e1c1db93e9e1c244178e83556c4d082a49

Assets (in order):
  [0] Pool NFT (amount: 1)         — unique pool identifier
  [1] LP Token (amount: remaining)  — unclaimed LP tokens
  [2] Token Y (amount: reserve)     — the traded token

Value: ERG reserve (nanoERG)

R4: Fee numerator (e.g., 997 = 0.3% fee, 995 = 0.5% fee)
```

### T2T (Token-to-Token) Pool Box
```
ErgoTree Template Hash: 8b159b63f668c5782400b6b0a0a11db995888c0153a29e30594c8d88d5b9430c

Assets (in order):
  [0] Pool NFT (amount: 1)
  [1] LP Token (amount: remaining)
  [2] Token X (amount: reserve)
  [3] Token Y (amount: reserve)

Value: Minimal ERG for box storage

R4: Fee numerator
```

### LP Valuation Formula
```
Max LP Supply = 9,223,372,036,854,774,807  (constant for ALL Spectrum pools = 2^63 - 1)
Circulating LP = Max LP Supply - LP tokens in pool box
Your Value = (Your_LP_Balance / Circulating_LP) × Pool_Total_Value
Pool_Total_Value = (Reserve_X × Price_X) + (Reserve_Y × Price_Y)
```

### AMM Swap Math (Constant Product)
```
Buy Token (ERG → Token):
  output_amount = (reserve_Y × input_ERG × fee_num) / (reserve_X × 1000 + input_ERG × fee_num)

Sell Token (Token → ERG):
  output_erg = (reserve_X × input_token × fee_num) / (reserve_Y × 1000 + input_token × fee_num)
```

---

## Wins

- **`/v1/price-tracking/markets` genuinely returns historical data** — this was a major discovery. Pool count and prices differ across dates.
- **Pool template hashes** — N2T and T2T pools have distinct ErgoTree template hashes, enabling bulk discovery via GQL
- **LP valuation formula** — Max LP supply is constant (2^63 - 1), simplifying circulating LP calculation
- **Direct pool box queries** work reliably via Explorer/GQL with the Pool NFT token ID

## Stumbling Blocks

- **`/v1/amm/pools/stats` ignores timestamp parameters** — returns current state regardless of `from`/`to`. This invalidated an entire historical backfill attempt. Only discovered because a pool created in Aug 2024 showed data for Jan 2022.
- **API availability is spotty** — went down multiple times in 2025. No SLA, no status page.
- **No historical pool reserves endpoint** — current reserves only. For historical LP valuation, must query spent pool boxes on-chain (complex UTXO tracking)
- **Historical pool state requires UTXO chain walking** — pool boxes are spent/recreated on every swap. Finding "pool state at height X" means querying ALL boxes (spent+unspent) containing the Pool NFT, building a timeline of creation/spending heights, then finding which box was active at your target height. Never fully solved.
- **Pool box disambiguation** — when querying by Pool NFT ID via Explorer, you sometimes get the current box plus recently spent predecessors. Need to filter for the actual current UTXO.
- **Fee numerator varies by pool** — most are 997 (0.3% fee) but some use 995, 990, or others. Always read R4 from the pool box.
