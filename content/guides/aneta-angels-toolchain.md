---
title: "Aneta Angels NFT Toolchain — Technical Reference"
category: guide
difficulty: advanced
tags: [nft, aneta-angels, toolchain, scraper, rarity, ipfs]
author: CannonQ
source: original
updated: 2026-03-09
---
# Aneta Angels NFT Toolchain — Technical Reference

**Date:** February 2026
**Collection:** Aneta Angels (Ergo blockchain)
**Stack:** Python 3.x + Local Ergo indexed node

---

## Infrastructure

All scripts run on a Windows workstation querying a local Ergo full node running on Ubuntu. The node is fully synced and indexed (`extraIndex=true` in `ergo.conf`), which enables the `/blockchain/*` API endpoints used throughout.

| Component | Detail |
|-----------|--------|
| Ergo node | ergo-6.1.2.jar, mainnet, UTXO mode |
| API port | 9053 |
| P2P port | 9030 |
| Python | 3.14 (Windows) |
| Only dependency | `requests` (`pip install requests`) |

The public Ergo Explorer API (`api.ergoplatform.com/api/v1`) is available as a fallback in every script. All scripts auto-detect whether the local node is reachable and fall back to the public API with a 0.3s rate limit delay if not.

---

## Scripts

### 1. `aneta_angels_scraper.py` — Token Enumeration & Enrichment

The core scraper. Enumerates all tokens minted from a wallet address, fetches metadata, checks burn status, and exports structured data.

**Commands:**

```
python aneta_angels_scraper.py test       # Verify node connection, peek at mint wallet
python aneta_angels_scraper.py enumerate  # Fast ID-only enumeration (no metadata)
python aneta_angels_scraper.py full       # Full scan: IDs + traits + burn check + holder distribution
```

**Enumeration logic:**

On Ergo, `tokenId = boxId of first input in the minting transaction`. The script paginates through all transactions from the mint address and identifies mints by checking if any output asset's `tokenId` matches the first input's `boxId`.

```
For each TX from mint wallet:
  first_input_box_id = tx.inputs[0].boxId
  for each output in tx.outputs:
    for each asset in output.assets:
      if asset.tokenId == first_input_box_id:
        → This is a MINT transaction
        → token_id = asset.tokenId
```

**Enrichment (2 API calls per token):**

1. `/blockchain/token/byId/{tokenId}` → name, description (contains traits as JSON), decimals
2. `/blockchain/box/unspent/byTokenId/{tokenId}` → if empty array, token is burned

**Name filter:** Tokens whose name doesn't start with "Aneta" are skipped (filters out 219 "Hazey's Test NFT" tokens minted from the same wallet).

**Output files:**

| File | Contents |
|------|----------|
| `aneta_angels_all_TIMESTAMP.json` | Full data (active + burned tokens) |
| `aneta_angels_active_TIMESTAMP.json` | Active tokens only (the registry) |
| `aneta_angels_active_TIMESTAMP.csv` | Flat CSV for spreadsheets |

**Final numbers:**

```
Total minted from wallet:  4,664
Aneta Angels (name filter): 4,445
  Active:                    4,406
  Burned:                       39
Skipped (non-Aneta):           219
```

---

### 2. `aneta_traits.py` — Trait Distribution Analysis

Reads the active tokens JSON and produces trait frequency counts across all 6 categories.

```
python aneta_traits.py aneta_angels_active_TIMESTAMP.json
```

**Outputs:**

| File | Contents |
|------|----------|
| `aneta_angels_trait_summary.json` | Per-category value counts with percentages |
| `aneta_angels_trait_summary.csv` | Flat CSV: Category, Value, Count, Pct |

**Console output includes ASCII bar charts per trait value.**

**Notable finding:** A typo entry `Backgrounds` (with an 's') appeared with 1 token — likely a minting error. The scripts handle this by treating category names as-is from the on-chain data.

---

### 3. `aneta_rarity.py` — Rarity Scoring (Approach D)

Computes a rarity score for each token using normalized inverse frequency, assigns tiers by percentile, and maps Skin Tone to a Focus gameplay modifier.

```
python aneta_rarity.py aneta_angels_active_TIMESTAMP.json
```

**Scoring methodology (Approach D — Normalized Inverse Frequency per Category):**

1. For each trait value: `raw_score = 1 / (frequency_pct / 100)`
2. Normalize each category independently to 0–100: `normalized = (raw - cat_min) / (cat_max - cat_min) × 100`
3. Sum normalized scores across 5 categories (Wings, Body, Face, Head, Background). Max = 500.
4. Assign tier by percentile rank.

Skin Tone is excluded from rarity scoring (all 4 tones are ~25% each, adds only noise). Instead, Skin Tone maps to a Focus modifier for gameplay (Tone 1 = 0.85 high focus, Tone 4 = 0.40 low focus).

**Tier distribution:**

| Tier | Percentile | Count | Score Range |
|------|-----------|-------|-------------|
| Common | 0–30% | 1,321 | 0.6 – 36.3 |
| Uncommon | 30–60% | 1,321 | 36.3 – 61.5 |
| Rare | 60–80% | 882 | 61.5 – 101.5 |
| Epic | 80–92% | 529 | 101.5 – 127.8 |
| Legendary | 92–98% | 264 | 127.8 – 163.7 |
| Mythic | Top 2% | 89 | 163.7 – 265.0 |

**Output files:**

| File | Purpose |
|------|---------|
| `aneta_angels_scored.json` | Full data with scores and tiers (GitHub Pages) |
| `aneta_angels_scored.csv` | Flat CSV for spreadsheets |
| `aneta_angels_avl_entries.json` | Minimal key-value pairs for AVL tree builder |
| `aneta_angels_scoring_reference.json` | Methodology doc — SHA-256 hash goes on-chain |

**AVL tree value format:** 1 byte per token — `bits 7-4 = tier_code (0–5)`, `bits 3-0 = focus_code (0–3)`.

---

### 4. `aneta_ipfs.py` — IPFS Artwork URL Enrichment

Fetches the IPFS artwork URL and SHA-256 hash for each token from the minting box registers.

```
python aneta_ipfs.py aneta_angel_traits.json
python aneta_ipfs.py aneta_angel_traits.json --source aneta_angels_active.json  # faster
```

**Register layout (Aneta Angels EIP-004):**

| Register | Content | Example |
|----------|---------|---------|
| R4 | Token name | `Aneta #1304` |
| R5 | Description JSON (traits) | `{"721":{"1304":{"name":"...","traits":{...}}}}` |
| R6 | Decimals | `0` |
| R7 | NFT type flags | `0x01 0x01` (Image NFT) |
| R8 | SHA-256 hash of artwork | `ef623174ac21c147c655bb6afa910dee...` |
| R9 | Artwork URL (IPFS) | `http://ipfs.io/ipfs/Qmacqao3z7hUsgJfz...` |

**Two-step API flow (without `--source`):**

1. `/blockchain/token/byId/{tokenId}` → get `boxId` (issuance box)
2. `/blockchain/box/byId/{boxId}` → read `additionalRegisters.R9` and `.R8`

With `--source`, step 1 is skipped using the `outputBoxId` from the scraper data (halves API calls).

**Output files:**

| File | Contents |
|------|----------|
| `aneta_angel_traits_ipfs.json` | Input JSON enriched with `ipfsUrl` + `sha256Hash` |
| `aneta_angels_ipfs_urls.csv` | Flat CSV: token_id, name, ipfsUrl, sha256Hash |

---

## Ergo Node API Reference (What Worked, What Didn't)

### The Big Gotcha: POST vs GET on Local Node

The critical bug that blocked initial development. The local indexed node's `/blockchain/transaction/byAddress` endpoint uses **POST** with the address in the request body — not GET with query params. The public Explorer API uses GET.

**What failed:**

```python
# WRONG for local node — returns 400 Bad Request
url = f"{node_url}/blockchain/transaction/byAddress"
params = {"address": address, "offset": 0, "limit": 100}
resp = requests.get(url, params=params)  # ← GET doesn't work
```

**What works:**

```python
# CORRECT for local node — POST with address as JSON string body
url = f"{node_url}/blockchain/transaction/byAddress"
params = {"offset": 0, "limit": 100}  # offset/limit stay as query params
resp = requests.post(
    url,
    params=params,
    headers={"Content-Type": "application/json"},
    data=json.dumps(address),  # address goes in body as a quoted string
    timeout=30
)
```

The public Explorer API uses a completely different pattern:

```python
# Public API — GET with address in URL path
url = f"https://api.ergoplatform.com/api/v1/addresses/{address}/transactions"
params = {"offset": 0, "limit": 100}
resp = requests.get(url, params=params)
```

### Endpoints That Work with GET (Local Node)

These take the ID as a path parameter and work fine with GET:

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/blockchain/token/byId/{tokenId}` | GET | Token metadata (name, description, decimals, boxId) |
| `/blockchain/box/byId/{boxId}` | GET | Full box data including `additionalRegisters` |
| `/blockchain/box/unspent/byTokenId/{tokenId}` | GET | Array of unspent boxes containing this token |
| `/blockchain/indexedHeight` | GET | Current indexed height (verifies node is indexed) |
| `/info` | GET | Node info (name, height, network, stateType) |
| `/utxo/byId/{boxId}` | GET | Unspent box by ID (returns 404 if spent) |

### Local Node vs Public API Response Differences

| Field | Local Node | Public API |
|-------|-----------|------------|
| Token ID field | `id` | `tokenId` |
| Token type field | Not returned | `type` (e.g., "EIP-004") |
| TX list from address | Returns raw array | Returns `{"items": [...], "total": N}` |
| Box registers | Raw hex in `additionalRegisters` | May include `renderedValue` dict |
| Token name in TX output | Not embedded | Included in asset data |

### Register Decoding (Coll[Byte] → String)

Ergo registers store values as serialized bytes. For string values (URLs, names, descriptions), the format is:

```
0e          ← Type prefix: Coll[Byte]
XX          ← VLQ-encoded length (1+ bytes)
[hex data]  ← UTF-8 bytes encoded as hex
```

**VLQ (Variable Length Quantity) decoding:**

```python
pos = 2  # skip "0e" prefix
length = 0
shift = 0
while pos < len(hex_str):
    byte_val = int(hex_str[pos:pos+2], 16)
    pos += 2
    length |= (byte_val & 0x7F) << shift
    shift += 7
    if (byte_val & 0x80) == 0:
        break
# Then: bytes.fromhex(hex_str[pos:pos + length * 2]).decode('utf-8')
```

**Example:** R9 register `0e42687474703a2f2f...`

- `0e` = Coll[Byte] type
- `42` = length 66 (0x42, single byte since < 128)
- Remaining hex decodes to `http://ipfs.io/ipfs/Qmacqao3z7hUsgJfzJsY35eHiyFR9muB1epLmLtb76bjEP`

### The R7/R9 Mixup

Initial assumption was R7 = artwork URL (matching some EIP-004 documentation). For Aneta Angels, the actual layout is:

- R7 = NFT type flags (`0e020101` → 2 bytes: `0x01, 0x01` = Image NFT). Decoding this as a string produces `\u0001\u0001`.
- R9 = Artwork URL (IPFS)

This was diagnosed by fetching a raw box (`curl .../blockchain/box/byId/{boxId}`) and manually decoding each register.

---

## Data Schemas

### aneta_angel_traits.json (Production — GitHub Pages)

```json
{
  "collection": "Aneta Angels",
  "generated_at": "2026-02-14T04:18:00.282Z",
  "total_tokens": 4406,
  "tokens": [
    {
      "token_id": "000b70a75b...",
      "name": "Aneta #0001",
      "number": 1,
      "traits": {
        "Wings": "Angel Wings",
        "Body": "Robot",
        "Face": "Dia De Los Muertos",
        "Head": "French Crop",
        "Background": "Light Pink",
        "Skin Tone": "Tone 1"
      },
      "rarity_tier": "Common",
      "rarity_score": 36.2,
      "normalized_scores": {
        "Wings": 0,
        "Body": 21.13,
        "Face": 0,
        "Head": 13.45,
        "Background": 1.62
      },
      "ipfsUrl": "http://ipfs.io/ipfs/Qm...",
      "sha256Hash": "ef623174ac21c147...",
      "status": "circulating"
    }
  ]
}
```

### aneta_angels_avl_entries.json (AVL Tree Builder Input)

```json
{
  "collection": "Aneta Angels",
  "entry_format": "key=token_id(32bytes), value=packed_byte(tier<<4|focus)",
  "entry_count": 4406,
  "entries": [
    {
      "key": "994fdc7164378120c03a5177eb798567dcc1366bde1b23acff4e1dad9d11fa35",
      "value_byte": 83,
      "value_hex": "53",
      "tier": "Mythic",
      "focus": "Low Focus",
      "score": 264.96
    }
  ]
}
```

### Raw Scraper Output (Intermediate)

```json
{
  "tokenId": "c1aafd25beb2276f...",
  "name": "Aneta #1955",
  "amount": 1,
  "mintTxId": "7347ab7ffa921a66...",
  "outputBoxId": "f9d6d7688f835433...",
  "parsedName": "Aneta #1955",
  "description": "{\"721\":{\"1955\":{...}}}",
  "decimals": 0,
  "type": "",
  "emissionAmount": 1,
  "traits": {
    "Wings": "Falcon Wings",
    "Skin Tone": "Tone 2",
    "Body": "Orlando",
    "Face": "Meme 4",
    "Head": "Crown",
    "Background": "Light Green"
  },
  "status": "active"
}
```

---

## On-Chain Verification (AVL Tree)

The rarity scores are frozen on-chain via a single Ergo box containing:

| Register | Contents | Size |
|----------|----------|------|
| R4 | AVL tree root hash | 32 bytes |
| R5 | SHA-256 of scoring methodology document | 32 bytes |
| R6 | Data URL (GitHub Pages) | ~80 bytes |

**Total box size:** ~350 bytes (well under 4,096 byte limit)

The full tree data (4,406 entries × 4 bytes each) lives off-chain on GitHub Pages. Anyone can rebuild the tree from the published data and verify the root hash matches R4. If a single score were changed, the hash would not match.

---

## Pipeline Order

```
1. aneta_angels_scraper.py full
   → Enumerate mint wallet, fetch metadata, check burns
   → Output: aneta_angels_active_TIMESTAMP.json

2. aneta_traits.py <active_json>
   → Count trait frequencies
   → Output: aneta_angels_trait_summary.csv

3. aneta_rarity.py <active_json>
   → Score tokens, assign tiers, map focus
   → Output: aneta_angels_scored.json, aneta_angels_avl_entries.json

4. aneta_ipfs.py <traits_json>
   → Fetch IPFS URLs from minting box R9 register
   → Output: aneta_angel_traits_ipfs.json

5. [Manual] Clean and merge into aneta_angel_traits.json for GitHub Pages

6. [Future] AVL tree builder → mint on-chain box with root hash
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ERGO_NODE_URL` | `http://localhost:9053` | Local node address |
| `ERGO_USE_PUBLIC` | `0` | Set to `1` to force public API |

---

## Prior Art

This toolchain was adapted from a prior NFT scraper which enumerated 15,349 tokens across 11 collections using the same mint-wallet-enumeration approach. Key difference: the prior scraper used the public Explorer API exclusively, while the Aneta Angels scraper was built for local node use, which required discovering the POST vs GET difference on `/blockchain/transaction/byAddress`.
