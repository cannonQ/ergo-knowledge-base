#!/usr/bin/env python3
"""
Calculate LP Circulating Supply
=================================
Queries the current pool box for Spectrum LP pools and calculates
circulating LP token supply, reserves, and approximate LP value.

Key Formula:
  Max LP Supply = 9,223,372,036,854,774,807  (constant = 2^63 - 1)
  Circulating LP = Max LP Supply - LP tokens remaining in pool box
  Your LP Value  = (Your Balance / Circulating LP) × Pool Total Value

Data Sources:
  - Explorer API:  /boxes/unspent/byTokenId/{poolNftId}
  - GraphQL:       boxes(tokenId, spent: false)

Usage:
  python calc_lp_supply.py
  python calc_lp_supply.py --pool-nft <pool_nft_id> --lp-token <lp_token_id>

Requirements:
  pip install requests
Author: CannonQ
License: AGPL-3.0
"""

import requests
import json
import sys
import time

# API Endpoints
EXPLORER_API = "https://api.ergoplatform.com/api/v1"
GRAPHQL_API = "https://gql.ergoplatform.com/"

# Max LP supply (same for ALL Spectrum pools)
MAX_LP_SUPPLY = 9223372036854774807

# Example pools (edit or use CLI args)
TEST_POOLS = [
    {
        "name": "ERG/SigUSD",
        "pool_nft_id": "9916d75132593c8b07fe18bd8d583bda1652eed7565cf41a4738ddd90fc992ec",
        "lp_token_id": "d71693c49a84fbbecd4908c94813b46514b18b67a99952dc1e6e4791556de413",
    },
    {
        "name": "ERG/SPF",
        "pool_nft_id": "f4b04c3a3a64fb40b35ad69e89b9f3c7e5e65f80be62e71e19e4ad5cc97bcde5",
        "lp_token_id": "e5ac7a89b8909cae1378f5ca11feec63dcbae4e84c64d38d7dba0a068c6f0734",
    },
]


def get_pool_box_explorer(pool_nft_id):
    """Get current pool box from Explorer API."""
    try:
        url = f"{EXPLORER_API}/boxes/unspent/byTokenId/{pool_nft_id}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("items"):
                return data["items"][0]
    except Exception as e:
        print(f"    Explorer error: {e}")
    return None


def get_pool_box_graphql(pool_nft_id):
    """Get current pool box from GraphQL (fallback)."""
    query = """
    query GetPoolBox($tokenId: String!) {
      boxes(tokenId: $tokenId, spent: false, take: 1) {
        boxId
        creationHeight
        value
        assets { tokenId amount }
      }
    }
    """
    try:
        resp = requests.post(
            GRAPHQL_API,
            json={"query": query, "variables": {"tokenId": pool_nft_id}},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 200:
            boxes = resp.json().get("data", {}).get("boxes", [])
            if boxes:
                return boxes[0]
    except Exception as e:
        print(f"    GQL error: {e}")
    return None


def extract_asset_amount(box, token_id):
    """Extract the amount of a specific token from a box's assets."""
    for asset in box.get("assets", []):
        if asset.get("tokenId") == token_id:
            return int(asset.get("amount", 0))
    return 0


def fmt(n):
    """Format large number with commas."""
    return f"{n:,}"


def analyze_pool(pool_info):
    """Analyze a single pool: query box, compute circulating supply."""
    name = pool_info["name"]
    pool_nft_id = pool_info["pool_nft_id"]
    lp_token_id = pool_info["lp_token_id"]

    print(f"\n{'='*70}")
    print(f"Pool: {name}")
    print(f"{'='*70}")
    print(f"  Pool NFT: {pool_nft_id}")
    print(f"  LP Token: {lp_token_id}")

    # Query pool box
    print(f"\n  Querying Explorer API...")
    box = get_pool_box_explorer(pool_nft_id)
    if not box:
        print(f"  Explorer failed, trying GraphQL...")
        box = get_pool_box_graphql(pool_nft_id)

    if not box:
        print(f"  ERROR: Pool box not found!")
        return None

    box_id = box.get("boxId", "")
    creation_height = box.get("creationHeight", 0)
    erg_value = int(box.get("value", 0))

    print(f"\n  Pool box found!")
    print(f"    Box ID: {box_id[:24]}...")
    print(f"    Creation Height: {creation_height}")
    print(f"    ERG in pool: {erg_value / 1e9:,.4f} ERG")

    # Extract LP token balance
    lp_in_pool = extract_asset_amount(box, lp_token_id)

    # List all assets
    print(f"    Assets in box: {len(box.get('assets', []))}")
    for asset in box.get("assets", []):
        tid = asset.get("tokenId", "")
        amt = int(asset.get("amount", 0))
        label = "Pool NFT" if amt == 1 and tid == pool_nft_id else \
                "LP Token" if tid == lp_token_id else "Reserve token"
        print(f"      - {label}: {fmt(amt)}")

    # Calculate circulating supply
    circulating_lp = MAX_LP_SUPPLY - lp_in_pool
    pct = (circulating_lp / MAX_LP_SUPPLY) * 100

    print(f"\n  {'─'*50}")
    print(f"  CIRCULATING LP CALCULATION:")
    print(f"  {'─'*50}")
    print(f"    Max Supply:     {fmt(MAX_LP_SUPPLY)}")
    print(f"    LP in Pool Box: {fmt(lp_in_pool)}")
    print(f"    {'─'*40}")
    print(f"    Circulating LP: {fmt(circulating_lp)}")
    print(f"    % Circulating:  {pct:.10f}%")

    # Approximate value
    if circulating_lp > 0:
        erg_per_lp = (erg_value / 1e9) / circulating_lp
        print(f"\n  Approx ERG per LP token: {erg_per_lp:.18f} ERG")
        print(f"  (ERG reserve only — doesn't include token Y value)")

    return {
        "name": name,
        "pool_nft_id": pool_nft_id,
        "lp_token_id": lp_token_id,
        "lp_in_pool": lp_in_pool,
        "circulating_lp": circulating_lp,
        "erg_reserve": erg_value,
    }


def main():
    print("=" * 70)
    print("CALCULATE LP CIRCULATING SUPPLY")
    print("=" * 70)
    print(f"Max LP Supply (all Spectrum pools): {fmt(MAX_LP_SUPPLY)}")
    print(f"Formula: Circulating = Max Supply - LP tokens in pool box")

    # CLI mode: specific pool
    if len(sys.argv) >= 5 and sys.argv[1] == "--pool-nft":
        pool = {
            "name": "Custom Pool",
            "pool_nft_id": sys.argv[2],
            "lp_token_id": sys.argv[4] if sys.argv[3] == "--lp-token" else "",
        }
        analyze_pool(pool)
        return

    # Default: analyze test pools
    results = []
    for pool in TEST_POOLS:
        result = analyze_pool(pool)
        if result:
            results.append(result)
        time.sleep(0.5)

    # Summary
    print(f"\n{'='*70}")
    print("LP VALUATION FORMULA:")
    print(f"{'='*70}")
    print("  Your LP Value = (Your_LP_Balance / Circulating_LP) × Pool_Total_Value")
    print("  Pool_Total_Value = (ERG_Reserve × ERG_USD) + (Token_Reserve × Token_USD)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
