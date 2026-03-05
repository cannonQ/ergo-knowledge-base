---
title: duckpools/lend-protocol-contracts — collateral.md
description: "ErgoScript contract analysis: contracts/pools/SIGRSV-POOL/collateral.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/SIGRSV-POOL/collateral.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Collateral Management (DuckPools Lending Protocol)

## Purpose

This contract manages collateral boxes in a lending protocol, enforcing two primary operations: (1) **collateral adjustment**, allowing borrowers to modify their collateral amounts while maintaining liquidation thresholds, and (2) **repayment/liquidation**, enabling loan repayment or forced liquidation when collateral drops below safety thresholds. It uses compound interest calculations across a hierarchical interest rate index structure to determine total loan obligations.

---

## Inputs / Outputs

### Inputs
- **SELF (Input 0 or 1)**: The collateral box being spent, containing:
  - The borrower's collateral in ERG (native token, box value)
  - Borrow tokens (NFT proving loan identity) in `tokens(0)`
  - User cryptographic key in R8 for authorization
  
- **Data Inputs (Context.dataInputs)**: Read-only reference boxes
  - **dataInputs(0)**: Base child interest rate box (contains historical rates from `childIndex` onwards)
  - **dataInputs(1)**: Parent interest rate box (root of interest hierarchy)
  - **dataInputs(2)**: Head child interest rate box (current leaf of rate history)
  - **dataInputs(3)** *(collateral adjustment only)*: DEX pool box (for price calculation)

### Outputs (Collateral Adjustment Branch)
- **OUTPUTS(0)**: Successor collateral box—identical script, same borrow tokens, adjusted ERG value, all registers preserved

### Outputs (Repayment/Liquidation Branch)
- **OUTPUTS(0)**: Borrower's recipient box (refunded collateral minus fees)
- **OUTPUTS(1)**: Repayment box (locked to `RepaymentContractScript`, contains loan tokens and borrow token proof)
- **OUTPUTS(2)** *(partial repay)*: New collateral box (if loan not fully repaid)

---

## Key Logic

### 1. **Interest Calculation (Multi-Tier Compound Interest)**
- Traverses three interest rate boxes in hierarchical order:
  1. **Base child rates** from `childIndex` to end
  2. **Head child rates** (if parent index advanced)
  3. **Parent rates** (if parent has multiple snapshots)
- Compounds interest multiplicatively: `result = initial_amount × (rate₁/denom) × (rate₂/denom) × ...`
- **denominator**: `InterestRateDenom = 100,000,000`
- Final total owed: `totalOwed = 1 + (loanAmount × compoundedInterest / denom)`
- Ensures borrower always owes slightly more than principal (1 unit buffer)

### 2. **Collateral Adjustment Path** (INPUTS(0) == SELF)
Validates successor collateral box while allowing ERG adjustment:
- **Invariant preservation**: Borrow tokens, borrower address, interest indexes, liquidation threshold, penalty, DEX NFT, user key must match
- **DEX price calculation**: 
  - Reads DEX pool reserves (ERG and token amounts) and swap fee
  - Computes collateral value using constant-product AMM formula with slippage tolerance (2%)
  - Formula: `collateralValue = (tokenReserves × inputAmount × dexFee) / ((ergReserves × slippage_adjusted) × LpTaxDenom + inputAmount × dexFee)`
- **Liquidation safety check**: 
  - `collateralValue > (totalOwed × liquidationThreshold / 1000)`
  - Successor box value ≥ `3 × MinimumBoxValue + MinimumTransactionFee` (enough for future operations)
- **Authorization**: Requires Schnorr signature from user (proveDlog on R8 key)

### 3. **Repayment/Liquidation Path** (INPUTS(1) == SELF)
Handles loan closure or liquidation:
- **Borrower refund validation**: 
  - Recipient box script matches borrower address from R4
  - Receives full collateral minus network fees
- **Repayment box validation**:
  - Script hash equals `RepaymentContractScript` (ensures routing to correct handler)
  - Contains borrow token (proof of loan) and loan tokens ≥ `totalOwed`
  - Box value ≥ `MinimumBoxValue + MinimumTransactionFee`
- **Two sub-branches**:
  - **Full repayment**: Loan fully paid; only borrower and repayment outputs
  - **Partial repayment**: Loan not fully paid; outputs successor collateral box with adjusted borrow tokens and reduced ERG

### 4. **Interest Rate Box Validation**
- **Base child**: NFT ID matches `ChildInterestNft`, index must equal `parentIndex`
- **Parent**: NFT ID matches `ParentInterestNft`
- **Head child**: NFT ID matches `ChildInterestNft`, index equals parent's rate history size (proving it's the "current leaf")

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Borrower's wallet address (script hash); receiver in repayment path |
| **R5** | `(Int, Int)` | `(parentIndex, childIndex)` — pointers into interest rate history for compound interest calculation |
| **R6** | `(Long, Long)` | `(liquidationThreshold, liquidationPenalty)` — safety ratio (numerator/1000) and penalty rate; threshold defines collateral-to-debt ratio requirement |
| **R7** | `Coll[Byte]` | DEX pool NFT ID for price oracle lookups during collateral adjustments |
| **R8** | `GroupElement` | User's Schnorr public key (EC point) for spending authorization in collateral adjustment |
| **R9** | `(Long, Long)` | `(forcedLiquidationFlag, liquidationBuffer)` — liquidation control parameters; currently reads but not enforced in this contract version |

---

## Tokens

### Token Usage

| Token