---
title: rosen-bridge/contract — EventTrigger.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/EventTrigger.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/EventTrigger.es
project: rosen-bridge-contract
---
# EventTrigger Contract Analysis

## Purpose

The **EventTrigger** contract serves as a state machine box that orchestrates cross-chain event bridging on Ergo. It validates that incoming events (from an off-chain oracle/watcher) are either forwarded to a Permit contract for legitimate payment distribution, or diverted to a Fraud contract if consensus fraud is detected. This contract is central to the Rosen Bridge's event-driven architecture.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: `EventTrigger` box itself (SELF) — contains the event data and commitment metadata
- **INPUTS(1)** *(optional, conditional)*: **CleanupToken** box — only present in fraud scenarios; must hold the Cleanup NFT
- **Data Input**: **GuardNFTBox** — referenced as a read-only input to verify guard lock existence (not consumed)
- Additional **Commitment** boxes *(optional)*: May be provided as inputs but are not directly validated by this script

### Outputs
- **OUTPUTS(0)**: Either:
  - **Fraud box** (ErgoTree hash matches `FraudScriptHash`) — triggered if fraud is detected
  - **Permit box** (ErgoTree hash matches `SELF.R6`) — normal payment path for reward distribution
- **OUTPUTS(1..commitmentCount)**: **Reward boxes** — one per commitment; each must:
  - Have the same proposition bytes as OUTPUTS(0)
  - Hold RWT tokens split equally: `RWT_quantity / commitmentCount`
  - Carry a WID (Witness ID) in R4
- **Final outputs**: Change boxes and other protocol outputs

---

## Key Logic

The contract enforces a **two-branch state machine**:

### Branch 1: Fraud Detection Path
```
IF blake2b256(OUTPUTS(0).propositionBytes) == FraudScriptHash THEN
  ✓ INPUTS(1) MUST contain Cleanup NFT token
  ✓ Cleanup confirmation delay MUST have elapsed:
    HEIGHT - CLEANUP_CONFIRMATION >= SELF.creationInfo._1
```
When fraud is detected (externally by off-chain consensus), the EventTrigger directs RWT tokens to the Fraud contract instead of Permit.

### Branch 2: Normal Payment Path
```
IF blake2b256(OUTPUTS(0).propositionBytes) == SELF.R6[Coll[Byte]] THEN
  ✓ A GuardLock box MUST exist in INPUTS (verified by blake2b256 hash)
  ✓ OUTPUTS(0) proposition must match R6 digest (Permit contract script)
```
Normal operation: event data flows to Permit contract for legitimate reward distribution.

### Commitment Validation (Both Branches)
Regardless of path taken, the contract **always validates** that:

1. **Commitment Count Matches**:
   - `rewards.size == commitmentCount` (exactly R7 outputs with RWT tokens)

2. **WID Digest Integrity**:
   - Collects all R4 values (WIDs) from reward boxes
   - Concatenates them: `WIDs.fold(Coll[Byte](), (a, b) => a ++ b)`
   - Verifies blake2b256 hash equals `SELF.R4` (immutable event fingerprint)
   - **Purpose**: Prevents tampering with witness identities

3. **Equal RWT Distribution**:
   - Each reward box receives exactly `RWT_total / commitmentCount` tokens
   - All reward boxes share identical proposition bytes (same Permit/Fraud contract)
   - **Purpose**: Ensures deterministic, tamper-proof reward splits

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **WID List Digest** — blake2b256 hash of concatenated witness IDs; serves as event fingerprint for integrity verification |
| **R5** | `Coll[Coll[Byte]]` | **Event Data** — the cross-chain event payload (e.g., lock proof, transaction details); passed to Permit contract |
| **R6** | `Coll[Byte]` | **Permit Contract Script Digest** — blake2b256 hash of the Permit contract's ErgoTree; allows this EventTrigger to reference Permit polymorphically |
| **R7** | `Int` | **Commitment Count** — number of independent oracles/witnesses that signed this event; determines RWT distribution splits and output count |

All registers are **read-only** in this script; they encode the event's immutable state.

---

## Tokens

### RWT (Reward Token)
- **Role**: Native token used for oracle/witness compensation
- **Location in Box**: `SELF.tokens(0)` (first token in EventTrigger box)
- **Quantity Rule**: 
  - Total RWT held by EventTrigger is split equally across `commitmentCount` reward boxes
  - Each reward box receives: `SELF.tokens(0)._2 / commitmentCount` units
- **Authentication**: Presence of RWT token in reward outputs proves this is a legitimate event-triggered transaction (guards against unauthorized spending)

### Cleanup NFT
- **Role**: Singleton NFT that unlocks fraud resolution
- **Location in Box**: `INPUTS(1).tokens(0)` (first token in second input, fraud path only)
- **Purpose**: Authorizes the transition to Fraud contract; prevents accidental fraud declarations
- **Constraint**: Only consumed together with sufficient time delay (HEIGHT check)

---

## Integration Pattern

### Off-Chain Watcher / Event Oracle Flow

1. **Event Detection**:
   - Off-chain watcher observes cross-chain event (e.g., lock on Ethereum)
   - Collects cryptographic proofs and witness signatures

2. **Construct Transaction**:
   - **If Legitimate** (normal consensus):
     - Build tx with EventTrigger → Permit path
     - Create `commitmentCount` reward boxes with split RWT
     - Ensure all R4 WIDs hash to expected digest
     - Include GuardLock box in inputs
   - **If Fraud Detected** (consensus failure or double-spend