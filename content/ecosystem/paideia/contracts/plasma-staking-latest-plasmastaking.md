---
title: paideiadao/paideia-contracts — plasmaStaking.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/plasma_staking/ergoscript/latest/plasmaStaking.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/plasma_staking/ergoscript/latest/plasmaStaking.es
project: paideiadao-paideia-contracts
---
# Plasma Staking Contract Analysis

## Purpose

This contract manages a **plasma staking state machine** where users stake tokens to earn emission-based rewards. It maintains staker records via an AVL tree, tracks historical snapshots for reward distribution, and supports five transaction types: stake creation, stake modification, unstaking, periodic snapshots, and reward compounding.

---

## Inputs / Outputs

### Inputs
- **SELF (INPUTS(0))**: The Plasma Staking singleton box containing:
  - State NFT (`tokens(0)`) for authentication
  - Staked token pool (`tokens(1)`) tracking total staked value
  - AVL tree of active staker balances (R4)
  - Configuration parameters in R5 (emission amount, delay, cycle length, snapshot index, staker count, total staked)
  - Historical snapshots in R6

- **INPUTS(1)** (conditional):
  - For UNSTAKE: User's staker NFT box to be consumed
  - For other operations: may be absent

### Outputs
- **OUTPUTS(0)**: Updated Plasma Staking box with same:
  - Script hash (propositionBytes)
  - State NFT and staked token pool (with modified quantities)
  - Updated registers reflecting new state

- **OUTPUTS(1)** (conditional):
  - For STAKE: User receives newly minted staker NFT
  - For CHANGE_STAKE: User's staker NFT box with updated stake amount
  - For other operations: may be absent

---

## Key Logic

### Transaction Type Routing
The contract validates **five mutually-exclusive operation types** (0–4), specified via context variable 0:

| Type | Operation | Core Validation |
|------|-----------|-----------------|
| **0: STAKE** | Add new staker | Mint 1 staker NFT, insert key into AVL tree, verify token amount matches state delta |
| **1: CHANGE_STAKE** | Modify existing stake | Update AVL tree entry, verify staker NFT key exists in output, check token delta matches state change |
| **2: UNSTAKE** | Remove staker completely | Remove key from AVL tree, verify staker NFT consumed from input, unstaked tokens returned |
| **3: SNAPSHOT** | Record periodic state | Prepend new snapshot (staker count, total staked, AVL tree) to history, shift old snapshots, maintain emission delay window |
| **4: COMPOUND** | Distribute & reinvest rewards | Calculate rewards per staker from `emissionAmount` using historical snapshot proportions, update stakes and total, clean snapshot history |

### Invariants Enforced

1. **Output Integrity**: Successor box must have identical script hash and state NFT
2. **Token Conservation**: Changes to staked token quantity must match AVL tree state mutations
3. **AVL Tree Validity**: All operations verified against provided cryptographic proofs
4. **Snapshot Window**: History size capped at `emissionDelay` entries; oldest snapshot removed when threshold reached
5. **Reward Calculation**: `reward[i] = (snapshotStake[i] * emissionAmount) / snapshotTotalStaked`
6. **Stake Consistency**: Total staked amount in R5 must equal sum of all AVL tree entries

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `AvlTree` | Authenticated set of staker keys → stake amount (encoded as 8-byte long prefix in value) |
| **R5** | `Coll[Long]` | Configuration tuple: `[emissionAmount, emissionDelay, cycleLength, nextSnapshot, stakers, totalStaked]` |
| **R6** | `Coll[(Long, (Long, AvlTree))]` | Historical snapshots; each entry: `(staker_count, (total_staked, avl_tree_snapshot))` indexed from 0 (most recent) |

---

## Tokens

### State NFT (`tokens(0)`)
- **Purpose**: Singleton authentication — ensures only legitimate successor boxes update state
- **Invariant**: `propositionBytes` and token ID must match between SELF and output
- **Quantity**: Always 1 (not modified)

### Staked Token Pool (`tokens(1)`)
- **Purpose**: Reserve of user-staked tokens; quantity encodes total value staked
- **Mutations**:
  - **STAKE**: Increases by `stakeAmount`
  - **CHANGE_STAKE**: Delta equals new stake minus current stake
  - **UNSTAKE**: Decreases by unstaked amount
  - **SNAPSHOT/COMPOUND**: No direct change; COMPOUND increases due to reward inclusion in state

---

## Integration Pattern

### Off-Chain Workflow

1. **Read SELF box** from blockchain to extract:
   - Current AVL tree digest and snapshot history
   - Total staked, staker count, emission parameters

2. **Construct transaction** based on operation type:

   **STAKE:**
   - Prepare: `stakeOperations = [(staker_id, longToByteArray(amount))]`
   - Generate: AVL tree insertion proof for `staker_id`
   - Set context vars: `(0 → STAKE, 1 → stakeOperations, 2 → proof)`
   - Mint: 1 NFT with ID = SELF.id in OUTPUTS(1)

   **CHANGE_STAKE:**
   - Prepare: `stakeOperations = [(staker_id, longToByteArray(newAmount))]`
   - Generate: AVL tree update proof
   - Set context vars: `(0 → CHANGE_STAKE, 1 → stakeOperations, 2 → proof)`
   - User provides OUTPUTS(1) with updated NFT

   **UNSTAKE:**
   - Set context vars: `(0 → UNSTAKE, 1 → [staker_id], 2 → proof)`
   - Consume user's staker NFT in INPUTS(1)
   - Tokens returned in OUTPUTS(1)

   **SNAPSHOT:**
   - Set context var: `0 → SNAPSHOT` (no proofs needed)
   - Contract auto-constructs new snapshot from R4, R5
   - Shifts history and truncates