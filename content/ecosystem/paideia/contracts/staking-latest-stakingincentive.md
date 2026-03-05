---
title: paideiadao/paideia-contracts — stakingIncentive.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/latest/stakingIncentive.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/latest/stakingIncentive.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: stakingIncentive

## Purpose

This contract governs the Staking Incentive Box, a singleton state box that holds ERG reserves to pay execution fees for four critical operations in a DAO staking system: consolidating dust, emitting new staking rewards, compounding rewards to stakers, and withdrawing funds. It acts as a fee reservoir that ensures continuous operation of the staking infrastructure.

## Inputs / Outputs

### Consolidate Transaction
- **Inputs:** Multiple Staking Incentive Dust Boxes (all sharing `SELF.propositionBytes`)
- **Outputs:** 
  - New Staking Incentive Box (consolidated, same contract guard)
  - TX Operator Output Box (dust collection reward)
  - Miner Fee Box

### Emit Transaction
- **Inputs:** Stake State Box, Stake Pool Box, Emission Box, Staking Incentive Box
- **Outputs:** 
  - New Stake State Box
  - New Stake Pool Box
  - New Emission Box
  - Emission Fee Box
  - New Staking Incentive Box
  - TX Operator Output Box

### Compound Transaction
- **Inputs:** Emission Box, multiple Stake Boxes, Staking Incentive Box
- **Outputs:** 
  - New Emission Box
  - Updated Stake Boxes (one per staker)
  - New Staking Incentive Box
  - TX Operator Output Box

### Remove Funds Transaction
- **Inputs:** Staking Incentive Box
- **Outputs:** New Stake Pool Box

---

## Key Logic

### Consolidate TX Validation
1. **Identify consolidation:** Verify `SELF.value ≤ StakingIncentiveBoxMaxValue` (100 ERG) AND output count = 3
2. **Count dust boxes:** Filter all INPUTS matching `SELF.propositionBytes` (same contract guard)
3. **Verify consolidation reward:** Operator receives `DustCollectionReward × dustBoxCount`
4. **Verify new box:** 
   - New Incentive Box value > SELF value (accumulation)
   - Guarded by identical contract (`propositionBytes`)
5. **Verify fee:** Miner fee box = `DustCollectionMinerFee`

### Emit TX Validation
1. **Require ≥3 inputs** (Stake State, Stake Pool, Emission boxes)
2. **Verify NFT identities:**
   - INPUTS(0) contains `StakeStateNFT`
   - INPUTS(2) contains `EmissionNFT`
3. **Check output count:** Must equal 6 (State, Pool, Emission, Fee, Incentive, Operator)
4. **Validate emissions:**
   - New Emission Box receives DAO tokens from Stake Pool
   - State Box checkpoint increments
5. **Verify fees:** Emit reward + miner fee deducted from Incentive Box

### Compound TX Validation
1. **Verify first input is Emission Box** with `EmissionNFT`
2. **Count stake inputs:** All subsequent inputs until Incentive Box are Stake Boxes with `StakeToken`
3. **Calculate dynamic fees:** 
   - Base fee: `BaseCompoundReward + BaseCompoundMinerFee`
   - Variable fee: `(VariableCompoundReward + VariableCompoundMinerFee) × stakeBoxCount`
4. **Verify distribution:** Emission Box DAO tokens distributed proportionally to Stake Boxes
5. **Verify output count:** 2 + stakeBoxCount + 2 (Emission, Stake outputs, Incentive, Operator)

### Remove Funds TX Validation
1. **Single input:** Only Staking Incentive Box
2. **Single output:** New Stake Pool Box
3. Transfer all available ERG to Stake Pool

---

## Registers Used

### Staking Incentive Box (SELF)
- **R4–R9:** Not used (only ERG value)

### Stake State Box (Input/Output)
- **R4[Coll[Long]]:** State array
  - [0] Total Amount Staked (nanosats)
  - [1] Checkpoint (current staking cycle counter)
  - [2] Stakers (count of active stakers)
  - [3] Last Checkpoint Timestamp (ms)
  - [4] Cycle Duration (ms between emissions)

### Stake Pool Box (Input/Output)
- **R4[Long]:** Emission Amount (DAO tokens to emit per cycle)
- **R5[Coll[Byte]]:** Stake Pool Key (auxiliary identifier)

### Emission Box (Input/Output)
- **R4[Coll[Long]]:** Emission state
  - [0] Total Amount Staked (snapshot from State Box)
  - [1] Checkpoint (cycle when emitted)
  - [2] Stakers (count snapshot)
  - [3] Emission Amount (total DAO tokens to distribute)

### Stake Box (Input/Output)
- **R4[Coll[Long]]:** Staker state
  - [0] Checkpoint (last claim cycle)
  - [1] Staking Time (when stake was created, for lock-up logic)
- **R5[Coll[Byte]]:** Stake Key ID (unique identifier for unstaking authorization)

---

## Tokens

### Staking Incentive Box
- **None** (only holds ERG)

### Stake State Box
- **Token 0:** `StakeStateNFT` (Coll[Byte])
  - Amount: 1 (singleton identifier)
  - Purpose: Uniquely identifies the State Box across transactions
- **Token 1:** `StakeToken` (Coll[Byte])
  - Amount: ≤ 1 billion
  - Purpose: Proof token minted when stakes are created

### Stake Pool Box
- **Token 0:** `StakePoolNFT` (Coll[Byte])
  - Amount: 1 (singleton identifier)
- **Token 1:** `DaoTokenID` (Coll[Byte])
  - Amount: ≤ total DAO token supply