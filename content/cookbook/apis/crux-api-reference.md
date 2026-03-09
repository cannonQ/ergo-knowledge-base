---
title: "Crux Finance API Reference"
category: reference
difficulty: intermediate
tags: [api, crux-finance, spectrum, token-prices, defi]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# Crux Finance API Reference

**Base URL:** `https://api.cruxfinance.io`
**Method:** GET
**Auth:** None required
**Rate Limits:** Undocumented — use 0.15s+ delays between calls for bulk queries
**Docs:** Swagger at `https://api.cruxfinance.io/docs/`

---

## Overview

Crux Finance provides the only reliable historical token price API on Ergo. It indexes Spectrum DEX trades and calculates token prices in ERG, USD, and USE. Useful for building historical price databases across the Ergo token ecosystem. Crux also provides current pool data and token information.

**Status note:** Crux changed hands in late 2025. The API remains operational but with no guarantees on long-term availability — consider backing up any critical data to your own infrastructure.

---

## Key Endpoints

### Token Price (Historical)

```
GET /spectrum/price?token_id={id}&time_point={ms}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `token_id` | string | Ergo token ID (64-char hex) |
| `time_point` | integer | UNIX timestamp in **milliseconds** |

**Returns:**
```json
{
  "erg": 0.001234,
  "usd": 0.00567,
  "use": 0.00890
}
```

**This is the money endpoint.** Returns the token's price at the specified point in time. Prices are derived from Spectrum DEX pool state.

### Token Price Stats (with min/max/avg)

```
GET /spectrum/price_stats?token_id={id}&time_point={ms}&time_window={ms}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `token_id` | string | Ergo token ID |
| `time_point` | integer | Center of time window (UNIX ms) |
| `time_window` | integer | Window width in milliseconds |

**Returns:**
```json
{
  "token_info": {
    "token_id": "...",
    "name": "heisenbERG",
    "description": "...",
    "minted": 100000000000000,
    "decimals": 5
  },
  "max": { "erg": 0.00001633, "usd": 0.00002809, "use": 0.10539 },
  "min": { "erg": 0.00000500, "usd": 0.00000436, "use": 0.0000000044 },
  "average": { "erg": 0.00001050, "usd": 0.00000514, "use": 0.00000514 }
}
```

**Note:** `time_window` can be very large. Setting it equal to `time_point` effectively gives you "all time" stats.

---

## Proven Working Patterns

### Historical Price Fetch (Python)
```python
import requests
import time

def get_token_price(token_id, timestamp_ms):
    url = f"https://api.cruxfinance.io/spectrum/price"
    params = {"token_id": token_id, "time_point": timestamp_ms}
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code == 200:
        return resp.json()  # {"erg": ..., "usd": ..., "use": ...}
    return None

# Bulk fetch with rate limiting
for height, ts_ms in height_timestamp_pairs:
    price = get_token_price(token_id, ts_ms)
    time.sleep(0.15)  # Rate limit
```

### Month-End Prices for All Tokens
```python
from datetime import datetime, timezone

# Convert month-end date to milliseconds
dt = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
time_point = int(dt.timestamp() * 1000)

# Fetch price
price = get_token_price(token_id, time_point)
```

---

## Wins

- **Actually returns historical data** — unlike Spectrum's `/amm/pools/stats` which ignores timestamps and returns current state, Crux genuinely returns prices at the specified point in time
- **Three price units** — ERG, USD, and USE in every response
- **Token metadata included** in `/price_stats` — name, description, decimals, minted supply
- **No auth required**
- **Reliable** — handles thousands of price queries without errors in bulk backfills
- **Price derivation from DEX trades** — prices reflect actual market activity on Spectrum

## Stumbling Blocks

- **Wrong endpoint initially** — the correct path is `/spectrum/price_stats` NOT `/spectrum/get_price_stats`. No error was thrown — just 404. Cost debugging time.
- **Timestamps must be milliseconds** — not seconds. Easy to mess up.
- **Returns null/zero for tokens with no trades** — if a token had no Spectrum liquidity at that date, you get back zeros. This is correct behavior but needs handling.
- **No bulk endpoint** — must query one token at a time. For large bacfills (hundreds of tokens × dozens of months), expect thousands of individual API calls. Rate limiting to 0.15s keeps it manageable.
- **Ownership change risk** — Crux changed hands. API could change or disappear. Back up any critical data.
- **ERG price is relative** — the `erg` field is the token's price denominated in ERG. To get USD, use the `usd` field directly (Crux handles ERG/USD conversion internally).
- **No pool-level data** — Crux gives token prices, not pool reserves. For LP valuation, you still need pool box queries.
