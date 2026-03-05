---
title: duckpools/lend-protocol-contracts — lendPool.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/lendPool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/lendPool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Lend Pool

## Purpose

This contract manages a lending pool that accepts deposits of ERG and other assets, issues LP tokens (lend tokens) to depositors, and facilitates borrowing against collateral. It enforces invariants on token valuations, collects tiered service fees, and validates loan origination with collateral assessment and liquidation mechanics.

---

## Inputs / Outputs

### Inputs
- **SELF** (Input 0): The current pool box, containing:
  - ERG value (pooled assets)
  - Three native tokens: Pool NFT (singleton), Lend tokens, Borrow tokens

- **Data Inputs** (variable count depending on operation):
  - **For exchange/deposit only**: Service parameter box (holds fee configuration)
  - **For loan origination**: 
    - Dex pool box (for collateral price discovery)
    - Parent interest index box
    - Child interest index box
    - Parameter box (collateral settings)

### Outputs
- **Output 0**: Successor pool box (must preserve script, NFT, and token IDs)
- **Output 1**: 
  - For exchange/deposit: Service fee recipient box
  - For loan: Collateral/user box with loan state

---

## Key Logic

### Universal Validations (All Spending Paths)
1. **Script preservation**: Successor box must have identical ErgoTree
2. **Pool NFT invariant**: Singleton token must be preserved (prevents pool duplication)
3. **Token ID persistence**: Lend and borrow token IDs cannot change
4. **Minimum box value**: Successor ≥ 1 ERG (relaxed if assets increasing)

### Lend Token Valuation Invariant
```
LendTokenValue = LendTokenMultiplier × (PooledAssets + TotalBorrowed) / CirculatingLendTokens
```
- **Critical constraint**: `successorLendTokenValue > currentLendTokenValue`
- Prevents LP token devaluation; inflation only increases value
- Ensures deposits/repayments benefit all holders

### Exchange Operation (Deposit/Withdrawal)
- Assets must increase (`deltaAssetsInPool > 0`)
- Borrow tokens unchanged (no repayment here)
- **Tiered service fee validation**:
  - ≤ 20 ERG: 1/160 (0.625%)
  - 20–200 ERG: 1/200 (0.5%) on excess + step one fee
  - > 200 ERG: 1/250 (0.4%) on excess + prior tiers
  - Fee box must match script from parameter box and hold ≥ calculated fee

### Deposit Operation
- Lend tokens must be **unchanged** (no minting/burning)
- Assets increase, borrow tokens return to pool
- Repayment of borrowed assets

### Loan Origination (When `dataInputs.size > 1`)
1. **Collateral validation**:
   - Queries external Dex pool (data input) for collateral/ERG price
   - Validates collateral asset matches parameter box registry
   
2. **Loan-to-value (LTV) checks**:
   - Compares loan size vs. collateral market value with liquidation threshold
   - Applies liquidation penalty multiplier
   - Two liquidation triggers: forced (immediate shortfall) and buffer (safety margin)

3. **Interest accrual**:
   - Reads parent/child interest index boxes to compute accrued interest
   - Applies interest to loan amount before collateral validation

4. **Borrow token accounting**:
   - Reduces circulating borrow tokens (mints new loans)
   - Updates total borrowed in pool state

---

## Registers Used

| Register | Type | Purpose | Used In |
|----------|------|---------|---------|
| **R4** | `Coll[Byte]` (Collateral box) | Owner identity (optional) | Loan |
| **R4** | `Coll[Long]` (Parent/Child/Param boxes) | Interest history / Thresholds | Loan interest & collateral config |
| **R5** | `(Int, Int)` (Collateral box) | Parent & child interest indexes | Loan interest accrual |
| **R5** | `Coll[Coll[Byte]]` (Param box) | Collateral asset IDs | Collateral validation |
| **R6** | `(Long, Long)` (Collateral box) | Threshold penalty & duration | Liquidation mechanics |
| **R6** | `Coll[Coll[Byte]]` (Param box) | Dex NFT registry | Price oracle mapping |
| **R6** | `Int` (Child box) | Child index pointer | Interest lookup |
| **R7** | `Coll[Byte]` (Collateral box) | Dex NFT identifier | Price discovery |
| **R7** | `Coll[Long]` (Param box) | Liquidation penalties | Collateral haircut |
| **R8** | `Coll[Byte]` (Service param box) | Fee recipient script | Service fee routing |
| **R8** | `GroupElement` (Collateral box) | User public key (optional) | Loan ownership |
| **R9** | `(Long, Long)` (Collateral box) | Forced & buffer liquidation thresholds | Liquidation trigger logic |

---

## Tokens

### Native Token Types
1. **Pool NFT** (Token 0, SELF):
   - Singleton identifying the active pool
   - Preserved in all successor boxes
   - Prevents multiple concurrent pools

2. **Lend Tokens** (Token 1, SELF):
   - LP tokens issued to depositors
   - Max supply: 9,000,000,001 (genesis value = 1)
   - Circulating: `MaxLendTokens - reserved`
   - ID must remain constant; quantity changes on deposit/withdrawal

3. **Borrow Tokens** (Token 2, SELF):
   - Represents outstanding loans
   - Max supply: 9,000,000,000
   - Circulating: `MaxBorrowTokens - reserved`
   -