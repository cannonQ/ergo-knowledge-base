---
title: duckpools/lend-protocol-contracts — collateral.md
description: "ErgoScript contract analysis: contracts/pools/drafts/SIGUSD-POOL/collateral.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/drafts/SIGUSD-POOL/collateral.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: SIGUSD-POOL Collateral Manager

## Purpose

This contract manages collateralized loan positions in a lending protocol, enabling borrowers to adjust collateral levels and repay loans with accrued interest. It enforces liquidation thresholds, validates interest calculations across a multi-level interest rate index hierarchy, and supports both full repayment and partial liquidation scenarios.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)** (Collateral Adjustment Path): The current SELF collateral box being spent
- **INPUTS(1)** (Repayment/Liquidation Path): The current SELF collateral box being spent
- **Data Inputs**:
  - `CONTEXT.dataInputs(0)`: Base child interest box (holds historical rates from parent index checkpoint)
  - `CONTEXT.dataInputs(1)`: Parent interest box (root of rate hierarchy)
  - `CONTEXT.dataInputs(2)`: Head child interest box (current leaf of rate tree)
  - `CONTEXT.dataInputs(3)`: DEX pool box (for collateral valuation via AMM)

### Outputs
- **Collateral Adjustment Path**:
  - `OUTPUTS(0)`: Successor collateral box (state continuation, same contract)
  
- **Repayment/Liquidation Path**:
  - `OUTPUTS(0)`: Borrower's box (receives original collateral token)
  - `OUTPUTS(1)`: Repayment box (receives interest-bearing borrow tokens and repayment assets)
  - `OUTPUTS(2)` (optional): Change box for partial repayment

---

## Key Logic

### 1. **Interest Calculation Chain**
The contract validates a three-tier interest rate index system:

```
Base Child Rates [childIndex → size] 
    ↓ (fold with multiplication)
Head Child Rates [0 → size]
    ↓ (fold with multiplication)
Parent Rates [parentIndex+1 → size]
```

**Compounded Interest Formula:**
```
compoundedInterest = fold(1.0, rate → z * rate / InterestRateDenom)
totalOwed = ceiling(loanAmount * compoundedInterest / InterestRateDenom)
```

This allows efficient off-chain interest accrual: instead of updating rates on-chain, the contract reads historical snapshots and replays calculations deterministically.

### 2. **Collateral Adjustment Branch** (INPUTS(0) == SELF)

**Validation Chain:**
1. **Interest box validation:**
   - Base child NFT matches `ChildInterestNft` constant
   - Base child index equals stored `parentIndex` (points to correct rate history)
   - Parent NFT matches `ParentInterestNft` constant
   - Head child index equals current parent rate size (latest rates)

2. **DEX box validation:**
   - DEX box NFT matches stored `currentDexNft`
   - Computes collateral value using Spectrum DEX formula:
     ```
     collateralValue = (deltaXAmount * inputAmount * dexFee) / 
                      (dexReserves + slippage * dexReserves) * DexLpTaxDenomination + 
                      (inputAmount * dexFee)
     ```

3. **Successor box validation:**
   - Script (ErgoTree) unchanged (preserves state machine)
   - Value ≥ current value (no ERG leakage)
   - Collateral token type unchanged
   - Borrow tokens unchanged
   - All registers (R4-R9) unchanged

4. **Collateral sufficiency check:**
   ```
   collateralValue ≥ (totalOwed * liquidationThreshold) / LiquidationThresholdDenom
   ```

5. **Authorization:**
   ```
   proveDlog(currentUserPk) ∧ [all validations above]
   ```

### 3. **Repayment/Liquidation Branch** (INPUTS(1) == SELF)

**Two sub-paths:**

#### a) **Full Repayment**
Validates:
- Borrower box script equals original borrower address
- Borrower receives exact original collateral tokens
- Repayment box script hash matches `RepaymentContractScript`
- Repayment box value ≥ `MinimumBoxValue + MinimumTransactionFee` (meets minimum box value requirement)
- Repayment assets ≥ `totalOwed` (covers accrued interest)
- Repayment borrow tokens match original loan tokens

#### b) **Partial Liquidation** (triggered if conditions met)
- Assumes liquidator paid for collateral via DEX
- Liquidator receives remaining collateral at liquidation price
- Penalty applied: `liquidationPenalty / PenaltyDenom`
- Borrower receives residual after fees

**Shared Interest Validation:** Both paths verify the three interest box chain before processing.

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|-----------|
| **R4** | `Coll[Byte]` | Borrower address (Sigma protocol script) | Immutable |
| **R5** | `(Int, Int)` | Index pair: (parentIndex, childIndex) for rate history lookup | Immutable |
| **R6** | `(Long, Long)` | (liquidationThreshold, liquidationPenalty) denominated in units of 1000 | Immutable |
| **R7** | `Coll[Byte]` | DEX pool NFT ID (identifies correct AMM for valuation) | Immutable |
| **R8** | `GroupElement` | User's public key (Schnorr commitment for Σ-protocol) | Immutable |
| **R9** | `Long` | Forced liquidation flag/timestamp | Immutable |

**Tokens (R2):**
- **Index 0:** Collateral token (native token pair: ID + amount)
- **Index 1:** Borrow token (stablecoin: ID + principal amount)

---

## Tokens

### 1. **NFT Tokens** (Authentication