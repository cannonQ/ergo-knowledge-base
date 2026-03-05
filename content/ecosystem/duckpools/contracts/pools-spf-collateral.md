---
title: duckpools/lend-protocol-contracts — collateral.md
description: "ErgoScript contract analysis: contracts/pools/spf/collateral.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/spf/collateral.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Collateral Management (Duck Pools Lend Protocol)

## Purpose

This contract manages collateral boxes in a lending protocol, enforcing two primary transaction flows: (1) **collateral adjustments** where borrowers can add/remove collateral while maintaining liquidation thresholds, and (2) **loan repayment or liquidation** where loans are settled and collateral is returned or liquidated. The contract compounds interest across a multi-tier hierarchy of interest-rate boxes and validates all state transitions against strict solvency requirements.

---

## Inputs / Outputs

### Inputs
- **SELF (INPUTS[0] or INPUTS[1])**: The collateral box itself—contains the current loan state and collateral reserve
- **Data Input (CONTEXT.dataInputs[0])**: Base child interest box (NFT-authenticated, contains historical rates)
- **Data Input (CONTEXT.dataInputs[1])**: Parent interest box (holds the live interest-rate timeline)
- **Data Input (CONTEXT.dataInputs[2])**: Head child interest box (the newest rate accumulator in the hierarchy)
- **Data Input (CONTEXT.dataInputs[3])**: DEX pool box (only for collateral adjustments; provides exchange rates for collateral valuation)

### Outputs

**For Collateral Adjustment (INPUTS[0] == SELF):**
- **OUTPUTS[0]**: Successor collateral box (same script, same borrow tokens, updated ERG reserve)

**For Repayment/Liquidation (INPUTS[1] == SELF):**
- **OUTPUTS[0]**: Borrower's refund box (receives remaining collateral after repayment)
- **OUTPUTS[1]**: Repayment contract box (receives repayment tokens and loan record tokens, enforces loan settlement)
- **OUTPUTS[2]** (optional): Successor collateral box (if partial repayment; maintains remaining loan)

---

## Key Logic

### 1. **Interest Calculation (Multi-Tier Compounding)**
The contract compounds interest across three tiers of interest boxes:
- Slices historical rates from the **base child** (starting at `childIndex`)
- Chains through the **head child** (if parent has advanced)
- Chains through the **parent** rates (if parent index advanced by >1)
- Each rate is applied multiplicatively: `compounded = fold(initial, rates, (z, r) => z * r / InterestRateDenom)`
- **Total owed** = `1 + (loanAmount × compoundedInterest / InterestRateDenom)` (adds 1 to prevent zero-owed edge case)

### 2. **Collateral Adjustment Branch (INPUTS[0] == SELF)**
**Conditions:**
- Successor box must retain the **same script** (ErgoTree) and **same borrow tokens**
- All registers (borrower, indexes, thresholds, DEX NFT, user PK, liquidation flags) must remain **identical**
- Collateral value is calculated via DEX swap simulation:
  ```
  collateralValue = (dexReservesToken × inputAmount × dexFee) / 
                   ((dexReservesErg + slippage%) × DexLpTax + inputAmount × dexFee)
  ```
  This represents the token amount obtainable if ERG collateral were swapped
- **Liquidation check**: `collateralValue > totalOwed × liquidationThreshold / 1000`
  - Ensures collateral-to-debt ratio stays above threshold
- Successor must have minimum box value: `≥ 3 × MinimumBoxValue + MinimumTransactionFee`
- **Requires user signature**: `proveDlog(currentUserPk)` ∧ (all validations)

### 3. **Repayment/Liquidation Branch (INPUTS[1] == SELF)**
**Two sub-paths determined by output structure:**

**Path A: Full Repayment** (OUTPUTS has 2 boxes; INPUTS[0] has ≥3 tokens)
- Repayment box receives:
  - Borrow token record (the original loan ID token)
  - Loan tokens ≥ `totalOwed` amount
- Borrower receives collateral: `≥ currentValue - MinimumTransactionFee`
- Repayment box script hash must equal `RepaymentContractScript`

**Path B: Partial Repayment** (OUTPUTS has 3+ boxes; INPUTS[0] has <3 tokens)
- Similar to Path A, but successor collateral box is created
- Successor must:
  - Retain script and borrow tokens
  - Retain all registers except possibly updated liquidation flags
  - Have `≥ 3 × MinimumBoxValue + MinimumTransactionFee` value

### 4. **Data Input Validation**
All three interest boxes must be authenticated via NFT:
- Base child: `baseChildNft._1 == ChildInterestNft` ∧ `baseChildIndex == parentIndex`
- Parent: `parentNft._1 == ParentInterestNft`
- Head child: `headChildNft._1 == ChildInterestNft` ∧ `headChildIndex == parentInterestRates.size`

The **DEX box** is validated by NFT: `dexNft._1 == currentDexNft`

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **Borrower's address** (ErgoScript contract script bytes); used to route collateral on repayment |
| **R5** | `(Int, Int)` | **Interest rate indexes**: `(parentIndex, childIndex)` — pointers into the parent/child interest-rate timelines |
| **R6** | `(Long, Long)` | `(liquidationThreshold, liquidationPenalty)` — threshold in basis points (÷1000) and penalty multiplier |
| **R7** | `Coll[Byte]` | **DEX NFT ID** — identifies which DEX pool provides collateral valuation (used for ERG↔token swap price) |
|