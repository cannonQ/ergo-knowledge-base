---
title: duckpools/lend-protocol-contracts — childInterest.md
description: "ErgoScript contract analysis: contracts/pools/QUACKS-POOL/childInterest.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/QUACKS-POOL/childInterest.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: childInterest.md

## Purpose

This contract manages the interest rate calculation and history tracking for a lending pool in the QUACKS-POOL protocol. It periodically updates a historical record of computed interest rates based on pool utilization, using a polynomial function with coefficients stored in a parameter box. The contract acts as a stateful singleton that accumulates interest rate data over time while maintaining invariants around box value, tokens, and script validity.

---

## Inputs / Outputs

### Inputs
- **SELF**: The current childInterest box (the contract being validated)
  - Contains historical interest rate data and metadata
- **CONTEXT.dataInputs(0) (pool)**: A read-only data input containing the pool state
  - Provides token balances to calculate current utilization
- **CONTEXT.dataInputs(1) (parameterBox)**: A read-only data input with interest rate coefficients
  - Supplies polynomial coefficients (a–f) for rate calculation

### Outputs
- **OUTPUTS(0) (successor)**: The updated childInterest box
  - Preserves all prior state while appending the newly calculated interest rate to the history register
  - Must maintain script, tokens, and sufficient ERG for transaction costs

---

## Key Logic

The contract enforces the following validation conditions:

1. **Update Timing**: `isReadyToUpdate`
   - Block height advancement must be ≥ 120 blocks since last update to prevent spam

2. **Interest Rate Calculation**:
   - Computes utilization ratio: `util = borrowed / (poolAssets + borrowed)`
   - Applies a 6-degree polynomial: `rate = M + a + bx/D + cx²/MD + dx³/MD² + ... + fx⁶/MD⁵`
   - Where x = utilization, M = 100M (interest denomination), D = 100M (coefficient denomination)

3. **History Append Validation**: `validInterestUpdate`
   - All prior history entries must remain identical (immutable)
   - New rate must match calculated `currentRate`
   - History length increases by exactly 1

4. **State Preservation**:
   - Script bytes must not change (same ErgoTree)
   - Token set must remain identical
   - Child index must not change
   - Dummy registers (R7–R9) must remain `true`

5. **Box Value Conservation**: `retainedERG`
   - Successor box ERG ≥ SELF value − MaximumExecutionFee (allows fee deduction only)

6. **Safety Caps**:
   - Interest history size ≤ 430 entries
   - Final height delta between data input (parameterBox) and current block must be 0–5 blocks (freshness check)

7. **NFT Authentication**:
   - Pool box must carry the PoolNft token
   - Parameter box must carry the InterestParameterBoxNft token

8. **No Dust Tokens**: `noMoreTokens`
   - Successor must not introduce additional native tokens

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Interest rate history (SELF); updated history appended with new rate (successor) |
| **R5** | `Long` | Block height when last update occurred (SELF); new current HEIGHT (successor) |
| **R6** | `Int` | Child index identifier (unchanged across updates) |
| **R7** | `Boolean` | Dummy register; must remain `true` for successor |
| **R8** | `Boolean` | Dummy register; must remain `true` for successor |
| **R9** | `Boolean` | Dummy register; must remain `true` for successor |

---

## Tokens

- **PoolNft** (`CDFbkWeJdXSxbWys91ojhnuD395cYHk1N2c5t6m7qWBz`): Singleton NFT identifying the authoritative pool box; used as data input for current token balances
- **InterestParameterBoxNft** (`3ENugtBmx1WFWcQuuuWEYkTXKUdc2pap8r795ajpyJvr`): Singleton NFT identifying the parameter box; used as data input for polynomial coefficients

The childInterest box itself holds no specific NFT; instead, it is identified by its own Token ID rule (stored tokens must remain constant).

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Monitor Block Height**: Track HEIGHT and detect when `HEIGHT - recordedHeight ≥ 120`

2. **Fetch Data Inputs**:
   - Retrieve the live pool box via PoolNft lookup
   - Retrieve the parameter box via InterestParameterBoxNft lookup

3. **Calculate Interest Rate**:
   - Extract token balances from pool: `poolAssets = pool.tokens(3)._2`, `borrowed = MaximumBorrowTokens - pool.tokens(2)._2`
   - Compute utilization: `util = (borrowed * 100M) / (poolAssets + borrowed)`
   - Evaluate polynomial using coefficients from parameterBox.R4

4. **Construct Successor Box**:
   - Copy SELF's ErgoTree to successor
   - Append calculated `currentRate` to SELF.R4 to form successor.R4
   - Set successor.R5 = HEIGHT
   - Preserve successor.R6, R7, R8, R9 unchanged
   - Ensure successor.value ≥ SELF.value − 2M (MaximumExecutionFee)
   - Preserve all tokens from SELF

5. **Verify Freshness**:
   - Confirm that parameterBox.HEIGHT is within the last 5 blocks of transaction submission

6. **Build & Submit Transaction**:
   - Include SELF as input, successor as output
   - Include pool and parameterBox as read-only data inputs (CONTEXT.dataInputs)
   - Ensure total fees ≤ 2M nanoERG

---

## Related Contracts

- **Pool Contract**: Referenced via PoolNft; must implement compatible token slots (tokens(2) = borrowed balance, tokens(3) = pool assets)