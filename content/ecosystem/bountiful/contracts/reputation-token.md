---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — reputation_token.es
description: "ErgoScript contract analysis: contracts/reputation_token.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/reputation_token.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: `reputation_token.es`

## Purpose

This contract manages a **Reputation Token** state machine within the Bountiful Bounty Platform ecosystem. It enforces rules for reputation token lifecycle management, including supply validation, owner-controlled locking mechanisms, and immutable state preservation across transactions. The contract acts as a Singleton / State NFT controller that maintains invariants over reputation token distributions across multiple boxes in the eUTXO model.

---

## Inputs / Outputs

### Inputs
- **SELF (Primary Input):** The current reputation token box, containing:
  - Reputation token (primary, at index 0)
  - Optional secondary tokens (bounty/reward tokens)
  - State stored in registers R4–R9
  
- **Secondary Inputs (repBoxesOnInputs):** Additional reputation token boxes matching SELF's script hash, token ID, and owner, used in supply validation during owner-controlled transactions.

### Data Inputs (repBoxesOnDataInputs)
- Read-only reputation token boxes used to validate state consistency without consuming them.
- Filtered by matching script hash, token ID, total supply, and owner.
- Used in correctness checks without being spent.

### Outputs
- **Successor Box:** A new box with the same ErgoTree (proposition) as SELF.
  - Must preserve reputation tokens and all state registers in `publicTopUpPath`.
  - May redistribute reputation tokens and add secondary tokens in `ownerSignedPath`.
  - Must maintain minimum box value (Storage rent).

---

## Key Logic

### Two Execution Paths (OR composition):

#### **Path 1: `ownerSignedPath` (Owner-Controlled)**
Requires proof that an input box in the transaction has a proposition matching the owner's signature (stored in R7).

**Validations:**

1. **Owner Authentication:**
   - `INPUTS.exists { blake2b256(b.propositionBytes) == SELF.R7[Coll[Byte]].get }`
   - Ensures transaction is signed by the owner's box.

2. **Lock State & Total Supply:**
   - Reads `R6: (Boolean, Long)` → `(isLocked, totalSupply)`
   - All reputation boxes must have identical total supply.

3. **Supply Conservation (`correctManagedSupply`):**
   - `dataInputsAmount + inputsAmount == totalSupply` (all reputation tokens accounted for)
   - `inputsAmount == outputsAmount` (spent reputation tokens reappear in outputs)
   - **Secondary Token Preservation:** For all secondary tokens (index 1+):
     - `sum(outputs) >= sum(inputs)` per token ID
     - Prevents loss of bounty/reward tokens while allowing additions.

4. **Output Validity (`outputsValid`):**
   - **Type Token Existence:** R4 contains a type token ID; must exist in a **Digital Public Good** box (data input) created before current block height.
   - **Uniqueness in Data Inputs:** The pair `(R4, R5)` must be unique across data inputs (no duplicate reputation type + recipient combos).
   - **Uniqueness in Outputs:** The pair `(R4, R5)` must be unique across all outputs (no duplicate recipients for same type).

5. **Lock Enforcement (`correctLock`):**
   - If `isLocked == true`, a successor output must exist with:
     - Token amount `>= SELF.tokens(0)._2`
     - Same R4, R5 (type & recipient immutable)
     - R6._1 == true (remains locked)
     - Same R9 (lock metadata)
   - If `isLocked == false`, no constraint (can be freely distributed).

#### **Path 2: `publicTopUpPath` (Public Value Top-Up)**
Allows anyone to add Ergs to SELF without modifying state or token distribution.

**Validations:**

1. **Single Successor:** Exactly one output box with the same proposition and reputation token ID.
2. **Register Immutability:** All registers R4–R9 unchanged.
3. **Token Immutability:** Token vector identical (no minting/burning/redistribution).
4. **Erg Top-Up Only:** `successor.value >= SELF.value` (can only add Ergs, covering Storage rent increases).

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **Type Token ID** – Identifies the reputation category/bounty type from a Digital Public Good box. |
| **R5** | `Coll[Byte]` | **Recipient Address** – The entity (user, bounty submitter) who earned this reputation token. |
| **R6** | `(Boolean, Long)` | **(isLocked, totalSupply)** – Lock flag indicates if reputation is frozen; total supply tracks all reputation tokens in circulation for validation. |
| **R7** | `Coll[Byte]` | **Owner's Proposition Bytes** – Hash of the owner's signing script; used to authenticate owner-controlled path. |
| **R8** | `Boolean` | **Status Flag** – Metadata for reputation state (exact semantics context-dependent). |
| **R9** | `Coll[Byte]` | **Lock Metadata** – Additional lock context (e.g., lock reason, timestamp reference). Must be preserved when locked. |

**Register Semantics:**
- Registers are **immutable within `publicTopUpPath`** (can only top-up Ergs).
- Registers may be **modified within `ownerSignedPath`** but with constraints (e.g., R6._1 must remain true if locked).

---

## Tokens

### Primary Token (Index 0)
- **Token ID:** `SELF.tokens(0)._1`
- **Amount:** `SELF.tokens(0)._2`
- **Role:** Reputation token itself (NFT-like, unique per type + recipient pair).
- **Validation:** Must be preserved across transactions (no minting/burning in both paths).

### Secondary Tokens (Index 1+)
- **Role:** Bounty rewards, payment tokens, or collateral associated with the reputation record.
- **Conservation:** Amount per token ID must not decrease (can be added,