---
title: paideiadao/paideia-contracts — stake.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.0/stake.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.0/stake.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: Stake.es

## Purpose

This contract manages individual staking positions in the Paideia DAO staking protocol. It enables users to stake tokens (ErgoPad), earn rewards through a compounding mechanism, and unstake their holdings while maintaining state consistency with a central stake state contract.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: 
  - In compound transactions: Emission box (holds emission NFT, total staked amount, and per-checkpoint emission quantity)
  - In unstake/add-stake transactions: Stake state box (holds the Stake State NFT for authorization)
- **INPUTS(1)**: 
  - In unstake/add-stake transactions: Must be SELF (the current stake box), validating the stake exists in inputs
- **SELF**: The stake box being validated (contains user's staked tokens, checkpoint, stake time, and stake key)

### Outputs
- **Compound Transaction**: 
  - Output at same index as SELF: Replicated stake box with incremented checkpoint and compounded token balance
  - Reward tokens distributed back to the stake box
- **Unstake Transaction**:
  - OUTPUTS(0): Updated stake state box (with decremented checkpoint counter)
  - OUTPUTS(1): User output box (receives unstaked tokens)
  - OUTPUTS(2): Optional: Remaining stake box (if partial unstake or re-staking)
- **Add Stake Transaction**:
  - Updated stake state box in OUTPUTS(0)
  - Additional staked tokens added to SELF's token balance

## Key Logic

### Compound Transaction (`compoundTx`)
1. **Precondition**: INPUTS(0) holds the Emission NFT
2. **Proportional Reward Calculation**: 
   - `reward = (emissionAmount × userStake) / totalAmountStaked`
   - Rewards are calculated as a proportional share of total emission
3. **State Consistency**:
   - Stake box is replicated (same script, value, tokens)
   - **Checkpoint incremented** by 1 (tracks emission rounds)
   - **Staked tokens increased** by calculated reward
   - Stake Key and Stake Time remain unchanged
4. **Validation**: All conditions must pass via `allOf()` to authorize compounding

### Unstake Transaction (`unstakeTx`)
1. **Precondition**: INPUTS(1).id == SELF.id (stake box is input)
2. **Stake State Authorization**: Stake state box present in INPUTS(0) with decremented checkpoint (proves state reduction)
3. **Output Handling**:
   - **OUTPUTS(1)**: User receives tokens
   - **OUTPUTS(2)** (optional): If present and matches SELF's script, it must:
     - Retain the same Stake Key (R5)
     - Link user output token to Stake Key (via R5 token ID)
4. **Partial Unstake Support**: Optional remaining stake box allows partial withdrawals

### Add Stake Transaction (`addStakeTx`)
1. **Precondition**: INPUTS(1).id == SELF.id
2. **Stake State Authorization**: Requires Stake State NFT in INPUTS(0)
3. **Action**: Stake state contract handles validation logic; this box only verifies state presence
4. **Design Rationale**: Minimizes stake box size by offloading complex add-stake validation to state contract

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | **Tuple of 2+ longs**: <br> - R4(0): `checkpoint` — tracks emission round for proportional reward calculation <br> - R4(1): `stakeTime` — timestamp of initial stake (immutable, used for lock-up periods or historical tracking) |
| **R5** | `Coll[Byte]` | **Stake Key ID** — User's identifier/public key for unstaking authorization; ensures only the staker can unlock their tokens |

## Tokens

### Token Composition (2 tokens per stake box)

| Index | Type | Quantity | Purpose |
|-------|------|----------|---------|
| **tokens(0)** | **Stake NFT** | 1 | Singleton token proving this is a legitimate stake box; enables box identification and prevents forgery |
| **tokens(1)** | **Staked Token (ErgoPad)** | User-defined | The actual staked asset; balance increases via compounding rewards |

### NFT Authentication

| NFT | Location | Purpose |
|-----|----------|---------|
| **stakeStateNFT** | Constant `_stakeStateNFT` | Identifies the singleton Stake State box; required in INPUTS(0) for unstake and add-stake |
| **emissionNFT** | Constant `_emissionNFT` | Identifies the Emission box; triggers compound transaction pathway |

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

#### 1. **Compound Transaction Construction**
```
For each stake box:
  → Fetch Emission box (with emissionNFT)
  → Calculate: reward = (emissionAmount × userStake) / totalStaked
  → Build output stake box:
    - Copy SELF's propositionBytes (ErgoTree)
    - Copy SELF's value (nERG)
    - Set R4[0] = checkpoint + 1
    - Set R4[1] = stakeTime (unchanged)
    - Set R5 = stakeKey (unchanged)
    - Set tokens(1)._2 = userStake + reward
  → Submit transaction
```

#### 2. **Unstake Transaction Construction**
```
User initiates unstake:
  → Fetch stake box
  → Fetch Stake State box (with stakeStateNFT)
  → Verify checkpoint decrements in state box output
  → Construct outputs:
    - OUTPUTS(0): Updated Stake State box (checkpoint - 1)
    - OUTPUTS(1): User output with unstaked tokens
    - OUTPUTS(2)* (optional): Remaining stake box if partial unstake
  → Submit transaction
```

#### 3. **Add Stake Transaction Construction**
```
User adds tokens to stake: