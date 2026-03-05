---
title: duckpools/lend-protocol-contracts — child.md
description: "ErgoScript contract analysis: contracts/pools/rsAda/child.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsAda/child.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: rsAda Child Pool Interest Rate Contract

## Purpose

This contract manages a **child pool state box** that tracks historical interest rate calculations for an rsAda lending pool. It validates that interest rates are computed correctly based on utilization metrics and that the history is maintained in an append-only fashion without exceeding storage constraints.

## Inputs / Outputs

| Component | Details |
|-----------|---------|
| **SELF (Input)** | Child pool state box holding interest rate history, last update height, and child index |
| **OUTPUTS(0) (Successor)** | Updated child pool box with appended interest rate to history, new height recorded, same index |
| **Data Input 0** | Pool box (authenticated by PoolNft) containing borrowed tokens and total pool assets |
| **Data Input 1** | Parameter box (authenticated by InterestParameterBoxNft) containing polynomial coefficients (a-f) |

## Key Logic

The contract enforces a **multi-stage interest rate update state machine** with these validations:

1. **Update Frequency Gate**: At least 120 blocks must have passed since the last recorded height (`deltaHeight >= updateFrequency`)

2. **Interest Rate Calculation**: Computes a polynomial interest rate based on utilization:
   - Utilization `x = (Borrowed / (PoolAssets + Borrowed)) * 100,000,000`
   - Rate formula: `M + a + bx/D + cx²/M/D + dx³/M²/D + ex⁴/M³/D + fx⁵/M⁴/D`
   - Where `M = 100,000,000` (InterestDenomination) and `D = 100,000,000` (CoefficientDenomination)

3. **History Invariant**: The new interest rate must be appended to the history collection (previous history is prefix-preserved, new entry added at index `size`)

4. **Storage Bounds**: Interest history size cannot exceed 430 entries (MaximumHistoryHeight)

5. **Box Preservation**:
   - ERG value must not decrease by more than 2,000,000 (MaximumExecutionFee)
   - Token set must remain identical
   - Script must remain unchanged (deterministic successor)
   - Child index must stay constant

6. **Timestamp Validity**: Final height must be within ±5 blocks of current HEIGHT (prevents stale transactions)

7. **NFT Authentication**: Data inputs authenticated via singleton NFTs (PoolNft, InterestParameterBoxNft)

8. **Dummy Register Flag**: Registers R7, R8, R9 must all be `true` (unused fields for future protocol extension)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Interest rate history (append-only log of computed rates) |
| **R5** | `Long` | Last recorded block height (HEIGHT when interest was last updated) |
| **R6** | `Int` | Child pool index identifier (immutable state machine identifier) |
| **R7** | `Boolean` | Dummy register (reserved for future use, must be `true`) |
| **R8** | `Boolean` | Dummy register (reserved for future use, must be `true`) |
| **R9** | `Boolean` | Dummy register (reserved for future use, must be `true`) |

## Tokens

| Token | Role | Authentication |
|-------|------|-----------------|
| **PoolNft** (9wyjwbs7wTs6VxM77vieD4b68Jsc1ABVDtSnydYTRCt2) | Singleton identifying the parent pool box in data inputs | Verified via `pool.tokens(0)._1` |
| **InterestParameterBoxNft** (4pranhmdN5btZ9FZKHAcQwD8tU6sTFg6NeVjzGArUs53) | Singleton identifying the coefficient parameter box | Verified via `parameterBox.tokens(0)._1` |
| **Child State Tokens** | Preserved exactly across state transitions | `noMoreTokens` and `preservedInterestNFT` checks |

## Integration Pattern

**Off-Chain Bot Flow:**

1. **Read** current child pool box (SELF) to extract history size, current height, and child index
2. **Read** pool box (data input) to compute borrowed tokens: `MaximumBorrowTokens - pool.tokens(2)._2`
3. **Read** parameter box (data input) to fetch coefficients a-f from R4
4. **Calculate** utilization and polynomial interest rate using formula above
5. **Construct** successor box with:
   - R4: `interestHistory ++ Coll(currentRate)` (append new rate)
   - R5: `HEIGHT` (current block height)
   - R6: unchanged child index
   - R7-R9: `true` flags
   - Tokens: identical to SELF
   - Value: SELF.value minus up to MaximumExecutionFee
6. **Build transaction** with SELF as input, successor as output, and two data inputs (pool, parameter box)
7. **Sign** with private key controlling the child box (or multi-sig if applicable)

**Verification Path**: Contract validates all invariants; if any condition fails, the sigmaProp returns `false` and transaction is rejected.

## Related Contracts

- **Parent Pool Contract**: Referenced via PoolNft singleton in data inputs; manages borrowed token ledger and total pool assets
- **Interest Parameter Contract**: Referenced via InterestParameterBoxNft; maintains polynomial coefficients (a-f) for interest rate model
- **Multi-Child Architecture**: This is one of potentially multiple child boxes (each with distinct `childIndex` in R6), suggesting a **sharded state design** to avoid boxing contention at high utilization

## Notable Design Patterns

- **Append-Only History**: Interest rates form an immutable log, enabling historical audits and rate change tracking
- **Data Input Oracle**: Pool and parameter boxes passed as read-only data inputs, avoiding state mutation conflicts
- **Polynomial Interest Curve**: Uses degree-5 polynomial with utilization-based elasticity (standard DeFi interest rate model)
- **Execution Cost Recovery**: Allows up