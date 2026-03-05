---
title: paideiadao/paideia-contracts — stake.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/latest/stake.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/latest/stake.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: Stake.es

## Purpose

This contract governs the **compound, unstake, and add stake transactions** for individual stake boxes in the Paideia DAO staking protocol. It validates reward distribution during compound cycles, manages stake additions, and enforces proper stake key-based unstaking by users holding the corresponding Singleton NFT.

---

## Inputs / Outputs

### Compound Transaction
- **Inputs:**
  - `INPUTS(0)`: Emission Box (holds emission rewards and staking state)
  - `INPUTS(stakeBoxIndex)`: `SELF` (current Stake Box)
  
- **Outputs:**
  - `OUTPUTS(stakeBoxIndex)`: New Stake Box (replicated with accumulated rewards)
  - Emission Box and other stake boxes updated off-chain coordination

### Unstake Transaction
- **Inputs:**
  - Stake State Box (tracks global staking state)
  - `SELF`: Stake Box (being unstaked)
  - Unstake Proxy Box (signed proof of user intent)
  
- **Outputs:**
  - Updated Stake State Box
  - User Wallet Box (receives unstaked DAO tokens)
  - (Optionally) New Stake Box (if partial unstake)

### Add Stake Transaction
- **Inputs:**
  - Stake State Box
  - `SELF`: Existing Stake Box
  - Add Stake Proxy Box (contains additional DAO tokens + user pubkey)
  
- **Outputs:**
  - Updated Stake State Box
  - Updated Stake Box (increased staked amount)
  - User Wallet Box (receives Stake Key NFT)

---

## Key Logic

### **Compound Transaction Validation**

1. **Emission Box Identification:** Verify `INPUTS(0)` holds the **Emission NFT** (Singleton token).

2. **Reward Calculation:**
   ```
   rewardAmount = (emissionAmount × stakedAmount) / totalAmountStaked
   ```
   Uses proportional distribution based on individual stake vs. total staked.

3. **Stake Box Self-Replication (`validSelfReplication`):**
   - Box value, propositionBytes (ErgoTree), and stake token preserved
   - **Checkpoint increments** (`R4[0]` incremented by 1)
   - **Staking time preserved** (`R4[1]` unchanged)
   - **Stake Key NFT preserved** (`R5` unchanged)
   - **DAO token balance increases** by `rewardAmount`

### **Unstake Transaction Validation**

1. **Stake Key Verification:**
   - Unstake Proxy Box holds the user's **Stake Key NFT** (must match `SELF.R5`)
   - Proves authorization without requiring user signature (proxy handles it)

2. **User Authorization:**
   - Proxy box contains user's **ErgoTree bytes** (`R5`), validated against expected recipient

3. **Amount Validation:**
   - If unstaking full amount: Entire DAO token balance returned
   - If partial unstake: Remaining balance stays in new Stake Box with updated checkpoint

4. **State Update:**
   - Stake State Box `R4[0]` (total staked) decremented by unstaked amount
   - Staker count decremented if full unstake

### **Add Stake Transaction Validation**

1. **Stake Key Verification:** Add Stake Proxy contains matching **Stake Key NFT**

2. **DAO Token Addition:** New DAO tokens from proxy appended to existing stake box tokens

3. **Staking Time Reset:** Updated to current time (`R4[1]` in new box)

4. **State Increment:** Total staked amount increased in Stake State Box

---

## Registers Used

### Stake Box (`SELF`)

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | `[0]` = Checkpoint (emission cycle counter); `[1]` = Staking Time (block height when staked) |
| **R5** | `Coll[Byte]` | Stake Key ID (Singleton NFT enabling unstake/add-stake) |

### Emission Box (Data Source)

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | `[0]` = Total Amount Staked; `[1]` = Checkpoint; `[2]` = Staker count; `[3]` = Emission Amount |

### Stake State Box (Global State)

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | `[0]` = Total staked; `[1]` = Checkpoint; `[2]` = Staker count; `[3]` = Last checkpoint timestamp; `[4]` = Cycle duration |

### Proxy Boxes (Unstake/Add Stake)

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | `[0]` = Amount (unstake) or Stake time (add-stake) |
| **R5** | `Coll[Byte]` | User's ErgoTree bytes (pubkey for recipient wallet) |

---

## Tokens

### Native Tokens Used

| Token | Holder | Quantity | Purpose |
|-------|--------|----------|---------|
| **Stake Token** | Stake Box (token index 0) | 1 | Singleton NFT proving valid stake box creation; burned if full unstake |
| **DAO Token** | Stake Box (token index 1) | > 0 (variable) | Staked asset; amount increases via compound, decreases via unstake |
| **Stake Key NFT** | Unstake/Add Stake Proxy | 1 | Authorization token; proves user owns the stake box; held in proxy during transaction |
| **Emission NFT** | Emission Box | 1 | Singleton identifier for emission state box |
| **Stake State NFT** | Stake State Box | 1 | Singleton identifier for global staking state |

### Token ID Rule
The contract enforces **constant segregation** of token I