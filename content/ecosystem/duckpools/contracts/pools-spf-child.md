---
title: duckpools/lend-protocol-contracts — child.md
description: "ErgoScript contract analysis: contracts/pools/spf/child.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/spf/child.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: duckpools Child Interest Box

## Purpose

This contract manages a **child interest history box** in the duckpools lending protocol, maintaining a time-series record of interest rates computed from pool utilization. It validates that interest rate snapshots are appended at controlled intervals and that the computation follows a polynomial interest rate model derived from on-chain parameters.

## Inputs / Outputs

### Inputs
- **SELF** (Spent Box): The current child interest history box, containing historical interest rates and metadata
- **Data Input 0** (`pool`): Read-only reference to the main pool box (provides current borrow/asset amounts)
- **Data Input 1** (`parameterBox`): Read-only reference to the interest parameter box (supplies polynomial coefficients a–f)

### Outputs
- **OUTPUTS(0)** (`successor`): The updated child interest history box with an appended interest rate snapshot, preserving tokens, NFTs, and ERG value minus execution fees

## Key Logic

The contract enforces a **state machine transition** with these validations:

1. **Update Frequency Gate**: `deltaHeight >= updateFrequency` (120 blocks) — prevents spam updates and ensures interest snapshots are recorded at regular intervals

2. **Interest Rate Computation** (6th-degree polynomial model):
   ```
   Rate = M + a + (b·x)/D + (c·x²)/D·M + (d·x³)/D·M² + (e·x⁴)/D·M³ + (f·x⁵)/D·M⁴
   ```
   where:
   - `x` = utilization ratio = `(borrowed × M) / (poolAssets + borrowed)`
   - `borrowed` = `MaximumBorrowTokens - pool.tokens(2)._2`
   - `M` = `InterestDenomination` (100,000,000)
   - `D` = `CoefficientDenomination` (100,000,000)

3. **History Validation**: The successor's history must preserve all prior entries and append exactly one new rate entry equal to `currentRate`

4. **Temporal Bounds**: The successor's recorded height must be within 5 blocks of the current block height, preventing backdating

5. **Resource Conservation**:
   - Retained ERG ≥ `SELF.value - MaximumExecutionFee` (2M nanoERG max fee)
   - All native tokens preserved (no token loss or injection)
   - Child index retained (immutable identity)

6. **Script & State Integrity**:
   - Successor script remains identical (no logic upgrade without explicit migration)
   - Dummy registers R7, R8, R9 must be true (placeholder for future extensibility)
   - History size ≤ `MaximumHistoryHeight` (430 snapshots max)

7. **NFT Authentication**:
   - Pool box authenticated via `PoolNft` token
   - Parameter box authenticated via `InterestParamaterBoxNft` token

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Interest rate history (list of computed rates over time) |
| **R5** | `Long` | Last recorded block height (for update frequency throttling) |
| **R6** | `Int` | Child box index (immutable identifier for ordering/batching) |
| **R7** | `Boolean` | Dummy register (reserved for future use; must be true) |
| **R8** | `Boolean` | Dummy register (reserved for future use; must be true) |
| **R9** | `Boolean` | Dummy register (reserved for future use; must be true) |

## Tokens

- **PoolNft** (`o7mKcicqmdpUNzVHAhWTAK3JsZHJzWr3mi1zPnCxyf4`): Singleton token identifying the pool data input; prevents substitution of pool state
- **InterestParameterBoxNft** (`4wmF74iSVGSR6JNyjgw3Pgdq6TiwHwjzvyTwMF3Yb5wM`): Singleton token identifying the parameter box; ensures coefficients come from authorized source
- **SELF.tokens**: Native tokens held by this box are preserved unchanged in successor (immutable collateral or dust)

## Integration Pattern

### Off-Chain Bot / Updater Responsibilities

1. **Monitor Block Height**: Track when `HEIGHT - recordedHeight >= 120` to determine update eligibility
2. **Read Pool State**: Query the UTXO set for:
   - Pool box (identified by PoolNft) → extract borrow and asset amounts from tokens(2) and tokens(3)
   - Parameter box (identified by InterestParameterBoxNft) → extract coefficients from R4
3. **Compute Interest Rate**: Evaluate the 6th-degree polynomial using current pool utilization
4. **Construct Successor Box**:
   - Append computed rate to R4 history
   - Update R5 with current HEIGHT
   - Keep R6, R7, R8, R9 unchanged
   - Preserve SELF.tokens
   - Set value = `SELF.value - executionFee` (capped at MaximumExecutionFee)
   - Copy proposition bytes from SELF (no script change)
5. **Build & Sign Transaction**:
   - Include SELF as input
   - Include pool and parameter boxes as data inputs (not spent)
   - Output successor box
   - Pay execution fee to transaction author or burn
   - Sign with sufficient Sigma protocol proofs to satisfy SELF's contract

### Validation Flow (On-Chain)

The contract is satisfied iff all 12 conditions hold:
- Frequency gate passed
- History cap not exceeded
- Script unchanged
- Rates correctly computed & appended
- Height deltas valid
- Resources conserved
- NFTs authentic
- Dummy registers set
- No token mutations

## Related Contracts

### Inferred Dependencies
- **Pool Box Contract**: Referenced as data input; likely maintains borrow/lend balances and validates that child boxes compute interest correctly. The pool box token serves as singleton proof.
- **Interest Parameter Box Contract**: Referenced as data input; holds polynomial coefficients and likely validates