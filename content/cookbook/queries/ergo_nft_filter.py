#!/usr/bin/env python3
"""
Ergo NFT Token Filter

Classifies tokens from a collection into three categories:
  - Circulating: held by a wallet that is NOT the mint wallet
  - Burned: no unspent box exists (token destroyed)
  - Unissued: still sitting in the mint wallet (never distributed)

Works with the output of ergo_nft_scraper.py.

Usage:
    python ergo_nft_filter.py <input_json> <mint_wallet>

Examples:
    python ergo_nft_filter.py my_collection_rest.json 9abc123...xyz
    python ergo_nft_filter.py walrus_nfts_rest.json 9fxYz...abc

Output:
    <input>_filtered.json   - Circulating tokens only
    <input>_burned.json     - Burned tokens
    <input>_unissued.json   - Tokens still in mint wallet
Author: CannonQ
License: AGPL-3.0
"""

import json
import sys
import requests
import time

ERGO_API = "https://api.ergoplatform.com/api/v1"


def get_token_current_box(token_id: str) -> dict:
    """Get current unspent box containing this token"""
    url = f"{ERGO_API}/boxes/unspent/byTokenId/{token_id}"
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                return items[0]
        return None
    except Exception as e:
        print(f"Error fetching box for {token_id}: {e}")
        return None


def check_token_status(token_id: str, mint_wallet: str) -> dict:
    """Classify token as circulating, burned, or unissued"""
    box = get_token_current_box(token_id)

    if box is None:
        return {"status": "burned", "holder": None}

    holder = box.get("address", "")
    if holder == mint_wallet:
        return {"status": "unissued", "holder": holder}

    return {"status": "circulating", "holder": holder}


def filter_collection(input_file: str, mint_wallet: str):
    """Filter collection JSON into circulating/burned/unissued"""

    with open(input_file, 'r') as f:
        data = json.load(f)

    tokens = data.get("tokens", [])
    print(f"{'=' * 50}")
    print(f"Filtering: {input_file}")
    print(f"Mint wallet: {mint_wallet[:20]}...{mint_wallet[-8:]}")
    print(f"Total tokens: {len(tokens)}")
    print(f"{'=' * 50}\n")

    circulating = []
    burned = []
    unissued = []

    for i, token in enumerate(tokens):
        token_id = token.get("token_id")
        name = token.get("name", "Unknown")

        print(f"[{i+1}/{len(tokens)}] {name}...", end=" ", flush=True)

        # Retry logic
        status_info = None
        for attempt in range(3):
            status_info = check_token_status(token_id, mint_wallet)
            if status_info["status"] != "burned" or attempt == 2:
                break
            print("retry...", end=" ", flush=True)
            time.sleep(3)

        status = status_info["status"]
        token["current_holder"] = status_info["holder"]
        token["status"] = status

        if status == "circulating":
            circulating.append(token)
            print("circulating")
        elif status == "burned":
            burned.append(token)
            print("burned")
        else:
            unissued.append(token)
            print("unissued (in mint wallet)")

        # Rate limiting
        if (i + 1) % 10 == 0:
            time.sleep(1)
        else:
            time.sleep(0.2)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"SUMMARY")
    print(f"{'=' * 50}")
    print(f"Circulating: {len(circulating)}")
    print(f"Burned:      {len(burned)}")
    print(f"Unissued:    {len(unissued)}")
    print(f"Total:       {len(tokens)}")

    # Save filtered output
    output_file = input_file.replace(".json", "_filtered.json")
    with open(output_file, 'w') as f:
        json.dump({
            "mint_address": data.get("mint_address"),
            "summary": {
                "total_minted": len(tokens),
                "circulating": len(circulating),
                "burned": len(burned),
                "unissued": len(unissued)
            },
            "tokens": circulating
        }, f, indent=2)
    print(f"\nSaved circulating tokens to: {output_file}")

    # Save burned list
    burned_file = input_file.replace(".json", "_burned.json")
    with open(burned_file, 'w') as f:
        json.dump({"count": len(burned), "tokens": burned}, f, indent=2)
    print(f"Saved burned tokens to: {burned_file}")

    # Save unissued list
    unissued_file = input_file.replace(".json", "_unissued.json")
    with open(unissued_file, 'w') as f:
        json.dump({"count": len(unissued), "tokens": unissued}, f, indent=2)
    print(f"Saved unissued tokens to: {unissued_file}")

    return circulating, burned, unissued


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Ergo NFT Token Filter")
        print("=" * 50)
        print("\nClassifies tokens as circulating, burned, or unissued.")
        print("\nUsage: python ergo_nft_filter.py <input_json> <mint_wallet_address>")
        print("\nExample:")
        print("  python ergo_nft_filter.py my_nfts_rest.json 9abc123...full_address_here")
        print("\nThe mint wallet address is used to identify unissued tokens")
        print("(tokens still held by the original minting wallet).")
        sys.exit(1)

    input_file = sys.argv[1]
    mint_wallet = sys.argv[2]

    filter_collection(input_file, mint_wallet)
