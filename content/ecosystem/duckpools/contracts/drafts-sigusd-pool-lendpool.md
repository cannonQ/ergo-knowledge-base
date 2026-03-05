---
title: duckpools/lend-protocol-contracts — lendPool.md
description: "ErgoScript contract analysis: contracts/pools/drafts/SIGUSD-POOL/lendPool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/drafts/SIGUSD-POOL/lendPool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: SIGUSD-POOL lendPool

## Purpose

This contract manages a **lending pool** that enables collateralized borrowing and lending of SigmaUSD or similar assets on the Ergo blockchain. It validates three core operations: **exchanges** (swaps with fee collection), **deposits** (adding collateral), and **loans** (creating secured debt positions with interest accrual). The contract enforces invariants on token supplies, valuations, and collateralization ratios across state transitions.

---

## Inputs / Outputs

### Inputs
- **SELF (Box 0)**: The current pool box, containing:
  - Pool State NFT (Token 0)
  - Lend tokens in reserve (Token 1)
  - Borrow tokens in reserve (Token 2)
  - Pooled assets (Token 3)
  - ERG value (pool fees/reserves)

- **Data Inputs** (Context.dataInputs):
  - `dataInputs(0)`: Service parameter box (NFT-authenticated, provides fee configuration in R8)
  - `dataInputs(0-3)`: For loan operations—DEX pool, parent interest box, child interest box, parameter box (all NFT-authenticated)

### Outputs
- **Box 0 (successor)**: Updated pool box with same script and NFTs, reflecting state changes
- **Box 1**: 
  - For exchanges: Service fee collection box (receives assets)
  - For loans: Collateral box (secured debt position with registers)

---

## Key Logic

### 1. **Universal Invariants** (All Spending Paths)
```
- Successor script ≡ Current script (ErgoTree immutability)
- Pool State NFT preserved
- Pooled asset token ID unchanged
- Successor box value ≥ MinimumBoxValue (1 ERG)
- Lend token ID consistency maintained
```

### 2. **Exchange Operation** (`isValidExchange`)
**Triggered when**: Lend/borrow token quantities unchanged between SELF and successor.

**Validations**:
- Borrow tokens **completely unchanged** (`isBorrowTokensUnchanged`)
- Lend token **value monotonically increases**:
  ```
  successorLendTokenValue > currentLendTokenValue
  where LendTokenValue = (PooledAssets + TotalBorrowed) / CirculatingLendTokens
  ```
  This ensures LP token holders cannot be harmed by the transaction.
  
- **Service fee collected** via a parameter-authenticated fee box (Box 1):
  - Fee is tiered based on absolute asset delta:
    - ≤ 2,000 units: 1/160 fee ratio
    - ≤ 200,000 units: step-wise calculation (previous + (delta − 2,000) / 200)
    - > 200,000 units: three-tier accumulation (+ final delta / 250)
  - Fee box receives minimum 1 unit of pooled asset
  - Fee box script matches parameter box's R8 (scriptbytes authentication)
  - Parameter box has NFT `ParamaterBoxNft`

### 3. **Deposit Operation** (`isValidDeposit`)
**Triggered when**: Lend tokens **completely unchanged** AND assets increasing.

**Validations**:
- Pooled assets increase (`deltaAssetsInPool > 0`)
- Total borrowed decreases (borrow tokens added to reserve: `deltaTotalBorrowed < 0`)
- Borrow token ID maintained
- All universal invariants satisfied

### 4. **Loan Operation** (Multi-box Collateral Creation)
**Triggered when**: `CONTEXT.dataInputs.size > 1`

**Collateral Box (Output 1) Validation**:
- Script matches `CollateralContractScript` (constant)
- Tokens:
  - Token 0: Supplied collateral asset
  - Token 1: Borrow tokens (loan amount)
- **Registers**:
  - **R4**: Collateral owner PK (optional, if undefined → unclaimed position)
  - **R5**: `(parentInterestIndex, childInterestIndex)` — pointers to interest accrual trees
  - **R6**: `(liquidationThreshold, penalty)` — health factor limits
  - **R7**: DEX NFT (for price discovery)
  - **R8**: User public key (optional)
  - **R9**: Forced liquidation timestamp (Long)

**Interest Accrual Mechanism**:
- **Parent Interest Box** (dataInput 1): Contains `R4[Coll[Long]]` — cumulative interest history indexed by parent pointer
- **Child Interest Box** (dataInput 2): Contains `R4[Coll[Long]]` history + `R6[Int]` child index
- Interest is computed from historical rates, enabling non-interactive interest compound tracking

**DEX Integration**:
- DEX pool (dataInput 0) provides price feeds
- Token matching logic: If `dexTokens(3) == PoolNativeCurrencyId`, use tokens (3,2); else (2,3)
- DEX fee extracted from `R4[Int]`

**Collateral Validation** (from parameter box):
- Parameter box NFT: `ParamaterBoxNft`
- `R4[Coll[Long]]`: Liquidation thresholds per asset class
- `R5[Coll[Coll[Byte]]]`: Allowed collateral asset IDs
- `R6[Coll[Coll[Byte]]]`: Allowed DEX NFTs for price oracles

---

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** | `Coll[Byte]` (Collateral Box) | Collateral owner public key | Read |
| **R4** | `Coll[Long]` (Interest/Param Box) | Interest history or liquidation thresholds | Read |
| **R5** | `(Int, Int)` (Collateral Box) | Parent and child interest index pointers | Read |
| **R5** | `Coll[Coll[Byte]]` (Param