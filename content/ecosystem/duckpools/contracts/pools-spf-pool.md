---
title: duckpools/lend-protocol-contracts — pool.md
description: "ErgoScript contract analysis: contracts/pools/spf/pool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/spf/pool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Duck Pools Lending Protocol – Pool Box

## Purpose

This contract manages a **lending pool box** in a decentralized lending protocol, maintaining the core state machine for deposits, withdrawals, and loan facilitation. It enforces invariants on pool collateral, lend/borrow token supplies, and service fee collection, while ensuring the lend token value never decreases across state transitions.

---

## Inputs / Outputs

### Inputs
- **SELF** (Pool Box): The current pool state box, containing:
  - Native ERG value (`value`)
  - **Token 0**: Pool State NFT (Singleton / State NFT)
  - **Token 1**: Lend tokens (minted by pool, representing LP shares)
  - **Token 2**: Borrow tokens (supply tracking, always MaxBorrowTokens - circulating)
  - **Token 3**: Pooled assets (the underlying collateral token)

- **CONTEXT.dataInputs**: Read-only boxes providing:
  - Service parameter box (contains fee script in R8, identified by `ParamaterBoxNft`)
  - Collateral box (when processing loans; identifies borrower collateral)
  - DEX pool box (for price discovery on liquidations)
  - Parent/Child interest index boxes (for accrued interest tracking)
  - Parameter box (liquidation thresholds, collateral asset IDs, DEX NFTs)

### Outputs
- **OUTPUTS(0)**: Successor pool box (must preserve script, NFT, and state invariants)
- **OUTPUTS(1)**: 
  - Service fee box (for exchange operations) – receives accumulated protocol fees
  - Collateral box (for loan operations) – updated loan state

---

## Key Logic

### Core Invariants (All Spending Paths)
1. **Script Preservation**: `successorScript == currentScript` (eUTXO pattern)
2. **State NFT Preservation**: Pool Singleton NFT must remain in output(0)
3. **Minimum Box Value**: `successorPoolValue >= MinimumBoxValue` (storage rent)
4. **Pooled Asset Preservation**: Token ID of pooled assets unchanged
5. **Lend Token Value Monotonicity**: 
   ```
   successorLendTokenValue > currentLendTokenValue
   ```
   Where: `LendTokenValue = (PooledAssets + TotalBorrowed) / LendTokensCirculating * Multiplier`
   - Ensures LP token value never decreases (protection against MEV/slippage attacks)

### Exchange Operation (Liquidity Provider Swaps)
- Validates **service fee collection** from a dedicated fee box (OUTPUTS(1))
- **Tiered fee structure** based on asset delta:
  - `≤ 5e9`: 1/160 (0.625%)
  - `≤ 5e10`: (excess at 1/200) + (first at 1/160)
  - `> 5e10`: (excess at 1/250) + (middle at 1/200) + (first at 1/160)
- Requires `ParamaterBoxNft` in data inputs to authorize fee recipient script
- Condition: `isBorrowTokensUnchanged` (borrow supply static during swaps)

### Deposit Operation
- Assets flow **into** pool: `deltaAssetsInPool > 0`
- Borrow tokens decrease (added to pool): `deltaTotalBorrowed < 0`
- Lend tokens **unchanged** (no new LP shares minted; deposit is bridge operation)
- No service fee required

### Loan Processing (Collateral Box Logic)
- Reads collateral box with borrow tokens (`OUTPUTS(1)` when `CONTEXT.dataInputs.size > 1`)
- Tracks collateral owner (R4), interest indices (R5), liquidation thresholds (R6), DEX NFT (R7), user pubkey (R8)
- Accesses **three interest boxes** (parent + child hierarchy) for index compounding
- Validates liquidation eligibility via **forced liquidation timestamp** (R9._1) and **buffer** (R9._2)
- Enforces minimum loan value: `MinLoanValue = 50e6` (50 ERG)

---

## Registers Used

### Pool Box (SELF) – Read Only
- **R0–R3**: Implicit (value, tokens, script)
- **R4–R9**: Unused

### Collateral Box (OUTPUTS(1) during loans)
- **R4**: `Coll[Byte]` – Collateral owner (Optional)
- **R5**: `(Int, Int)` – Interest index pair: `(parentIndex, childIndex)`
- **R6**: `(Long, Long)` – Liquidation threshold & penalty multiplier
- **R7**: `Coll[Byte]` – DEX NFT ID (for price discovery)
- **R8**: `GroupElement` – User Sigma pubkey (Optional)
- **R9**: `(Long, Long)` – `(forcedLiquidationTimestamp, bufferTime)`

### Service Parameter Box (CONTEXT.dataInputs(0) for exchange)
- **R8**: `Coll[Byte]` – Authorized fee recipient script

### Interest Index Boxes (Parent/Child)
- **R4**: `Coll[Long]` – Interest history array (compounding history)
- **R6**: `Int` – Index pointer (child box only)

### Parameter Box (CONTEXT.dataInputs(3) for loans)
- **R4**: `Coll[Long]` – Liquidation thresholds per collateral type
- **R5**: `Coll[Coll[Byte]]` – Authorized collateral asset IDs
- **R6**: `Coll[Coll[Byte]]` – Authorized DEX NFT IDs
- **R7**: `Coll[Long]` – Liquidation penalty percentages

---

## Tokens

### Native Tokens Used

| Token | Role | Quantity | Notes |
|-------|------|----------|-------|
| **Pool State NFT** (Token 0) | Singleton identifier | 1 (immutable) | Ensures single active pool;