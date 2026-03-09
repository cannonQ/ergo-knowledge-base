#!/usr/bin/env python3
"""
Ergo NFT Collection Scraper

General-purpose tool for enumerating NFT collections on the Ergo blockchain.
Given a mint wallet address, discovers all tokens minted from that address
using the Ergo minting rule: token ID = box ID of first input in minting tx.

Usage:
    pip install requests
    python ergo_nft_scraper.py enumerate <mint_address> <collection_name>
    python ergo_nft_scraper.py enumerate <mint_address> <collection_name> --graphql
    python ergo_nft_scraper.py fetch-details <input_json>
    python ergo_nft_scraper.py test
Author: CannonQ
License: AGPL-3.0
"""

import requests
import json
import time
import sys
import re
from typing import Optional, Dict, List


# API Endpoints
ERGO_API = "https://api.ergoplatform.com/api/v1"
ERGO_GRAPHQL = "https://gql.ergoplatform.com/"
ERGO_GRAPHQL_ALT = "https://explore.sigmaspace.io/api/graphql"


# --- API Helpers ---

def get_token_info(token_id: str) -> Optional[Dict]:
    """Fetch token info from Ergo Explorer API"""
    url = f"{ERGO_API}/tokens/{token_id}"
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching token {token_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Request failed for {token_id}: {e}")
        return None


def get_box_info(box_id: str) -> Optional[Dict]:
    """Fetch box info including additionalRegisters"""
    url = f"{ERGO_API}/boxes/{box_id}"
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Request failed for box {box_id}: {e}")
        return None


def search_tokens(query: str, limit: int = 50, offset: int = 0) -> List[Dict]:
    """Search for tokens by name"""
    url = f"{ERGO_API}/tokens/search"
    params = {"query": query, "limit": limit, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    except Exception as e:
        print(f"Search failed: {e}")
        return []


def graphql_query(query: str, variables: Dict = None, endpoint: str = None) -> Optional[Dict]:
    """Execute GraphQL query against Ergo GraphQL API"""
    endpoint = endpoint or ERGO_GRAPHQL
    try:
        response = requests.post(
            endpoint,
            json={"query": query, "variables": variables or {}},
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                print(f"GraphQL errors: {data['errors']}")
            return data.get("data")
        else:
            print(f"GraphQL request failed: {response.status_code}")
            if endpoint == ERGO_GRAPHQL:
                print("Trying alternate endpoint...")
                return graphql_query(query, variables, ERGO_GRAPHQL_ALT)
            return None
    except Exception as e:
        print(f"GraphQL request error: {e}")
        return None


# --- Register Decoding ---

def decode_register_string(hex_value: str) -> Optional[str]:
    """
    Decode Ergo register value from hex to string.
    Ergo encodes strings as: 0e + length_vlq + utf8_bytes
    """
    if not hex_value:
        return None
    try:
        if hex_value.startswith("0e"):
            hex_value = hex_value[2:]
            length_byte = int(hex_value[:2], 16)
            if length_byte < 128:
                data_hex = hex_value[2:2 + length_byte * 2]
            else:
                data_hex = hex_value[4:]
            return bytes.fromhex(data_hex).decode('utf-8', errors='ignore')
        return bytes.fromhex(hex_value).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Failed to decode: {hex_value[:50]}... Error: {e}")
        return None


def parse_token_metadata(token_data: Dict) -> Dict:
    """
    Parse token data into structured format.
    Extracts number from name if present (e.g., "MyNFT #1234" -> 1234).
    """
    result = {
        "token_id": token_data.get("id"),
        "name": token_data.get("name"),
        "description": token_data.get("description"),
        "decimals": token_data.get("decimals", 0),
        "emission_amount": token_data.get("emissionAmount", 1),
        "box_id": token_data.get("boxId"),
    }

    name = result.get("name", "")
    match = re.search(r'#(\d+)', name)
    if match:
        result["number"] = int(match.group(1))

    return result


# --- Enumeration (REST API) ---

def fetch_minted_token_ids(mint_address: str, limit: int = 100) -> List[str]:
    """
    Discover all tokens minted by an address by scanning transaction history.
    
    Ergo minting rule: token ID = box ID of first input in minting transaction.
    Scans all transactions from the mint address, checks each for this pattern.
    """
    token_ids = []
    offset = 0

    while True:
        url = f"{ERGO_API}/addresses/{mint_address}/transactions"
        params = {"offset": offset, "limit": limit}

        try:
            print(f"  Scanning transactions {offset}...", end=" ", flush=True)
            response = requests.get(url, params=params, timeout=90)
            if response.status_code != 200:
                print(f"API returned {response.status_code}")
                break

            items = response.json().get("items", [])
            if not items:
                print("done")
                break

            batch_found = 0
            for tx in items:
                inputs = tx.get("inputs", [])
                if not inputs:
                    continue
                first_input_box_id = inputs[0].get("boxId")

                for output in tx.get("outputs", []):
                    for asset in output.get("assets", []):
                        token_id = asset.get("tokenId")
                        if token_id == first_input_box_id and token_id not in token_ids:
                            token_ids.append(token_id)
                            batch_found += 1

            print(f"found {batch_found} (total: {len(token_ids)})")
            offset += limit

            # Rate limiting
            if offset % (limit * 10) == 0:
                time.sleep(1)
            else:
                time.sleep(0.3)

            if len(items) < limit:
                break

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
            continue

    return token_ids


def enumerate_collection(mint_address: str, collection_name: str) -> List[Dict]:
    """
    Full enumeration: discover token IDs, then fetch metadata for each.
    """
    print(f"\n{'=' * 50}")
    print(f"Enumerating collection: {collection_name}")
    print(f"Mint address: {mint_address}")
    print(f"{'=' * 50}\n")

    # Step 1: Find all minted token IDs
    print("Step 1: Scanning mint wallet transactions...")
    token_ids = fetch_minted_token_ids(mint_address)
    print(f"\nFound {len(token_ids)} token IDs\n")

    if not token_ids:
        print("No tokens found. Check the mint address.")
        return []

    # Step 2: Fetch metadata for each token
    print("Step 2: Fetching token metadata...")
    tokens = []
    for i, token_id in enumerate(token_ids):
        print(f"[{i+1}/{len(token_ids)}] {token_id[:20]}...", end=" ", flush=True)

        token_info = get_token_info(token_id)
        if token_info:
            parsed = parse_token_metadata(token_info)
            tokens.append(parsed)
            print(f"-> {parsed.get('name', 'unnamed')}")
        else:
            print("-> not found")

        # Rate limiting
        if (i + 1) % 10 == 0:
            time.sleep(1)
        else:
            time.sleep(0.2)

        # Checkpoint every 500 tokens
        if (i + 1) % 500 == 0:
            checkpoint_file = f"{collection_name}_checkpoint.json"
            with open(checkpoint_file, 'w') as f:
                json.dump({"processed": i + 1, "tokens": tokens}, f, indent=2)
            print(f"\n  [Checkpoint: {i+1} tokens saved to {checkpoint_file}]\n")

    # Save final output
    output_file = f"{collection_name}_rest.json"
    with open(output_file, 'w') as f:
        json.dump({
            "mint_address": mint_address,
            "token_count": len(tokens),
            "tokens": tokens
        }, f, indent=2)

    print(f"\n{'=' * 50}")
    print(f"COMPLETE: {len(tokens)} tokens saved to {output_file}")
    print(f"{'=' * 50}")

    return tokens


# --- Enumeration (GraphQL) ---

def enumerate_collection_graphql(mint_address: str, collection_name: str) -> List[Dict]:
    """
    Enumerate using GraphQL API. Faster for some use cases but
    endpoint availability varies.
    """
    print(f"\n{'=' * 50}")
    print(f"Enumerating (GraphQL): {collection_name}")
    print(f"Mint address: {mint_address}")
    print(f"{'=' * 50}\n")

    query = """
    query GetTransactions($address: String!, $take: Int, $skip: Int) {
        transactions(address: $address, take: $take, skip: $skip) {
            transactionId
            inputs { boxId assets { tokenId amount } }
            outputs { boxId address value assets { tokenId amount } additionalRegisters }
        }
    }
    """

    issued_tokens = []
    offset = 0
    batch_size = 50

    while True:
        print(f"  Fetching transactions {offset}-{offset + batch_size}...", end=" ", flush=True)
        variables = {"address": mint_address, "take": batch_size, "skip": offset}
        data = graphql_query(query, variables)

        if not data:
            print("no data")
            break

        transactions = data.get("transactions", [])
        if not transactions:
            print("done")
            break

        batch_found = 0
        for tx in transactions:
            inputs = tx.get("inputs", [])
            if not inputs:
                continue
            first_input_box_id = inputs[0].get("boxId")

            input_token_ids = set()
            for inp in inputs:
                for asset in inp.get("assets", []):
                    input_token_ids.add(asset.get("tokenId"))

            for output in tx.get("outputs", []):
                for asset in output.get("assets", []):
                    token_id = asset.get("tokenId")
                    if token_id and token_id not in input_token_ids:
                        if token_id == first_input_box_id:
                            issued_tokens.append({
                                "token_id": token_id,
                                "tx_id": tx.get("transactionId"),
                                "amount": asset.get("amount"),
                            })
                            batch_found += 1

        print(f"found {batch_found} (total: {len(issued_tokens)})")
        offset += batch_size
        time.sleep(0.5)

        if len(transactions) < batch_size:
            break
        if offset > 50000:
            print("  Safety limit reached")
            break

    print(f"\nFound {len(issued_tokens)} token IDs via GraphQL")

    # Fetch metadata
    print("\nFetching token metadata...")
    tokens = []
    for i, item in enumerate(issued_tokens):
        token_id = item["token_id"]
        print(f"[{i+1}/{len(issued_tokens)}] {token_id[:20]}...", end=" ", flush=True)

        token_info = get_token_info(token_id)
        if token_info:
            parsed = parse_token_metadata(token_info)
            tokens.append(parsed)
            print(f"-> {parsed.get('name', 'unnamed')}")
        else:
            print("-> not found")

        if (i + 1) % 10 == 0:
            time.sleep(1)
        else:
            time.sleep(0.2)

    output_file = f"{collection_name}_rest.json"
    with open(output_file, 'w') as f:
        json.dump({
            "mint_address": mint_address,
            "token_count": len(tokens),
            "tokens": tokens
        }, f, indent=2)

    print(f"\nCOMPLETE: {len(tokens)} tokens saved to {output_file}")
    return tokens


# --- Detail Fetching ---

def fetch_details(input_file: str):
    """
    Fetch full register data for tokens from a previous enumeration.
    Reads a _rest.json file and adds R4-R9 register values.
    """
    print(f"\n{'=' * 50}")
    print(f"Fetching register details")
    print(f"Input: {input_file}")
    print(f"{'=' * 50}\n")

    with open(input_file, 'r') as f:
        data = json.load(f)

    tokens = data.get("tokens", [])
    print(f"Found {len(tokens)} tokens to process\n")

    for i, token in enumerate(tokens):
        token_id = token.get("token_id")
        if not token_id:
            continue

        print(f"[{i+1}/{len(tokens)}] {token.get('name', token_id[:16])}...", end=" ", flush=True)

        box_id = token.get("box_id") or token_id
        box_data = get_box_info(box_id)

        if box_data:
            registers = box_data.get("additionalRegisters", {})
            token["registers"] = {}

            for reg_key, reg_value in registers.items():
                if isinstance(reg_value, dict):
                    token["registers"][reg_key] = reg_value.get("serializedValue", "")
                    decoded = decode_register_string(reg_value.get("serializedValue", ""))
                else:
                    token["registers"][reg_key] = str(reg_value)
                    decoded = decode_register_string(str(reg_value))

                if decoded:
                    token[f"{reg_key}_decoded"] = decoded

            # Check for IPFS CID in R9
            r9 = token.get("R9_decoded", "")
            if "ipfs" in r9.lower() or r9.startswith("Qm") or r9.startswith("bafy"):
                token["ipfs_cid"] = r9

            print(f"registers: {list(registers.keys())}")
        else:
            print("box not found")

        if (i + 1) % 10 == 0:
            time.sleep(1)
        else:
            time.sleep(0.3)

    output_file = input_file.replace(".json", "_detailed.json")
    with open(output_file, 'w') as f:
        json.dump({
            "mint_address": data.get("mint_address"),
            "token_count": len(tokens),
            "tokens": tokens
        }, f, indent=2)

    print(f"\nSaved {len(tokens)} detailed tokens to {output_file}")


# --- CLI ---

def print_usage():
    print("""
Ergo NFT Collection Scraper
============================

Enumerate any NFT collection on Ergo given its mint wallet address.

Commands:
  enumerate <mint_address> <name>            Enumerate via REST API
  enumerate <mint_address> <name> --graphql  Enumerate via GraphQL
  fetch-details <input_json>                 Add register data to enumerated tokens
  test                                       Test API connectivity

Examples:
  python ergo_nft_scraper.py enumerate 9abc123...xyz my_collection
  python ergo_nft_scraper.py fetch-details my_collection_rest.json
  python ergo_nft_scraper.py test

How it works:
  Ergo minting rule: token ID = box ID of first input in minting transaction.
  The scraper scans all transactions from the mint address and identifies
  minting events using this rule. Then fetches metadata for each token.

Output:
  <name>_rest.json           Token IDs, names, descriptions, numbers
  <name>_rest_detailed.json  Above + R4-R9 register values
  <name>_checkpoint.json     Progress checkpoint (every 500 tokens)
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    command = sys.argv[1]

    if command == "test":
        print("\n=== Testing Ergo Explorer API ===")
        url = f"{ERGO_API}/info"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                print(f"REST API: OK")
            else:
                print(f"REST API: {resp.status_code}")
        except Exception as e:
            print(f"REST API: Failed ({e})")

        print("\n=== Testing GraphQL ===")
        result = graphql_query("{ state { height } }")
        if result:
            print(f"GraphQL: OK (height: {result.get('state', {}).get('height')})")
        else:
            print("GraphQL: Failed")

    elif command == "enumerate":
        if len(sys.argv) < 4:
            print("Usage: python ergo_nft_scraper.py enumerate <mint_address> <collection_name> [--graphql]")
            sys.exit(1)

        mint_address = sys.argv[2]
        collection_name = sys.argv[3]
        use_graphql = "--graphql" in sys.argv

        if use_graphql:
            enumerate_collection_graphql(mint_address, collection_name)
        else:
            enumerate_collection(mint_address, collection_name)

    elif command == "fetch-details":
        if len(sys.argv) < 3:
            print("Usage: python ergo_nft_scraper.py fetch-details <input_json>")
            sys.exit(1)
        fetch_details(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print_usage()
