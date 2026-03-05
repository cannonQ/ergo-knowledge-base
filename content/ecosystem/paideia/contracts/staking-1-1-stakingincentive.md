---
title: paideiadao/paideia-contracts — stakingIncentive.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.1/stakingIncentive.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.1/stakingIncentive.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: stakingIncentive.es

## Purpose

This contract governs a **Staking Incentive Box** that orchestrates four core transaction types in a DAO staking system: consolidating dust ERG, emitting rewards from a stake pool, distributing emissions to stakers, and withdrawing funds. It acts as a state machine coordinator between the Stake State Box, Stake Pool Box, Emission Box, and individual Stake Boxes, ensuring atomicity and correct fund flow across the staking lifecycle.

---

## Inputs / Outputs

### Consolidate Transaction
| Direction | Box | Purpose |
|-----------|-----|---------|
| **Input** | Multiple StakingIncentiveBoxes (dust) | Consolidate fragmented ERG across multiple self-referential boxes |
| **Input** | StakingIncentiveBox (SELF) | Current incentive box holding execution reserves |
| **Output** | NewStakingIncentiveBox | Consolidated box with increased ERG value, same script |
| **Output** | TxOperatorOutputBox | Reward for off-chain bot (`DustCollectionReward × count`) |
| **Output** | MinerFeeBox | Fixed mining fee (`DustCollectionMinerFee`) |

### Emit Transaction
| Direction | Box | Purpose |
|-----------|-----|---------|
| **Input** | StakeStateBox | Singleton NFT tracking total staked, checkpoint, staker count |
| **Input** | StakePoolBox | Singleton NFT holding DAO token emission reservoir |
| **Input** | EmissionBox | Singleton NFT buffer for current epoch distributions |
| **Input** | StakingIncentiveBox (SELF) | Pays execution fees |
| **Output** | NewStakeStateBox | Updated with incremented checkpoint and timestamp |
| **Output** | NewStakePoolBox | Decremented by emission amount withdrawn |
| **Output** | NewEmissionBox | Replenished with DAO tokens for compound distribution |
| **Output** | EmissionFeeBox | Protocol fee extracted |
| **Output** | NewStakingIncentiveBox | Replenished after fee deduction |
| **Output** | TxOperatorOutputBox | Emit reward |

### Compound Transaction
| Direction | Box | Purpose |
|-----------|-----|---------|
| **Input** | EmissionBox | DAO token reservoir for distribution |
| **Input** | StakeBoxes (N) | Individual user stakes with checkpoint state |
| **Input** | StakingIncentiveBox (SELF) | Variable reward scaled by stake count |
| **Output** | NewEmissionBox | Decremented by distributed amounts |
| **Output** | NewStakeBoxes (N) | Updated with new checkpoint, compounded rewards |
| **Output** | NewStakingIncentiveBox | Replenished |
| **Output** | TxOperatorOutputBox | `BaseCompoundReward + (VariableCompoundReward × stakeCount)` |

### Remove Funds Transaction
| Direction | Box | Purpose |
|-----------|-----|---------|
| **Input** | StakingIncentiveBox (SELF) | Withdrawal request |
| **Output** | NewStakePoolBox | Receives withdrawn ERG |

---

## Key Logic

### Consolidate Validation

```
IF (current_box_value ≤ MaxValue AND output_count == 3) THEN
  - Count all INPUTS with same propositionBytes as SELF (dust boxes)
  - Verify NewStakingIncentiveBox:
    • Has MORE ERG than SELF (consolidation occurred)
    • Protected by identical contract script
  - Verify TxOperatorOutputBox value == DustCollectionReward × dustBoxCount
  - Verify MinerFeeBox value == fixed DustCollectionMinerFee
  - PERMIT transaction
ELSE
  - REJECT
```

### Emit Validation

```
IF (input_count ≥ 3) THEN
  - Identify StakeStateBox (INPUTS[0]) by StakeStateNFT token
  - Identify EmissionBox (INPUTS[2]) by EmissionNFT token
  - Extract stakeStateData from R4: [totalStaked, checkpoint, stakers, lastTimestamp, cycleDuration]
  - Extract emissionAmount from StakePoolBox R4
  - Verify NewStakeStateBox:
    • Contains StakeStateNFT (unchanged)
    • R4 checkpoint incremented by 1
    • R4 lastTimestamp updated to current block timestamp
    • totalStaked and stakers unchanged
  - Verify NewStakePoolBox:
    • DAO token amount decreased by emissionAmount
  - Verify NewEmissionBox:
    • DAO token amount increased by emissionAmount
  - Verify EmissionFeeBox receives extracted protocol fee
  - Verify NewStakingIncentiveBox replenished by (EmitReward + EmitMinerFee)
  - PERMIT transaction
ELSE
  - REJECT
```

### Compound Validation

```
IF (emission_box_found AND stake_boxes_found) THEN
  - Count valid StakeBoxes (contain StakeTokenID)
  - For each stake box:
    • Calculate reward = (emissionAmount / totalStakers) × (currentCheckpoint - stakeCheckpoint)
    • Verify output stake box:
      - Checkpoint set to currentCheckpoint (claims reward)
      - DAO token amount increased by reward
      - StakingTime unchanged
  - Calculate operator reward:
    • Base = BaseCompoundReward
    • Variable = VariableCompoundReward × stakeCount
    • Total = Base + Variable (scales with # stakes to compound)
  - Verify NewEmissionBox DAO token amount decremented by total distributed
  - PERMIT transaction
ELSE
  - REJECT
```

### Remove Funds Validation

```
IF (remove_funds_tx) THEN
  - Verify ERG withdrawn from StakingIncentiveBox to StakePoolBox
  - Verify NewStakingIncentiveBox value reduced accordingly
  - PERMIT transaction
ELSE
  - REJECT
```

---

## Registers Used

### StakingIncentiveBox (SELF)
| Register | Type | Purpose |
|-------