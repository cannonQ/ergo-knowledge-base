---
title: "NFT Collection Toolchain — Technical Reference"
category: guide
difficulty: advanced
tags: [nft, toolchain, scraper, ipfs, registers, mint-enumeration]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# NFT Collection Toolchain — Technical Reference

**Stack:** Python 3.x + Local Ergo indexed node

This guide documents a reusable toolchain for enumerating, enriching, and analyzing NFT collections on the Ergo blockchain. Originally built for the Aneta Angels collection, the patterns apply to any Ergo NFT project.

---

## Infrastructure

All scripts run against an Ergo full node with indexing enabled (`extraIndex=true` in `ergo.conf`), which enables the `/blockchain/*` API endpoints used throughout.

| Component | Detail |
|-----------|--------|
| Ergo node | Mainnet, UTXO mode, indexed |
| API port | 9053 |
| Python | 3.x |
| Only dependency | `requests` (`pip install requests`) |

The public Ergo Explorer API (`api.ergoplatform.com/api/v1`) is available as a fallback in every script. All scripts auto-detect whether the local node is reachable and fall back to the public API with a 0.3s rate limit delay if not.

---

## Script 1: Token Enumeration from Mint Wallet

The core scraper. Enumerates all tokens minted from a wallet address, fetches metadata, checks burn status, and exports structured data.

**Commands:**

```
python nft_scraper.py test       # Verify node connection, peek at mint wallet
python nft_scraper.py enumerate  # Fast ID-only enumeration (no metadata)
python nft_scraper.py full       # Full scan: IDs + traits + burn check + holder distribution
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

**Output files:**

| File | Contents |
|------|----------|
| `collection_all_TIMESTAMP.json` | Full data (active + burned tokens) |
| `collection_active_TIMESTAMP.json` | Active tokens only (the registry) |
| `collection_active_TIMESTAMP.csv` | Flat CSV for spreadsheets |

---

## Script 2: Trait Distribution Analysis

Reads the active tokens JSON and produces trait frequency counts across all categories.

```
python trait_analyzer.py collection_active.json
```

**Outputs:**

| File | Contents |
|------|----------|
| `trait_summary.json` | Per-category value counts with percentages |
| `trait_summary.csv` | Flat CSV: Category, Value, Count, Pct |

Console output includes ASCII bar charts per trait value. Useful for identifying rare traits, minting errors (e.g. typo categories), and distribution anomalies.

---

## Script 3: IPFS Artwork URL Enrichment

Fetches the IPFS artwork URL and SHA-256 hash for each token from the minting box registers.

```
python ipfs_enricher.py collection_traits.json
python ipfs_enricher.py collection_traits.json --source collection_active.json  # faster
```

**Register layout (EIP-004 NFTs):**

| Register | Content | Example |
|----------|---------|---------|
| R4 | Token name | `Collection #1304` |
| R5 | Description JSON (traits) | `{"721":{"1304":{"name":"...","traits":{...}}}}` |
| R6 | Decimals | `0` |
| R7 | NFT type flags | `0x01 0x01` (Image NFT) |
| R8 | SHA-256 hash of artwork | `ef623174ac21c147c655bb6afa910dee...` |
| R9 | Artwork URL (IPFS) | `http://ipfs.io/ipfs/Qmacqao3z7hUsgJfz...` |

**Two-step API flow (without `--source`):**

1. `/blockchain/token/byId/{tokenId}` → get `boxId` (issuance box)
2. `/blockchain/box/byId/{boxId}` → read `additionalRegisters.R9` and `.R8`

With `--source`, step 1 is skipped using the `outputBoxId` from the scraper data (halves API calls).

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

Initial assumption was R7 = artwork URL (matching some EIP-004 documentation). The actual layout for many collections is:

- R7 = NFT type flags (`0e020101` → 2 bytes: `0x01, 0x01` = Image NFT). Decoding this as a string produces `\u0001\u0001`.
- R9 = Artwork URL (IPFS)

This was diagnosed by fetching a raw box (`curl .../blockchain/box/byId/{boxId}`) and manually decoding each register. Always verify register layout against actual on-chain data.

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ERGO_NODE_URL` | `http://localhost:9053` | Local node address |
| `ERGO_USE_PUBLIC` | `0` | Set to `1` to force public API |
