#!/usr/bin/env python3
"""
Token Creation Height Lookup via GraphQL
=========================================
Finds the block height at which an Ergo token was created.

On Ergo, Token ID = Box ID of the first input in the minting transaction.
The minting box's creation height tells us when the token was born.

Approach (two-step GQL):
  1. tokens(tokenId) -> boxId  (the issuance box)
  2. boxes(boxId)    -> creationHeight

Usage:
  python token_creation_height.py
  python token_creation_height.py <token_id>
  python token_creation_height.py --from-file lp_token_pairs_v3.json

Requirements:
  pip install requests
Author: CannonQ
"""

import requests
import json
import sys
import time

GQL_ENDPOINT = "https://gql.ergoplatform.com/"
REQUEST_DELAY = 0.1  # Seconds between calls

# Example tokens (edit or use CLI args)
EXAMPLE_TOKENS = {
    "SigUSD": "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04",
    "SigRSV": "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0",
    "SPF":    "9a06d9e545a41fd51eeffc5e20d818073bf820c635e2a9d922269913e0de369d",
}


def graphql_query(query, variables=None):
    """Execute a GraphQL query."""
    try:
        resp = requests.post(
            GQL_ENDPOINT,
            json={"query": query, "variables": variables or {}},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("data", {})
    except Exception as e:
        print(f"  GQL error: {e}")
    return {}


def get_token_mint_box(token_id):
    """Step 1: Get the mint box ID for a token."""
    query = """
    query GetToken($tokenId: String!) {
        tokens(tokenId: $tokenId) {
            boxId
        }
    }
    """
    data = graphql_query(query, {"tokenId": token_id})
    tokens = data.get("tokens", [])
    if tokens:
        return tokens[0].get("boxId")
    return None


def get_box_creation_height(box_id):
    """Step 2: Get creation height for a box."""
    query = """
    query GetBox($boxId: String!) {
        boxes(boxId: $boxId) {
            creationHeight
        }
    }
    """
    data = graphql_query(query, {"boxId": box_id})
    boxes = data.get("boxes", [])
    if boxes:
        return boxes[0].get("creationHeight")
    return None


def get_token_creation_height(token_id):
    """
    Combined lookup: token ID -> mint box -> creation height.
    """
    mint_box = get_token_mint_box(token_id)
    if not mint_box:
        return None

    time.sleep(REQUEST_DELAY)

    creation_height = get_box_creation_height(mint_box)
    return creation_height


def lookup_from_file(filepath):
    """Extract Pool NFT IDs from lp_token_pairs JSON and look up creation heights."""
    with open(filepath, 'r', encoding='utf-8') as f:
        pools = json.load(f)

    results = []
    total = len(pools)

    for i, pool in enumerate(pools):
        pool_nft = pool.get("pool_nft_id", "")
        pair_name = pool.get("pair_name", "Unknown")

        print(f"  [{i+1}/{total}] {pair_name}...", end=" ")

        height = get_token_creation_height(pool_nft)
        if height:
            print(f"height={height}")
            pool["creation_height"] = height
        else:
            print("not found")
            pool["creation_height"] = None

        results.append(pool)
        time.sleep(REQUEST_DELAY)

    # Write updated file
    output_file = filepath.replace(".json", "_with_heights.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {output_file}")

    return results


def main():
    print("=" * 60)
    print("TOKEN CREATION HEIGHT LOOKUP")
    print("=" * 60)

    # Mode: from file
    if len(sys.argv) >= 3 and sys.argv[1] == "--from-file":
        print(f"\nLooking up creation heights from: {sys.argv[2]}")
        lookup_from_file(sys.argv[2])
        return

    # Mode: single token ID
    if len(sys.argv) == 2:
        token_id = sys.argv[1]
        tokens = {"CLI_TOKEN": token_id}
    else:
        tokens = EXAMPLE_TOKENS

    for name, token_id in tokens.items():
        print(f"\n[{name}]")
        print(f"  Token ID: {token_id[:24]}...")

        mint_box = get_token_mint_box(token_id)
        if mint_box:
            print(f"  Mint box: {mint_box[:24]}...")

            time.sleep(REQUEST_DELAY)
            height = get_box_creation_height(mint_box)

            if height:
                print(f"  Creation height: {height}")
            else:
                print(f"  Creation height: not found")
        else:
            print(f"  Mint box: not found")

        time.sleep(REQUEST_DELAY)


if __name__ == "__main__":
    main()
