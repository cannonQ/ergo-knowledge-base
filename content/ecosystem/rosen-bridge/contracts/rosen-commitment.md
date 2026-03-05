---
title: rosen-bridge/contract — Commitment.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/Commitment.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/Commitment.es
project: rosen-bridge-contract
---
# ErgoScript Contract Analysis: Commitment.es

## Purpose

The **Commitment** contract is a core component of the Rosen Bridge's multi-signature event validation system. It aggregates cryptographic commitments from Watchers for cross-chain events, validates that sufficient consensus (quorum) has been reached, and orchestrates the transition from commitments to watcher permits—enabling reward distribution and event finality.

## Inputs / Outputs

### Inputs
- **Primary Input (SELF)**: A Commitment Box containing:
  - Native token (X-RWT) for authentication and accounting
  - Register data: WID, Event ID, Event Data Digest, Permit Script Digest
  
- **Multiple Commitment Boxes** (filtered by same ErgoTree): Parallel commitments from other Watchers for the same event
  
- **Event Trigger Box** (either INPUTS(0) or OUTPUTS(0)): Created/verified box that aggregates all commitments

- **Data Inputs** (context-only, not consumed):
  - RepoConfigBox: Contains configuration parameters (RWT requirements, quorum formula)
  - RWT Repo Box: Repository tracking total watcher count and RWT token distribution

### Outputs
Depends on execution path:

**Path 1 — Reward Distribution** (missed commitments):
- **WatcherPermit Boxes**: One per rewarded watcher, holding X-RWT tokens
- **BridgeWallet Box**: Receives remaining ERG

**Path 2 — Event Trigger Creation** (consensus reached):
- **EventTrigger Box**: Aggregates all WID commitments, event digest, and RWT tokens for reward distribution
- Commitment boxes are consumed; funds consolidated into EventTrigger

**Path 3 — Commitment Redeem** (simple conversion):
- **Permit Box**: Receives X-RWT tokens, replaces Commitment box
- **User WID Box**: Receives user identification token

---

## Key Logic

### Path 1: Reward Distribution (Missed Commitments)

Triggered when: `blake2b256(INPUTS(0).propositionBytes) == eventTriggerHash` (EventTrigger is input)

**Validation conditions:**
1. **Permit Script Match**: Output permit box's ErgoTree digest must equal stored R7
2. **Token Preservation**: Permit box receives identical X-RWT tokens as Commitment
3. **No Duplicate Rewards**: Current watcher's WID must NOT appear in the `WIDs` list extracted from EventTrigger's R7 (count of first N outputs)
4. **Single Commitment**: Exactly one Commitment box with current watcher's WID exists in inputs
5. **Data Integrity**: Event data digest (`blake2b256(eventData ++ myWID)`) must match R6
6. **Prevents Double-Claiming**: WIDExists check ensures this watcher wasn't already included in the processed event

**Purpose**: Rewards watchers whose commitments were verified post-event-trigger creation, preventing double-counting.

---

### Path 2: Event Trigger Creation (Consensus Reached)

Triggered when: `blake2b256(OUTPUTS(0).propositionBytes) == eventTriggerHash` (EventTrigger is output)

**Validation conditions:**

1. **Repository Validation**:
   - RepoConfigBox holds `REPO_CONFIG_NFT` (singleton, ensures single source of truth)
   - RWT Repo holds `RWT_REPO_NFT` (singleton, tracks watcher registry)

2. **No Duplicate Commitments**: Current watcher contributes exactly 1 commitment (prevents Sybil attacks)

3. **Event Trigger Parameters**:
   - Trigger receives sufficient ERG (sum of all commitment box values)
   - Trigger's permit script digest (R6) matches SELF's R7
   - Trigger's watcher count (R7) equals total commitments received
   - Trigger's WID list digest (R4) matches hash of concatenated WIDs

4. **Data Validation**:
   - Event data digest: `blake2b256(eventData ++ myWID) == SELF.R6`
   - Event ID from trigger's R5 matches SELF.R5

5. **Quorum & RWT Requirements**:
   - **Quorum Formula**: `required = min(maxCommitment, baseCommitment + (watcherCount × percentage) / 100)`
   - Actual commitments must **exceed** required threshold
   - Each Commitment box holds exactly `repoConfig(0)` RWT tokens
   - EventTrigger receives total RWT = `repoConfig(0) × commitmentBoxes.size`

6. **Token Consistency**: All X-RWT token IDs must match across inputs and outputs

**Purpose**: Finalizes event consensus when quorum is reached; prevents premature trigger creation and ensures RWT backing.

---

### Path 3: Commitment Redeem (Simple Path)

Triggered when: Neither EventTrigger is input nor output (direct redemption)

**Validation conditions:**
1. **SELF Consumption**: Commitment box is the first input
2. **Token Propagation**: Output permit box receives identical X-RWT tokens
3. **WID Preservation**: Output permit box copies WID from R4
4. **User Token**: Second output receives a user-identification token with ID = myWID
5. **Permit Contract**: Output permit box's ErgoTree digest matches stored R7

**Purpose**: Converts a Commitment into a Permit without event consensus (e.g., for alternate validation workflows).

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **WID** (Watcher Identifier) — unique, deterministic identifier for each watcher |
| **R5** | `Coll[Byte]` | **Event ID** — `blake2b256` hash of the triggering transaction/event data |
| **R6** | `Coll[Byte]` | **Event Data Digest** — `blake2b256(eventData ++ myWID)` for non-repudiation |
| **R7** | `Coll[Byte]` | **Permit Script Digest** — `blake2b256` of the Permit contract's ErgoTree |