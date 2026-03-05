---
title: paideiadao/paideia-contracts — stake.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.1/stake.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.1/stake.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: `stake.es`

## Purpose

This contract governs the staking lifecycle for a DAO token staking protocol on Ergo. It validates three core transaction types: **compound** (distribute emission rewards to stake boxes), **stake** (add new or additional DAO tokens to a stake position), and **unstake** (withdraw staked tokens). The contract acts as a state machine that preserves staking positions across emission cycles while enforcing cryptographic authorization via Stake Key NFTs.

---

## Inputs / Outputs

### **Compound Transaction**
- **Inputs:**
  - `INPUTS(0)`: Emission Box (holds DAO rewards and emission parameters)
  - `INPUTS(1..n)`: Stake Boxes (user staking positions; `SELF` is one of these)
  - Staking Incentive Box (optional; referenced in documentation)

- **Outputs:**
  - `OUTPUTS(stakeBoxIndex)`: New Stake Box (replicated with updated token balance + reward)
  - `OUTPUTS(0)`: New Emission Box (updated with reduced token supply)
  - Transaction Operator Output Box (fee collection)

### **Stake Transaction**
- **Inputs:**
  - Stake State Box (tracks total staked amount, checkpoints, staker count)
  - Stake Proxy Box OR Add Stake Proxy Box + existing Stake Box
  - New or existing Stake Box (in add-stake variant)

- **Outputs:**
  - New Stake State Box (updated metrics)
  - New or updated Stake Box
  - User Wallet Box (receives Stake Key NFT on initial stake)

### **Unstake Transaction**
- **Inputs:**
  - Stake State Box
  - Stake Box (`SELF`)
  - Unstake Proxy Box (contains amount to unstake and user ErgoTree)

- **Outputs:**
  - New Stake State Box (decremented metrics)
  - User Wallet Box (receives unstaked DAO tokens)
  - New Stake Box (optional; if partial unstake, remaining position is replicated)

---

## Key Logic

### **Compound Transaction Validation** (`validCompoundTx`)

1. **Input Validation:**
   - First input must hold the **Emission NFT** (Singleton identifier)
   - Emission Box contains: `[totalAmountStaked, checkpoint, stakers, emissionAmount]`

2. **Reward Calculation:**
   - `rewardAmount = (emissionAmount × userStakedAmount) / totalAmountStaked`
   - Proportional distribution: rewards scale with user's stake fraction

3. **Stake Box Replication** (`validSelfReplication`):
   - **Value preserved:** `newStakeBox.value == SELF.value` (Ergo native coins)
   - **Guard unchanged:** `newStakeBox.propositionBytes == SELF.propositionBytes` (same contract)
   - **Checkpoint incremented:** `R4[0]` increases by 1 (emission cycle counter)
   - **Staking time immutable:** `R4[1]` unchanged (original stake timestamp)
   - **Stake Key preserved:** `R5` unchanged (authorization token)
   - **Stake Token (NFT) preserved:** `tokens(0)` unchanged (1 unit of proof NFT)
   - **Reward added to stake:** `tokens(1)._2 += rewardAmount` (DAO token balance grows)

### **Unstake Transaction Validation** (`validUnstakeTx`)

*Logic truncated in provided code; inferred structure:*

1. **Authorization:**
   - Unstake Proxy Box must contain the correct Stake Key (matches `SELF.R5`)
   - Proxy `R5` contains user's ErgoTree (destination address)
   - Proxy `R4[0]` specifies amount to unstake

2. **State Transition:**
   - **Full unstake:** Stake Box consumed entirely; user receives all DAO tokens + accrued rewards
   - **Partial unstake:** New Stake Box created with reduced balance; `R4[0]` (checkpoint) likely reset or updated

3. **Stake State Box Update:**
   - `R4[0]` (totalAmountStaked) decremented by unstaked amount
   - `R4[2]` (stakers count) decremented if full unstake

---

## Registers Used

| Register | Type | Purpose | Mutable |
|----------|------|---------|---------|
| **R4** (Stake Box) | `Coll[Long]` | `[checkpoint, stakingTime]` | Checkpoint increments on compound; Time immutable |
| **R5** (Stake Box) | `Coll[Byte]` | Stake Key NFT ID | Immutable (authorization token) |
| **R4** (Stake State Box) | `Coll[Long]` | `[totalStaked, checkpoint, stakers, lastTimestamp, cycleDuration]` | Updated on stake/unstake/compound |
| **R5** (Stake Pool Box) | `Coll[Byte]` | Stake Pool Key (governance) | Immutable |
| **R4** (Emission Box) | `Coll[Long]` | `[totalStaked, checkpoint, stakers, emissionAmount]` | Updated after compound |
| **R5** (Emission Box) | — | (not specified in excerpt) | — |
| **R4** (Proxy Boxes) | `Coll[Long]` | `[unstakeAmount]` or `[stakeTime]` | Consumed in transaction |
| **R5** (Proxy Boxes) | `Coll[Byte]` | User ErgoTree (recipient address) | Consumed in transaction |

---

## Tokens

### **Stake Box Tokens**
| Token | Index | Quantity | Purpose |
|-------|-------|----------|---------|
| **Stake Token** | `0` | 1 | NFT proving this box was created by the staking protocol; preserved across all TXs |
| **DAO Token** | `1` | `> 0` | User's staked amount; increases on compound and add-stake; decreases on unstake |

### **Stake State Box Tokens**
| Token |