---
title: duckpools/lend-protocol-contracts — pool.md
description: "ErgoScript contract analysis: contracts/pools/SIGRSV-POOL/pool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/SIGRSV-POOL/pool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: SIGRSV-POOL

## Purpose

This contract implements a **lending pool state machine** for the duckpools protocol, managing deposits, borrows, and liquidations of collateralized loans. It validates all transitions of the pool's singleton state box (identified by Pool NFT), ensuring the invariant that lend token value never decreases and borrowed assets remain properly backed by collateral.

## Inputs / Outputs

### Inputs
- **SELF** (Spending input): The current pool box containing:
  - ERG value + protocol fees
  - Token[0]: Pool singleton NFT (PoolBoxNft)
  - Token[1]: Lend tokens (liquidity provider shares)
  - Token[2]: Borrow tokens (tracks total borrowed amount)
  - Token[3]: Pooled asset tokens (underlying collateral asset)

- **Data Inputs** (Context-dependent, read-only):
  - Service parameter box (NFT: `ParamaterBoxNft`, provides fee script in R8)
  - Dex pool box (for price discovery on liquidations)
  - Parent interest box (tracks cumulative interest history)
  - Child interest box (tracks periodic interest snapshots)
  - Parameter box (stores liquidation thresholds, penalties, collateral asset IDs)
  - Additional collateral boxes (for loan repayment/liquidation validation)

### Outputs
- **OUTPUTS(0)**: Successor pool box (same structure, updated state)
- **OUTPUTS(1)**: Service fee box OR collateral management box (operation-dependent)
- Additional outputs for loan operations (collateral state transitions)

## Key Logic

### Core Invariants (All Operations)
1. **Script Preservation**: `successorScript == currentScript` — Pool contract code immutable
2. **NFT Singleton**: Pool NFT in output[0] matches input NFT
3. **Minimum Value**: Successor pool holds ≥ 1,000,000 nanoERG
4. **Pooled Asset ID**: Underlying collateral token ID unchanged

### Lend Token Valuation (Critical)
```
LendTokenValue = (PooledAssets + TotalBorrowed) * LendTokenMultiplier 
                 / LendTokensCirculating
```
- **Invariant**: `successorLendTokenValue ≥ currentLendTokenValue`
- Prevents LP token dilution; enforces interest accrual or fee collection
- Uses `BigInt` arithmetic to avoid overflow with 18-decimal scaling

### Operation: **Exchange** (Swap/Add-Remove Liquidity)
**Validates**:
- Borrow tokens unchanged (`isBorrowTokensUnchanged`)
- Lend token value maintained
- Service fee collected:
  - **Tiered fee structure**:
    - ≤ 200,000 tokens: 1/160 (0.625%)
    - ≤ 2,000,000 tokens: 1/200 (0.5%) on delta + tier 1 on base
    - > 2,000,000 tokens: 1/250 (0.4%) on delta + prior tiers
  - Fee box must receive `totalServiceFee` of pooled assets
  - Fee box script must match parameter box R8
- Service parameter box must hold `ParamaterBoxNft`

**Calculation**:
```scala
deltaAssetsInPool = successorPooledAssets - currentPooledAssets
// Tiered fee applied to absolute delta
```

### Operation: **Deposit** (Add Collateral)
**Validates**:
- Lend tokens locked (`isLendTokensUnchanged`)
- Assets in pool increase (`deltaAssetsInPool > 0`)
- Borrow tokens decrease (`deltaTotalBorrowed < 0`) — deposits add borrow tokens to reserve
- Pool value ≥ minimum

### Operation: **Loan Management** (Borrow/Repay/Liquidate)
**Requires data inputs**:
- Collateral box (output[1]) with:
  - R4: Owner PK (optional)
  - R5: Interest indexes `(parentIndex, childIndex)` — pointers into interest history
  - R6: Threshold penalty tuple `(liquidationThreshold, penalty)`
  - R7: Dex pool NFT for price discovery
  - R8: User public key (optional)
  - R9: Liquidation buffer tuple `(forcedLiquidation, bufferLiquidation)`
- Dex pool box (read-only) for exchange rate
- Parent/child interest boxes for accrued interest calculation
- Parameter box specifying:
  - R4: Liquidation thresholds per asset
  - R5: Collateral asset IDs
  - R6: Dex NFTs
  - R7: Liquidation penalties
  - R8: Service fee address

**Liquidation Logic** (inferred from structure):
- Collateral value checked against `collateralDexNft` on dex
- Interest accrued via `childInterestHistory[childIndex]`
- Liquidation triggered if: `(borrowedValue * (1000 + threshold)) / 1000 > collateralValue`
- `forcedLiquidationBuffer` (500,000) and `defaultBuffer` (100,000,000) applied to LTV calculations

---

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** (Collateral) | `Coll[Byte]` (Owner) | Identifies loan owner for authorization | Read |
| **R5** (Collateral) | `(Int, Int)` | Interest index pointers: (parentIndex, childIndex) for historical interest lookups | Read |
| **R6** (Collateral) | `(Long, Long)` | `(liquidationThreshold, penalty)` — LTV ratio and liquidation fee | Read |
| **R7** (Collateral) | `Coll[Byte]` | Dex pool NFT for price discovery on liquidations | Read |
| **R8** (Collateral) | `GroupElement` (User PK) | User signature key (optional) | Read |
| **R8** (Parameter) | `