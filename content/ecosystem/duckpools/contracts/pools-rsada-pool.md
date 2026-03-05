---
title: duckpools/lend-protocol-contracts — pool.md
description: "ErgoScript contract analysis: contracts/pools/rsAda/pool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsAda/pool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: DuckPools Lend Protocol – Pool Contract

## Purpose

This contract manages a **lending pool state machine** in the DuckPools protocol, acting as the central hub for depositing collateral assets, borrowing against them, and liquidating under-collateralized positions. It maintains invariants on token supplies (lend and borrow tokens), pool reserves, and enforces service fees while coordinating with collateral, interest-rate, and parameter boxes via data inputs.

---

## Inputs / Outputs

### Inputs
- **Self (SELF):** The current pool box containing:
  - ERG value for storage rent and transaction fees
  - 4 native tokens: Pool NFT (authentication), Lend tokens (LP tokens), Borrow tokens (debt), Pooled assets (collateral reserves)
  - Proposition: ErgoTree enforcing this contract logic

### Data Inputs (Read-Only)
- **Service Parameter Box** (index 0 when dataInputs.size > 0): Contains service fee configuration and script reference
- **Collateral Box** (index 1 when loan operations): Active loan position with borrow tokens and collateral metadata
- **DEX Pool Box** (index 0 in loan context): Price oracle for collateral valuation via DEX reserves
- **Parent Interest Box** (index 1 in loan context): Aggregate interest accrual history
- **Child Interest Box** (index 2 in loan context): Granular per-block interest tracking
- **Parameter Box** (index 3 in loan context): Liquidation thresholds, collateral asset IDs, DEX NFT mappings, penalties

### Outputs
- **Output(0):** Successor pool box (same script, preserved NFT, updated token/asset quantities)
- **Output(1):** Service fee receiver box OR Collateral box (context-dependent; receives pooled assets as fee or holds updated collateral state)

---

## Key Logic

### Universal Invariants
1. **Script Preservation:** `successorScript == currentScript` – Pool contract code remains unchanged
2. **NFT Singleton:** `successorPoolNft == currentPoolNft` – Ensures exactly one pool box per transaction via Token ID rule
3. **Minimum Box Value:** `successorPoolValue >= MinimumBoxValue` (1 ERG) – Prevents dust outputs
4. **Pooled Asset ID Preservation:** `successorPooledTokens._1 == currentPooledTokens._1` – The collateral token type never changes

### Exchange Operation (User Deposits/Withdraws)
**Triggered when:** `CONTEXT.dataInputs.size > 0` (service parameter box present)

**Core Conditions:**
- Borrow tokens must remain unchanged: `isBorrowTokensUnchanged`
- Lend token value must not decrease: `successorLendTokenValue > currentLendTokenValue`
  - Formula: `LendTokenValue = (pooledAssets + totalBorrowed) / circulatingLendTokens × 10^15`
  - Protects existing LPs from dilution
- **Service Fee Validation:**
  - Reads service parameter box from R8 (fee receiver script)
  - Calculates tiered fee based on asset delta:
    - ≤ 200 ERG: 0.625% (1/160)
    - ≤ 2000 ERG: step-wise accumulation at 0.5% (1/200)
    - \> 2000 ERG: final tier at 0.4% (1/250)
  - Verifies Output(1) receives ≥ calculated fee in pooled assets
  - Validates service parameter box holds `ParamaterBoxNft`

### Deposit Operation
**Triggered when:** Assets increase AND borrow tokens decrease

**Conditions:**
- Lend tokens unchanged (no minting): `isLendTokensUnchanged`
- Borrow token count decreases (returns debt): `deltaTotalBorrowed < 0`
- Pool assets increase: `deltaAssetsInPool > 0`
- All universal invariants hold

### Loan & Liquidation Operations
**Triggered when:** `CONTEXT.dataInputs.size > 1` (collateral context)

**Data Structure Loading:**
- **Collateral Box Registers:**
  - R4: Collateral owner (optional)
  - R5: `(parentIndex: Int, childIndex: Int)` – pointers into interest history trees
  - R6: `(liquidationThreshold, penalty)` – LTV and penalty percent
  - R7: DEX NFT for price oracle
  - R8: User public key (optional, for signatures)
  - R9: `(forcedLiquidationBuffer, bufferLiquidation)` – liquidation safety margins

- **Interest Box Registers:**
  - R4: `Coll[Long]` – historical interest accumulation per block
  - R6 (child only): `Int` – current index in history

- **Parameter Box Registers:**
  - R4: `Coll[Long]` – liquidation thresholds per asset class
  - R5: `Coll[Coll[Byte]]` – allowed collateral asset IDs
  - R6: `Coll[Coll[Byte]]` – DEX NFT mappings
  - R7: `Coll[Long]` – liquidation penalties

**Loan Validation (Incomplete in Truncated Code):**
- Cross-validates collateral box NFT against parameter box
- Enforces liquidation threshold: `collateralValue × threshold ≥ loanAmount × LendTokenValue`
- DEX pool provides oracle pricing for non-native collateral
- Interest accrual applied via parent/child index lookups

---

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** (Collateral) | `Coll[Byte]` | Collateral owner identity | Read |
| **R5** (Collateral) | `(Int, Int)` | Parent & child interest indices | Read |
| **R6** (Collateral) | `(Long, Long)` | Liquidation threshold & penalty | Read |
| **R6** (Child Interest) | `Int` |