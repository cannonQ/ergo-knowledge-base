---
title: rosen-bridge/contract — Permit.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/Permit.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/Permit.es
project: rosen-bridge-contract
---
# ErgoScript Contract Analysis: Permit.es

## Purpose

The **Permit** contract is a state machine component in the Rosen Bridge that manages permit tokens (X-RWT) for controlling bridge operations. It orchestrates two distinct transaction flows: (1) returning permits after RWT transfers between a repository and collateral, and (2) consuming permits to create event commitments that trigger cross-chain bridge operations.

## Inputs / Outputs

### Inputs

**Returning Permit Flow:**
- `INPUTS(0)`: RWT Repository box (holds X-RWT tokens and Singleton NFT `RWTRepoNFT`)
- `INPUTS(1)`: Collateral box
- `INPUTS(2)`: Current Permit box (`SELF`)
- `INPUTS(3)`: WID box (Singleton NFT token with quantity ≥ 2)

**Event Commitment Creation Flow:**
- `INPUTS(0..n)`: One or more Permit boxes (same script, same token ID, aggregated RWT quantity)
- `INPUTS(?)`: WID box (Singleton NFT token)

### Outputs

**Returning Permit Flow:**
- `OUTPUTS(0)`: Updated RWT Repository box
- `OUTPUTS(1)`: Updated Collateral box
- `OUTPUTS(2)`: Optional new Permit box (if RWT remains unspent) or user change
- `OUTPUTS(3..n)`: Updated WID box and other outputs

**Event Commitment Creation Flow:**
- `OUTPUTS(0)`: Remaining Permit box (same script, reduced RWT quantity)
- `OUTPUTS(1)`: New Commitment box (validated script hash, with event data in R5–R7)
- `OUTPUTS(2)`: Updated WID box (Singleton NFT token)

## Key Logic

### Branch 1: Returning Permits (RWT Withdrawal)

The contract validates that when the RWT Repository box (`OUTPUTS(0)`) is present in outputs:

1. **RWT Balance Reconciliation**: The amount of RWT transferred *out* of the repository (`transferedRwt = OUTPUTS(0).tokens(1)._2 - INPUTS(0).tokens(1)._2`) must match the total permits being consumed.

2. **Permit Accounting**: 
   - All input Permit boxes holding the same token ID are aggregated (`inputPermitsRwt`).
   - If an output Permit exists (`OUTPUTS(2)`), its RWT quantity must equal unspent permits: `inputPermitsRwt - transferedRwt`.
   - If no output Permit, all permits must have been consumed: `inputPermitsRwt == transferedRwt`.

3. **Permit Integrity**: Any output Permit must:
   - Retain the same script hash as the input Permit (`SELF.propositionBytes`)
   - Preserve the WID value in R4

4. **WID Validation**: The WID Singleton NFT must have quantity ≥ 2, confirming multi-signature or threshold requirement satisfaction.

### Branch 2: Event Commitment Creation

When the RWT Repository box is *not* in outputs, the contract validates commitment creation:

1. **Permit Consumption**: 
   - Output Permit (`OUTPUTS(0)`) must hold the same token ID as input permits.
   - Output Commitment (`OUTPUTS(1)`) must receive the *difference*: `inputPermitsRwt - OUTPUTS(0).tokens(0)._2`.

2. **Commitment Box Requirements**:
   - Script hash must match `commitmentScriptHash` (blake2b256 hash of Commitment script)
   - R4 must contain the WID
   - R5 and R6 must be defined (event data: cross-chain parameters)
   - R7 must contain `blake2b256(SELF.propositionBytes)` — linking back to this Permit script for traceability

3. **State Continuity**:
   - Output Permit retains the same script and WID in R4
   - WID Singleton NFT appears in `OUTPUTS(2)`

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **Withdrawal ID (WID)**: Unique identifier linking permits to a specific bridge operation or user request. Preserved across state transitions. |
| **R5** | `Coll[Byte]` | **Event/Commitment Data (Commitment only)**: Cross-chain event parameters (e.g., target chain, recipient address, token details). Required but not validated by this contract. |
| **R6** | `Coll[Byte]` | **Signature/Proof (Commitment only)**: Cryptographic material or event proof. Required but not validated by this contract. |
| **R7** | `Coll[Byte]` | **Permit Script Hash (Commitment only)**: blake2b256 hash of the originating Permit script, creating an immutable audit trail. |

## Tokens

### Primary Token: X-RWT (Permit Token)

- **Token ID**: Retrieved dynamically from `SELF.tokens(0)._1`
- **Quantity**: Tracked across all input/output Permits; represents "permit units" or "authorization weight"
- **Purpose**: Acts as a fungible authorization token — each unit grants the right to trigger one cross-chain bridge operation (or proportional portion thereof)

### Secondary Token: RWTRepoNFT (Singleton)

- **Token ID**: Hardcoded constant `fromBase64("RWT_REPO_NFT")`
- **Quantity**: Immutable (singleton)
- **Purpose**: Identifies the RWT Repository box; prevents spoofing via script hash collision

### Tertiary Token: WID (Withdrawal ID, Singleton)

- **Token ID**: Stored in R4; dynamically identified
- **Quantity**: Must be ≥ 2 in "Returning Permit" flow; ≥ 1 in "Event Commitment Creation" flow
- **Purpose**: Singleton Nonce/State NFT linking all boxes in a single bridge withdrawal transaction; enforces atomic state transitions

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **For Returning Permits Flow**:
   - Monitor pending withdrawal requests