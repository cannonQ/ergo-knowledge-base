---
title: StabilityNexus/BenefactionPlatform-Ergo — contract_v2.es
description: "ErgoScript contract analysis: contracts/bene_contract/contract_v2.es"
tags: [stabilitynexus, benefactionplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
contract_file: contracts/bene_contract/contract_v2.es
project: stabilitynexus-benefactionplatform-ergo
---
# BenefactionPlatform Fundraising Contract Analysis

## Purpose

This ErgoScript contract implements a **multi-token fundraising platform** that enables projects to raise funds (in ERG or any native token) by issuing Proof-of-Funding Tokens (PFTs) to contributors. The contract manages the exchange of base tokens for PFTs at a fixed rate while tracking sold/refunded amounts and enforcing temporal constraints on refunds.

---

## Inputs / Outputs

### Expected Inputs
- **SELF (Contract Box)**
  - **Tokens:**
    - **APT (Auxiliary Proof Token)**: ID-based NFT; amount = `PFT_emission + 1` (singleton identifier for the project)
    - **PFT (Proof-of-Funding Token)**: Native token; amount = maximum base tokens the project aims to raise
  - **Value**: ERG (minimum box value + any accumulated funds if using ERG as base)
  - **Base Token** (optional): If non-ERG base token, holds contributed tokens
  
- **User Input Box** (for contribution or refund transactions)
  - Contains base tokens (ERG or configured native token ID)

### Produced Outputs
- **Replicated Contract Box** (at `OUTPUTS(0)`)
  - Same structure as SELF with updated registers
  - Updated `R6` counters: `[sold, refunded, exchanged]`
  - Updated PFT/base token amounts reflecting the transaction
  
- **User Output Box**
  - Receives PFTs in exchange for base tokens, OR
  - Receives refunded base tokens (if refund conditions met)

- **Dev Fee Box** (optional)
  - Sent to contract specified in `R8` with developer's fee share

---

## Key Logic

### Core Validation Rules

1. **Box Replication (State Machine Pattern)**
   - Output box at index 0 must be a valid replica of SELF with:
     - Same APT ID and amount (`APTokenRemainsConstant`)
     - Same PFT total amount (`ProofFundingTokenRemainsConstant`)
     - Same ERG/base token value (`mantainValue`)
     - Same R4, R5, R7, R8, R9 registers (immutable project parameters)
     - Same ErgoTree/script bytes (`sameScript`)
   - Prevents adding unexpected tokens or modifying core parameters

2. **Temporal Refund Logic**
   - `R4: (Boolean, Long)` specifies refund deadline:
     - `Boolean = false`: Block height limit
     - `Boolean = true`: Timestamp limit
   - Refunds only permitted AFTER this limit if minimum tokens `R5` were NOT sold
   - If minimum threshold met, funds are locked (no refund possible)

3. **Exchange Rate Enforcement**
   - `R7: Long` stores base tokens required per 1 PFT
   - All exchanges must respect this fixed ratio
   - Works for both ERG and custom base tokens

4. **Multi-Token Support**
   - `baseTokenId` in `R8(4)`:
     - Empty (length 0) → contributions in ERG only
     - Specified → contributions in that native token only
   - `isERGBase` flag gates between ERG (value-based) and token-based amount calculations

5. **Funding Token Availability Calculation**
   ```
   available_APT = PFT_balance - sold + refunded + exchanged
   ```
   - Prevents overselling by accounting for:
     - **sold**: Total PFTs exchanged
     - **refunded**: Total PFTs returned to contributors
     - **exchanged**: APT tokens converted back to PFT (for rebalancing)

6. **Counter Management (R6)**
   - `R6[0]`: Total tokens sold (cumulative)
   - `R6[1]`: Total tokens refunded (cumulative)
   - `R6[2]`: Auxiliary exchange counter (APT→PFT conversions)
   - All counters must remain constant unless transaction explicitly updates them
   - Enables atomic accounting across multi-box transactions

7. **Token Validation**
   - Maximum token count in replication box:
     - ERG base: 1–2 tokens (APT ± PFT)
     - Non-ERG base: 1–3 tokens (APT ± PFT ± base_token)
   - Prevents dust or spam token injection

### Authorization Pattern
- `R8(0)`: Owner ErgoTree (may be P2PK or P2S) for project control
- `R8(1)`: Dev fee contract bytes hash (Blake2b-256) for routing fees
- `R8(2)`: Dev fee percentage (e.g., 5 for 5%)

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|-----------|
| **R4** | `(Boolean, Long)` | Refund deadline (block height or timestamp) | Immutable |
| **R5** | `Long` | Minimum tokens that must be sold to lock funds | Immutable |
| **R6** | `Coll[Long]` | State counters: `[sold, refunded, exchanged]` | Mutable (incremented only) |
| **R7** | `Long` | Exchange rate: base tokens per PFT | Immutable |
| **R8** | `Coll[Coll[Byte]]` | Constants array: `[owner_ergotree, dev_fee_contract_hash, dev_fee%, pft_token_id, base_token_id]` (Base58-encoded JSON) | Immutable |
| **R9** | `Coll[Byte]` | Project metadata (Base58-encoded JSON with "title" & "description") | Immutable |

**Register Access Pattern:**
```ergoscript
val r8 = SELF.R8[Coll[Coll[Byte]]].get
val ownerErgoTree = r8(0)          // P2PK/P2S authorization
val devFeeHash = r8(1)             // Dev fee recipient validation
val devFee = byteArrayToBigInt(r8(2))  // Fee percentage