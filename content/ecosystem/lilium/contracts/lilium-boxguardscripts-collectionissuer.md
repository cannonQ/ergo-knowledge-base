---
title: LiliumErgo/scala-api — CollectionIssuer.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/CollectionIssuer.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/CollectionIssuer.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: CollectionIssuer

## Purpose

The **Collection Issuer** contract guards a singleton box that mints and issues collection tokens (NFTs). It enforces that when the issuer box is spent, the correct amount of collection tokens is minted in the output, and the issuer box's logic is preserved in a subsequent state box. This contract is part of a multi-stage contract system for managing NFT collections.

---

## Inputs / Outputs

### Inputs
- **SELF**: The Collection Issuer box itself, containing:
  - Collection metadata in Registers R4–R8
  - The target token amount to mint in Register R9
  - Exact NFT identification (SELF.id)

### Outputs
- **OUTPUTS(0)**: A new Collection Issuer box (state continuation) that:
  - Contains the first newly minted token(s) with ID equal to SELF.id and quantity from R9
  - Is guarded by the same contract script (recovered from context extension variable `collectionIssuanceContractBytes`)
  - Preserves the issuer's metadata and control logic

---

## Key Logic

The contract validates two critical invariants before allowing the transaction:

1. **Token Minting Invariant** (`nftBox`):  
   Verifies that exactly one token with ID matching `SELF.id` and quantity matching `SELF.R9[Long]` is present in the first output. This ensures the correct amount of collection tokens is minted—no more, no less.

2. **State Continuity Invariant** (`properOutput`):  
   Confirms that the first output box is protected by an identical contract script. This ensures the issuer logic is preserved across transactions, maintaining the singleton's authority.

3. **Authorization** (`_txOperatorPK`):  
   The transaction must be signed by the compile-time operator key, providing exclusive control over when collection tokens are minted.

All three conditions must be satisfied via an AND conjunction and Sigma protocol proof aggregation.

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Int` | Collection Standard Version (metadata format identifier) |
| **R5** | `Coll[Coll[Byte]]` | Collection Info (e.g., name, description, media URIs) |
| **R6** | `Coll[(Coll[Byte], Coll[Byte])]` | Collection Socials (key-value pairs: website, Discord, Twitter, etc.) |
| **R7** | `Long` | Minting Expiry Timestamp (milliseconds; defines cutoff for token issuance) |
| **R8** | `Coll[(Coll[Byte], Coll[Byte])]` | Additional Information (extensible metadata as key-value pairs) |
| **R9** | `Long` | **Amount of Collection Tokens to Mint** (core issuance quantity) |

---

## Tokens

- **Collection Token (NFT)**:
  - **Token ID**: Equals `SELF.id` (the box's ID itself, creating a 1:1 link)
  - **Quantity**: Specified in R9 (typically 1 for an NFT, or > 1 for a fungible collection asset)
  - **Role**: Serves as a Singleton / State NFT, uniquely identifying the collection and preventing unauthorized issuance
  - **Authentication**: The token's presence in OUTPUTS(0) with correct ID and amount is the primary state machine invariant

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Box Retrieval**:
   - Locate the Collection Issuer box (UTXO) by its contract script hash or token ID filter

2. **Transaction Construction**:
   - Create a transaction with SELF as input
   - Construct OUTPUTS(0) with:
     - The minted token tuple `(SELF.id, R9[Long].get)` in the tokens list
     - A box value meeting **Minimum box value** requirements
     - The same ErgoScript contract guarding it (via context extension variable)
   - Include appropriate **Minimum transaction fee**

3. **Context Extension Assembly**:
   - Populate **Context extension** variable at index `0` with `collectionIssuanceContractBytes`—the serialized ErgoScript contract protecting the issuer
   - This allows the contract to re-enforce itself without embedding large scripts inline

4. **Signing**:
   - Provide a **Sigma protocol** proof via the operator's private key (corresponding to `_txOperatorPK`)

5. **Validation**:
   - Verify off-chain that:
     - R9 contains a positive `Long` for the minting amount
     - R7 (expiry) has not passed (optional business logic; not enforced on-chain here)
     - The output box value covers the **Storage rent** for future transactions

---

## Related Contracts

Based on the Lilium collection framework structure:

- **Parent/Coordinator**: Likely a **Collection Manager** or **Collection Factory** contract that:
  - Instantiates Collection Issuer boxes
  - May validate metadata consistency across the issuer ecosystem
  - Could enforce global collection constraints (e.g., max supply, royalties)

- **Peer Contracts** (inferred):
  - **NFT Holder / Marketplace Contracts**: Accept and validate tokens minted by this issuer
  - **Royalty / Payment Contracts**: May receive a portion of proceeds tied to collection tokens

- **State Machine Chain**:
  - This contract is typically part of a **Multi-stage contract** pipeline where:
    - Stage 1 (this contract): Issues the collection token
    - Stage 2+: Token utility contracts (trading, staking, burning, etc.)

---

## Notes & Security Considerations

- **No Expiry Enforcement**: The R7 timestamp is metadata but not checked on-chain; expiry logic must be enforced off-chain or in a parent contract.
- **No Supply Cap**: The contract does not validate R9 against a maximum; this is assumed to be enforced at creation or via parent contracts.
- **Context Extension Dependency**: The contract's re-protection depends on correct serialization of the ErgoScript in the context extension; any mismatch breaks the state machine.
- **Single Output