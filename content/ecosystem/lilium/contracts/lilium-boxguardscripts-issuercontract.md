---
title: LiliumErgo/scala-api — IssuerContract.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/IssuerContract.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/IssuerContract.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: IssuerContract.es

## Purpose

This contract guards an **issuer box** in a multi-stage NFT issuance workflow. It enforces that the issuer box can only be spent to mint an NFT if the NFT's metadata matches a pre-authorized entry stored in an AVL tree maintained by a companion sales/state contract. It acts as a gatekeeper ensuring only approved NFTs (with cryptographically verified metadata) can be created from this issuer's authority.

## Inputs / Outputs

### Inputs
- **SELF**: The issuer box being spent; contains:
  - Registers R4–R9 with issuance parameters (artwork standard, royalties, metadata structure, collection ID, etc.)
  - A native token with ID = SELF.id and quantity 1L (the issuer NFT itself)
  - ERG value to cover the NFT issuance output and miner fee
- **Data Input (CONTEXT.dataInputs(0))**: A sales/state contract box containing:
  - R4: An AVL tree (AvlTree) that maps metadata hashes to authorized NFT definitions
  - Acts as a read-only source of truth; not consumed

### Outputs
- **OUTPUTS(0)**: The minted NFT issuance box, which must:
  - Hold value = SELF.value − _minerFee
  - Be guarded by the buyer's SigmaProp (buyerSigmaProp)
  - Contain the newly minted native token (SELF.id, quantity 1L)
  - Store metadata in registers R4–R9 (name, description, decimals, asset type, media hash, media link)
- **OUTPUTS(1)**: Miner fee box with value = _minerFee

## Key Logic

The contract validates the **entire NFT issuance transaction** through nested boolean checks:

1. **AVL Tree Lookup**:
   - Extracts `buyerSigmaProp` and `index` from SELF.R9
   - Constructs a key by hashing the index (`blake2b256(longToByteArray(index))`)
   - Retrieves the authorized metadata definition from the state contract's AVL tree using the provided `proof` (zero-knowledge proof of membership)

2. **Metadata Verification**:
   - Reconstructs a hash from the output NFT's metadata fields: name (R4), description (R5), asset type (R7), media hash (R8), media link (R9)
   - Compares this reconstructed hash against the AVL tree value to ensure **immutability and authorization**
   - Verifies decimals (R6) = base64("MA==") = 0 (no fractional units)

3. **Token and Value Checks**:
   - Confirms the output NFT box receives exactly one native token with ID = SELF.id (the issuer's singleton token)
   - Ensures value conservation: output NFT value + miner fee = SELF value

4. **Recipient Verification**:
   - The output NFT box must be guarded by `buyerSigmaProp` from SELF.R9, ensuring the authorized buyer receives it

5. **Fee Compliance**:
   - Miner fee output must contain exactly `_minerFee` (a compile-time constant)

All conditions must be satisfied (`sigmaProp(validNFTMintTx)`); the transaction fails if any check fails.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | Int | Artwork Standard Version (self); output R4: UTF-8 bytes of NFT name |
| **R5** | Coll[(Coll[Byte], Int)] | Royalty specification (self); output R5: UTF-8 bytes of NFT description |
| **R6** | Complex struct | Metadata structure (self); output R6: Base64-encoded decimals (must be "0") |
| **R7** | Coll[Byte] | Collection Token ID (self); output R7: UTF-8 bytes of asset type |
| **R8** | Coll[(Coll[Byte], Coll[Byte])] | Additional information (self); output R8: SHA hash of media content |
| **R9** | Coll[(SigmaProp, Long)] | **Buyer SigmaProp and Index** (critical): buyer's signing condition and AVL tree lookup index |

**Note**: The self box's registers store issuance configuration; the output NFT box's registers (R4–R9) store the actual NFT metadata and are validated against the AVL tree.

## Tokens

- **Issuer NFT (Singleton Token)**: 
  - Token ID = SELF.id (the issuer box's box ID)
  - Quantity: 1L per transaction
  - Purpose: Enforces that only this issuer box can authorize NFT minting; transferred to the output NFT box
  - Acts as a **state token** or **singleton** to maintain issuer authority across transactions

## Integration Pattern

The off-chain dApp/bot must construct transactions as follows:

1. **Query the Sales/State Contract**:
   - Fetch the current box holding the AVL tree (CONTEXT.dataInputs(0))
   - Retrieve the AVL tree from R4

2. **Prepare the Issuance Request**:
   - Decide on the NFT metadata: name, description, asset type, media hash, media link
   - Compute the metadata hash: `blake2b256(length_prefixed_concat(name, desc, asset_type, media_hash, media_link))`
   - Query the AVL tree to find if this metadata hash is authorized; if found, extract the index

3. **Generate the AVL Proof**:
   - Use the AVL tree's built-in proof mechanism to generate a compact zero-knowledge proof (`proof`) that the metadata hash exists at the computed key (`blake2b256(longToByteArray(index))`)

4. **Construct the Transaction**:
   - **Input**: The issuer box (SELF) with its current state
   - **Data Input**: The sales/state contract box (read-only)
   - **Context Extension**: Set variable 0 to the AVL proof bytes
   - **Output 0**: