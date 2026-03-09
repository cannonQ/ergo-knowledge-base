#!/usr/bin/env python3
"""
Process MewMart GraphQL Export — Extract NFT Sales
===================================================
Parses spent boxes from a MewMart (or similar) marketplace contract,
decodes register values, cross-references against an NFT registry,
and outputs enriched sales data.

Workflow:
  1. Query GQL for spent boxes by ErgoTree (marketplace contract)
  2. Save paginated results as JSON files
  3. Merge with merge_gql_exports.py if needed
  4. Run this script to parse, decode, and filter

Register Layout (MewMart):
  R4: Price (SLong or BigInt) — in nanoERG or token smallest unit
  R5: Seller proposition bytes (SigmaProp)
  R6: Royalty basis points (SLong)
  R7: Payment token ID (Coll[Byte]) — empty = ERG payment
  R8: Label string (Coll[Byte]) — e.g. "MewMart,CollectionName,Sell"
  R9: Fee basis points (SLong)

Usage:
  python process_mewmart_gql.py -i gql_merged.json --registry nft_registry.json
  python process_mewmart_gql.py -i gql_merged.json --registry nft_registry.json --all

Requirements:
  pip install requests  (only if enriching with Crux prices)
Author: CannonQ
License: AGPL-3.0
"""

import json
import os
import sys
import csv
import argparse
from datetime import datetime, timezone
from collections import defaultdict


# =============================================================================
# REGISTER DECODERS
# =============================================================================

def decode_vlq(data):
    """Decode Variable Length Quantity. Returns (value, bytes_consumed)."""
    result = 0
    shift = 0
    consumed = 0
    for byte in data:
        consumed += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, consumed


def zigzag_decode(n):
    """Decode zigzag-encoded signed integer."""
    return (n >> 1) ^ -(n & 1)


def decode_slong(hex_str):
    """Decode SLong (type prefix 05 or 06) from register hex."""
    if not hex_str:
        return 0
    if hex_str.startswith(("05", "06")):
        hex_str = hex_str[2:]
    data = bytes.fromhex(hex_str)
    value, _ = decode_vlq(data)
    return zigzag_decode(value)


def decode_bigint(hex_str):
    """Decode BigInt (type prefix 06 + length + big-endian bytes)."""
    if not hex_str:
        return 0
    if hex_str.startswith("06"):
        hex_str = hex_str[2:]
    data = bytes.fromhex(hex_str)
    length, idx = decode_vlq(data)
    if length <= 0:
        return 0
    return int.from_bytes(data[idx:idx + length], 'big', signed=True)


def decode_coll_byte(hex_str):
    """Decode Coll[Byte] (type prefix 0e) to raw hex content."""
    if not hex_str:
        return ""
    if hex_str.startswith("0e"):
        hex_str = hex_str[2:]
    data = bytes.fromhex(hex_str)
    length, idx = decode_vlq(data)
    if length <= 0:
        return ""
    return data[idx:idx + length].hex()


def decode_coll_byte_utf8(hex_str):
    """Decode Coll[Byte] to UTF-8 string."""
    content_hex = decode_coll_byte(hex_str)
    if not content_hex:
        return ""
    try:
        return bytes.fromhex(content_hex).decode('utf-8', errors='ignore')
    except Exception:
        return content_hex


def decode_sigmaprop(hex_str):
    """Decode SigmaProp. Returns compressed public key hex."""
    if not hex_str:
        return ""
    if hex_str.startswith("08"):
        hex_str = hex_str[2:]
    if hex_str.startswith("cd"):
        return hex_str[2:2 + 66]  # 33-byte compressed pubkey
    return hex_str


def decode_price(hex_str):
    """Decode R4 price — handles both SLong and BigInt encodings."""
    if not hex_str:
        return 0
    if hex_str.startswith("05"):
        return abs(decode_slong(hex_str))
    elif hex_str.startswith("06"):
        # Try BigInt first (for large values)
        try:
            val = decode_bigint(hex_str)
            if val > 0:
                return val
        except Exception:
            pass
        return abs(decode_slong(hex_str))
    return 0


# =============================================================================
# NFT REGISTRY
# =============================================================================

def load_nft_registry(json_path):
    """
    Load NFT registry mapping tokenId -> collection name.
    Supports registry format:
      {"collection_a": ["tokenId1", ...], "collection_b": ["tokenId2", ...], "_metadata": {...}}
    """
    tokens = {}
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"  Warning: Registry not found: {json_path}")
        return tokens

    if isinstance(data, dict):
        for collection_name, token_ids in data.items():
            if collection_name.startswith('_'):
                continue
            if isinstance(token_ids, list):
                for token_id in token_ids:
                    tokens[token_id] = collection_name

    print(f"  Loaded {len(tokens)} token IDs from registry")
    return tokens


# =============================================================================
# BOX PARSING
# =============================================================================

def parse_listing_box(box, nft_registry):
    """
    Parse a single marketplace listing box into a sale record.
    Returns dict or None (if not a valid sale).
    """
    box_id = box.get("boxId", "")
    spent_by = box.get("spentBy")

    # Must be spent to be a completed sale (or cancellation)
    if not spent_by:
        return None

    spent_tx_id = spent_by.get("transactionId", "") if isinstance(spent_by, dict) else ""

    assets = box.get("assets", [])
    if not assets:
        return None

    # First asset is the NFT
    nft = assets[0]
    nft_token_id = nft.get("tokenId", "")
    nft_amount = int(nft.get("amount", 0))
    nft_name = nft.get("name", "")

    # Parse registers
    registers = box.get("additionalRegisters", {})

    r4_hex = registers.get("R4", "")
    r5_hex = registers.get("R5", "")
    r6_hex = registers.get("R6", "")
    r7_hex = registers.get("R7", "")
    r8_hex = registers.get("R8", "")
    r9_hex = registers.get("R9", "")

    price = decode_price(r4_hex)
    seller_pk = decode_sigmaprop(r5_hex)
    royalty_bps = abs(decode_slong(r6_hex)) if r6_hex else 0
    payment_token_hex = decode_coll_byte(r7_hex)
    label = decode_coll_byte_utf8(r8_hex)
    fee_bps = abs(decode_slong(r9_hex)) if r9_hex else 0

    # Determine payment type
    payment_token_id = payment_token_hex if payment_token_hex else None
    payment_type = "TOKEN" if payment_token_id else "ERG"

    # Check NFT registry
    collection = nft_registry.get(nft_token_id, None)

    creation_height = box.get("creationHeight", 0)
    settlement_height = box.get("settlementHeight", 0)

    return {
        "box_id": box_id,
        "nft_token_id": nft_token_id,
        "nft_name": nft_name,
        "nft_amount": nft_amount,
        "collection": collection,
        "price_raw": price,
        "price_erg": price / 1e9 if payment_type == "ERG" else None,
        "payment_type": payment_type,
        "payment_token_id": payment_token_id,
        "seller_pk": seller_pk,
        "royalty_bps": royalty_bps,
        "fee_bps": fee_bps,
        "label": label,
        "creation_height": creation_height,
        "settlement_height": settlement_height,
        "spent_tx_id": spent_tx_id,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Process marketplace GQL export')
    parser.add_argument('--input', '-i', required=True,
                        help='Input JSON file (merged GQL export)')
    parser.add_argument('--registry', '-c', required=True,
                        help='NFT registry JSON (nft_registry.json)')
    parser.add_argument('--output', '-o', default='marketplace_sales',
                        help='Output filename prefix (default: marketplace_sales)')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Include all NFTs, not just registry matches')

    args = parser.parse_args()

    print("=" * 70)
    print("MARKETPLACE GQL SALES PROCESSOR")
    print("=" * 70)

    # Load registry
    print(f"\n[1] Loading NFT registry: {args.registry}")
    registry = load_nft_registry(args.registry)

    # Load GQL export
    print(f"\n[2] Loading GQL export: {args.input}")
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"  ERROR: File not found: {args.input}")
        return
    except json.JSONDecodeError as e:
        print(f"  ERROR: Invalid JSON — did you run merge_gql_exports.py first?")
        print(f"         {e}")
        return

    boxes = data.get("data", {}).get("boxes", [])
    print(f"  Loaded {len(boxes)} boxes")

    # Process
    print(f"\n[3] Processing listings...")
    all_listings = []
    registry_matches = []
    errors = 0

    for box in boxes:
        try:
            listing = parse_listing_box(box, registry)
            if listing:
                all_listings.append(listing)
                if listing["collection"]:
                    registry_matches.append(listing)
        except Exception as e:
            errors += 1

    print(f"  Parsed: {len(all_listings)} listings")
    print(f"  Registry matches: {len(registry_matches)}")
    if errors:
        print(f"  Errors: {errors}")

    # Determine output set
    output_set = all_listings if args.all else registry_matches
    if not output_set:
        print("\n  No matching sales found!")
        return

    # Collection stats
    collection_stats = defaultdict(lambda: {"count": 0, "erg_total": 0})
    for sale in output_set:
        coll = sale.get("collection", "unknown")
        collection_stats[coll]["count"] += 1
        if sale["payment_type"] == "ERG" and sale["price_erg"]:
            collection_stats[coll]["erg_total"] += sale["price_erg"]

    # Save JSON
    output_data = {
        "metadata": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "source": "GraphQL marketplace box export",
            "total_listings": len(output_set),
            "erg_listings": sum(1 for s in output_set if s["payment_type"] == "ERG"),
            "token_listings": sum(1 for s in output_set if s["payment_type"] == "TOKEN"),
        },
        "collection_stats": dict(collection_stats),
        "listings": output_set,
    }

    json_file = f"{args.output}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    print(f"\n  Saved {json_file}")

    # Save CSV
    csv_file = f"{args.output}.csv"
    fieldnames = list(output_set[0].keys())
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_set)
    print(f"  Saved {csv_file}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for coll, stats in sorted(collection_stats.items()):
        print(f"  {coll}: {stats['count']} listings, "
              f"{stats['erg_total']:.2f} ERG volume")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
