---
title: duckpools/lend-protocol-contracts — collateral.md
description: "ErgoScript contract analysis: contracts/pools/eSIGUSD-POOL/collateral.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/eSIGUSD-POOL/collateral.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: eSIGUSD-POOL Collateral Contract

## Purpose

This contract manages collateralized loan positions in a decentralized lending protocol, tracking borrowed assets and their accruing interest through a hierarchical index system. It validates collateral adjustments, repayments, and liquidations by computing compound interest across multi-level interest rate structures and ensuring collateral ratios remain above liquidation thresholds.

## Inputs / Outputs

### Inputs
- **SELF (INPUTS(0) or INPUTS(1))**: The current collateral box containing:
  - Borrow tokens (borrowed asset record with quantity)
  - Collateral in ERG
  - Borrower address, interest indexes, liquidation parameters, DEX NFT identifier, user public key, forced liquidation flag, and liquidation buffer
  
- **Data Inputs**:
  - `CONTEXT.dataInputs(0)`: Base child interest box (read-only, contains historical interest rates from a child node)
  - `CONTEXT.dataInputs(1)`: Parent interest box (read-only, contains parent-level interest rates)
  - `CONTEXT.dataInputs(2)`: Head child interest box (read-only, latest child node in interest index tree)
  - `CONTEXT.dataInputs(3)`: DEX pool box (read-only, for collateral valuation via AMM pricing)

### Outputs

**Path A (Collateral Adjustment, INPUTS(0) == SELF)**:
- `OUTPUTS(0)`: Successor collateral box with adjusted ERG value, same script and registers as SELF

**Path B (Repayment/Liquidation, INPUTS(1) == SELF)**:
- `OUTPUTS(0)`: Borrower's box (receives collateral refund) OR DEX box (in liquidation)
- `OUTPUTS(1)`: Repayment box (script hash matches `RepaymentContractScript`) containing:
  - Current borrow tokens (as record)
  - Loan tokens (quantity must exceed totalOwed)
  - Minimum value and fees

**Path C (Liquidation)**:
- `OUTPUTS(0)`: DEX box (receives collateral for swap)
- `OUTPUTS(1)`: Liquidator's box (receives liquidation penalty)
- `OUTPUTS(2)`: Liquidation proceeds box

## Key Logic

### 1. **Interest Calculation (Multi-Level Compound)**
   - Extracts interest rate history from base child, head child, and parent interest boxes
   - Slices relevant rate ranges based on stored parent/child indexes
   - Compounds rates using fold: `(z * rate) / InterestRateDenom` for each historical period
   - Handles three scenarios:
     - Parent unchanged: use base child rates only
     - Parent grown by 1: apply head child rates to base result
     - Parent grown >1: apply parent rates to head child result
   - **totalOwed = 1 + (loanAmount × compoundedInterest) / InterestRateDenom**

### 2. **Collateral Adjustment Path (INPUTS(0) == SELF)**
   - User rebalances collateral via DEX pool (data input)
   - Extracts DEX reserves and fee from pool box
   - **Calculates collateral value via AMM formula:**
     ```
     collateralValue = (dexReserveToken × inputAmount × dexFee) / 
                       ((dexReserveErg + slippage) × DexLpTaxDenom + inputAmount × dexFee)
     ```
   - **Validates:**
     - Successor box retains same script, borrow tokens, and all registers
     - `collateralValue > totalOwed × liquidationThreshold / LiquidationThresholdDenom`
     - Successor has minimum 3 boxes worth of value + network fee
     - Interest index boxes are authentic and current
   - **Authorization:** `proveDlog(currentUserPk)` with sigma proposition combining all validations

### 3. **Repayment Path (INPUTS(1) == SELF)**
   - Borrower repays loan and receives collateral refund
   - **Validates:**
     - `OUTPUTS(0)` is borrower's address receiving ERG ≥ currentValue - MinimumTransactionFee
     - `OUTPUTS(1)` is repayment box with script hash == `RepaymentContractScript`
     - Repayment box contains borrow tokens (original record) and loan tokens (quantity > totalOwed)
     - Interest boxes are authentic and current
   - **Sub-branches on partial vs. full repayment:**
     - **Partial repay:** Successor collateral box created with same structure, reduced borrow token quantity
     - **Full repay:** Loan fully closed (borrow tokens burned or transferred)

### 4. **Liquidation Path**
   - Protocol initiates liquidation if collateral falls below threshold or forced liquidation flag is set
   - Swaps collateral through DEX pool to loan currency
   - **Validates:**
     - Liquidation proceeds exceed `totalOwed`
     - Liquidator penalty = proceeds × (PenaltyDenom - liquidationPenalty) / PenaltyDenom
     - DEX pool receives ERG collateral, sends loan tokens back
     - Interest box validations pass
     - Forced liquidation buffer consumed or forcedLiquidation flag checked

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Borrower's script (contract address) |
| **R5** | `(Int, Int)` | Interest indexes: (parentIndex, childIndex) — position in hierarchical rate tree |
| **R6** | `(Long, Long)` | (liquidationThreshold, liquidationPenalty) — collateral ratio requirement and penalty rate |
| **R7** | `Coll[Byte]` | DEX pool NFT identifier — authenticates AMM pool for pricing |
| **R8** | `GroupElement` | User's public key (Schnorr group element) — signed authorization for collateral adjustments |
| **R9** | `(Long, Long)` | (forcedLiquidation flag, liquidationBuffer