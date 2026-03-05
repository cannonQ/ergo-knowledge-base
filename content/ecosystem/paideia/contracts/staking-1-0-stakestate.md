---
title: paideiadao/paideia-contracts — stakeState.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.0/stakeState.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.0/stakeState.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: stakeState

## Purpose

The **stakeState** contract governs the core state machine for a DAO staking protocol on Ergo. It manages state transitions across stake (initial and add-stake), emit (daily reward distribution), and unstake (full and partial withdrawal) transactions, maintaining invariants for total staked amounts, checkpoint tracking, and staker counts.

---

## Inputs / Outputs

### Transaction Types & Box Flow

#### **Stake Transaction (Initial)**
- **Inputs:**
  - `SELF`: Stake State Box (state machine box)
  - Stake Proxy Box (user's intent to stake DAO tokens)
- **Outputs:**
  - New Stake State Box (updated state)
  - New Stake Box (user's staking position, holds Stake Token NFT + DAO tokens)
  - User Wallet Box (change/refund)

#### **Add Stake Transaction**
- **Inputs:**
  - `SELF`: Stake State Box
  - Existing Stake Box (user's prior staking position)
  - Add Stake Proxy Box (additional DAO tokens + Stake Key)
- **Outputs:**
  - New Stake State Box
  - Updated Stake Box
  - User Wallet Box

#### **Emit Transaction (Daily Reward Distribution)**
- **Inputs:**
  - `SELF`: Stake State Box
  - Stake Pool Box (holds DAO tokens for emission)
  - Emission Box (tracks emission state across cycles)
  - Staking Incentive Box (treasury/fee account)
- **Outputs:**
  - New Stake State Box
  - New Stake Pool Box
  - New Emission Box
  - Emission Fee Box
  - New Staking Incentive Box
  - Tx Operator Output Box (operator fee)

#### **Unstake Transaction (Full or Partial)**
- **Inputs:**
  - `SELF`: Stake State Box
  - Stake Box (user's staking position)
  - Unstake Proxy Box (Stake Key + unstake amount intent)
- **Outputs (Full Unstake):**
  - New Stake State Box
  - User Wallet Box (with DAO tokens + accrued rewards)
- **Outputs (Partial Unstake):**
  - New Stake State Box
  - User Wallet Box (withdrawn amount + rewards)
  - New Stake Box (remaining stake)

---

## Key Logic

### **Invariant: Self-Replication**

Every transaction **must preserve the Stake State Box** with:
- **Same ERG value** (no value extraction by operators)
- **Same ErgoTree** (contract code unchanged)
- **Same Stake State NFT** (token ID `0`: singleton identifier, amount = 1)
- **Same Stake Token ID** (token ID `1`: minting authority for Stake Boxes)
- **Cycle Duration constant** (emission schedule immutable)
- **Exactly 2 tokens** (Stake State NFT + Stake Token ID authority)

### **Stake Transaction Validation**

1. **Detect Stake Type:**
   - If `OUTPUTS(1).tokens(0)._1 == stakeTokenID` → This is a Stake Tx

2. **Distinguish Initial vs. Add-Stake:**
   - `isInitialStake = newStakeStateBox.tokens(1)._2 < SELF.tokens(1)._2`
     - Initial stake: Stake Token supply **decreases** (new Stake Box consumes one)
     - Add-stake: User's existing Stake Box receives additional tokens

3. **Initial Stake Validation:**
   - Input: Stake Proxy Box with DAO tokens + staking timestamp
   - Output: Stake Box with:
     - Register R4: `[checkpoint, stakingTime]`
     - Register R5: Stake Key ID (user's identity for unstaking)
     - Token 0: Stake Token (proves legitimacy)
     - Token 1: DAO tokens staked
   - State updates:
     - `totalAmountStaked` incremented
     - `stakers` count incremented
     - `checkpoint` updated to current emission cycle

4. **Add-Stake Validation:**
   - Input: Existing Stake Box + Add Stake Proxy Box (Stake Key + additional DAO tokens)
   - Output: Stake Box with increased token amount
   - State updates:
     - `totalAmountStaked` incremented
     - `stakers` count **unchanged**
     - Checkpoint updated

### **Emit Transaction Validation**

- **Runs daily** to distribute rewards
- **Inputs:** Stake Pool (source of emission), Emission Box (cycle state), Staking Incentive Box (fee pool)
- **Outputs:** New Emission Box with updated checkpoint, redistributed DAO tokens
- **State updates:**
  - `checkpoint` incremented (new emission cycle)
  - `checkpointTimestamp` advanced by cycle duration
  - Stake Pool DAO token balance reduced

### **Unstake Transaction Validation**

1. **Input Validation:**
   - Stake Box contains user's Stake Token
   - Unstake Proxy Box contains matching Stake Key (proof of ownership)

2. **Full Unstake:**
   - All staked DAO tokens returned + accrued rewards
   - Stake Box destroyed (token burned)
   - `totalAmountStaked` decremented
   - `stakers` count decremented

3. **Partial Unstake:**
   - Specified amount returned
   - Remaining stake in new Stake Box (with checkpoint preserved)
   - `totalAmountStaked` decremented (by withdrawal amount only)

---

## Registers Used

| Register | Type | Purpose | Used In |
|----------|------|---------|---------|
| **R4** (Stake State) | `Coll[Long]` | `[totalAmountStaked, checkpoint, stakers, checkpointTimestamp, cycleDuration]` | All transactions; tracks protocol state |
| **R4** (Stake Box) | `Coll[Long]` | `[checkpoint, stakingTime]` | Stake/Add-Stake outputs; tracks user's entry point |
| **R5** (Stake Box) | `Coll[Byte]` |