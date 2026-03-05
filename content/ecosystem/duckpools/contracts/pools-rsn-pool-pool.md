---
title: duckpools/lend-protocol-contracts — pool.md
description: "ErgoScript contract analysis: contracts/pools/RSN-POOL/pool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/RSN-POOL/pool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: RSN-POOL/pool.md

## Purpose

This contract manages a **lending pool** that facilitates deposits, withdrawals, and collateralized loans with dynamic interest accrual. It maintains invariants on lend token valuation, enforces tiered service fees, validates collateral liquidation, and preserves the pool's singleton state across transactions via a State NFT.

## Inputs / Outputs

### Inputs
- **SELF**: Current pool Box containing:
  - Pool State NFT (tokens(0))
  - Lend tokens (tokens(1))
  - Borrow tokens (tokens(2))
  - Pooled assets (tokens(3))
  - ERG value and registers for pool state

- **Data Inputs** (context-dependent, up to 4):
  - Service Parameter Box (optional, R8 contains service fee script)
  - Collateral Box (in loan scenarios, holds borrowed tokens + collateral details)
  - DEX Pool Box (for price feed / liquidation pricing)
  - Parent Interest History Box
  - Child Interest History Box
  - Parameter Box (liquidation thresholds, collateral asset IDs, penalties)

### Outputs
- **OUTPUTS(0)**: Successor pool Box (must preserve script, NFT, minimum value)
- **OUTPUTS(1)**: 
  - Service fee recipient (in exchange/loan operations)
  - Collateral box (in loan scenarios)
- Additional boxes as transaction context requires

## Key Logic

### Universal Invariants (All Spending Paths)
1. **Script Preservation**: `successorScript == currentScript` — pool contract remains unchanged
2. **Pool NFT Preserved**: Singleton State NFT ensures single authoritative pool state
3. **Minimum Box Value**: `successorPoolValue >= MinimumBoxValue` (1,000,000 nanoERG)
4. **Token ID Preservation**: Lend, borrow, and pooled asset token IDs remain constant

### Exchange Operation (`isValidExchange`)
Allows LP token holders to exchange lend tokens for pool assets with price protection:

1. **Borrow Tokens Unchanged**: No new debt is created/destroyed
2. **Lend Token Value Maintained**: 
   - Current value: `(pooledAssets + totalBorrowed) / circulatingLendTokens` (scaled by `LendTokenMultiplier`)
   - Successor value must be **strictly greater** (prevents LP token value dilution)
3. **Service Fee Validation** (tiered):
   - If change ≤ 400,000 units: fee = change / 160
   - If change ≤ 4,000,000 units: fee = (change - 400,000) / 200 + 400,000 / 160
   - Otherwise: fee = (change - 4,400,000) / 250 + 4,000,000 / 200 + 400,000 / 160
   - Fee box must receive fee tokens and match service script from parameter box

### Deposit Operation (`isValidDeposit`)
Allows depositing pooled assets to mint new lend tokens:

1. **Lend Tokens Unchanged**: No LP tokens minted/burned (handled off-chain)
2. **Assets Increasing**: `deltaAssetsInPool > 0`
3. **Borrow Tokens Decrease**: `deltaTotalBorrowed < 0` (adds repaid borrow tokens back to pool)
4. **No Service Fee**: Deposits are not penalized

### Loan & Liquidation Logic (Conditional on `CONTEXT.dataInputs.size > 1`)
Complex collateral-backed lending with interest accrual:

1. **Collateral Validation**:
   - Collateral box holds borrowed tokens (`tokens(0)`)
   - Registers R4–R9 encode ownership, interest indices, liquidation thresholds, DEX oracle reference

2. **Interest Accrual**:
   - Parent/Child interest history boxes (AVL tree-like structure) track cumulative rates
   - Interpolates historical interest via `collateralInterestIndexes`

3. **Liquidation Conditions**:
   - **Forced Liquidation** (`forcedLiquidation` in R9): Immediate liquidation allowed
   - **Buffer Liquidation** (`bufferLiquidation` in R9): Liquidation allowed if collateral health falls below threshold
   - DEX pool (from data input) provides price oracle for collateral ↔ pooled asset conversion

4. **Health Check**:
   - Validates loan-to-value against `liquidationThresholds` from parameter box
   - Applies `liquidationPenalties` if liquidated

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** (Collateral) | `Coll[Byte]` | Collateral owner identity (optional) |
| **R4** (Parameter) | `Coll[Long]` | Liquidation thresholds array |
| **R4** (Parent/Child) | `Coll[Long]` | Interest rate history (cumulative) |
| **R5** (Collateral) | `(Int, Int)` | Interest indices: (parentIndex, childIndex) |
| **R5** (Parameter) | `Coll[Coll[Byte]]` | Collateral asset token IDs |
| **R6** (Collateral) | `(Long, Long)` | Threshold & penalty pair for this loan |
| **R6** (Parameter) | `Coll[Coll[Byte]]` | DEX NFT IDs for price oracles |
| **R6** (Child) | `Int` | Child box index in interest history |
| **R7** (Collateral) | `Coll[Byte]` | DEX Pool NFT reference |
| **R8** (Collateral) | `GroupElement` | User public key (optional, for signature) |
| **R8** (Parameter) | `Coll[Byte]` | Service fee recipient script |
| **R9** (Collateral) | `(Long, Long)` | `(forcedLiquidation, bufferLiquidation)` flags |

---

## Tokens

| Token