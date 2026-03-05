---
title: duckpools/lend-protocol-contracts — interestRateContract.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/interestRateContract.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/interestRateContract.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Interest Rate Contract

## Purpose

This contract maintains a historical record of interest rates for the DuckPools lending protocol, calculating rates based on a polynomial function of utilization metrics. It validates state transitions where the interest rate history is extended at regular intervals (every 120 blocks), ensuring the contract acts as a singleton state machine with immutable historical data.

## Inputs / Outputs

### Inputs
- **SELF**: The Interest Rate Box itself—contains the current interest rate history and metadata.
- **CONTEXT.dataInputs(0)**: Pool Box (read-only)—provides current borrowing state via `tokens(2)._2` (borrowed amount) and `value` (total ERG).
- **CONTEXT.dataInputs(1)**: Parameter Box (read-only)—contains interest rate polynomial coefficients in R4.

### Outputs
- **OUTPUTS(0)** (`successor`): The updated Interest Rate Box—must contain the appended interest rate history and increment the height record.

## Key Logic

1. **Update Frequency Guard**: Validates that at least `updateFrequency` (120) blocks have elapsed since the last recorded height (`HEIGHT - recordedHeight >= 120`).

2. **Interest Rate Calculation**: Computes the current interest rate using a 6-term polynomial:
   - **Inputs**: Utilization ratio `x = (borrowed / (ERG + borrowed)) * 10^8`
   - **Formula**: `M + (a + (b*x)/D + (c*x²)/D*M + (d*x³)/(D*M²) + ... + (f*x⁶)/(D*M⁵))`
   - Where `M = 10^8` (InterestDenomination) and `D = 10^8` (CoefficientDenomination)

3. **State Transition Validation**:
   - Previous history must be an exact prefix of the new history.
   - New rate appended equals calculated `currentRate`.
   - History size increments by exactly 1.

4. **Singleton Preservation**:
   - `SELF.propositionBytes == successor.propositionBytes` (ErgoTree unchanged)
   - `SELF.tokens == successor.tokens` (NFT/tokens unchanged)
   - `finalChildIndex == childIndex` (immutable index field)

5. **Storage Rent & Fees**:
   - Successor value ≥ self value − 2,000,000 nanoERG (execution fee buffer)

6. **Box Validity Checks**:
   - Pool Box authenticated by PoolNft token.
   - Parameter Box authenticated by InterestParameterBoxNft token.
   - History size capped at 430 entries (MaximumHistoryHeight).
   - Final height stamped within ±5 blocks of current HEIGHT.

7. **Dummy Register Guards**: R7, R8, R9 must all be `true` (likely future-proofing flags).

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | **Interest rate history** — list of historical interest rates; on each valid update, appended with new rate |
| **R5** | `Long` | **Recorded height** — block height of the last update; successor must set `finalHeight` to current or near-current `HEIGHT` |
| **R6** | `Int` | **Child index** — immutable identifier; must remain unchanged across all state transitions |
| **R7** | `Boolean` | **Dummy flag 1** — always checked as `true`; semantic purpose unclear (extensibility hook) |
| **R8** | `Boolean` | **Dummy flag 2** — always checked as `true` |
| **R9** | `Boolean` | **Dummy flag 3** — always checked as `true` |

## Tokens

- **PoolNft** (`Ahk13GiqmS1txRpk9TdJmbs1Qr6wGya8MstvhMVfNDbq`): Authentication token on the Pool Box data input; ensures the contract reads the authoritative pool state.
- **InterestParameterBoxNft** (`6iLeQkyfvgqRHkSfgr3JtTecngCBRwNPAdssXzyhmYAK`): Authentication token on the Parameter Box data input; ensures rate coefficients come from the official parameter source.
- **SELF.tokens**: Preserved unchanged in the successor (no token minting/burning).

## Integration Pattern

### Off-Chain Bot / Headless dApp Workflow

1. **Monitor Chain State**:
   - Track the Interest Rate Box (identified by `childIndex` in R6).
   - Poll the Pool Box (holds borrow state).
   - Monitor the Parameter Box (holds polynomial coefficients).

2. **Trigger Conditions** (every block):
   - Calculate `deltaHeight = HEIGHT - recordedHeight`.
   - If `deltaHeight >= 120`, proceed to transaction construction.

3. **Transaction Construction**:
   - **Input**: Current Interest Rate Box (SELF).
   - **Data Inputs**: 
     - Current Pool Box (CONTEXT.dataInputs(0)).
     - Current Parameter Box (CONTEXT.dataInputs(1)).
   - **Output**: New Interest Rate Box with:
     - R4: `interestHistory ++ [calculatedRate]` (append only).
     - R5: Set to `HEIGHT`.
     - R6: Unchanged (`childIndex`).
     - R7, R8, R9: All `true`.
     - `value`: ≥ `SELF.value - 2,000,000` (retain ERG minus fee).
     - `tokens`: Identical to SELF.

4. **Off-Chain Calculation** (before submission):
   - Extract coefficients (a–f) from Parameter Box R4.
   - Compute borrowed = `MaximumBorrowTokens - pool.tokens(2)._2`.
   - Calculate utilization: `x = (InterestDenomination * borrowed) / (pool.value + borrowed)`.
   - Evaluate polynomial with these inputs.
   - Construct the output box matching the script's expectations.

5. **Transaction Submission**:
   - Sign with the key controlling the