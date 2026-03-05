---
title: duckpools/lend-protocol-contracts — pool.md
description: "ErgoScript contract analysis: contracts/pools/rsbtc/pool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsbtc/pool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: DuckPools Lending Protocol – Pool Contract

## Purpose

This contract manages the core liquidity pool for the DuckPools lending protocol, maintaining the state machine for a decentralized lending pool that accepts deposits, facilitates borrowing, and tracks lend/borrow token supplies. It enforces invariants on pool asset valuation, handles service fees via tiered calculations, and integrates with collateral boxes and DEX pools to execute loans with interest accrual and liquidation mechanics.

---

## Inputs / Outputs

### Inputs
- **SELF (Current Pool Box)**
  - Holds: Pool NFT (Singleton), Lend tokens, Borrow tokens, Pooled assets (the underlying collateral token)
  - Value: Minimum 1,000,000 nanoErgs
  - Script: The contract's own ErgoTree

- **Data Inputs (Context.dataInputs)**
  - **For Exchange Operations (1 data input):**
    - Service Parameter Box: Contains fee structure and service fee script (NFT: `ParamaterBoxNft`)
  - **For Loan Operations (4 data inputs):**
    - DEX Pool Box: Reserves (ERG + token), DEX NFT, fee parameters
    - Parent Interest Box: Historical interest rates (NFT: `ParentBoxNft`)
    - Child Interest Box: Child interest history, index pointer (NFT: `ChildBoxNft`)
    - Parameter Box: Liquidation thresholds, collateral asset IDs, collateral DEX NFTs, penalties

### Outputs
- **Output(0): Successor Pool Box**
  - Same script, same pool NFT, updated token balances and ERG value
  - Must preserve lend/borrow/pooled token IDs
  - Must satisfy all state transition invariants

- **Output(1) for Exchange:** Service Fee Box
  - Script: Defined in parameter box (R8)
  - Value: ≥ 1,000,000 nanoErgs
  - Tokens: Accumulated service fees (same token type as pooled assets)

- **Output(1) for Loans:** Collateral Box
  - Script: `CollateralContractScript` (from58("4VhkMqk2obBxz8j8pw9QbDqmiuBC3E6H7r5GDqGA1nha"))
  - Holds: Borrow tokens as collateral
  - Multiple registers (R4–R9) for loan state tracking

---

## Key Logic

### Core Validation (All Paths)

1. **Script Continuity:** The successor box must execute the same contract script (`successorScript == currentScript`)
2. **Pool NFT Preservation:** Singleton NFT is immutable across transitions
3. **Token ID Invariants:**
   - Lend token ID unchanged
   - Borrow token ID unchanged  
   - Pooled asset token ID (underlying collateral) unchanged
4. **Minimum Box Value:** Successor must hold ≥ 1,000,000 nanoErgs
5. **Lend Token Valuation:** 
   - **Formula:** `LendTokenValue = (PooledAssets + TotalBorrowed) × 10^15 / LendTokensCirculating`
   - **Constraint:** Successor value must be ≥ current value (monotonic increase)
   - **Rationale:** Ensures LP token value per unit never decreases

### Exchange Operation Path

Triggered when `CONTEXT.dataInputs.size == 1` (only service param box).

**Conditions:**
- All core validations pass
- `isBorrowTokensUnchanged`: Borrow token count stays constant
- `isLendTokenValueMaintained`: Lend token value increases
- `isPooledAssetPreserved`: Pooled token type unchanged
- **Service Fee Validation:**
  - Service param box holds NFT `ParamaterBoxNft`
  - Service fee script (from param box R8) matches output(1) script
  - Tiered fee calculation applied:
    - If `absDeltaAssetsInPool ≤ 200,000`: Fee = delta / 160
    - Else if `≤ 2,000,000`: Fee = (delta − 200k)/200 + 200k/160
    - Else: Fee = (delta − 2M − 200k)/250 + 2M/200 + 200k/160
  - Service fee box receives ≥ calculated fee amount

**Use Case:** Swaps/rebalancing within the pool; assets can flow in or out, but lend token value per unit is protected.

### Deposit Operation Path

Triggered when `CONTEXT.dataInputs.size <= 1` (no collateral boxes).

**Conditions:**
- All core validations pass
- `isLendTokensUnchanged`: Lend tokens locked (no new LP tokens minted or burned)
- `isAssetsInPoolIncreasing`: `deltaAssetsInPool > 0`
- `isDepositDeltaBorrowedValid`: `deltaTotalBorrowed < 0` (borrow tokens returned to pool)
- Pooled asset type unchanged

**Use Case:** Depositing collateral to borrow; borrow tokens are minted and sent to borrower's collateral box, while assets sit in pool.

### Loan Operation Path

Triggered when `CONTEXT.dataInputs.size > 1` (multiple interest/parameter boxes).

**Key Extractions:**
- **Collateral Box (Output(1)):**
  - Borrow tokens held as collateral
  - R4: Collateral owner (Coll[Byte])
  - R5: Interest indexes (parentIndex, childIndex)
  - R6: Threshold & penalty (Long, Long)
  - R7: DEX NFT reference
  - R8: User public key (GroupElement)
  - R9: Liquidation parameters (forced liquidation amount, buffer)

- **DEX Box (DataInput(0)):**
  - Reserves: ERG value + token reserves
  - R4: DEX fee (Int)
  - Used for liquidation price discovery

- **Interest Boxes:**
  - **Parent (DataInput(1)):** Historical interest rates in R4 (C