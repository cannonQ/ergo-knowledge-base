---
title: duckpools/lend-protocol-contracts — collateral.md
description: "ErgoScript contract analysis: contracts/pools/rsbtc/collateral.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsbtc/collateral.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Collateral Box (duckpools/lend-protocol-contracts)

## Purpose

This contract manages collateral boxes in a lending protocol, enforcing the maintenance of sufficient collateral to back borrowed funds while calculating compound interest across a multi-tier interest rate index structure. It enables two primary operations: collateral adjustments (when users modify their collateral positions) and loan repayment/liquidation (when loans are settled or liquidated due to insufficient collateral).

## Inputs / Outputs

### Inputs
- **INPUTS(0) = SELF** (Collateral Adjustment Branch):
  - Current collateral box containing ERG reserves and state
  - Produces successor collateral box (OUTPUTS(0)) with updated collateral amount
  
- **INPUTS(1) = SELF** (Repayment/Liquidation Branch):
  - Current collateral box being spent for loan settlement
  - Produces borrower's box (OUTPUTS(0)) and repayment box (OUTPUTS(1))

### Data Inputs
- **CONTEXT.dataInputs(0)**: Base child interest box (read-only, contains child interest rate history)
- **CONTEXT.dataInputs(1)**: Parent interest box (read-only, contains parent interest rate history)
- **CONTEXT.dataInputs(2)**: Head child interest box (read-only, points to latest interest rate snapshot)
- **CONTEXT.dataInputs(3)**: DEX pool box (read-only, used for ERG-to-collateral token price discovery)

### Outputs
**Collateral Adjustment Branch:**
- OUTPUTS(0): Successor collateral box (same contract, updated collateral value)

**Repayment/Liquidation Branch:**
- OUTPUTS(0): Borrower's box (receives remaining collateral if partial repay; DEX box if full liquidation)
- OUTPUTS(1): Repayment box (sends to RepaymentContractScript with loan tokens and borrow token proof)

## Key Logic

### 1. **Interest Calculation (Multi-Tier Compounding)**
```
baseChildCompoundedInterest = fold(rates[childIndex:], 1.0, (z, base) => z * base / 10^8)
If parent index unchanged:
  totalCompoundedInterest = baseChildCompoundedInterest
Else if parent index advanced by 1:
  Apply headChildRates, then multiply by baseChildCompoundedInterest
Else (parent index advanced >1):
  Apply headChildRates, then parentRates[parentIndex+1:], then baseChild compound
totalOwed = loanAmount * compoundedInterest / 10^8 + 1
```

### 2. **Collateral Adjustment Validation**
- Successor box retains **same contract script** (state machine invariant)
- Borrow tokens (loan record) must **remain unchanged**
- All registers (R4-R9) must **remain unchanged** except collateral (value)
- **Liquidation threshold check**: `collateralValue > totalOwed * liquidationThreshold / 1000`
- Successor must hold **minimum reserves**: `value ≥ 3 * MinimumBoxValue + MinimumTransactionFee`
- **Authorization**: `proveDlog(userPublicKey)` required

### 3. **Repayment/Liquidation Validation**

**Full Repayment Path:**
- Borrower receives all remaining collateral: `borrowerValue ≥ currentValue - MinimumTransactionFee`
- Repayment box must send to `blake2b256(repaymentScript) == RepaymentContractScript`
- Repayment box must contain ≥ `totalOwed` of PoolCurrencyId tokens
- Borrow token record transferred to repayment box (proof of loan)

**Partial Repayment Path:**
- Successor collateral box created (OUTPUTS(0)) with reduced borrow tokens
- Successor maintains liquidation threshold: `collateralValue' > totalOwed' * threshold / 1000`
- Repayment box (OUTPUTS(1)) receives partial PoolCurrencyId repayment

**Liquidation Path:**
- Triggered if `OUTPUTS(0) == INPUTS(0)` (DEX output for collateral sale)
- DEX output must have ≥ 2 tokens (reserves), collateral box < 3 tokens
- Borrower receives proceeds after DEX execution

### 4. **Interest Box Validation**
- **Base Child**: NFT = `ChildInterestNft`, index = `parentIndex`
- **Parent**: NFT = `ParentInterestNft`
- **Head Child**: NFT = `ChildInterestNft`, index = `parentInterestRates.size` (latest)

All interest boxes must be **read-only data inputs** (immutable during transaction).

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **Borrower's address** – script hash of original borrower |
| **R5** | `(Int, Int)` | **Interest rate indexes** – `(parentIndex, childIndex)` pointing into parent/child interest rate histories |
| **R6** | `(Long, Long)` | **Threshold & Penalty** – `(liquidationThreshold, liquidationPenalty)` in basis points (denom 1000) |
| **R7** | `Coll[Byte]` | **DEX NFT ID** – identifies the Spectrum/DEX pool for price discovery |
| **R8** | `GroupElement` | **User Public Key** – Sigma protocol group element for `proveDlog` authorization |
| **R9** | `(Long, Long)` | **Liquidation Parameters** – `(forcedLiquidationBlock, liquidationBuffer)` controlling when automatic liquidation is triggered |

---

## Tokens

### Primary Tokens

| Token ID | Purpose | Count | Held In |
|----------|---------|-------|---------|
| **PoolCurrencyId** (constant) | Loan denomination – amount borrowed and repaid in this token | Variable | Repayment box (OUTPUTS(1)) |
| **currentBorrowTokens