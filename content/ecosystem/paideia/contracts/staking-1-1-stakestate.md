---
title: paideiadao/paideia-contracts — stakeState.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.1/stakeState.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.1/stakeState.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: `stakeState.es`

## Purpose

The `stakeState` contract is the **state machine hub** for a Paideia DAO staking protocol. It governs all state transitions across stake creation, token emission, and unstaking operations by validating that the Stake State Box (a Singleton State NFT box) is updated correctly in each transaction type while preserving protocol invariants.

## Inputs / Outputs

### Input Boxes (UTXO Context)

| Transaction Type | Input Boxes | Purpose |
|---|---|---|
| **Stake (Initial)** | Stake State Box (SELF), Stake Proxy Box | User initiates staking; proxy holds DAO tokens |
| **Add Stake** | Stake State Box (SELF), Existing Stake Box, Add Stake Proxy Box | User adds tokens to existing stake; uses Stake Key NFT |
| **Emit** | Stake State Box (SELF), Stake Pool Box, Emission Box, Staking Incentive Box | Daily reward distribution; emits tokens from pool |
| **Unstake (Full/Partial)** | Stake State Box (SELF), Stake Box, Unstake Proxy Box | User removes staked tokens; uses Stake Key NFT |

### Output Boxes (UTXO Creation)

| Transaction Type | Output Boxes | State Changes |
|---|---|---|
| **Stake** | New Stake State Box, New Stake Box, User Wallet Box | Increment `stakers` & `totalAmountStaked`; mint Stake Key NFT |
| **Add Stake** | New Stake State Box, Updated Stake Box, User Wallet Box | Increment `totalAmountStaked` only; no staker increment |
| **Emit** | New Stake State Box, New Stake Pool Box, New Emission Box, Fee Box, Incentive Box, Operator Box | Increment `checkpoint`; transfer emission tokens |
| **Unstake** | New Stake State Box, User Wallet Box, (Optional) New Stake Box | Decrement `totalAmountStaked` & `stakers`; burn Stake Key NFT (full unstake) |

## Key Logic

### **Invariant: Valid Self-Replication**
Every output Stake State Box must satisfy:
- **ERG value preserved**: `newStakeStateBox.value == SELF.value`
- **Contract identity maintained**: `newStakeStateBox.propositionBytes == SELF.propositionBytes` (same ErgoTree)
- **State NFT preserved**: Token at index 0 (Stake State NFT) remains identical
- **Stake Token ID preserved**: Token at index 1 (Stake Token ID) unchanged
- **Exactly 2 tokens**: No phantom tokens introduced
- **Cycle duration immutable**: `cycleDurationOut == cycleDuration`

### **Stake Transaction Logic**
1. **Detection**: Check if output box at index 1 has the Stake Token ID (`OUTPUTS(1).tokens(0)._1 == stakeTokenID`)
2. **Initial Stake Branch**:
   - Stake token amount decreases in state box → **minting new Stake Key NFT**
   - Increment `stakers` counter by 1
   - Increment `totalAmountStaked` by staked DAO token amount
   - Validate: staked amount ≥ `MinimumStake` (1000 tokens)
   - Validate: `OUTPUTS(1)` is a valid new Stake Box with correct registers (checkpoint, stake time)
3. **Add Stake Branch**:
   - Stake token amount constant in state box → **no new key**
   - `stakers` counter unchanged
   - Increment `totalAmountStaked` only
   - Validate: existing Stake Box is consumed from inputs and updated

### **Emit Transaction Logic**
- Triggered once per day
- Validate checkpoint advancement and timestamp progression
- Transfer emission allocation from Stake Pool Box to new Emission Box
- Fee collection for transaction execution
- Incentive box refunding to operator

### **Unstake Transaction Logic**
1. **Full Unstake**: All staked tokens withdrawn
   - Decrement `stakers` by 1
   - Decrement `totalAmountStaked` by full amount
   - Burn Stake Key NFT (stake token amount increases in state box)
   - Return DAO tokens to user wallet
2. **Partial Unstake**: Remove portion of stake
   - `stakers` unchanged
   - Decrement `totalAmountStaked` by partial amount
   - Stake Box persists with reduced balance
   - Stake Key NFT preserved

### **State Machine Transitions**
```
Initial State: totalAmountStaked=0, stakers=0, checkpoint=0
    ↓
Stake TX → stakers++, totalAmountStaked += amount, Stake Key minted
    ↓
Add Stake TX → totalAmountStaked += amount (stakers unchanged)
    ↓
Emit TX → checkpoint++, emission distributed
    ↓
Unstake TX → stakers--, totalAmountStaked -= amount, Stake Key burned
```

## Registers Used

### Stake State Box (SELF)

| Register | Type | Index | Purpose |
|---|---|---|---|
| **R4** | `Coll[Long]` | — | State vector (5 elements) |
| — | Long | [0] | **Total Amount Staked**: cumulative DAO tokens locked |
| — | Long | [1] | **Checkpoint**: emission cycle counter (incremented per emit TX) |
| — | Long | [2] | **Stakers**: count of active staking users |
| — | Long | [3] | **Last Checkpoint Timestamp**: time of last emit; validates cycle duration |
| — | Long | [4] | **Cycle Duration**: constant milliseconds between emissions (hard-coded immutable) |

### Stake Box (Individual User)

| Register | Type | Purpose |
|---|---|---|
| **R4** | `Coll[Long][2]` | `[0]` = Checkpoint (at time of stake), `[1]` = Staking Time (block timestamp) |
| **R5** | `Coll[Byte]` | **Stake Key ID**: serialized hash/ID