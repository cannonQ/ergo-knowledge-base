---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — reputation_token.es
description: "ErgoScript contract analysis: contracts/reputation_system/reputation_token.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/reputation_system/reputation_token.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: Reputation Token

## Purpose

This contract governs individual boxes within a distributed, atomically-validated collection of reputation tokens. It enforces coherence across the entire collection, ensures data uniqueness, and authorizes state mutations only by the owner while allowing any user to prevent storage rent demurrage through cost-free ERG top-ups.

---

## Inputs / Outputs

### Inputs
- **SELF**: The reputation token box being spent, containing:
  - Token(0): The reputation token (repTokenId, amount)
  - Registers R4–R9 with collection metadata and ownership proof
- **Other Input Boxes** (Admin Path): Sibling reputation boxes from the same collection, identified by matching script hash and token ID

### Data Inputs
- **Type NFT Box** (Admin Path, required): A box at `dataInputs[0]` holding the Type NFT (referenced by R4) that validates this box's adherence to a standard
- **Sibling Collection Boxes** (Admin Path): All other boxes in the reputation collection, provided as data inputs to prove completeness without consuming them

### Outputs
- **Admin Path**: Modified/recreated reputation boxes with:
  - Preserved token counts (reputation + secondary tokens)
  - Updated/maintained registers (R4–R9)
  - Preserved ERG value (≥ input value)
  - Same script hash (locked to this contract)
- **Top-Up Path**: Single output box that is an **exact replica** of SELF with increased (or equal) ERG value

---

## Key Logic

### Path 1: Admin Transaction (Owner-Signed)

1. **Owner Verification**
   - Checks that at least one input box's `blake2b256(propositionBytes)` matches `SELF.R7` (owner's script hash)
   - Ensures only the owner can authorize collection mutations

2. **Completeness Proof** (Multi-stage State Machine)
   - Collects all reputation boxes across:
     - `dataInputs` (read-only references)
     - `INPUTS` (being spent)
     - `OUTPUTS` (newly created)
   - Identifies them by:
     - Matching script hash (same contract)
     - Matching reputation token ID (`tokens(0)._1`)
     - Matching `totalSupply` in R6 (consistency across collection)
     - Matching owner hash in R7
     - Presence of R4, R5, R8 (metadata integrity)
   - **Invariant**: Sum of tokens on data inputs + sum on inputs must equal declared `totalSupply`

3. **Value Preservation**
   - **Reputation tokens**: Exact balance preservation (`inputsAmount == outputsAmount`)
   - **Secondary tokens** (index 1+): All token IDs must have output amount ≥ input amount
   - **Native ERG**: Total output value ≥ total input value

4. **Output Uniqueness & Validity** (Per-box constraints)
   - **Type Binding**: Each output's R4 (Type NFT ID) must exist in a data input box with:
     - Script hash matching `DIGITAL_PUBLIC_GOOD`
     - Creation height < current height (block ancestry validation)
   - **Uniqueness in Data Inputs**: No data input can reference the same (R4, R5) pair as the output
   - **Uniqueness in Outputs**: No two output boxes can have the same (R4, R5) pair
   - **Lock Status Respect**: If `isLocked == true`, output must be identical to input (frozen state)
   - **Metadata Immutability** (locked): R4, R5 unchanged in locked boxes

5. **Final Gate**: All conditions (supply, value, uniqueness, lock status) must be satisfied

### Path 2: ERG Top-Up (Public, Signature-Free)

- **Single Output Requirement**: Exactly one output created
- **Exact Replica Constraint**: Output must match SELF in:
  - All tokens (including amounts)
  - All registers (R4–R9)
  - Script (same ErgoTree)
- **Value Increase**: Output ERG value ≥ input ERG value
- **Purpose**: Prevents storage rent (demurrage) deduction by recycling the box with fresh ERG

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **Type NFT Token ID**: Identifier of the standard/schema this box adheres to; must reference a Type NFT box in data inputs |
| **R5** | `Coll[Byte]` | **Unique Object Data**: Metadata that, combined with R4, uniquely identifies this object within the collection; prevents duplicate (R4, R5) pairs |
| **R6** | `(Boolean, Long)` | **Lock Status & Total Supply**: Tuple of `(isLocked, totalSupply)`. `isLocked=true` freezes the box state; `totalSupply` is the expected sum of all reputation tokens in the collection |
| **R7** | `Coll[Byte]` | **Owner's Script Hash**: `blake2b256` of the owner's proposition bytes; used to authorize admin transactions |
| **R8** | `Boolean` | **Custom Flag**: Application-specific boolean for auxiliary logic or feature toggles |
| **R9** | `Coll[Byte]` | **Reserved**: Placeholder for future protocol extensions |

---

## Tokens

### Token(0): Reputation Token
- **Role**: Primary tracked asset in the collection
- **Type**: `(Coll[Byte], Long)` → `(repTokenId, amount)`
- **Rules**:
  - Sum of all amounts across collection must equal `R6._2` (totalSupply) under admin path
  - Must be preserved exactly (`inputsAmount == outputsAmount`) in admin transactions
  - Part of output replica requirement in top-up path

### Token(1..n): Secondary Tokens
- **Role**: Auxiliary assets (collateral, fees, or application-specific tokens)
- **Rules**:
  - Output amount ≥ input amount for each token ID (one-way flow)
  - Sliced from `tokens.slice(1, tokens.size)` and aggregated by ID
  - Included in value preservation