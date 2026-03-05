---
title: BetterMoneyLabs/chaincash — redemption.es
description: "ErgoScript contract analysis: contracts/layer2-old/redemption.es"
tags: [bettermoneylabs, chaincash, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
contract_file: contracts/layer2-old/redemption.es
project: bettermoneylabs-chaincash
---
# ErgoScript Contract Analysis: Redemption Box

## Purpose

This contract manages a **redemption box** in a layer-2 payment system that holds collateral and redemption history data. It allows disputes to be raised against malformed or fraudulent redemption claims, enabling collateral seizure when violations are detected. The contract implements a **multi-stage dispute resolution mechanism** where various claim types (wrong position, tree integrity, signature validation, etc.) can be contested within a 720-block window.

## Inputs / Outputs

### Inputs
- **SELF (Redemption Box):**
  - Token #0: Redemption contract NFT/State token (for singleton identification)
  - Native ERG: Collateral value
  - R4: AVL tree (history of redemption signatures indexed by position)
  - R5: Maximum position in tree (Long)
  - R6: Redemption position being claimed (Long)
  - R7: Contestation state tuple `(maxContestedPosition: Long, contestMode: Boolean)`
  - R8: Deadline (Int, blocks)

### Data Inputs
- **Reserve Box(es)** (referenced via `CONTEXT.dataInputs`):
  - Token #0: Reserve ID (32 bytes) matching reserve identifier
  - R4: Reserve public key `reservePk` (GroupElement for Sigma protocol verification)

### Outputs
- **SELF Output (for action -2 and -3):**
  - Same tokens, value, R4, R5, R6, R8 as input
  - Modified R7: Updated contestation state `(newMaxContestedPosition, newContestMode)`

## Key Logic

### Action -1: Wrong Max Position Claim
Validates that a claimed position exists in the history AVL tree by:
1. Computing the next position: `pos = R5 + 1`
2. **Sigma protocol verification**: Reconstructing the Schnorr signature from off-chain provided `(a, z)` values
   - Challenge: `e = blake2b256(treeHashDigest || reserveId || noteValue || holderId)`
   - Proof check: `g^z == a · reservePk^e` (discrete log equality)
3. **AVL tree proof validation**: Retrieving the leaf at `pos` from R4 and verifying it matches `(aBytes || zBytes)`
4. If both checks pass, collateral can be seized (no preservation required)

### Action -2: Tree Leaf Contestation (Two-Phase)
Implements an **interactive dispute protocol**:

**Phase 1 (contested = false):** Requester asks for a tree leaf
- Increment `maxContestedPosition` in R7
- Set `contestMode = true` in output R7
- All other registers preserved
- Validates that not all leaves have been traversed (`maxContestedPosition < R5`)

**Phase 2 (contested = true):** Responder provides the leaf
- Validates Sigma protocol signature at `currentContestedPosition = maxContestedPosition + 1`
- Proves leaf exists in AVL tree via Merkle proof
- Resets `contestMode = false` in output R7
- Preserves all registers except R7

### Action -3: Earlier Reserve Exists
Proves that an alternative reserve position (created before the redeemed position) exists, preventing collateral seizure. The contract:
1. References two reserve boxes (redeem and alternative reserve)
2. Validates the alternative reserve's tree leaf signature using Sigma protocol
3. Verifies the alternative position is earlier than the redeem position
4. Preserves all input registers if valid

### Action -4: Tree Cut Dispute
*(Partially visible in truncated code)*
Detects when a tree node at position `pos` has been removed or modified.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `AvlTree` | Merkle AVL tree mapping position (Long) → leaf data (a-bytes + z-bytes, 65 bytes) |
| **R5** | `Long` | Current maximum indexed position in the tree |
| **R6** | `Long` | The specific redemption position being claimed |
| **R7** | `(Long, Boolean)` | State machine: `(maxContestedPosition, contestMode)` for dispute tracking |
| **R8** | `Int` | Block deadline for redemption contest period (720 blocks) |

## Tokens

- **Token #0 (Redemption NFT):** 
  - Singleton token identifying this redemption box instance
  - Must be preserved across state transitions
  - Enables deterministic box identification in off-chain indexing

- **Reserve ID Token (in Reserve data input):**
  - 32-byte identifier in reserve box Token #0
  - Cross-referenced in Sigma protocol messages to bind signatures to specific reserves
  - Prevents signature reuse across different reserve pools

## Integration Pattern

### Off-Chain Bot / Off-Chain Validator Must:

1. **For Action -1 (Dispute wrong position):**
   - Extract the claimed position from R5
   - Generate Schnorr signature `(a, z)` for the position's message
   - Compute Fiat-Shamir challenge: `blake2b256(treeHashDigest || reserveId || noteValue || holderId)`
   - Obtain Merkle proof of the AVL tree leaf
   - Construct Context extension with variables 0-8:
     ```
     Var(0) = -1 (action)
     Var(1) = treeHashDigest (32 bytes)
     Var(2) = reserveId (32 bytes)
     Var(3) = noteValue (Long)
     Var(4) = holderId (32 bytes)
     Var(5) = a (GroupElement, encoded)
     Var(7) = zBytes (32 bytes)
     Var(8) = merkleProof (Coll[Byte])
     ```

2. **For Action -2 (Tree leaf contest):**
   - **Request phase:** Increment maxContestedPosition and toggle contestMode
   - **Response phase:** Provide leaf signature and Merkle proof matching the incremented position
   - Build new output box preserving all registers except R7

3. **For Action -3 