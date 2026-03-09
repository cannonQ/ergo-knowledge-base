#!/usr/bin/env python3
"""
Spectrum LP Pool Mapper via GraphQL
=====================================
Discovers all Spectrum Finance LP pools on Ergo by querying for pool boxes
using ErgoTree template hashes. Extracts Pool NFT ID, LP Token ID, and
reserve token IDs for each pool.

Pool Box Anatomy:
  N2T (Native-to-Token):
    Assets[0] = Pool NFT (1)       — unique identifier
    Assets[1] = LP Token (remaining supply)
    Assets[2] = Token Y (reserve)
    Value = ERG reserve (nanoERG)
    R4 = Fee numerator

  T2T (Token-to-Token):
    Assets[0] = Pool NFT (1)
    Assets[1] = LP Token (remaining supply)
    Assets[2] = Token X (reserve)
    Assets[3] = Token Y (reserve)
    R4 = Fee numerator

ErgoTree Template Hashes (confirmed):
  N2T: d19e23d1f7a101fef63861cd303ec5e1c1db93e9e1c244178e83556c4d082a49
  T2T: 8b159b63f668c5782400b6b0a0a11db995888c0153a29e30594c8d88d5b9430c

Approach:
  Query GQL with ergoTreeTemplateHash for N2T and T2T pools.
  Paginate with skip/take (200 per page).
  Parse asset positions to identify Pool NFT, LP Token, reserves.

Usage:
  python spectrum_lp_mapper.py

  Or use pre-exported GQL files:
  python spectrum_lp_mapper.py --from-files GetN2TPools_1.json GetN2TPools_2.json

Output:
  - lp_token_pairs.json     (complete pool data)
  - lp_token_pairs.csv      (Excel-ready)
  - lp_token_lookup.json    (LP Token ID -> Pool Info)

Requirements:
  pip install requests
Author: CannonQ
License: AGPL-3.0
"""

import requests
import json
import csv
import sys
import time

GQL_ENDPOINT = "https://gql.ergoplatform.com/"

# Pool template hashes (Spectrum Finance)
N2T_TEMPLATE = "d19e23d1f7a101fef63861cd303ec5e1c1db93e9e1c244178e83556c4d082a49"
T2T_TEMPLATE = "8b159b63f668c5782400b6b0a0a11db995888c0153a29e30594c8d88d5b9430c"

ERG_TOKEN_ID = "0" * 64
MAX_LP_SUPPLY = 9223372036854774807  # 2^63 - 1


def query_pools_gql(template_hash, skip=0, take=200):
    """Query current pool boxes by ErgoTree template hash."""
    query = """
    query GetPools($hash: String!, $skip: Int!, $take: Int!) {
      boxes(
        ergoTreeTemplateHash: $hash
        spent: false
        skip: $skip
        take: $take
      ) {
        boxId
        address
        value
        creationHeight
        assets {
          tokenId
          amount
        }
        additionalRegisters
      }
    }
    """

    try:
        resp = requests.post(
            GQL_ENDPOINT,
            json={
                "query": query,
                "variables": {"hash": template_hash, "skip": skip, "take": take}
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "errors" in data:
                print(f"  GQL errors: {data['errors']}")
                return []
            return data.get("data", {}).get("boxes", [])
    except Exception as e:
        print(f"  Error: {e}")
    return []


def fetch_all_pools(template_hash, pool_type):
    """Paginate through all pool boxes for a template hash."""
    all_boxes = []
    skip = 0
    take = 200

    while True:
        print(f"  Fetching {pool_type} pools (skip={skip})...", end=" ")
        boxes = query_pools_gql(template_hash, skip, take)
        print(f"{len(boxes)} boxes")

        if not boxes:
            break

        all_boxes.extend(boxes)
        if len(boxes) < take:
            break

        skip += take
        time.sleep(0.5)

    return all_boxes


def parse_n2t_pool(box):
    """Parse an N2T pool box into structured data."""
    assets = box.get("assets", [])
    if len(assets) < 3:
        return None

    # Assets order: [0]=Pool NFT, [1]=LP Token, [2]=Token Y
    pool_nft_id = assets[0].get("tokenId", "")
    lp_token_id = assets[1].get("tokenId", "")
    lp_in_pool = int(assets[1].get("amount", 0))
    token_y_id = assets[2].get("tokenId", "")
    token_y_amount = int(assets[2].get("amount", 0))
    erg_amount = int(box.get("value", 0))

    # R4 = fee numerator
    fee_num = 997  # default
    registers = box.get("additionalRegisters", {})
    r4 = registers.get("R4", "")
    if r4:
        try:
            from process_mewmart_gql import decode_slong
            fee_num = abs(decode_slong(r4))
        except ImportError:
            pass  # Use default

    return {
        "pool_type": "N2T",
        "pool_nft_id": pool_nft_id,
        "lp_token_id": lp_token_id,
        "asset_x": {"id": ERG_TOKEN_ID, "ticker": "ERG", "amount": erg_amount},
        "asset_y": {"id": token_y_id, "amount": token_y_amount},
        "lp_in_pool": lp_in_pool,
        "circulating_lp": MAX_LP_SUPPLY - lp_in_pool,
        "fee_numerator": fee_num,
        "creation_height": box.get("creationHeight", 0),
        "box_id": box.get("boxId", ""),
    }


def parse_t2t_pool(box):
    """Parse a T2T pool box into structured data."""
    assets = box.get("assets", [])
    if len(assets) < 4:
        return None

    # Assets order: [0]=Pool NFT, [1]=LP Token, [2]=Token X, [3]=Token Y
    pool_nft_id = assets[0].get("tokenId", "")
    lp_token_id = assets[1].get("tokenId", "")
    lp_in_pool = int(assets[1].get("amount", 0))
    token_x_id = assets[2].get("tokenId", "")
    token_x_amount = int(assets[2].get("amount", 0))
    token_y_id = assets[3].get("tokenId", "")
    token_y_amount = int(assets[3].get("amount", 0))

    return {
        "pool_type": "T2T",
        "pool_nft_id": pool_nft_id,
        "lp_token_id": lp_token_id,
        "asset_x": {"id": token_x_id, "amount": token_x_amount},
        "asset_y": {"id": token_y_id, "amount": token_y_amount},
        "lp_in_pool": lp_in_pool,
        "circulating_lp": MAX_LP_SUPPLY - lp_in_pool,
        "creation_height": box.get("creationHeight", 0),
        "box_id": box.get("boxId", ""),
    }


def load_from_files(filepaths):
    """Load pool boxes from pre-exported GQL JSON files."""
    all_boxes = []
    for fp in filepaths:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            boxes = data.get("data", {}).get("boxes", [])
            print(f"  {fp}: {len(boxes)} boxes")
            all_boxes.extend(boxes)
        except Exception as e:
            print(f"  Error loading {fp}: {e}")
    return all_boxes


def main():
    print("=" * 70)
    print("SPECTRUM LP POOL MAPPER")
    print("=" * 70)

    all_pools = []

    if len(sys.argv) >= 3 and sys.argv[1] == "--from-files":
        # Load from pre-exported files
        boxes = load_from_files(sys.argv[2:])
        for box in boxes:
            assets = box.get("assets", [])
            if len(assets) >= 4:
                pool = parse_t2t_pool(box)
            elif len(assets) >= 3:
                pool = parse_n2t_pool(box)
            else:
                continue
            if pool:
                all_pools.append(pool)
    else:
        # Query GQL directly
        print(f"\n[1] Fetching N2T pools...")
        n2t_boxes = fetch_all_pools(N2T_TEMPLATE, "N2T")
        for box in n2t_boxes:
            pool = parse_n2t_pool(box)
            if pool:
                all_pools.append(pool)

        print(f"\n[2] Fetching T2T pools...")
        t2t_boxes = fetch_all_pools(T2T_TEMPLATE, "T2T")
        for box in t2t_boxes:
            pool = parse_t2t_pool(box)
            if pool:
                all_pools.append(pool)

    print(f"\nTotal pools mapped: {len(all_pools)}")
    n2t_count = sum(1 for p in all_pools if p["pool_type"] == "N2T")
    t2t_count = sum(1 for p in all_pools if p["pool_type"] == "T2T")
    print(f"  N2T: {n2t_count}  |  T2T: {t2t_count}")

    # Save main output
    with open("lp_token_pairs.json", 'w', encoding='utf-8') as f:
        json.dump(all_pools, f, indent=2)
    print(f"\nSaved lp_token_pairs.json")

    # Save lookup table (LP Token ID -> pool info)
    lookup = {}
    for pool in all_pools:
        lookup[pool["lp_token_id"]] = {
            "pool_nft_id": pool["pool_nft_id"],
            "pool_type": pool["pool_type"],
            "asset_x_id": pool["asset_x"]["id"],
            "asset_y_id": pool["asset_y"]["id"],
        }

    with open("lp_token_lookup.json", 'w', encoding='utf-8') as f:
        json.dump(lookup, f, indent=2)
    print("Saved lp_token_lookup.json")

    # Save CSV
    csv_rows = []
    for pool in all_pools:
        csv_rows.append({
            "pool_type": pool["pool_type"],
            "pool_nft_id": pool["pool_nft_id"],
            "lp_token_id": pool["lp_token_id"],
            "asset_x_id": pool["asset_x"]["id"],
            "asset_y_id": pool["asset_y"]["id"],
            "creation_height": pool["creation_height"],
        })

    with open("lp_token_pairs.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)
    print("Saved lp_token_pairs.csv")


if __name__ == "__main__":
    main()
