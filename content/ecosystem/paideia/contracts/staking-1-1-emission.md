---
title: paideiadao/paideia-contracts — emission.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.1/emission.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.1/emission.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: emission.es

## Purpose

This contract governs the **staking emission mechanism** for a DAO token distribution system. It manages two critical transaction types: (1) **Emit Tx** — which withdraws allocated tokens from a stake pool into an emission box once per cycle, and (2) **Compound Tx** — which distributes emission tokens to individual stakers proportionally based on their stake and lockup time. The contract enforces invariants around token conservation, NFT identifiers, and cumulative distribution calculations.

---

## Inputs / Outputs

### Emit Transaction

**Inputs:**
- **INPUTS(0)**: Stake State Box — contains staking aggregate data (total staked, checkpoint, staker count, cycle duration)
- **INPUTS(1)**: Stake Pool Box — holds unallocated DAO tokens and the emission amount for this cycle
- **INPUTS(2)**: Emission Box (SELF) — the current emission box being processed
- **INPUTS(3+)**: Staking Incentive Box — provides ERG for transaction fees and executor rewards

**Outputs:**
- **OUTPUTS(0)**: New Stake State Box — updated state reflecting the checkpoint
- **OUTPUTS(1)**: New Stake Pool Box — reduced DAO token balance after emission withdrawal
- **OUTPUTS(2)**: New Emission Box — newly created box holding tokens to be distributed
- **OUTPUTS(3)**: Emission Fee Box — receives the 1% treasury fee (withdrawn from the emission amount)
- **OUTPUTS(4)**: New Staking Incentive Box — replenished incentive box for future transactions
- **OUTPUTS(5)**: Tx Operator Output Box — reward/change for transaction submitter

### Compound Transaction

**Inputs:**
- **INPUTS(0)**: Emission Box (SELF) — source of tokens for distribution
- **INPUTS(1...N)**: Stake Boxes — all stake boxes with a checkpoint matching `SELF.R4(1)` (the emission checkpoint)
- **INPUTS(N+1)**: Staking Incentive Box — ERG for fees and executor rewards

**Outputs:**
- **OUTPUTS(0)**: New Emission Box — updated with remaining undistributed tokens
- **OUTPUTS(1...N)**: New Stake Boxes — updated stake boxes with compounded rewards
- **OUTPUTS(N+1)**: New Staking Incentive Box — replenished for future transactions
- **OUTPUTS(N+2)**: Tx Operator Output Box — executor compensation

---

## Key Logic

### Emit Tx Validation (`validEmitTx`)

1. **Input Verification:**
   - `INPUTS(0)` must hold the Stake State NFT (`StakeStateNFT`)
   - `INPUTS(2)` must be the current Emission Box (`SELF.id`)

2. **New Emission Box Invariants:**
   - **Value Preservation**: `newEmissionBox.value == SELF.value` (ERG amount unchanged)
   - **Contract Identity**: `newEmissionBox.propositionBytes == SELF.propositionBytes` (same contract governs the box)
   - **State Sync**: First three elements of `R4` (Total Staked, Checkpoint, Stakers) copied from Stake State Box
   - **Emission Calculation**:
     ```
     emission_amount = 99% × stake_pool.emission_allocation  (1% → treasury)
     OR if (stake_pool.tokens_remaining < stake_pool.allocation):
       emission_amount = remaining_stake_pool_tokens + emission_box_dust
     ```
   - **Token Consistency**: Emission NFT ID and DAO token ID remain unchanged
   - **Token Quantity Invariant**: `newEmissionBox.tokens(1)._2 == newEmissionBox.R4[Coll[Long]].get(3)` (DAO token count matches R4 emission amount)

### Compound Tx Validation (`validCompoundTx`)

1. **Input Filtering:**
   - Stake boxes are identified by matching:
     - `stakeBox.tokens(0)._1 == StakeTokenID` (proof of valid stake creation)
     - `stakeBox.R4[Coll[Long]].get(0) == SELF.R4[Coll[Long]].get(1)` (checkpoint matches emission box checkpoint)

2. **Distribution Calculation:**
   - Each stake box receives tokens proportional to:
     ```
     staker_share = staker_dao_tokens / total_staked_dao_tokens
     reward = emission_amount × staker_share × (lockup_time_adjustment)
     ```
   - **Lockup Adjustment**: Applied via a multiplier based on `R4[1]` (staking time) to incentivize longer stakes

3. **New Emission Box Validation:**
   - **Remaining Emission**: All distributed tokens must be accounted for; the difference becomes `newEmissionBox.tokens(1)._2`
   - **Dust Accumulation**: Rounding errors are permitted to accumulate in the new emission box
   - **Checkpoint Update**: `newEmissionBox.R4[Coll[Long]].get(1)` is updated to reflect the next cycle checkpoint

4. **Stake Box Updates:**
   - Each `newStakeBox.R4[Coll[Long]].get(0)` (checkpoint) is updated to the next checkpoint value
   - DAO token balances increase by the calculated reward amount
   - Stake Token ID is preserved (singleton property)

---

## Registers Used

### Emission Box (SELF)

| Register | Type | Content |
|----------|------|---------|
| **R4** | `Coll[Long]` | `[Total Amount Staked, Checkpoint, Stakers Count, Emission Amount]` |
| **R5-R9** | (unused) | — |

### Stake State Box (INPUTS(0) in Emit Tx)

| Register | Type | Content |
|----------|------|---------|
| **R4** | `Coll[Long]` | `[Total Amount Staked, Checkpoint, Stakers Count, Last Checkpoint Timestamp, Cycle Duration]` |
| **R5-R9** | (unused) | —