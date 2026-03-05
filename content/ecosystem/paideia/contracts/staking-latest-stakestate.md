---
title: paideiadao/paideia-contracts — stakeState.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/latest/stakeState.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/latest/stakeState.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: `stakeState.es`

## Purpose

The `stakeState` contract is the core state machine governing a DAO staking protocol on Ergo. It validates and manages stake deposits, stake withdrawals (full and partial), and daily emission cycles that distribute rewards from a stake pool to active stakers. This contract maintains the single source of truth for total staked amounts, checkpoint counters, staker counts, and cycle timing.

---

## Inputs / Outputs

### Input Boxes (UTXOs)

The contract processes three distinct transaction types:

**Stake Transaction:**
- **Inputs:**
  - `SELF`: Current Stake State Box (State NFT holder)
  - Stake Proxy Box or Add Stake Proxy Box (user-initiated)
- **Data Inputs:** None

**Emit Transaction:**
- **Inputs:**
  - `SELF`: Current Stake State Box
  - Stake Pool Box (holds DAO token emission reserves)
  - Emission Box (tracks emission state)
  - Staking Incentive Box (covers execution costs)

**Unstake Transaction:**
- **Inputs:**
  - `SELF`: Current Stake State Box
  - Stake Box (user's staking position, identified by Stake Token)
  - Unstake Proxy Box (authorization & amount specification)

### Output Boxes (UTXOs)

**All Transactions:**
- `OUTPUTS(0)`: New Stake State Box (successor to `SELF`)

**Stake Transaction:**
- `OUTPUTS(1)`: New Stake Box (user's staking position record)
- `OUTPUTS(2)`: User Wallet Box (change/refund)

**Emit Transaction:**
- `OUTPUTS(1)`: New Stake Pool Box
- `OUTPUTS(2)`: New Emission Box
- `OUTPUTS(3)`: Emission Fee Box
- `OUTPUTS(4)`: New Staking Incentive Box
- `OUTPUTS(5)`: TX Operator Output Box (bot reward)

**Unstake Transaction:**
- `OUTPUTS(1)`: User Wallet Box (withdrawn tokens)
- `OUTPUTS(2)` *(partial unstake only)*: New Stake Box (remaining position)

---

## Key Logic

### 1. **Self-Replication Invariants** (`validSelfReplication`)

Every valid transaction must preserve the Stake State Box as a singleton with:
- Identical ERG value (storage rent preservation)
- Identical proposition bytes (same ErgoTree)
- Identical State NFT (the **Stake State NFT** in `tokens(0)`)
- Identical Stake Token ID in `tokens(1)._1`
- Constant cycle duration (`cycleDuration`)
- Exactly 2 tokens (State NFT + Stake Token)

This enforces the **State machine invariant**: the contract evolves deterministically with a single valid successor box per transaction.

---

### 2. **Stake Transaction Logic** (`validStakeTx`)

**Identifies stake transactions** by checking if the new stake box contains the Stake Token ID in its first token slot.

**Initial Stake Path:**
- Detects initial stake when `newStakeStateBox.tokens(1)._2 < SELF.tokens(1)._2` (Stake Token amount decreased because one was moved to the user's new Stake Box)
- **Updates:**
  - `totalAmountStaked` increases by the DAO token amount in the Stake Proxy Box
  - `stakers` increments by 1
  - `checkpoint` remains unchanged (carries forward)
- **Validation:** DAO token amount ≥ `MinimumStake` (1,000 tokens)

**Add Stake Path:**
- Detects when an existing Stake Box is consumed alongside an Add Stake Proxy Box
- **Updates:**
  - `totalAmountStaked` increases by additional DAO tokens
  - `stakers` count unchanged
  - `checkpoint` carries forward
- **Validation:** Added amount > 0

**Stake Box Invariants:**
- New Stake Box must contain exactly one Stake Token (NFT)
- New Stake Box must hold DAO tokens (amount > 0)
- R4 in Stake Box stores `[checkpoint, stakingTime]`
- R5 in Stake Box stores the Stake Key ID (used for unstaking)

---

### 3. **Emit Transaction Logic** (`validEmitTx`)

Executes once per cycle (cycle duration = configurable constant).

**Checkpoint Advancement:**
- Detects valid emit by checking if `checkpointOut == checkpoint + 1`
- **Validates timing:** `BlockTime >= checkpointTimestamp + cycleDuration`
- Updates `checkpointTimestamp` to current block timestamp

**Emission Mechanics:**
- Reads `emissionAmount` from Stake Pool Box R4
- Creates New Emission Box with updated state:
  - `totalAmountStaked`, `checkpoint`, `stakers` (copied from updated Stake State)
  - `emissionAmount` (for reward distribution)
- Decrements Stake Pool Box token balance (withdrawal of DAO tokens for emission)

**Bot Incentive:**
- Extracts ERG from Staking Incentive Box to cover:
  - TX operator/bot reward
  - TX mining fee (paid to Ergo network)
- Ensures protocol remains economically sustainable

---

### 4. **Unstake Transaction Logic** (`validUnstakeTx`)

**Identifies unstake** by checking if the Unstake Proxy Box is consumed (R4 contains unstake amount, R5 contains user's ErgoTree).

**Full Unstake Path:**
- When unstake amount equals total Stake Box token balance
- **Updates:**
  - `totalAmountStaked` decreases by withdrawn amount
  - `stakers` decrements by 1
  - Stake Box is destroyed (not propagated to outputs)

**Partial Unstake Path:**
- When unstake amount < total Stake Box token balance
- **Updates:**
  - `totalAmountStaked` decreases
  - `stakers` unchanged
  - Creates New Stake Box with reduced token amount
  - Preserves `checkpoint` and `stakingTime` in new Stake Box

**Authorization Mechanism:**
- Unstake Proxy Box R5 