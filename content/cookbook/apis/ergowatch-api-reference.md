---
title: "ErgoWatch API Reference"
category: reference
difficulty: intermediate
tags: [api, ergowatch, analytics, supply, rich-list]
author: CannonQ
source: original
updated: 2026-03-09
---
# ErgoWatch API Reference

**Base URL:** `https://api.ergo.watch`
**Frontend:** `https://ergo.watch`
**Method:** GET
**Auth:** None required
**Docs:** Swagger at `https://api.ergo.watch/docs` (renders client-side only — can't fetch remotely)
**Source:** `https://github.com/abchrisxyz/ergowatch`

---

## Overview

ErgoWatch is a community-built Ergo blockchain indexer and analytics platform maintained by a single developer (abchrisxyz). It provides pre-computed time series data for network health metrics, tokenomics, and the SigmaUSD dashboard. The indexer (`ew`) is written in Rust, syncs from an Ergo node, and writes to PostgreSQL. A FastAPI layer serves the REST API (labeled "legacy" in the README). The frontend (SvelteKit) connects directly to Postgres.

**Status: At risk.** The API is called "legacy." Single-maintainer project with no announced shutdown date but also no guarantees. This motivated our strategy to backfill all available data into Supabase before it potentially goes dark.

---

## Known Endpoints (reverse-engineered)

The Swagger UI renders client-side, so the full endpoint list isn't fetchable via API. These were discovered from the frontend source, the `tidyergo` R package, and GitHub issues.

### Address Metrics

| Endpoint (presumed) | Description |
|---------------------|-------------|
| `/api/v0/addresses/p2pk/count?bal_ge=X` | P2PK wallet count at balance tier |
| `/api/v0/addresses/contracts/count` | Contract address count |
| `/api/v0/addresses/balance-history/{address}` | Historical balance for any address |

Balance tier parameters: `bal_ge` (balance greater/equal), `bal_lt` (balance less than), `token_id` (filter by token).

### Supply / Emission

| Endpoint (presumed) | Description |
|---------------------|-------------|
| `/api/v0/tokens/{token_id}/supply` | Emitted, circulating, burned supply |
| `/api/v0/emission/...` | Emission schedule and inflation data |

### Network Metrics

| Endpoint (presumed) | Description |
|---------------------|-------------|
| UTXO count over time | Total unspent boxes on chain |
| Transfer volume | ERG moved per day/block |
| Transaction count | Daily TX count |

### SigmaUSD Dashboard

| Endpoint (presumed) | Description |
|---------------------|-------------|
| SigUSD circulating supply | Over time |
| SigRSV circulating supply | Over time |
| Oracle price history | ERG/USD from oracle pool |
| Reserve ratio | Over time |
| Mint/redeem activity | Historical |

### CEX Tracking

| Endpoint (presumed) | Description |
|---------------------|-------------|
| Exchange balances | Labeled addresses (KuCoin, Gate.io) |

---

## Data Available on ergo.watch Frontend

**Dashboards:**
- Emission — circulating supply, block reward, inflation rate
- SigmaUSD — SigUSD/SigRSV supply, oracle price, reserve ratio
- Sync status

**Charts (daily time series, back to genesis):**
- Address counts at balance tiers (≥0, ≥0.001, ≥0.01, ≥0.1, ≥1, ≥10, ≥100 ERG)
- Transfer volume
- UTXO count

**Lists:**
- Rich list / top holders

---

## Backfill Strategy

The plan for preserving ErgoWatch data:

1. **Hit API endpoints** from your local browser (Swagger loads at `https://api.ergo.watch/docs`)
2. **Catalog every endpoint** — screenshot or copy the full list
3. **Write a Python backfill script** that pulls all time series data and writes to Supabase
4. **Your own scanners** take over going forward for continued data

Alternatively, run the `ew` Rust indexer against your own node to reproduce the entire database locally.

---

## Estimated Data Size

- ~2,400 rows per metric (daily data × 6.5 years)
- ~20-30 metrics = ~50,000-75,000 rows total
- Well under Supabase free tier limits
- Your SR scanner (437K rows) is already larger than the entire ErgoWatch backfill would be

---

## What ErgoWatch Does NOT Track

- DEX swap data (Spectrum/Dexy trades, volumes, pool reserves)
- Oracle pool reward data
- NFT marketplace activity
- Rosen Bridge transfers
- Gluon/neutron/proton activity
- DuckPools lending activity
- Storage rent claims (your scanner fills this gap)

---

## Wins

- **Pre-computed aggregates** — address tier counts, supply data, and SigmaUSD metrics are expensive to derive from raw chain data. ErgoWatch has years of this computed.
- **Long history** — data back to genesis (2019)
- **Open source** — full Rust indexer available to self-host
- **Public node** at `node.ergo.watch` (separate from the API)

## Stumbling Blocks

- **No official API documentation accessible remotely** — Swagger renders client-side only. Can't fetch OpenAPI spec via curl or web_fetch.
- **"Legacy" API label** — the developer considers it legacy. Could disappear.
- **Single maintainer** — bus factor of 1
- **Frontend connects to Postgres directly** — the API doesn't necessarily expose everything the frontend shows
- **Endpoint paths unconfirmed** — the exact `/api/v0/` routes haven't been fully validated. Need to visit Swagger in a browser to confirm.
- **No known rate limits** — but single-maintainer infra means be respectful with bulk queries
