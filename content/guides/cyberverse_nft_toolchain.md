---
title: "Cyberverse NFT Enumeration & Data Toolchain"
category: guide
difficulty: advanced
tags: [nft, cyberverse, enumeration, scraper, explorer-api, github-actions]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# Cyberverse NFT Enumeration & Data Toolchain — Technical Reference

**Date:** January 2026
**Scope:** Complete registry of 15,349 Cyberverse NFTs across 11 Ergo collections + Ronin cross-chain data
**Stack:** Python 3.x + requests + Ergo Explorer API + ergexplorer API + GitHub Actions
**Repository:** github.com/cannonQ/cyberverse-viewer

---

## Background

Cyberverse is the flagship playable game on the Ergo blockchain — multiple NFT collections, active in-game economy, cross-chain presence on Ronin. Despite this, no open database or public registry of all NFTs existed. This toolchain was built to fill that gap: enumerate every collection, extract metadata and traits, track holders, monitor marketplace activity, and feed it all into a viewer website deployed on Vercel.

The original motivation was a wallet statement tool that needed to categorize Cyberverse tokens separately from generic NFTs and collectibles, since these are the only NFTs on Ergo with real game utility and in-game value.

### Why This Didn't Already Exist

Cyberverse is the only truly developed game on Ergo — playable, multi-collection, active economy — yet no one had published an open dataset of all the NFTs. No public repo, no API, no community database. The Cyberverse team has their own internal data, but it was never exposed for third-party builders. The Cyberverse wiki had partial data, but it was incomplete and undocumented.

This gap means the ecosystem was missing the infrastructure needed for rarity tools, price tracking, holder analytics, game integration by third parties, and even basic collection verification (distinguishing legitimate Cyberverse tokens from unrelated tokens with similar names). Ergo's NFT tooling in general lags behind — no equivalent of Etherscan's token tracker or Solana's Metaplex metadata standard with universal indexing.

**Important: No data was scraped from the Cyberverse game or the wiki.** Every token ID, every trait, every property in this dataset was enumerated directly from the Ergo blockchain via public Explorer APIs. The wiki's `cc2.json`/`cc3.json` files were discovered during research but not used — the on-chain enumeration was authoritative and complete without them. The only non-chain resources used were NFT images, sourced from two places with permission: A Cyberverse community dev granted access to the wiki's image set, and the creator of ergexplorer.com allowed use of his database of NFT images. Combined, the two sources provide the complete image set across all 11 collections. The viewer caches these images on-site to avoid hammering their infrastructure with repeated requests.

The toolchain documented here is now the most complete public Cyberverse dataset that exists. It was built entirely from on-chain data using public APIs, with no access to Cyberverse team internals beyond the image permission. The data files are hosted on GitHub and served via the viewer at cyberverse-viewer.vercel.app — available for any builder in the ecosystem to use.

---

## Infrastructure

| Component | Detail |
|-----------|--------|
| Runtime | Python 3.x (Windows 10 / PowerShell) |
| HTTP library | `requests` (only external dependency) |
| Primary API | `https://api.ergoplatform.com/api/v1` |
| Fallback API | `https://api.ergexplorer.com` (for high-tx wallets) |
| GraphQL | `https://gql.ergoplatform.com/` and `https://explore.sigmaspace.io/api/graphql` |
| Automation | GitHub Actions (cron workflows in cyberverse-viewer repo) |
| Hosting | Vercel (Next.js app at cyberverse-viewer.vercel.app) |
| Data format | JSON files served from `public/data/` in the repo |

---

## The Core Enumeration Pattern

Every script in the toolchain uses the same fundamental approach, rooted in a key Ergo blockchain property.

**Ergo Minting Rule:** A token's ID equals the Box ID of the first input in its minting transaction. This means you can enumerate every token minted by an address by scanning that address's transaction history and checking whether any output contains a token whose ID matches the first input's box ID.

```python
def enumerate_minted_tokens(mint_address: str) -> list:
    token_ids = []
    offset = 0
    
    while True:
        url = f"{ERGO_API}/addresses/{mint_address}/transactions"
        resp = requests.get(url, params={"offset": offset, "limit": 100}, timeout=30)
        items = resp.json().get("items", [])
        if not items:
            break
        
        for tx in items:
            first_input_box_id = tx["inputs"][0]["boxId"]
            for output in tx["outputs"]:
                for asset in output.get("assets", []):
                    if asset["tokenId"] == first_input_box_id:
                        token_ids.append(asset["tokenId"])
        
        offset += 100
        time.sleep(0.5)
    
    return token_ids
```

This pattern was used for Gen2, Gen3, Cars, Apartments, Pets, Skins, VIP Cards, Emotes, and Audio Tracks. The only exceptions were Eggs and Jackhammers, which required the ergexplorer API shortcut (see below).

---

## API Lessons

### Rate Limiting Is Your Friend (and Enemy)

The Ergo Explorer API at `api.ergoplatform.com` has no documented rate limits, but it will time out or drop connections under sustained load. The scripts evolved a pattern:

```python
# Rate limiting: pause 1 second every 10 requests, 0.2-0.3 seconds between others
if (i + 1) % 10 == 0:
    time.sleep(1)
else:
    time.sleep(0.2)
```

Early versions used `time.sleep(0.5)` uniformly, which was too slow for large collections (Gen3 at 5,999 tokens). Too fast and the API starts returning timeouts. The 10-request burst with 1-second pauses proved reliable across all collections.

**Timeouts on first request:** The API sometimes needed to "warm up" — the first few requests would hang or fail, then subsequent requests would flow normally. Adding a 60-90 second timeout on the initial request and retry logic solved this:

```python
for attempt in range(3):
    result = get_token_holder(token_id)
    if result["holder"]:
        break
    if attempt < 2:
        time.sleep(3)
```

### The ergexplorer API Shortcut

For wallets with extremely high transaction counts, scanning transaction-by-transaction becomes impractical. The CyberEggs mint wallet had 75,000+ transactions — at 100 per page with rate limiting, that's hours of scanning.

The ergexplorer API provides a direct "issued tokens" endpoint:

```
GET https://api.ergexplorer.com/tokens/byIssuedAddress?onlyNft=true&address={address}
```

This returns all tokens minted by an address in a single response, complete with an `isBurned` flag. No need to check each token individually. This endpoint was used for CyberEggs (599 tokens, 451 burned) and Jackhammers (5,203 tokens, none burned).

**Discovery process:** This endpoint wasn't documented anywhere. It was found by watching the Network tab in browser DevTools while viewing the ergexplorer.com address page — when the "Issued Assets" section loaded, the XHR request revealed the API URL.

### GraphQL: Useful but Fragile

The Ergo GraphQL endpoint (`gql.ergoplatform.com`) was essential for marketplace analysis — specifically querying by `ergoTree` to find all boxes matching a smart contract. The REST API doesn't support ErgoTree-based queries.

**Key GraphQL lesson:** The schema differs between endpoints. `gql.ergoplatform.com` does not have `spentTransactionId` as a field — you must use `spentBy { transactionId }` instead. This caused a validation error that was initially confusing:

```
Cannot query field "spentTransactionId" on type "Box". 
Did you mean "transactionId" or "transaction"?
```

**Pagination:** GraphQL uses `take` and `skip` (not `limit` and `offset`). Maximum `take` is typically 500. For large result sets (like SkyHarbor's 50,000+ contract interactions), you must paginate and save each batch to separate JSON files, then merge locally.

### Explorer API Pagination

The REST API defaults to 20 items per page (`limit` parameter) and supports up to 100. The total count is returned in the response, allowing pre-calculation of required pages. Always use `offset` parameter to paginate — never assume all results fit in one response.

---

## Token Status: Circulating vs. Burned vs. Unissued

Not all minted tokens are in circulation. Three categories exist:

| Status | Meaning | Detection |
|--------|---------|-----------|
| Circulating | Held by a non-mint wallet | `boxes/unspent/byTokenId` returns a box with non-mint address |
| Burned | No unspent box exists | `boxes/unspent/byTokenId` returns empty |
| Unissued | Still in mint wallet | Box exists but address matches mint wallet |

The `ergo_nft_filter.py` script implements this three-way classification. CyberPets and CyberEggs share a mint wallet — tokens remaining in that wallet were never distributed (per game lore, some NFTs were burned due to mint issues).

**The ergexplorer shortcut makes this easier:** Its `isBurned` flag eliminates the need to query each token individually. For the Eggs collection: 599 minted, 148 circulating, 451 burned — all determined from a single API call.

---

## EIP-24 Property Extraction

CyberCars and CyberApartments store properties in the issuer box's R6 register using a custom hex encoding with length-prefixed key-value pairs. This follows the EIP-24 artwork contract standard.

**Critical distinction:** The properties are in the **issuer box** (first input of the mint transaction), not the output box. Since token ID equals the issuer box ID, you can fetch properties by looking up the box with the same ID as the token:

```python
# Token ID = Issuer Box ID (per EIP-24)
box_data = requests.get(f"{ERGO_API}/boxes/{token_id}").json()
r6_hex = box_data["additionalRegisters"]["R6"]["serializedValue"]
```

**R6 decoding:** The hex value contains ASCII strings separated by length prefix bytes. A regex approach extracts readable sequences and pairs them as key-value:

```python
data = bytes.fromhex(hex_value)
text = data.decode('latin-1')
parts = re.findall(r'[A-Za-z0-9 \-\_\.]+', text)
# Filter noise, pair as key-value
```

**Parsing noise:** The regex approach catches some false positives. For apartments, "SMALL", "MEDIUM", and "LARGE" appeared as standalone keys when they were actually part of the APARTMENT value. The per-token JSON output was clean, but the summary statistics showed artifacts. Acceptable for the registry use case — individual token data was correct.

**Property keys discovered:**

| Collection | Keys | Example Values |
|------------|------|----------------|
| CyberCars | CAR BRAND, TYPE | HYRON, RX-ERG |
| CyberApartments | LOCATION, BUILDING, APARTMENT, SIZE | Neon Night St., 12, YACHT, 342 |

---

## Register Decoding

Ergo stores metadata in box registers R4-R9. The encoding follows a pattern: type prefix byte, VLQ-encoded length, then the data bytes.

```python
def decode_register_string(hex_value: str) -> str:
    if hex_value.startswith("0e"):  # 0e = Coll[Byte] type prefix
        hex_value = hex_value[2:]
        length_byte = int(hex_value[:2], 16)
        if length_byte < 128:
            data_hex = hex_value[2:2 + length_byte * 2]
        else:
            data_hex = hex_value[4:]  # VLQ for larger lengths
        return bytes.fromhex(data_hex).decode('utf-8', errors='ignore')
```

**Register layout varies by collection:**

| Register | Gen2/Gen3 | Audio Tracks | Aneta Angels |
|----------|-----------|--------------|--------------|
| R4 | Token name | Track name | Token name |
| R5 | Description/traits JSON | Creator/album/rarity JSON | Description/traits JSON |
| R6 | Decimals | Decimals | Decimals |
| R7 | NFT type flags | NFT type flags (`0x01 0x01`) | NFT type flags |
| R8 | SHA-256 hash | SHA-256 hash | SHA-256 hash (hex string) |
| R9 | IPFS URL | IPFS URL | IPFS URL |

**Lesson:** Never assume a register's purpose from its name. R7 was initially mistaken for a URL field in the Aneta Angels scraper — it's actually 2-byte NFT type flags (`01 01` = image NFT). The actual URL is in R9. Always decode and inspect before coding assumptions.

---

## Collection-Specific Challenges

### Audio Tracks (5 Mint Wallets)

Audio tracks were minted across 5 different wallets — the only collection with multiple mint addresses. The first wallet had many transactions and caused API timeouts. Solution: enumerate each wallet separately with a single-wallet variant of the scraper, then merge results into a combined audio JSON.

### CyberSkins (Fungible EIP-004 Tokens)

Unlike all other collections (1:1 NFTs), CyberSkins are fungible tokens. Each skin type has multiple copies (e.g., Razor has 300 copies). This required treating them differently — enumerate 23 unique token IDs rather than thousands of individual NFTs. The scraper's `CYBERSKINS` list hardcodes the 23 known skin names.

### Shared Mint Wallets (Pets + Eggs)

CyberPets and CyberEggs share the same mint wallet (`9fFMwTZ...`). Enumeration returns both types intermingled. Filtering relies on the token name prefix ("CyberPet" vs "CyberEgg") and burn status to separate them.

### Gen2 Traits (Pre-EIP-24, On-Chain in Description)

Gen2 Citizens were minted before EIP-24 was established. Their traits aren't stored in structured registers or external metadata — they're embedded directly in the token's `description` field as a 721-format JSON string:

```json
{
  "721": {
    "2080": {
      "Cybercitizen": "2080",
      "traits": {
        "Background": "Pink Fever",
        "Skin tone": "Tanned White",
        "Eyebrows": "Brown",
        "Eyes": "Purple",
        "Hair": "Brown buzzcut",
        "Shirt": "Purple T-shirt",
        "Chain": "Golden",
        "Clothes": "Luxury pimp",
        "Gender": "Male"
      }
    }
  }
}
```

This means Gen2 is fully self-contained — the scraper's `enumerate-rest` command captures token ID, citizen number, and complete traits in a single pass. No external file or second API call needed. The same 721-format pattern was later reused for Aneta Angels and CyberEggs, making it the de facto pre-EIP-24 trait standard on Ergo.

Parsing is straightforward: `json.loads(description)` → navigate `["721"][number]["traits"]`. The only wrinkle is that the description is a JSON string stored as a string (escaped quotes), not a nested object.

### Gen3 Traits (External Source, No On-Chain Storage)

Gen3 Citizens do not have traits on-chain at all. The `description` field contains only a generic string ("Generation 3 of creatures living in CyberVerse..."). R8 holds a SHA-256 hash of the image, and R9 holds an IPFS CID pointing to the image folder — but no `.json` metadata files exist alongside the images (confirmed by attempting to fetch `{CID}/2878.json` via IPFS gateways — "no link named" error).

Traits for Gen3 live exclusively in an external JavaScript file hosted by the game site. This file maps citizen number → trait set. To get full Gen3 data, the scraper output (which provides `token_id` → `number` mapping) must be joined with this traits file on the `number`/`id` field.

This is the key difference: Gen2 data is fully recoverable from the blockchain alone. Gen3 depends on an external file that could disappear if the game site goes offline. The traits file should be cached locally as part of any archival effort.

---

## Holder Analysis

The holder analysis script queries the current holder of every token in a collection by checking the unspent box:

```python
def get_token_holder(token_id: str) -> dict:
    url = f"{ERGO_API}/boxes/unspent/byTokenId/{token_id}"
    response = requests.get(url, timeout=60)
    items = response.json().get("items", [])
    if items:
        return {"holder": items[0]["address"], "box_id": items[0]["boxId"]}
    return {"holder": None, "box_id": None}
```

**Checkpoint saves:** For large collections (Gen3 = 5,999 tokens), the script saves a checkpoint every 500 tokens. If the API drops or the script crashes, you resume from the last checkpoint rather than starting over. This was added after losing progress on a Gen2 run that timed out at token 1,800.

**Results:**

| Collection | Tokens | Unique Holders | Avg per Holder |
|------------|--------|----------------|----------------|
| Gen2 | 2,083 | 418 | 5.0 |
| Gen3 | 5,999 | 363 | 16.5 |

Gen3 holder concentration is notable — the top 10 holders control 39.8% of all Gen3 Citizens, with the largest single holder at 370 tokens (6.2%).

---

## Marketplace Data Extraction

### MewMart (Current Ergo Marketplace)

MewMart listings live in smart contract boxes with a known ErgoTree. The approach:

1. Use GraphQL to query all spent boxes matching the MewMart ErgoTree
2. Parse R4 (price in nanoERG) and R5 (seller proposition bytes) from each box
3. Cross-reference token IDs against `cyberverse_ids.json` to identify Cyberverse sales
4. Enrich with USD values using CoinGecko historical price data

**Old vs. New MewMart contract:** MewMart has at least two contract versions with different ErgoTrees. Both must be queried to get complete sales history.

**Token payment discovery:** Some MewMart sales are denominated in tokens (CYPX, USE, RSN) rather than ERG. The script discovers payment tokens dynamically from the box data and queries current prices for conversion.

### SkyHarbor (Shut Down)

SkyHarbor used a different contract pattern — each listing had a unique ErgoTree with the seller's address baked into the contract constants. This means you cannot query all SkyHarbor listings by a single ErgoTree. Instead, query by the factory/proxy contract address (`26tpZU6i...`).

**Sale vs. Withdrawal:** With 50,000+ transactions on the SkyHarbor contract, distinguishing sales from withdrawals (tokens returned to sellers during shutdown) required checking whether the spending transaction sent ERG to the seller address or just returned the NFT.

---

## Cross-Chain Schema Comparison (Ergo vs. Ronin)

Cyberverse exists on both Ergo and Ronin (Gen4 Citizens and Apartments are Ronin-native). Working with both chains exposed fundamental differences in how NFT data is structured and accessed.

### Data Storage Model

| Aspect | Ergo | Ronin (EVM) |
|--------|------|-------------|
| Metadata location | On-chain in box registers (R4-R9) | Off-chain via tokenURI → IPFS/HTTP JSON |
| Property encoding | Custom hex in R6 (length-prefixed key-value) | Standard ERC-721 metadata JSON |
| Trait storage | R5 JSON string or external file | `attributes` array in metadata JSON |
| Token ID format | 64-char hex (= minting box ID) | Sequential uint256 |
| Burn detection | Query `boxes/unspent/byTokenId` → empty = burned | Check `ownerOf()` → reverts or zero address |
| Holder lookup | `boxes/unspent/byTokenId` → box address | `ownerOf(tokenId)` contract call |

### API Access Patterns

| Operation | Ergo | Ronin |
|-----------|------|-------|
| Enumerate collection | Scan mint wallet tx history | Query contract `totalSupply` + `tokenByIndex` |
| Get metadata | Fetch box registers, decode hex | Fetch `tokenURI`, follow to JSON |
| Sales history | GraphQL by ErgoTree (MewMart) or address (SkyHarbor) | Marketplace API (Sky Mavis) with structured endpoints |
| Floor price | No native source, must derive from listings | Sky Mavis API provides floor directly |
| Price denomination | nanoERG (or token ID for non-ERG sales) | RON with USD conversion via API |

### Practical Implications

Ergo's on-chain storage means metadata survives even if external services go down — you can always reconstruct a token's properties from the chain. But the encoding is non-standard and collection-specific (R6 hex for Cars vs. R5 JSON for Eggs vs. external JS file for Gen3 traits).

Ronin follows EVM conventions — standardized metadata JSON, marketplace APIs with pagination and filtering, direct floor/volume endpoints. The tradeoff is dependence on external metadata hosting (IPFS or HTTP) and marketplace uptime.

For the viewer, this means two completely different data pipelines. Ergo data is scraped once and updated manually. Ronin data is fetched daily via GitHub Actions from the Sky Mavis API, with prices already denominated in both RON and USD.

---

## GitHub Actions Automation

Three automated workflows run in the `cyberverse-viewer` repo:

| Workflow | Schedule | Script Location | Output |
|----------|----------|-----------------|--------|
| Floor Tracker | 23:59 UTC daily | `public/data/cyberverse_RON_floor_tracker.py` | `cyberverse_RON_floor_history.json` |
| Price Tracker | 00:05 UTC daily | `public/data/token_price_tracker.py` | `token_price_history.json` |
| MewMart Listings | 06:00 UTC daily | `scripts/update_mewmart_listings.py` | `mew_listings_cyber.json`, `.csv` |

**Workflow pattern (all three follow this):**

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: '3.11'
  - run: pip install requests
  - run: python scripts/the_script.py
  - run: |
      git config --local user.email "github-actions[bot]@users.noreply.github.com"
      git config --local user.name "github-actions[bot]"
      git add public/data/*.json
      git diff --staged --quiet || git commit -m "Update data $(date -u +%Y-%m-%d)"
      git push
```

**Critical setting:** GitHub Actions must have **Read and write permissions** under Settings → Actions → General → Workflow permissions. Without this, the commit step silently fails.

**The `git diff --staged --quiet ||` guard** prevents empty commits when the data hasn't changed (e.g., if the external API returned identical data).

### Ronin Floor Tracker

The floor tracker queries the Sky Mavis Ronin marketplace API for Gen4 Citizens and Apartments (Cyberverse collections on Ronin). It captures floor price, supply count, owner count, and owner distribution (wallets grouped by holding count).

### CoinGecko Price Tracker

Fetches daily ERG and RON prices at midnight UTC. Used to convert historical sale prices to USD and to display price charts on the viewer site. CoinGecko's free API tier was sufficient (no API key required for basic price queries).

---

## Data Freshness & Refresh Strategy

Not all datasets in the toolchain age at the same rate. Understanding what goes stale and when determines which scripts need re-running and which data can be treated as permanent.

### Static Data (Never Changes)

| Dataset | Why It's Static |
|---------|----------------|
| `cyberverse_ids.json` (token ID index) | Token IDs are immutable on-chain. A minted token's ID never changes. |
| Collection metadata (names, descriptions) | Set at mint time in registers, never modified. |
| EIP-24 properties (Cars, Apartments) | Stored in issuer box R6, immutable after minting. |
| Burn status (for completed collections) | Once burned, always burned. Eggs/Pets won't have new mints. |

These files can be generated once and committed to the repo permanently. The only reason to regenerate would be if a new collection launches or a data error is discovered.

### Slow-Changing Data (Monthly Refresh)

| Dataset | Change Driver | Refresh Cadence |
|---------|--------------|-----------------|
| Holder data (`_with_holders.json`) | Trades, transfers, marketplace sales | Monthly or after major sales events |
| Circulating supply (for active collections) | New mints (if any), additional burns | Monthly or on announcement |
| Holder rankings / concentration stats | Derived from holder data | Regenerate after holder refresh |

Holder data is the most expensive to refresh (3+ hours for Gen3). Only worth re-running if you need current whale tracking or concentration analysis. For the viewer's basic "who owns this token" feature, slightly stale data is acceptable.

### Fast-Changing Data (Daily via GitHub Actions)

| Dataset | Workflow | Staleness Threshold |
|---------|----------|-------------------|
| Ronin floor prices | `floor-tracker.yml` | 24 hours |
| ERG/RON token prices | `price-tracker.yml` | 24 hours |
| MewMart active listings | `update-mewmart.yml` | 24 hours |

These are handled by the three GitHub Actions cron jobs. If a workflow fails (API down, rate limit, GitHub outage), the data is stale but the viewer still serves the last-known-good JSON. No crash, just slightly old data.

### Event-Driven Data (Manual Trigger)

| Dataset | Trigger |
|---------|---------|
| MewMart historical sales | New contract version deployed, or periodic backfill |
| SkyHarbor sales | One-time extraction (marketplace shut down) |
| New collection enumeration | Cyberverse announces new collection |

SkyHarbor data is frozen — the marketplace shut down, so the 9,090 confirmed sales are the final dataset. MewMart historical sales should be backfilled periodically (quarterly) to capture new sales that accumulate between the daily listing snapshots.

### Recommended Maintenance Cadence

| Frequency | Action |
|-----------|--------|
| Daily | Automated — floor prices, token prices, active listings |
| Monthly | Re-run holder analysis if needed for analytics |
| Quarterly | Backfill MewMart historical sales, verify burn counts |
| On announcement | Enumerate any new collection, update `cyberverse_ids.json` |

---

## Data Output Structure

### Token ID Index (`cyberverse_ids.json`, ~650KB)

The master lookup file. Contains just token IDs grouped by collection — designed for O(1) membership testing in the frontend:

```javascript
const cvSets = Object.fromEntries(
  Object.entries(cv).filter(([k]) => k !== '_metadata')
    .map(([k, v]) => [k, new Set(v)])
);

function getCollection(tokenId) {
  for (const [name, set] of Object.entries(cvSets)) {
    if (set.has(tokenId)) return name;
  }
  return null;
}
```

### Detailed Collection Files (~29MB total)

Each collection has a full JSON file with token metadata, traits, and properties. Filtered versions (`_filtered.json`) exclude burned and unissued tokens.

### Holder Data

Separate files for Gen2 and Gen3 with `current_holder` field on each token, plus aggregated ranking files in both JSON and CSV format.

---

## Public Scripts

Two scripts are published alongside this document. Together they cover the foundational workflow for enumerating and classifying any Ergo NFT collection.

**`ergo_nft_scraper.py`** — General-purpose Ergo NFT enumeration tool. Given a mint wallet address, scans transaction history to identify all minted tokens using the Ergo minting rule (token ID = first input box ID). Supports both REST API and GraphQL modes, with built-in rate limiting, retry logic, and checkpoint saves every 500 tokens. Outputs a JSON file per collection with token IDs, names, descriptions, and parsed item numbers. Works with any Ergo NFT collection — just supply the mint address.

```
python ergo_nft_scraper.py enumerate <mint_address> <collection_name>
python ergo_nft_scraper.py enumerate <mint_address> <collection_name> --graphql
python ergo_nft_scraper.py fetch-details <collection_name>_rest.json
```

**`ergo_nft_filter.py`** — Token status classifier. Takes the output of the scraper and a mint wallet address, then queries each token's current unspent box to determine whether it is circulating (held by a non-mint wallet), burned (no unspent box exists), or unissued (still in the mint wallet). Outputs separate JSON files for each category.

```
python ergo_nft_filter.py <collection_name>_rest.json <mint_wallet_address>
```

These two scripts are the minimum viable toolkit for anyone working with Ergo NFT collections — without them, you can't do anything meaningful with a collection (holder analysis, trait-based airdrops, rarity scoring, marketplace tracking, etc.).

Additional tooling was built on top of these foundations for property extraction, holder analytics, marketplace data mining, cross-chain tracking, and automated daily updates. The patterns and lessons from that work are documented throughout this reference.

---

## Debugging Checklist

When a script hangs, returns unexpected results, or crashes:

1. **API timeout?** Increase `timeout` parameter to 60-90 seconds. The Ergo API sometimes needs to warm up.
2. **Empty results?** Check if the `offset` has exceeded total items. The API returns an empty `items` array, not an error.
3. **Rate limited?** Increase `time.sleep()` values. The 10-request burst pattern (0.2s between, 1s every 10th) is the tested sweet spot.
4. **Wrong mint address?** Double-check against the registry. CyberPets and CyberEggs share a wallet. Audio spans 5 wallets.
5. **Token appears burned but shouldn't be?** The `boxes/unspent/byTokenId` endpoint might have indexing lag. Retry after 30 seconds.
6. **R6 properties garbled?** The regex decoder catches noise. Check individual token JSONs — per-token output is usually clean even when the summary shows artifacts.
7. **GraphQL validation error?** Use `spentBy { transactionId }` not `spentTransactionId`. Schema varies by endpoint.
8. **GitHub Action didn't commit?** Verify workflow permissions are set to "Read and write" in repo Settings → Actions → General.
9. **High-tx wallet (75k+)?** Use the ergexplorer `byIssuedAddress` endpoint instead of scanning transactions.
10. **PowerShell vs CMD?** `(Get-Item file.json).Length` is PowerShell syntax. Use `dir file.json` in CMD.

---

## Reuse: The Aneta Angels Pattern

The entire enumeration approach was later reused for Aneta Angels (a separate Ergo NFT collection) with minimal adaptation. The key differences were:

- Different mint address
- R9 contains the IPFS URL (not R7 as initially assumed)
- R7 contains 2-byte type flags (`01 01` = image NFT)

**Lesson:** Any Ergo NFT collection can be enumerated with this toolchain if you know the mint address. The pattern is: scan mint wallet → identify mints via token ID = first input box ID → fetch metadata from registers → filter burned/unissued → export JSON. The only variables are which registers hold which data.

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Total tokens indexed | 15,349 |
| Ergo collections | 11 |
| Ronin collections | 2 (Gen4 Citizens, Apartments) |
| Unique mint wallets | 14 |
| Data files generated | ~29MB |
| Lookup index size | 650KB |
| GitHub Actions workflows | 3 (daily cron) |
| MewMart Cyberverse sales tracked | 230 (3,898 ERG / $3,067 USD volume) |
| Gen2 unique holders | 418 |
| Gen3 unique holders | 363 |

---

## Environment

All scripts run on Windows 10 with Python 3.x and a single dependency (`pip install requests`). No virtual environment needed. Output files are JSON with `indent=2` for readability. The `cyberverse-viewer` repo on GitHub hosts the processed data and serves it through Vercel.

The local Ergo indexed node (`http://localhost:9053`) was available but not used for enumeration — the public Explorer API was sufficient for all scraping tasks. The local node could serve as a fallback if the public API became unreliable.
