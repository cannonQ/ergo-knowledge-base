---
title: duckpools/lend-protocol-contracts — collateral.md
description: "ErgoScript contract analysis: contracts/pools/rsAda/collateral.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsAda/collateral.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: `collateral.md`

## Purpose

This contract manages **collateral boxes** in a lending protocol where borrowers deposit collateral (ERG) to secure loans denominated in a pool currency token. It validates two primary operations: **(1) collateral adjustments** where users can modify their collateral levels while maintaining liquidation safety thresholds, and **(2) loan repayment or liquidation** where loans are either repaid or positions are forcibly liquidated if collateral drops below threshold.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0) = SELF**: Collateral box being adjusted or spent
- **INPUTS(1) = SELF**: Collateral box undergoing repayment/liquidation

### Data Inputs (CONTEXT.dataInputs)
- **[0]** Base child interest box (tracks historical interest rates at loan origination index)
- **[1]** Parent interest box (tracks cumulative interest rate history for the pool)
- **[2]** Head child interest box (tracks interest since parent box last updated)
- **[3]** DEX box (Singleton NFT; provides ERG/token exchange rates for collateral valuation)

### Outputs

**For collateral adjustment (INPUTS(0) == SELF)**:
- **OUTPUTS(0)**: Successor collateral box (same script, updated ERG value)

**For repayment/liquidation (INPUTS(1) == SELF)**:
- **OUTPUTS(0)**: Borrower box or DEX box (destination for repayment proceeds)
- **OUTPUTS(1)**: Repayment box (script hash matches `RepaymentContractScript`; holds loan token repayment)
- **OUTPUTS(2+)**: Successor collateral boxes (if partial repayment)

---

## Key Logic

### 1. **Interest Calculation (Multi-Stage Compounding)**
The contract reconstructs the loan's interest burden by traversing three interest-rate history boxes:

```
compoundedInterest = baseChildRate × headChildRates × parentRates
```

- Slices each rate history from the loan's origination index to the current live index
- Compounds rates sequentially: `z = (z × rate) / InterestRateDenom`
- Derives `totalOwed = loanAmount × compoundedInterest / InterestRateDenom + 1`

**Why multi-stage?** The parent box grows over time; the base/head child boxes snapshot interest at specific epochs, avoiding re-calculation of historical rates.

### 2. **Collateral Adjustment Branch** (`INPUTS(0) == SELF`)

**Validation conditions:**
1. **Script continuity**: Successor must retain identical ErgoScript (`successorScript == currentScript`)
2. **Loan token retention**: Borrow token (identifying the loan) must remain unchanged
3. **Register preservation**: All loan metadata (borrower ID, indexes, thresholds, DEX NFT, user PK) immutable
4. **Collateral sufficiency**: 
   - Collateral value ≥ `totalOwed × liquidationThreshold / 1000`
   - Successor box ERG ≥ `3 × MinimumBoxValue + MinimumTransactionFee` (dust protection)
5. **DEX validation**: Data input DEX box must match expected DEX NFT
6. **Interest box validation**: All three interest boxes must have correct NFTs and indexes
7. **User authorization**: `proveDlog(currentUserPk)` signs the transaction

**Collateral valuation formula:**
```
collateralValue = (dexReservesToken × inputERG × dexFee) /
                  ((dexReservesERG × (1 + 2%)) × 1000 + inputERG × dexFee)
```
(Applies slippage and DEX fees to conservatively estimate token value)

### 3. **Repayment/Liquidation Branch** (`INPUTS(1) == SELF`)

Two sub-paths:

#### **Full Repayment Path**
- **Borrower box validation**: Script must be `currentBorrower` (borrower's address); value ≥ `currentValue - MinimumTransactionFee`
- **Repayment box validation**:
  - Script hash must match `RepaymentContractScript` (state machine transition)
  - Must contain loan tokens (borrow token) matching current loan ID
  - Must contain pool currency tokens in amount ≥ `totalOwed`
  - Value ≥ `MinimumBoxValue + MinimumTransactionFee`
- **Authorization**: No explicit user signature required (assumes repayment initiated by borrower or liquidator)

#### **Partial Repayment Path** (indicated by `OUTPUTS(0).tokens.size >= 1 && INPUTS(0).tokens.size < 3`)
- Successor collateral box created (updated registers and reduced collateral)
- Successor script, loan tokens, and core registers validated (similar to adjustment branch)
- Collateral sufficiency re-checked

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Borrower's address/script hash (identity of loan originator) |
| **R5** | `(Int, Int)` | Parent & child interest box indexes (pointers into interest history timeline) |
| **R6** | `(Long, Long)` | Liquidation threshold (denominator 1000) & penalty (unused in this contract) |
| **R7** | `Coll[Byte]` | DEX singleton NFT ID (reference to price oracle box) |
| **R8** | `GroupElement` | User's public key (for Sigma protocol signing in collateral adjustments) |
| **R9** | `(Long, Long)` | Forced liquidation flag & liquidation buffer (time-lock or safety threshold) |

---

## Tokens

### **NFTs (Singleton State Tokens)**

| Token | ID Constant | Role |
|-------|-------------|------|
| **Child Interest NFT** | `ChildInterestNft` | Identifies interest rate history snapshots at loan origination and pool head |
| **Parent Interest NFT** | `ParentInterestN