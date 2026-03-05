---
title: duckpools/lend-protocol-contracts — childInterest.md
description: "ErgoScript contract analysis: contracts/pools/SIGRSV-POOL/childInterest.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/SIGRSV-POOL/childInterest.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: childInterest

## Purpose

This contract manages the interest rate calculation and history tracking for a lending pool in the DuckPools protocol. It maintains a time-series record of interest rates computed from pool utilization metrics, updating periodically and validating that new rates conform to a polynomial interest rate curve defined by six coefficients.

## Inputs / Outputs

### Inputs
- **SELF**: The current interest history box (singleton state box)
- **Data Inputs**:
  - `pool` (CONTEXT.dataInputs(0)): Pool state box containing borrowed token amounts and available assets
  - `parameterBox` (CONTEXT.dataInputs(1)): Parameter box holding interest rate curve coefficients

### Outputs
- **OUTPUTS(0)** (`successor`): Updated interest history box carrying forward the accumulated interest rate history with one new entry appended

## Key Logic

The contract enforces the following validation rules:

1. **Update Frequency Gate**: At least `updateFrequency` (120) blocks must have elapsed since the last recorded height (`deltaHeight >= updateFrequency`).

2. **Interest Rate Calculation**: Computes the current utilization ratio `x` from pool state:
   - `x = (borrowed tokens) / (available assets + borrowed tokens) * InterestDenomination`
   - Calculates `currentRate` using a 6-term polynomial:
     ```
     currentRate = M + a + (b·x)/D + (c·x²)/(D·M) + ... + (f·x⁵)/(D·M⁴)
     ```
     where `M = 100000000` (interest denomination) and `D = 100000000` (coefficient denomination).

3. **History Preservation**: The new interest history must append exactly one new rate entry while preserving all prior entries.

4. **State Continuity**: 
   - Script propositionBytes (contract code) must remain unchanged
   - NFTs must be preserved
   - ERG value must not decrease by more than `MaximumExecutionFee` (2M nanoERG)
   - Child index must not change

5. **Box Validity Checks**: 
   - Pool box authenticated by `PoolNft` token
   - Parameter box authenticated by `InterestParamaterBoxNft` token

6. **History Bounds**: The interest history cannot exceed `MaximumHistoryHeight` (430) entries.

7. **Timestamp Validity**: The successor's final height must be within 5 blocks of the current HEIGHT.

8. **Dummy Registers**: Registers R7, R8, R9 must all be set to `true` (protocol convention for unused registers).

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Interest rate history (array of rates in M-denomination units) |
| **R5** | `Long` | Height at which the most recent interest rate was recorded |
| **R6** | `Int` | Child index identifier for this interest tracking box |
| **R7** | `Boolean` | Dummy register (must be `true`) |
| **R8** | `Boolean` | Dummy register (must be `true`) |
| **R9** | `Boolean` | Dummy register (must be `true`) |

## Tokens

- **PoolNft** (`8txwdGRnbi6RfPhR7rxgzvk5yaxzmm4PGXTaWjfVsfJa`): Singleton token identifying the pool state box (data input authentication)
- **InterestParameterBoxNft** (`CyAwUT5ijRsR8sKYit2ZdGYctUw1VwL2QuRRs72csDUP`): Singleton token identifying the coefficient parameter box (data input authentication)
- **Self tokens**: Preserved unchanged through the transaction (no token minting/burning)

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Monitor Block Height**: Watch for `HEIGHT - recordedHeight >= 120` condition becoming true.

2. **Fetch Pool State**: Construct a reference to the current pool box as a data input, verifying it holds the PoolNft token.

3. **Fetch Parameters**: Obtain the current parameter box (holding six interest coefficients in R4) as a data input.

4. **Calculate Interest Rate**: 
   - Extract pool utilization: `borrowed = MaximumBorrowTokens - pool.tokens(2)._2`
   - Extract available assets: `poolAssets = pool.tokens(3)._2`
   - Compute polynomial using the six coefficients

5. **Construct Successor**: 
   - Clone SELF with identical script, tokens, and ERG value (within fee tolerance)
   - Append computed rate to R4 history
   - Update R5 to current HEIGHT
   - Preserve R6 (childIndex) and R7–R9 (dummy flags)

6. **Transaction Constraints**:
   - Pay at least 2M nanoERG as execution fee
   - Do not exceed 430 total history entries
   - Set `finalHeight` in successor to HEIGHT (± 5 blocks)

## Related Contracts

- **Pool Contract**: Referenced as data input; maintains borrowed token quantities and available assets (tokens at indices 2 and 3)
- **Parameter / Coefficient Contract**: Holds the six interest rate curve coefficients in R4; updated separately by governance
- **Implied Parent Contract**: The `childIndex` register suggests this is a multi-stage or multi-instance design where multiple interest tracking boxes may exist in parallel, possibly coordinated by a parent contract managing pool lifecycle

## Technical Notes

- **State Machine Pattern**: This is a typical eUTXO state machine advancing through transactions via successor validation.
- **Polynomial Approximation**: The interest curve uses fixed coefficients to avoid complex computation on-chain; the formula approximates a smooth utilization-to-rate function.
- **Data Input Usage**: Pool and parameter boxes are immutable references (not spent), allowing read-only access to their state without creating circular spending dependencies.
- **Storage Rent**: The 430-entry history cap ensures box size remains within reasonable bounds for long-term storage on the blockchain.