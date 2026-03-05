---
title: paideiadao/paideia-contracts — stakingIncentive.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.0/stakingIncentive.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.0/stakingIncentive.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: Staking Incentive

## Purpose

This contract manages incentive distribution for a multi-action staking protocol. It validates and facilitates four distinct transaction types—dust consolidation, emission rewards, compound staking, and stake pool operations—while distributing protocol-specific rewards to operators and miners from a central incentive pool.

## Inputs / Outputs

### Inputs
- **Consolidate Transaction**: Multiple boxes with identical `propositionBytes` (dust boxes) + the incentive box (`SELF`)
- **Emit Transaction**: Box with `stakeStateNFT` (INPUTS(0)), intermediate boxes, box with `emissionNFT` (INPUTS(2)), and the incentive box (`SELF`) as last input
- **Compound Transaction**: Box with `emissionNFT` (INPUTS(0)), intermediate boxes, multiple stake boxes holding `stakeTokenID`, and the incentive box (`SELF`) as second-to-last input
- **Stake Pool Key Transaction**: Outputs a box with `stakePoolKey` token

### Outputs
- **Consolidate**: 
  - OUTPUTS(0): Consolidated incentive box (same script, value increased)
  - OUTPUTS(1): Operator reward box
  - OUTPUTS(2): Miner fee box
- **Emit**:
  - OUTPUTS(4): Refreshed incentive box (same script)
  - OUTPUTS(5): Operator reward box
  - OUTPUTS(6): Miner fee box
- **Compound**:
  - OUTPUTS(INPUTS.size-1): Refreshed incentive box (same script)
  - OUTPUTS(INPUTS.size): Operator reward box
  - OUTPUTS(INPUTS.size+1): Miner fee box
- **Stake Pool Key**: OUTPUTS(0) contains `stakePoolKey` token

## Key Logic

The contract enforces four mutually-exclusive transaction pathways, validated through guard conditions:

### 1. **Consolidate Transaction** (Dust Collection)
- **Guard**: `OUTPUTS.size == 3`
- Counts all inputs matching `SELF.propositionBytes` (dust boxes)
- Calculates reward as `dustCollectionReward * dustBoxes`
- Validates:
  - Incentive output preserves script and increases in value
  - `SELF.value ≤ 100,000,000 nanoErgs` (dust threshold)
  - Operator receives exact reward amount
  - Miner receives fixed fee (`dustCollectionMinerFee`)

### 2. **Emit Transaction** (State-Driven Reward Emission)
- **Guard**: INPUTS(0) holds `stakeStateNFT` NFT AND INPUTS(2) holds `emissionNFT` NFT AND not a consolidate tx
- Validates:
  - `SELF` is the **last input** (INPUTS(INPUTS.size-1))
  - Incentive output preserves script and retains sufficient value (≥ SELF.value - emitReward - emitMinerFee - 1M nanoErgs)
  - Operator receives `emitReward`
  - Miner receives `emitMinerFee`
- **Implication**: Emission is triggered by state machine advance (stakeStateNFT)

### 3. **Compound Transaction** (Multi-Stake Reward Pooling)
- **Guard**: INPUTS(0) holds `emissionNFT` NFT AND not consolidate/emit txs
- Counts stake boxes: filters inputs where token(0) == `stakeTokenID` AND R4[0] matches emission box's R4[1] (pool ID correlation)
- **Reward scaling**: 
  - Operator reward = `baseCompoundReward + variableCompoundReward * stakeBoxes`
  - Miner fee = `baseCompoundMinerFee + variableCompoundMinerFee * stakeBoxes`
- Validates:
  - `SELF` is second-to-last input
  - Incentive output preserves script and value ≥ SELF.value - totalReward - totalFee
  - INPUTS.size == stakeBoxes + 2 (emission box + incentive box + stake boxes)

### 4. **Stake Pool Key Transaction** (Pool Initialization/Management)
- **Default pathway**: Triggered if none of the above conditions apply
- Validates: OUTPUTS(0) contains `stakePoolKey` token
- **Minimal validation**: Permits pool state transitions without reward extraction

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** (Emission Box) | `Coll[Long]` | Index [1] holds pool ID; matched against stake box R4[0] to correlate compound rewards |
| **R4** (Stake Boxes) | `Coll[Long]` | Index [0] holds pool ID; used for filtering boxes belonging to a specific stake pool |

*No registers written by this contract; it reads R4 for pool association logic.*

## Tokens

| Token | Type | Purpose |
|-------|------|---------|
| **`emissionNFT`** | Singleton NFT (Coll[Byte]) | Signals emission reward trigger (held by oracle/manager); required in emit and compound txs |
| **`stakeStateNFT`** | Singleton NFT | Identifies the stake pool state machine box; required in emit txs to trigger state advance |
| **`stakeTokenID`** | Native token ID | Identifies staked asset tokens; used to filter and count stake box inputs in compound txs |
| **`stakePoolKey`** | Native token ID | Marks pool initialization/management output; validated in default pathway |

## Integration Pattern

### Off-Chain Bot / Headless dApp Requirements

1. **Consolidate Action**:
   - Aggregate dust boxes (value ≤ 100M nanoErgs, same script)
   - Construct 3-output transaction
   - Calculate operator reward: `dustCollectionReward × dustBoxCount`
   - Set operator output value = reward; miner output value = `dustCollectionMinerFee`

2. **Emit Action**:
   - Fetch stake state NFT box and emission NFT box
   - Place