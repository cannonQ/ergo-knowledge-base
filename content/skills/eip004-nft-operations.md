---
title: "EIP-004 NFT Operations Guide"
category: skill
difficulty: intermediate
tags: [eip-4, nft, registers, ipfs, tokens]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Skills/tree/main/skills/ergo-eip-004"
updated: 2026-03-09
---

# Ergo EIP-004 NFT Standard

A skill to create and interpret Ergo EIP-004 compliant Non-Fungible Tokens (NFTs), providing asset issuance and data parsing functionalities according to the standard.


# Ergo EIP-004 NFT Standard: Creation and Parsing

## 1. Overview

This document provides a comprehensive guide for an AI agent to interact with the Ergo blockchain according to the EIP-004 asset standard. EIP-004 (Ergo Improvement Proposal #004) specifies a standardized way to issue and represent Non-Fungible Tokens (NFTs), ensuring interoperability across different applications, wallets, and marketplaces within the Ergo ecosystem.

The standard defines a clear structure for both on-chain token data and off-chain metadata. By adhering to this standard, developers can create NFTs that are easily discoverable, displayable, and tradable. This skill encapsulates the logic of the standard, providing two primary functionalities:

1.  **`create_nft`**: Assembles the necessary on-chain registers and off-chain metadata JSON based on user-provided details. This command prepares all data required to mint a new EIP-004 compliant NFT.
2.  **`parse_nft`**: Retrieves and interprets the on-chain and off-chain data for a given EIP-004 NFT, resolving IPFS links to present a complete, validated picture of the asset.

## 2. Architecture

The EIP-004 standard has a two-part architecture: on-chain data stored directly on the Ergo blockchain and off-chain metadata stored externally, typically on the InterPlanetary File System (IPFS).

### 2.1. On-Chain Data Structure

An EIP-004 NFT is a standard Ergo token with a total supply of 1. What makes it an NFT under this standard is the specific data stored in the registers of its issuance box (the box that creates the token).

-   **Issuance**: The token must be issued in the first output (index 0) of the creation transaction.
-   **Amount**: The issuance amount must be exactly 1.
-   **Decimals**: The number of decimals must be 0.

#### Standard Token Registers:
These registers are standard for any Ergo token:

-   `R4` (Coll[Byte]): Token Name (UTF-8 encoded string). E.g., `\"My Ergo NFT\"`.
-   `R5` (Coll[Byte]): Token Description (UTF-8 encoded string). E.g., `\"A unique digital collectible created on the Ergo blockchain.\"`.
-   `R6` (Coll[Byte]): Number of Decimals (encoded as a string). For an NFT, this MUST be `\"0\"`.

#### EIP-004 Specific Registers:
These registers uniquely define the asset as an EIP-004 NFT.

-   `R7` (Coll[Byte]): Intended to contain a link to the off-chain metadata file, typically as a tuple of `(Int, Coll[Byte])` representing `(Link Type, Link Content)`. The recommended format is `(2, \"ipfs://<CID>\")`. However, in practice many NFTs store only a type marker here (e.g., `0101`) rather than a valid IPFS URI. See R7 Content Clarification below for parsing guidance.
-   `R8` (Coll[Byte]): SHA-256 hash of the main artwork file. The content of this register is a `Coll[Byte]` representing the 32-byte hash digest. This provides an on-chain integrity check for the primary media file.
-   `R9` (Coll[Byte]): A tuple of `(Int, Coll[Byte])` representing `(Cover Art Type, Cover Art Link)`. This optional register provides a link to a smaller, optimized image file (like a thumbnail) for faster loading in lists and galleries.

#### Explorer API Register Format

**Important**: The Ergo Explorer API (`/api/v1/boxes/{boxId}`) does NOT return registers as plain hex strings. Registers are returned as objects:

```json
"R9": {
    "serializedValue": "0e42697066733a2f2f...",
    "sigmaType": "Coll[SByte]",
    "renderedValue": "697066733a2f2f..."
}
```

-   `renderedValue` = raw hex bytes (no serialization prefix) — decode this directly with hex-to-UTF8.
-   `serializedValue` = includes `0e` prefix + VLQ length — must strip those first.
-   Always use `renderedValue` when available.

#### Token ID vs Box ID (Two-Step Lookup)

The `tokenId` is NOT the same as the `boxId`. To retrieve the issuance box registers for an NFT:

1.  Fetch `/api/v1/tokens/{tokenId}` — returns `{ "boxId": "..." }`.
2.  Fetch `/api/v1/boxes/{boxId}` — returns `{ "additionalRegisters": { "R4": {...}, "R5": {...}, ... "R9": {...} } }`.

#### R7 Content Clarification

R7 often contains just `0101` (a type indicator), NOT a valid IPFS URI. Many NFTs only store the image link in R9 and leave R7 as a type marker. The recommended parsing order is:

1.  Check R9 first (cover art / direct image link).
2.  Only try R7 as a metadata JSON fallback if R9 is empty.
3.  If R7 decodes to a valid `ipfs://` URI, fetch the JSON and read `media[0].uri`.

#### Image Loading in Browser Context

When loading IPFS images in a web page, do NOT use `loading="lazy"` on images created in memory. Lazy loading uses `IntersectionObserver` — if the `<img>` is not in the DOM, the browser never triggers the load. Always append the image to the DOM first, then set `src`.

### 2.2. Off-Chain Metadata (JSON Structure)

The `R7` register points to an external JSON file containing the detailed metadata for the NFT. This separation keeps the blockchain light while allowing for rich, descriptive content off-chain. The JSON file MUST adhere to the following structure:

```json
{
  \"name\": \"Artwork Name\",
  \"description\": \"Detailed description of the artwork.\",
  \"type\": \"nft:artwork\",
  \"media\": [
    {
      \"uri\": \"ipfs://<MainArtworkCID>\",
      \"sha256\": \"...\",
      \"type\": \"image/jpeg\"
    }
  ],
  \"files\": [
    {
      \"uri\": \"ipfs://<AdditionalFileCID>\",
      \"sha256\": \"...\",
      \"type\": \"application/pdf\"
    }
  ],
  \"attributes\": [
      {
          \"trait_type\": \"Background\",
          \"value\": \"Blue\"
      }
  ]
}
```

**Field-level Descriptions:**

-   `name` (string, optional): The name of the NFT. If omitted, applications should fall back to the on-chain name from register `R4`.
-   `description` (string, optional): A detailed description. If omitted, applications should fall back to the on-chain description from register `R5`.
-   `type` (string, required): The asset type, used for categorization. The common convention is `nft:<category>`, e.g., `nft:artwork`, `nft:collectible`, `nft:ticket`.
-   `media` (array, required): An array of objects representing the core media files of the NFT. At least one entry is required.
    -   `uri` (string, required): The URI of the media file (e.g., `\"ipfs://<CID>\"`). This MUST match the file whose hash is in `R8`.
    -   `sha256` (string, required): The SHA-256 hash of the file, represented as a hex string. This MUST match the hash in `R8`.
    -   `type` (string, required): The IANA MIME type of the file (e.g., `\"image/png\"`, `\"video/mp4\"`).
-   `files` (array, optional): An array of objects for any additional files associated with the NFT (e.g., licenses, 3D models, certificates). This is useful for bundling related documents or media.
-   `attributes` (array, optional): An array of objects representing traits or properties of the NFT, commonly used for rarity calculations in collections.
    -   `trait_type` (string, required): The name of the trait.
    -   `value` (string or number, required): The value of the trait.

### 2.3. IPFS Data Persistence

For an NFT's data to remain available, its content (the JSON file and all associated media files) must be **pinned** on IPFS. Simply adding a file to an IPFS node does not guarantee its persistence. Unpinned content may eventually be garbage collected and become unavailable.

-   **Pinning Services**: To ensure long-term availability, creators should use a pinning service. These services run IPFS nodes and guarantee that specific content remains available. Popular pinning services include Pinata, Infura, Fleek, and Filebase.
-   **Decentralized Pinning**: For maximum resilience, content can be pinned across multiple services or by a community of users, ensuring that the NFT's assets do not have a single point of failure.

## 3. Operations

### 3.1. `create_nft`

This operation prepares the data needed to mint an EIP-004 NFT. It takes high-level inputs (like name, description, and URIs) and constructs the structured on-chain register values and the off-chain JSON metadata.

**Process Flow:**

1.  The agent provides the NFT's name, description, artwork URI, artwork hash, and other metadata.
2.  The skill constructs the EIP-004 JSON object based on these inputs.
3.  It generates a placeholder URI for this JSON object. The user is responsible for uploading the generated JSON content to IPFS to get a real CID.
4.  It formats the values for registers `R4`, `R5`, `R6`, `R7`, and `R8` (and optionally `R9`) into the required hex-encoded format for a transaction.
5.  The output is a complete, structured representation of the data needed to build and submit an Ergo minting transaction.

### 3.2. `parse_nft`

This operation retrieves and interprets the data of an existing EIP-004 NFT.

**Process Flow:**

1.  The agent provides the `token_id` of the NFT.
2.  Fetch `/api/v1/tokens/{tokenId}` to get the `boxId` of the issuance box. The `tokenId` is NOT the `boxId`.
3.  Fetch `/api/v1/boxes/{boxId}` to read the registers (`R4` through `R9`). Registers are returned as objects with `renderedValue`, `serializedValue`, and `sigmaType` — use `renderedValue` for hex-to-UTF8 decoding.
4.  Check R9 first for a cover art / direct image link. If R9 is empty, try R7 as a metadata JSON fallback. Note that R7 often contains just `0101` (a type marker), not a valid IPFS URI.
5.  If a valid `ipfs://` URI is found, resolve it using the specified or default IPFS gateway.
6.  If the URI points to a JSON metadata file, fetch and parse it, then read `media[0].uri` for the artwork link.
7.  Validate the NFT's integrity by comparing the hash in `R8` with the hash of the main media file specified in the JSON (`media[0].sha256`).
8.  Finally, return a consolidated view of the NFT, combining on-chain and off-chain data.

## 4. Building the Minting Transaction

The `create_nft` command provides all the necessary data, but it does not perform the final step of building and submitting the transaction to the blockchain. This separation of concerns ensures that the skill remains stateless and does not require access to private keys.

A developer would take the output from `create_nft` and use an Ergo library like `ergo-lib-wasm` (for JavaScript/TypeScript) or `ergo-appkit` (for JVM languages) to complete the process:

1.  **Select Inputs**: Choose unspent transaction outputs (UTXOs) from a wallet that contain enough ERG to cover transaction fees and any required box value.
2.  **Construct Issuance Box**: Create a new output box for the transaction at index 0.
    -   Set its value (e.g., the minimum of 0.001 ERG).
    -   In its `mintToken` field, use the `token_details` object from the skill's output (`name`, `description`, `amount`, `decimals`).
    -   Populate the registers `R4`, `R5`, `R6`, `R7`, `R8` using the hex-encoded strings from the `required_registers` object in the skill's output.
3.  **Construct Change Box**: Create one or more change outputs to return the remaining ERG and any other tokens to the user's address.
4.  **Sign Transaction**: Sign the assembled, unsigned transaction using the wallet's private keys.
5.  **Submit Transaction**: Submit the signed transaction to an Ergo node.

## 5. Authentication and Security

-   **Blockchain Interaction**: This skill simulates the data preparation and parsing. Actual interaction with the Ergo blockchain requires an external component like a wallet or a service connected to a node. No private keys or authentication tokens are handled by this skill.
-   **IPFS Gateway**: The skill uses a public, user-configurable IPFS gateway. The default is `https://ipfs.io/ipfs/`. There is no authentication required for reading data from a public gateway.
-   **Security Considerations**:
    -   **Data Integrity**: The use of on-chain hashes (`R8`) is critical. The `parse_nft` function verifies that the hash of the main artwork declared in the off-chain JSON matches the hash stored on-chain. This prevents the off-chain metadata from being tampered with or pointing to a different file.
    -   **Input Sanitization**: When parsing data, especially from off-chain sources like IPFS, all inputs must be treated as untrusted. URIs should be validated, and content should be checked for malicious scripts if it is ever to be rendered in a web context.
    -   **Issuer Verification**: The authenticity of an NFT can be partially verified by checking the address that minted it. Provenance is key in the NFT space.

## 6. Error Handling

The `parse_nft` operation can encounter several errors, returned as a structured error object:

-   `TokenNotFound`: The provided `token_id` does not exist on the Ergo blockchain.
-   `NotAnNFT`: The token exists but has a supply greater than 1, so it cannot be an NFT.
-   `NotEIP004Compliant`: The token is an NFT but does not have the required EIP-004 registers (`R7`, `R8`) set correctly.
-   `InvalidMetadataURI`: The `R7` register does not contain a valid `ipfs://` URI.
-   `IPFSFetchFailed`: The skill could not retrieve the JSON file from the IPFS gateway (e.g., network error, invalid CID, gateway timeout).
-   `InvalidJSON`: The content fetched from IPFS is not valid JSON.
-   `HashMismatch`: The SHA-256 hash in the on-chain `R8` register does not match the `sha256` field of the main media file in the off-chain JSON, indicating potential tampering.

## 7. Constraints and Edge Cases

-   **Rate Limiting**: Calls to underlying Ergo nodes or public IPFS gateways are subject to their respective rate limits. This skill does not implement its own rate limiting but relies on the user to manage their usage of the configured endpoints.
-   **Payload Size**: The off-chain JSON metadata should be kept reasonably small (e.g., under 1MB) to ensure quick fetching from IPFS.
-   **Default Gateway**: The default IPFS gateway is `https://ipfs.io/ipfs/`. This may be rate-limited or slow. For production use, a dedicated or premium gateway is recommended.
-   **Mutable Links**: While IPFS links are immutable, it is technically possible to point `R7` to a traditional, mutable URL (`http://`). EIP-004 strongly discourages this, as the metadata can be changed, undermining the immutability of the NFT. This skill primarily focuses on the `ipfs://` standard.


## Input Schema

```json
{
  "required": [
    "command"
  ],
  "properties": {},
  "type": "object"
}
```

## Output Schema

```json
{
  "properties": {},
  "type": "object"
}
```

## Examples

### Happy path example demonstrating how to parse a valid EIP-004 NFT.

**Input:**
```json
{}
```

**Output:**
```json
{}
```

**Code Example:**
```
This is a conceptual tool. Below is a Python script showing how one might implement the parsing logic described.

```python
import requests
import json

def parse_ergo_nft(token_id: str, explorer_api: str = 'https://api.ergoplatform.com', ipfs_gateway: str = 'https://ipfs.io/ipfs/'):
    # Step 1: Get the boxId from the tokenId (two-step lookup)
    # token_resp = requests.get(f'{explorer_api}/api/v1/tokens/{token_id}')
    # box_id = token_resp.json()['boxId']
    # box_resp = requests.get(f'{explorer_api}/api/v1/boxes/{box_id}')
    # issuance_box = box_resp.json()

    # Mock response showing the ACTUAL Explorer API register format (objects, not hex strings)
    mock_issuance_box = {
        'boxId': 'f9e5ce5aa0d95f5d54a7bc89c46730d9a623271d7b42571b5ef1fd5f5e55b1b4',
        'value': 1000000,
        'assets': [{'tokenId': '0be1a7337a242c3886565106e8b4e7ce59b4ae6b334a6f7b31d1679469553fbe'}],
        'additionalRegisters': {
            'R4': {
                'serializedValue': '0e0b4d79204572676f204e4654',
                'sigmaType': 'Coll[SByte]',
                'renderedValue': '4d79204572676f204e4654'  # 'My Ergo NFT' in hex
            },
            'R5': {
                'serializedValue': '0e1d4120756e69717565206469676974616c20636f6c6c65637469626c652e',
                'sigmaType': 'Coll[SByte]',
                'renderedValue': '4120756e69717565206469676974616c20636f6c6c65637469626c652e'
            },
            'R6': {
                'serializedValue': '0e0130',
                'sigmaType': 'Coll[SByte]',
                'renderedValue': '30'  # '0' in hex
            },
            'R7': {
                'serializedValue': '0e020101',
                'sigmaType': 'Coll[SByte]',
                'renderedValue': '0101'  # Type marker, NOT an IPFS URI
            },
            'R8': {
                'serializedValue': '0e20e557176a3d9326f55561a380963d30b62e4c849767f40555c110906a25b17da2',
                'sigmaType': 'Coll[SByte]',
                'renderedValue': 'e557176a3d9326f55561a380963d30b62e4c849767f40555c110906a25b17da2'
            },
            'R9': {
                'serializedValue': '0e42697066733a2f2f516d5a576a4e396e504a746f7938384b63574c44706859346642...',
                'sigmaType': 'Coll[SByte]',
                'renderedValue': '697066733a2f2f516d5a576a4e396e504a746f7938384b63574c44706859346642...'
            }
        }
    }

    # Step 2: Parse on-chain data using renderedValue (raw hex, no serialization prefix)
    regs = mock_issuance_box['additionalRegisters']
    on_chain_name = bytes.fromhex(regs['R4']['renderedValue']).decode('utf-8')
    on_chain_hash_hex = regs['R8']['renderedValue']

    # Step 3: Check R9 first for cover art / direct image link, then fall back to R7
    # R7 often contains just '0101' (type marker), not a valid IPFS URI
    artwork_uri = None
    if 'R9' in regs:
        r9_decoded = bytes.fromhex(regs['R9']['renderedValue']).decode('utf-8', errors='replace')
        if r9_decoded.startswith('ipfs://'):
            artwork_uri = r9_decoded
    if not artwork_uri and 'R7' in regs:
        r7_decoded = bytes.fromhex(regs['R7']['renderedValue']).decode('utf-8', errors='replace')
        if r7_decoded.startswith('ipfs://'):
            # R7 points to metadata JSON — fetch and read media[0].uri
            metadata_url = f'{ipfs_gateway}{r7_decoded[7:]}'  # strip 'ipfs://'

    # Step 4: If we have a direct image URI from R9, use it directly
    if artwork_uri:
        return {
            'success': True,
            'token_id': token_id,
            'name': on_chain_name,
            'artwork_uri': artwork_uri,
            'artwork_hash': on_chain_hash_hex,
            'source': 'R9 (direct image link)'
        }

    # Step 5: If R7 had a metadata JSON link, fetch and parse it
    try:
        response = requests.get(metadata_url, timeout=10)
        response.raise_for_status()
        metadata = response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        return {'success': False, 'error': f'Failed to fetch or parse metadata: {e}'}

    # Step 6: Validate hash integrity
    off_chain_hash = metadata.get('media', [{}])[0].get('sha256')
    if on_chain_hash_hex != off_chain_hash:
        return {'success': False, 'error': 'Hash mismatch between on-chain R8 and off-chain metadata'}

    # Step 7: Return consolidated data
    return {
        'success': True,
        'token_id': token_id,
        'name': metadata.get('name', on_chain_name),
        'description': metadata.get('description'),
        'artwork_uri': metadata['media'][0]['uri'],
        'artwork_hash': off_chain_hash,
        'artwork_type': metadata['media'][0]['type'],
        'additional_files': metadata.get('files', []),
        'source': 'R7 (metadata JSON)'
    }

# --- Example Usage ---
nft_data = parse_ergo_nft(
    token_id='0be1a7337a242c3886565106e8b4e7ce59b4ae6b334a6f7b31d1679469553fbe',
    explorer_api='https://api.ergoplatform.com'
)
print(json.dumps(nft_data, indent=2))
```
```

### Example of creating the data structures for a new EIP-004 NFT.

**Input:**
```json
{}
```

**Output:**
```json
{}
```

**Code Example:**
```
This is a conceptual tool. Below is a Python script showing how one might implement the creation logic.

```python
import json
import hashlib

def create_nft_data(name: str, description: str, artwork_path: str, artwork_mime: str):
    # Step 1: Hash the artwork file
    hasher = hashlib.sha256()
    # In a real scenario, you would read the file content
    # For this example, we'll hash a placeholder string
    mock_file_content = b'This is the content of my beautiful artwork!'
    hasher.update(mock_file_content)
    artwork_hash = hasher.hexdigest()

    # Step 2: Define the off-chain JSON metadata
    # The URI and CID are hypothetical until the content is actually added to IPFS.
    hypothetical_artwork_cid = 'Qm...artwork'
    metadata = {
        'name': name,
        'description': description,
        'type': 'nft:artwork',
        'media': [{
            'uri': f'ipfs://{hypothetical_artwork_cid}',
            'sha256': artwork_hash,
            'type': artwork_mime
        }],
        'files': []
    }

    # Step 3: Create the metadata JSON string
    metadata_json_str = json.dumps(metadata, separators=(',', ':'))
    # In a real scenario, this JSON content would be added to IPFS to get a real CID.
    hypothetical_metadata_cid = 'Qm...metadata'

    # Step 4: Prepare the on-chain register values (in hex format for Ergo)
    registers = {
        'R4': name.encode('utf-8').hex(),
        'R5': description.encode('utf-8').hex(),
        'R6': '0'.encode('utf-8').hex(),
        # The construction of the serialized Coll below is simplified
        'R7': ('(2, "ipfs://' + hypothetical_metadata_cid + '")').encode('utf-8').hex(),
        'R8': artwork_hash,
        'R9': None # Optional, not included in this example
    }

    # Step 5: Consolidate the output
    # This output would then be used to construct a transaction in a wallet.
    return {
        'success': True,
        'eip4_json_content': metadata,
        'eip4_json_uri_placeholder': f'ipfs://{hypothetical_metadata_cid}',
        'required_registers': registers,
        'token_details': {
            'name': name,
            'description': description,
            'amount': 1,
            'decimals': 0
        }
    }

# --- Example Usage ---
nft_creation_data = create_nft_data(
    name='My First AI NFT',
    description='An artwork about the dawn of artificial general intelligence.',
    artwork_path='/path/to/my/artwork.png',
    artwork_mime='image/png'
)
print(json.dumps(nft_creation_data, indent=2))
```
```

### Error case where an agent attempts to parse a token ID that does not conform to the EIP-004 standard (e.g., missing R7 register).

**Input:**
```json
{}
```

**Output:**
```json
{}
```

**Code Example:**
```
This is a conceptual tool. The Python script below simulates discovering that a token is not EIP-004 compliant.

```python
import json

def check_eip4_compliance(token_id: str):
    # Simulate fetching a box for a token that is NOT an EIP-004 NFT
    mock_non_eip4_box = {
        'boxId': 'a1b2c3d4...',
        'assets': [{'tokenId': token_id}],
        'additionalRegisters': {
            'R4': '4d7920546f6b656e', # 'My Token'
            'R5': '4a20726567756c617220746f6b656e', # 'A regular token'
            'R6': '32' # '2' decimals
            # R7, R8, and R9 are missing
        }
    }

    registers = mock_non_eip4_box.get('additionalRegisters', {})
    
    if 'R7' not in registers or 'R8' not in registers:
        return {
            'success': False,
            'token_id': token_id,
            'error': 'NotEIP004Compliant',
            'message': 'The token is missing the required R7 (metadata link) or R8 (artwork hash) registers.'
        }
    
    # This part would not be reached
    return {'success': True}

# --- Example Usage ---
result = check_eip4_compliance(token_id='abc...123')
print(json.dumps(result, indent=2))
```
```

## Permissions

- `ergo_blockchain:read:box:*`
- `ergo_blockchain:write:transaction:minting`
- `ipfs:read:object:*`

## Constraints

- Max payload size for IPFS JSON: 1MB
- Default IPFS Gateway: https://ipfs.io/ipfs/
- SHA256 hashes must be 64 hexadecimal characters.
- Token name length limit: 128 characters
- Token description length limit: 512 characters
- Ergo register size limit: each of R4-R9 cannot exceed 64KB.
