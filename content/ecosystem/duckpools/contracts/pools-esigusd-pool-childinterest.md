---
title: duckpools/lend-protocol-contracts — childInterest.md
description: "ErgoScript contract analysis: contracts/pools/eSIGUSD-POOL/childInterest.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/eSIGUSD-POOL/childInterest.md
project: duckpools-lend-protocol-contracts
---
# eSIGUSD Pool Child Interest Contract Analysis

## Purpose

This contract maintains a historical record of interest rates for the eSIGUSD lending pool, computing them dynamically based on pool utilization (borrowed tokens vs. available assets). It functions as a **state machine** that updates interest rate history at regular intervals by reading coefficients from a parameter box and enforcing invariants on successor state transitions.

## Inputs / Outputs

### Inputs
- **SELF**: The current interest history box (state NFT), holding accumulated interest rate records in R4
- **Data Input 0** (`pool`): The main pool box, containing total borrowed and available tokens via its token array
- **Data Input 1** (`parameterBox`): A parameter box holding polynomial coefficients (a–f) for interest rate calculation

### Outputs
- **OUTPUTS(0)** (`successor`): The next iteration of this contract, with updated interest history in R4 and new height in R5

## Key Logic

1. **Update Frequency Gate**: Validates that at least `updateFrequency` (120) blocks have elapsed since the last recorded height (`recordedHeight` in R5) before allowing an update.

2. **Utilization Calculation**: Computes `util` as the ratio of borrowed tokens to total pool liquidity (borrowed + available), normalized to `InterestDenomination` (100M).

3. **Polynomial Rate Computation**: Uses a 6-term polynomial with coefficients a–f to calculate the current interest rate:
   ```
   currentRate = M + a + (b·x)/D + (c·x²)/(D·M) + (d·x³)/(D·M²) + (e·x⁴)/(D·M³) + (f·x⁵)/(D·M⁴)
   ```
   where `x = util`, `D = CoefficientDenomination`, `M = InterestDenomination`.

4. **History Preservation**: Ensures the new interest history extends the old one by exactly one element (the computed `currentRate`), and that history size never exceeds `MaximumHistoryHeight` (430 entries).

5. **Successor Validation**:
   - Script remains identical (`validSuccessorScript`)
   - Tokens and NFTs are preserved (`preservedInterestNFT`)
   - ERG value does not decrease by more than `MaximumExecutionFee` (2M nanoERGs)
   - Child index remains constant (`retainIndex`)
   - Future block height (`finalHeight`) is within 5 blocks of current HEIGHT
   - Dummy registers R7, R8, R9 are all `true` (placeholder validation)
   - No new tokens are introduced

6. **Box Authenticity**: Verifies that both pool and parameter boxes carry their respective singleton NFTs (`PoolNft` and `InterestParamaterBoxNft`).

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Interest rate history (appended each update) |
| **R5** | `Long` | Last recorded HEIGHT when history was updated |
| **R6** | `Int` | Child index identifier (constant across updates) |
| **R7** | `Boolean` | Dummy validation flag (always true in successor) |
| **R8** | `Boolean` | Dummy validation flag (always true in successor) |
| **R9** | `Boolean` | Dummy validation flag (always true in successor) |

## Tokens

- **PoolNft** (`8A5R3bhY16TCJXPF8cCNL5bgdBg1vHZyM3f8W1PqAvdM`): Singleton NFT on the pool data input; ensures only the authentic pool box is read.
- **InterestParamaterBoxNft** (`BXxXTVP6PH2aSCui9K3wyBdzBmxyMvGpSgY5FbbF4Tis`): Singleton NFT on the parameter box; ensures only authentic coefficients are used.
- **SELF.tokens**: Assumed to be preserved through the entire lifecycle (no token minting/burning).

## Integration Pattern

### Off-Chain Bot / Headless dApp Requirements

1. **Monitor HEIGHT**: Track when `HEIGHT - recordedHeight >= 120` to trigger an update.
2. **Fetch Pool State**: Read the current pool box (identified by PoolNft) to extract borrowed and available token quantities.
3. **Fetch Parameters**: Read the coefficient box (identified by InterestParamaterBoxNft) to get the latest a–f values.
4. **Compute Interest Rate**: Execute the polynomial formula locally to calculate `currentRate`.
5. **Construct Successor Box**:
   - Copy SELF to OUTPUTS(0)
   - Update R4 with the extended interest history (append `currentRate`)
   - Update R5 to current `HEIGHT`
   - Keep R6 unchanged
   - Set R7, R8, R9 to `true`
   - Ensure ERG value is at least `SELF.value - MaximumExecutionFee`
6. **Verify Constraints**: All 12 conditions in the final `sigmaProp` must evaluate to `true`.
7. **Sign & Broadcast**: The transaction must be signed by the contract's spending path (Sigma protocol).

### Context Extension
- No explicit Context extension is read; all data is sourced from data inputs and box fields.

## Related Contracts

Based on references in the code:

- **Pool Contract** (identified by `PoolNft`): The main lending pool that holds borrowed token counts and available liquidity. This contract reads its state via data input.
- **Parameter Box Contract** (identified by `InterestParamaterBoxNft`): Manages interest rate coefficients. Updates to this box propagate into future interest rate calculations.
- **eSIGUSD Lending Protocol**: The broader protocol this contract is part of (inferred from project name and SigUSD references).

## Invariants & Security Notes

1. **Atomic Update**: Interest rates and height are updated atomically in a single transaction.
2. **Monotonic History**: History only grows; old entries never change.
3. **Bounded History**: Max 430 entries prevent register overflow.
4. **No 