#!/usr/bin/env python3
"""
Ergo Storage Rent Scanner
=========================
Scans the Ergo blockchain for Storage Rent claim transactions and writes
results to Supabase + local CSV backup.

SR Detection Criteria:
  1. Input has empty spendingProof.proofBytes
  2. Box age >= 1,051,200 blocks (~4 years)

API Flow:
  1. /blocks/at/{height}              -> block header ID
  2. /blocks/{blockId}/transactions   -> TX list (check for empty proofBytes)
  3. /blockchain/transaction/byId/... -> full TX details with creationHeight

Usage:
  python sr_scanner.py                  # Test: scan last 150 blocks
  python sr_scanner.py 1130354 1130400  # Custom range
  python sr_scanner.py --resume         # Resume from last saved position
  python sr_scanner.py --full           # Full historical scan from SR start

Requirements:
  pip install requests

Setup:
  1. Set NODE_URL to your Ergo node (must have extraIndex=true)
  2. Set SUPABASE_URL and SUPABASE_KEY for your Supabase project
  3. Create the sr_claims table (see SQL below)

Supabase Table SQL:
  CREATE TABLE sr_claims (
      id BIGSERIAL PRIMARY KEY,
      tx_id TEXT UNIQUE NOT NULL,
      block_height INTEGER NOT NULL,
      timestamp BIGINT,
      claimer_address TEXT NOT NULL,
      claimed_box_id TEXT NOT NULL,
      original_owner_address TEXT,
      box_creation_height INTEGER NOT NULL,
      box_age_blocks INTEGER NOT NULL,
      erg_value BIGINT NOT NULL,
      box_original_value BIGINT,
      tokens JSONB DEFAULT '[]',
      created_at TIMESTAMPTZ DEFAULT NOW()
  );
Author: CannonQ
License: AGPL-3.0
"""

import requests
import json
import csv
import time
import os
import sys

# =============================================================================
# CONFIGURATION — UPDATE THESE FOR YOUR ENVIRONMENT
# =============================================================================

NODE_URL = os.environ.get("ERGO_NODE_URL", "http://localhost:9053")
SUPABASE_URL = os.environ.get("SUPABASE_URL")  # e.g. https://xxx.supabase.co
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # service role key from Supabase dashboard

# Storage rent parameters
SR_PERIOD = 1_051_200          # ~4 years in blocks
SR_START_BLOCK = 1_051_200     # First block where SR became possible

PROGRESS_FILE = "sr_scanner_progress.json"
CSV_BACKUP_FILE = "sr_claims_backup.csv"


# =============================================================================
# NODE API FUNCTIONS
# =============================================================================

def get_current_height():
    """Get current blockchain height from node."""
    resp = requests.get(f"{NODE_URL}/info", timeout=10)
    resp.raise_for_status()
    return resp.json().get("fullHeight", 0)


def get_block_transactions(height):
    """Get all transactions for a block at given height."""
    # Step 1: Get block header ID
    resp = requests.get(f"{NODE_URL}/blocks/at/{height}", timeout=10)
    resp.raise_for_status()
    block_ids = resp.json()
    if not block_ids:
        return []

    # Step 2: Get transactions
    block_id = block_ids[0]
    resp = requests.get(f"{NODE_URL}/blocks/{block_id}/transactions", timeout=10)
    resp.raise_for_status()
    return resp.json().get("transactions", [])


def get_full_transaction(tx_id):
    """Get full transaction details including creationHeight on inputs."""
    resp = requests.get(f"{NODE_URL}/blockchain/transaction/byId/{tx_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


# =============================================================================
# SR DETECTION
# =============================================================================

def has_empty_proof_candidate(tx):
    """Quick check: does this TX have any inputs with empty proofBytes?"""
    for inp in tx.get("inputs", []):
        proof = inp.get("spendingProof", {})
        proof_bytes = proof.get("proofBytes", "")
        if proof_bytes == "":
            return True
    return False


def find_sr_claims(full_tx, block_height):
    """
    Analyze a full transaction for SR claims.
    Returns list of claim dicts.
    """
    claims = []
    tx_id = full_tx.get("id", "")
    inputs = full_tx.get("inputs", [])
    outputs = full_tx.get("outputs", [])

    # Find the claimer address (first output with value)
    claimer_address = ""
    if outputs:
        claimer_address = outputs[0].get("address", "")

    for inp in inputs:
        proof = inp.get("spendingProof", {})
        proof_bytes = proof.get("proofBytes", "")

        if proof_bytes != "":
            continue  # Has a real signature, not SR

        box_id = inp.get("boxId", "")
        creation_height = inp.get("creationHeight", 0)
        box_value = inp.get("value", 0)
        box_address = inp.get("address", "")

        # Check age requirement
        box_age = block_height - creation_height
        if box_age < SR_PERIOD:
            continue  # Too young for SR

        # Extract tokens
        tokens = []
        for asset in inp.get("assets", []):
            tokens.append({
                "tokenId": asset.get("tokenId", ""),
                "amount": asset.get("amount", 0)
            })

        # Determine actual ERG received by claimer
        erg_received = box_value
        if outputs:
            erg_received = outputs[0].get("value", box_value)

        claims.append({
            "tx_id": tx_id,
            "block_height": block_height,
            "claimer_address": claimer_address,
            "claimed_box_id": box_id,
            "original_owner_address": box_address[:20] if box_address else "",
            "box_creation_height": creation_height,
            "box_age_blocks": box_age,
            "erg_value": erg_received,
            "box_original_value": box_value,
            "tokens": json.dumps(tokens),
        })

    return claims


def scan_block(height):
    """Scan a single block for SR claims."""
    txs = get_block_transactions(height)
    all_claims = []

    for tx in txs:
        if not has_empty_proof_candidate(tx):
            continue

        # Fetch full TX for creationHeight data
        tx_id = tx.get("id", "")
        try:
            full_tx = get_full_transaction(tx_id)
            claims = find_sr_claims(full_tx, height)
            all_claims.extend(claims)
        except Exception as e:
            print(f"  Error fetching TX {tx_id[:16]}...: {e}")

    return all_claims


# =============================================================================
# PERSISTENCE
# =============================================================================

def save_to_supabase(claims):
    """Write claims to Supabase. Returns number saved."""
    if not claims:
        return 0

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates"
    }

    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/sr_claims",
            headers=headers,
            json=claims,
            timeout=30
        )
        if resp.status_code in (200, 201):
            return len(claims)
        else:
            print(f"  Supabase error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  Supabase error: {e}")

    return 0


def save_to_csv(claims):
    """Append claims to local CSV backup."""
    if not claims:
        return

    file_exists = os.path.exists(CSV_BACKUP_FILE)
    fieldnames = [
        "tx_id", "block_height", "claimer_address", "claimed_box_id",
        "original_owner_address", "box_creation_height", "box_age_blocks",
        "erg_value", "box_original_value", "tokens"
    ]

    with open(CSV_BACKUP_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(claims)


def save_progress(height):
    """Save last scanned height to JSON."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({"last_scanned": height}, f)


def load_progress():
    """Load last scanned height."""
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f).get("last_scanned", SR_START_BLOCK)
    except FileNotFoundError:
        return SR_START_BLOCK


# =============================================================================
# MAIN SCAN LOOP
# =============================================================================

def scan_range(start_height, end_height):
    """Scan a range of blocks for SR claims."""
    total_blocks = end_height - start_height + 1
    total_claims = 0
    total_erg = 0
    total_tokens = 0
    save_every = 10

    print(f"\n{'='*60}")
    print(f"ERGO STORAGE RENT SCANNER")
    print(f"{'='*60}")
    print(f"Range: {start_height:,} to {end_height:,}")
    print(f"Total blocks: {total_blocks:,}")
    print(f"{'='*60}")

    for height in range(start_height, end_height + 1):
        pct = (height - start_height) / total_blocks * 100
        if height % 100 == 0:
            print(f"\nBlock {height:,} ({pct:.1f}%)")

        try:
            claims = scan_block(height)

            if claims:
                for c in claims:
                    erg = c["erg_value"] / 1e9
                    tokens = json.loads(c["tokens"])
                    token_count = len(tokens)
                    total_claims += 1
                    total_erg += c["erg_value"]
                    total_tokens += token_count

                    print(f"\n  *** SR CLAIM in block {height}!")
                    print(f"      TX: {c['tx_id'][:40]}...")
                    print(f"      Box had: {c['box_original_value']/1e9:.4f} ERG"
                          f" | Claimer got: {erg:.4f} ERG")
                    print(f"      Box age: {c['box_age_blocks']:,} blocks")
                    print(f"      Claimer: {c['claimer_address'][:40]}")

                # Persist
                save_to_csv(claims)
                save_to_supabase(claims)

            # Save progress periodically
            if height % save_every == 0:
                save_progress(height)

        except Exception as e:
            print(f"  Error at block {height}: {e}")
            time.sleep(1)

    save_progress(end_height)

    print(f"\n{'='*60}")
    print(f"SCAN COMPLETE")
    print(f"{'='*60}")
    print(f"Blocks scanned: {total_blocks:,}")
    print(f"SR claims found: {total_claims}")
    print(f"Total rent collected: {total_erg / 1e9:.4f} ERG")
    print(f"Total tokens claimed: {total_tokens}")
    print(f"{'='*60}\n")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    current_height = get_current_height()
    print(f"Current node height: {current_height:,}")

    if len(sys.argv) == 1:
        start = current_height - 150
        end = current_height
        print("TEST MODE: Scanning last 150 blocks")

    elif len(sys.argv) == 3:
        start = int(sys.argv[1])
        end = int(sys.argv[2])

    elif sys.argv[1] == "--resume":
        start = load_progress() + 1
        end = current_height
        print(f"RESUME MODE: Continuing from block {start:,}")

    elif sys.argv[1] == "--full":
        start = SR_START_BLOCK
        end = current_height
        print(f"FULL MODE: Scanning from SR start block {start:,}")

    else:
        print("Usage:")
        print("  python sr_scanner.py                  # Test: last 150 blocks")
        print("  python sr_scanner.py <start> <end>    # Custom range")
        print("  python sr_scanner.py --resume         # Resume from last position")
        print("  python sr_scanner.py --full           # Full historical scan")
        sys.exit(1)

    scan_range(start, end)
