#!/usr/bin/env python3
"""
Fetch Historical Token Prices from Crux Finance API
=====================================================
Queries Crux /spectrum/price endpoint for month-end prices across
a configurable date range. Supports both a hardcoded token list and
automatic extraction from an LP pool mapping file.

API:
  GET https://api.cruxfinance.io/spectrum/price
    ?token_id={64-char hex}
    &time_point={unix_ms}
  Returns: {"erg": float, "usd": float, "use": float}

Outputs:
  - historical_token_prices.json  (structured data)
  - historical_token_prices.csv   (Excel-ready)

Usage:
  python fetch_historical_token_prices.py
  python fetch_historical_token_prices.py --from-pools lp_token_pairs_v3.json

Requirements:
  pip install requests
Author: CannonQ
License: AGPL-3.0
"""

import requests
import json
import csv
import time
import os
import sys
import calendar
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# CONFIGURATION
# =============================================================================

CRUX_API = "https://api.cruxfinance.io/spectrum/price"
REQUEST_DELAY = 0.15  # Seconds between API calls (be respectful)

# ERG token ID (skip — it's the base currency)
ERG_TOKEN_ID = "0" * 64

# Date range
START_YEAR = 2022
START_MONTH = 1
END_YEAR = 2025
END_MONTH = 12

# Example tokens (add your own or use --from-pools)
TOKEN_IDS = {
    "SigUSD": "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04",
    "SigRSV": "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0",
    "SPF":    "9a06d9e545a41fd51eeffc5e20d818073bf820c635e2a9d922269913e0de369d",
    "NETA":   "472c3d4ecaa08fb7392ff041ee2e6af75f4a558810a74b28600549d5392810e8",
}


# =============================================================================
# TIMESTAMP GENERATION
# =============================================================================

def get_month_end_timestamps(start_year, start_month, end_year, end_month):
    """Generate month-end timestamps in reverse chronological order."""
    months = []
    now = datetime.now(timezone.utc)
    year, month = start_year, start_month

    while (year < end_year) or (year == end_year and month <= end_month):
        last_day = calendar.monthrange(year, month)[1]
        month_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

        if month_end > now:
            break

        months.append({
            "date": month_end.strftime("%Y-%m-%d"),
            "year_month": month_end.strftime("%Y-%m"),
            "timestamp_ms": int(month_end.timestamp() * 1000),
        })

        month += 1
        if month > 12:
            month = 1
            year += 1

    months.reverse()  # Newest first
    return months


# =============================================================================
# TOKEN EXTRACTION FROM LP POOLS
# =============================================================================

def extract_tokens_from_pools(pool_file):
    """Extract unique non-ERG tokens from lp_token_pairs_v3.json."""
    with open(pool_file, 'r', encoding='utf-8') as f:
        pools = json.load(f)

    tokens = {}
    for pool in pools:
        for asset_key in ["asset_x", "asset_y"]:
            asset = pool.get(asset_key, {})
            token_id = asset.get("id", "")
            ticker = asset.get("ticker", "???")
            if token_id and token_id != ERG_TOKEN_ID:
                tokens[ticker] = token_id

    return tokens


# =============================================================================
# PRICE FETCHING
# =============================================================================

def fetch_price(token_id, timestamp_ms):
    """Fetch token price from Crux API at a specific timestamp."""
    try:
        resp = requests.get(
            CRUX_API,
            params={"token_id": token_id, "time_point": timestamp_ms},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Check for actual data (not all zeros)
            if data and (data.get("erg", 0) > 0 or data.get("usd", 0) > 0):
                return data
    except Exception as e:
        print(f"  Error: {e}")
    return None


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Check for --from-pools flag
    tokens = TOKEN_IDS
    if len(sys.argv) >= 3 and sys.argv[1] == "--from-pools":
        pool_file = sys.argv[2]
        print(f"Extracting tokens from: {pool_file}")
        tokens = extract_tokens_from_pools(pool_file)
        print(f"Found {len(tokens)} unique tokens")

    # Generate timestamps
    timestamps = get_month_end_timestamps(START_YEAR, START_MONTH, END_YEAR, END_MONTH)

    print("=" * 60)
    print("FETCH HISTORICAL TOKEN PRICES")
    print("=" * 60)
    print(f"Date range: {timestamps[-1]['date']} to {timestamps[0]['date']}")
    print(f"Total months: {len(timestamps)}")
    print(f"Tokens: {len(tokens)}")

    all_prices = []

    for token_name, token_id in tokens.items():
        print(f"\n[{token_name}] {token_id[:16]}...")
        consecutive_nulls = 0

        for ts_info in timestamps:
            print(f"  {ts_info['date']}...", end=" ")

            price_data = fetch_price(token_id, ts_info["timestamp_ms"])

            if price_data:
                consecutive_nulls = 0
                all_prices.append({
                    "token_name": token_name,
                    "token_id": token_id,
                    "date": ts_info["date"],
                    "year_month": ts_info["year_month"],
                    "price_erg": price_data.get("erg", 0),
                    "price_usd": price_data.get("usd", 0),
                    "price_use": price_data.get("use", 0),
                })
                print(f"ERG={price_data.get('erg', 0):.8f}  "
                      f"USD={price_data.get('usd', 0):.8f}")
            else:
                consecutive_nulls += 1
                print("No data")

                # If 6+ months with no data (going backwards), skip rest
                if consecutive_nulls >= 6:
                    print(f"  Skipping remaining months (no data)")
                    break

            time.sleep(REQUEST_DELAY)

    # Save JSON
    output = {
        "metadata": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "source": "Crux Finance API /spectrum/price",
            "tokens": len(tokens),
            "price_points": len(all_prices),
            "date_range": f"{timestamps[-1]['date']} to {timestamps[0]['date']}",
        },
        "prices": all_prices,
    }

    with open("historical_token_prices.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved historical_token_prices.json")

    # Save CSV
    if all_prices:
        fieldnames = list(all_prices[0].keys())
        with open("historical_token_prices.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_prices)
        print("Saved historical_token_prices.csv")

    # Summary
    print(f"\n{'='*60}")
    print(f"Total price points: {len(all_prices)}")
    print(f"Tokens queried: {len(tokens)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
