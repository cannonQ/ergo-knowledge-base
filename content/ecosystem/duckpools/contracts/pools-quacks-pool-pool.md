---
title: duckpools/lend-protocol-contracts — pool.md
description: "ErgoScript contract analysis: contracts/pools/QUACKS-POOL/pool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/QUACKS-POOL/pool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: QUACKS-POOL

## Purpose

This is a **lending pool smart contract** that manages deposits, borrows, and liquidations in a decentralized finance (DeFi) protocol. It maintains invariants on lend token valuation, processes multi-step exchanges and deposits, enforces service fees via tiered structures, and orchestrates collateral liquidations through complex interest index calculations and DEX price oracles.

---

## Inputs / Outputs

### Inputs
- **SELF (Primary Input)**: The current pool Box, containing:
  - Pool state NFT (singleton, token index 0)
  - Lend token supply tracking (token index 1)
  - Borrow token supply tracking (token index 2)
  - Pooled collateral assets (token index 3)
  - ERG value (liquidity reserves)

- **Data Inputs** (optional, context-dependent):
  - Service Parameter Box: Contains fee configuration and service recipient script (R8)
  - DEX Pool Box: Oracle data for collateral pricing (reserves, fee tier in R4)
  - Parent Interest Box: Historical interest rates for parent loan cohort (R4)
  - Child Interest Box: Historical interest rates for child loan cohort (R4, R6)
  - Parameter Box: Liquidation thresholds, collateral asset IDs, DEX NFTs (R4-R7)

### Outputs
- **Output 0 (Successor Pool Box)**: Updated pool state with same script, NFT, and asset structure
- **Output 1 (Conditional)**:
  - **If exchange/deposit**: Service fee recipient Box (receives tiered service fee)
  - **If collateral action**: Updated collateral Box or liquidation proceeds Box

---

## Key Logic

### 1. **Pool State Machine Invariants**

All spending paths enforce:
- **Script preservation**: `successorScript == currentScript` (eUTXO state continuity)
- **Pool NFT singleton**: `successorPoolNft == currentPoolNft` (prevents pool duplication)
- **Minimum box value**: `successorPoolValue >= 1,000,000` ergs (storage rent requirement)
- **Pooled asset token ID preservation**: `successorPooledTokens._1 == currentPooledTokens._1`

### 2. **Lend Token Valuation (Core Invariant)**

```
Lend Token Value = LendTokenMultiplier × (PooledAssets + TotalBorrowed) / LendTokensCirculating

where:
  - CurrentLendTokensCirculating = 9,000,000,000,000,010 - ReserveSupply
  - CurrentTotalBorrowed = 9,000,000,000,000,000 - BorrowTokensReserve
  - LendTokenMultiplier = 10^15 (fixed-point precision)
```

**Enforcement**: `successorLendTokenValue > currentLendTokenValue`  
This ensures LP tokens appreciate or maintain value; prevents dilution attacks.

### 3. **Exchange Operation (Swap Liquidity)**

**Preconditions**:
- Borrow tokens unchanged: `successorBorrowTokens == currentBorrowTokens`
- Lend token value maintained
- Service fee validated and routed

**Logic**: Allows arbitrary asset swaps in/out of the pool, updating pooled asset quantities while preserving token supply invariants.

### 4. **Deposit Operation**

**Preconditions**:
- Lend tokens fully preserved: `successorLendTokens == currentLendTokens`
- Pooled assets increase: `deltaAssetsInPool > 0`
- Total borrowed decreases: `deltaTotalBorrowed < 0` (borrow tokens added back to reserve)

**Logic**: Enables liquidity providers to add collateral; reduces outstanding loan supply.

### 5. **Service Fee Tiering**

Collected when `|ΔPooledAssets| > 0`. Three-tier structure based on asset change magnitude:

| Tier | Asset Range | Fee Rate |
|------|------------|----------|
| 1 | ≤ 2,000 | 1/160 (0.625%) |
| 2 | 2,000–200,000 | 1/200 (0.5%) |
| 3 | > 200,000 | 1/250 (0.4%) |

**Validation**:
- Service fee box script matches parameter box specification (R8)
- Fee tokens ≥ calculated total
- Tokens use pooled asset ID
- Minimum box value maintained

### 6. **Collateral Liquidation (Complex Path)**

When `CONTEXT.dataInputs.size > 1`:

- **Reads collateral box** (Output 1):
  - R4: Collateral owner (optional)
  - R5: Interest indexes (parent, child)
  - R6: Threshold penalty tuple
  - R7: DEX NFT for price oracle
  - R8: User public key (optional)
  - R9: Liquidation buffer tuple `(forcedBuffer, defaultBuffer)`

- **Computes liquidation health**:
  - Accrues interest from parent/child interest boxes
  - Fetches DEX reserves to calculate collateral price
  - Determines if `(LoanAmount × AccruedInterest) / CollateralValue > LiquidationThreshold`

- **Enforces liquidation penalty**:
  - If threshold breached, penalty applies (tiered by collateral type)
  - Forced liquidation uses `forcedLiquidationBuffer` (500,000)
  - Default uses `defaultBuffer` (100,000,000)

- **Validates parameter box**:
  - NFT matches `ParamaterBoxNft` singleton
  - Collateral asset IDs must be in whitelist (R5)
  - DEX oracle NFTs must match whitelist (R6)

---

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| R4 | `Coll[Byte]` (Collateral) | Collateral owner PK | Read |
| R4 | `Coll[Long]` (Parameter Box) | Liquidation threshold array