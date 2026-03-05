---
title: rosen-bridge/contract — Lock.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/Lock.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/Lock.es
project: rosen-bridge-contract
---
# ErgoScript Contract Analysis: Lock.es

## Purpose

This contract implements a **multi-signature guard mechanism** for the Rosen Bridge, requiring a configurable threshold of signatures from authorized signers before funds can be unlocked. It validates that a Guard Box (referenced as a data input) holds the required Guard NFT and enforces an m-of-n signature scheme where m is dynamically read from the Guard Box state.

## Inputs / Outputs

### Inputs
- **Spending Input**: The box being protected by this contract (contains the actual value/tokens to be guarded)
- **Data Input (CONTEXT.dataInputs(0))**: The **Guard Box** — a reference-only input containing:
  - Guard NFT token (authentication credential)
  - R4: Collection of encoded public key points (Coll[Coll[Byte]])
  - R5: Signature threshold configuration (Coll[Int], where index 0 holds the required signature count)

### Outputs
- None specified in this contract; outputs are determined by the transaction that satisfies the guard condition

## Key Logic

The contract enforces the following validation chain:

1. **Guard NFT Verification** (`verifyGuard`):
   - Scans all tokens in the Guard Box
   - Confirms at least one token matches the hardcoded `GuardNFT` identifier
   - Ensures the data input is authentically the designated guard state box

2. **Threshold Signature Validation** (`atLeast(...)`):
   - Extracts `paymentSignCount` from Guard Box R5[0]
   - Decodes the public key points stored in Guard Box R4 using `decodePoint()`
   - Converts each decoded point into a Sigma protocol proof via `proveDlog()`
   - Validates that **at least `paymentSignCount` of these proofs are satisfied** in the transaction context

3. **Final Assertion**:
   - Both conditions must be true (AND logic via `allOf`)
   - Returns a `sigmaProp` that binds the spending to Sigma protocol verification

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Coll[Byte]]` | Encoded ECDSA/Schnorr public key points for authorized signers |
| **R5** | `Coll[Int]` | Configuration array; R5[0] stores the minimum signature count (threshold m) |

Both registers are read-only in this contract; they reside in the Guard Box (data input), not the spending box.

## Tokens

- **Guard NFT** (`GuardNFT`):
  - Hardcoded as a Base64-encoded token ID constant
  - Serves as the **singleton/state NFT** proving the data input is the authoritative Guard Box
  - Required to prevent substitution attacks (ensures the correct guard state is being referenced)
  - Enables a **state machine pattern** where the Guard Box can be updated in separate transactions while maintaining identity

## Integration Pattern

### Off-Chain Bot / Headless dApp Workflow

1. **Query Guard State**:
   - Off-chain indexer fetches the current Guard Box (identified by Guard NFT)
   - Reads R4 (signer list) and R5[0] (threshold)

2. **Construct Spending Transaction**:
   - Dapp creates a transaction that:
     - Includes the Lock-protected box as a spending input
     - Includes the Guard Box as a **data input** (read-only reference)
     - Collects m-of-n signatures from authorized signers

3. **Signature Collection**:
   - Off-chain code solicits `paymentSignCount` signatures from the public key holders listed in R4
   - Each signature must correspond to a `proveDlog` proof that can be satisfied in the transaction context

4. **Proof Generation**:
   - Ergo wallet/signer generates Sigma protocol commitments and responses
   - Transaction is submitted with valid proof bytes in the proof context

5. **Validation**:
   - Node verifies `atLeast(m, signedColl)` — ensuring m Sigma proofs are valid
   - Node verifies Guard NFT presence in the referenced data input

## Related Contracts

Based on naming conventions, this contract likely composes with:

- **Guard.es** — Likely manages the Guard Box state (R4/R5 updates, signer set changes, threshold reconfigurations)
- **Bridge contracts** (not shown) — Spending inputs using this lock contract protect cross-chain value transfers
- **Auction / Slashing contracts** — May depend on multi-sig guard for sensitive state transitions in the Rosen Bridge protocol

The Guard Box state machine pattern suggests a **multi-stage contract** architecture where:
1. Lock.es enforces signature thresholds
2. Guard.es evolves the guard state (signer rotation, threshold adjustment)
3. Bridge logic contracts orchestrate the atomic swap / value transfer once guards validate

---

**Key Ergo Concepts Used**:
- **eUTXO model**: Data input pattern for non-consuming state reference
- **Native tokens**: NFT as proof of box identity
- **Sigma protocols**: Multi-signature via `proveDlog` and `atLeast`
- **State machine**: Guard Box evolves independently, Lock enforces current state
- **Context extension**: Signature proofs supplied via transaction proof context