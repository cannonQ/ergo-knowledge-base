---
title: duckpools/lend-protocol-contracts — collateral.md
description: "ErgoScript contract analysis: contracts/pools/RSN-POOL/collateral.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/RSN-POOL/collateral.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Collateral Management (RSN-POOL)

## Purpose

This contract manages collateral boxes in a lending protocol, enforcing loan-backed collateral requirements and enabling two primary operations: collateral adjustments (when users deposit/withdraw collateral) and loan repayment/liquidation (when loans are settled). It validates interest accrual across a hierarchical interest rate structure and ensures collateral value remains above liquidation thresholds.

## Inputs / Outputs

### Inputs
- **INPUTS(0) = SELF** (Collateral adjustment path):
  - Current collateral box with ERG and borrow tokens
  - Outputs successor collateral box with modified collateral value
  
- **INPUTS(1) = SELF** (Repayment/Liquidation path):
  - Current collateral box being repaid/liquidated
  - Outputs borrower box and repayment box (or DEX box in liquidation)

### Outputs
- **Collateral Adjustment**: 
  - OUTPUTS(0): Successor collateral box (same script, modified ERG value)
  
- **Repayment/Liquidation**:
  - OUTPUTS(0): Borrower's destination box OR DEX swap box
  - OUTPUTS(1): Repayment box (contains loan tokens for settlement)
  - Additional outputs for state machine continuation or liquidation proceeds

### Data Inputs
- **CONTEXT.dataInputs(0)**: Base child interest rate box (ChildInterestNft, indexed at `parentIndex`)
- **CONTEXT.dataInputs(1)**: Parent interest rate box (ParentInterestNft, contains full rate history)
- **CONTEXT.dataInputs(2)**: Head child interest rate box (ChildInterestNft at current parent size)
- **CONTEXT.dataInputs(3)**: DEX liquidity pool box (for collateral value pricing)

## Key Logic

### Interest Accrual Calculation
1. Scans **base child** rate history from `childIndex` to present, computing compounded interest via fold:
   ```
   compoundedInterest = initialRate * rate[i] / denominator (iteratively)
   ```
2. If parent index has advanced, incorporates **head child** rates (new generation added).
3. If parent index advanced beyond +1, includes **parent** historical rates.
4. **Total owed** = `loanAmount * compoundedInterest / InterestRateDenom` (with +1 rounding buffer).

### Collateral Adjustment Branch (INPUTS(0) == SELF)
**Validation conditions** (all must pass):
- Successor box uses **identical script** (same contract)
- **Borrow tokens retained** (same NFT/amount)
- **All registers preserved** (borrower, indexes, thresholds, DEX NFT, user pubkey, liquidation flags)
- **DEX box validated** (NFT matches `currentDexNft`)
- **Collateral sufficiency**: 
  ```
  collateralValue > totalOwed * liquidationThreshold / 1000
  successor.value >= 3M ERG + 1M ERG (minimum box values + network fee)
  ```
- **Interest rate box chain validated** (child NFTs, parent NFT, index continuity)
- **User signs** via `proveDlog(currentUserPk)`

**Collateral value** computed from DEX swap simulation:
```
collateralValue = (dexReserves_token * inputAmount * dexFee) / 
                  ((dexReserves_erg + slippage) * 1000 + (inputAmount * dexFee))
```

### Repayment/Liquidation Branch (INPUTS(1) == SELF)
**Two sub-branches** based on output configuration:

#### Full Repayment
- Borrower box: receives entire collateral (`borrowerValue >= currentValue - 1M`)
- Repayment box: receives loan tokens to settle debt
- **Validation**:
  - Repayment script matches `blake2b256(RepaymentContractScript)`
  - Loan tokens (`PoolCurrencyId`) amount > `totalOwed`
  - Repayment box value >= 1M + 1M
  - Borrow tokens (loan record) transferred to repayment box
  - Interest rate boxes validated

#### Partial Repayment / Liquidation
- Successor collateral box created (OUTPUTS(0)) OR DEX liquidation box
- Reduces borrow token amount proportionally
- Validates new collateral still exceeds threshold
- Liquidation applies **penalty** to interest calculation if triggered (`currentForcedLiquidation == 1`)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Borrower script hash (destination for repayment) |
| **R5** | `(Int, Int)` | Indexes: (parentIndex, childIndex) — pointers into interest rate history |
| **R6** | `(Long, Long)` | (liquidationThreshold, liquidationPenalty) — ratio/1000 denominated |
| **R7** | `Coll[Byte]` | DEX pool NFT ID (for collateral pricing) |
| **R8** | `GroupElement` | User's public key (Sigma protocol commitment for signing) |
| **R9** | `(Long, Long)` | (forcedLiquidation flag, liquidationBuffer) — state machine signals |

## Tokens

### NFTs (Singleton State Tokens)
- **ChildInterestNft** (`DWvuhYpDdvP322QqyUdNKAgT79VjbzN1yoM3QCWEbRuF`):
  - Multiple instances in child interest boxes
  - Each holds rate history slice (R4 = `Coll[Long]` interest rates)
  - Index tracked in R6
  
- **ParentInterestNft** (`TsBqrGRa3m743ZKZyNws8oqyjdXTm1yWBP79b9ojvd9`):
  - Single parent box tracking cumulative rate history
  - Used as