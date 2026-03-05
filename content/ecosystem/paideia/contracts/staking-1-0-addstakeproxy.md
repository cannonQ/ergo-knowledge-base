---
title: paideiadao/paideia-contracts — addStakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.0/addStakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.0/addStakeProxy.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: `addStakeProxy.es`

## Purpose

This contract acts as a **proxy box for stake deposits** in a staking protocol, enabling users to atomically add their tokens to an existing stake position or refund their deposit. It validates that stake tokens are properly combined with the staking state and distributes rewards to the staking incentive contract, transaction executor, and miners.

---

## Inputs / Outputs

### Inputs
- **SELF** (INPUTS(0)): The proxy box itself, holding:
  - Native tokens to stake (token ID in `tokens(1)`)
  - User's redemption key or proof (R5)
  - ERG for transaction fees and rewards
  
- **INPUTS(1)** (conditionally): The active stake box, identified by holding the **State NFT** (`stakeStateNFT`), containing:
  - Current stake token quantity in `tokens(1)`
  - Stake metadata in registers

### Outputs
For **addStakeTx** path (6 outputs):
- **OUTPUTS(0)**: (implicit) Stake state box (advanced with State NFT)
- **OUTPUTS(1)**: Updated stake box with combined token amount
- **OUTPUTS(2)**: User output box, locked to user's `propositionBytes`, holding the **stake key** NFT
- **OUTPUTS(3)**: Staking incentive contract box (receives `toStakingIncentive` ERG)
- **OUTPUTS(4)**: Executor reward output (`executorReward` ERG)
- **OUTPUTS(5)**: Miner fee output (`minerFee` ERG)

For **refundTx** path (2 outputs):
- **OUTPUTS(0)**: User refund box (all tokens + ERG minus 1000000 nanoERG storage rent)
- **OUTPUTS(1)**: (implicit) Change or miner fee

---

## Key Logic

### **Add Stake Transaction Path** (`addStakeTx`)

1. **State Validation**: Verify INPUTS(0) holds the `stakeStateNFT` token (singleton pattern).

2. **Token Consolidation**:
   - Ensure output stake box tokens increase by exactly `SELF.tokens(1)._2` (amount from proxy)
   - Verify token ID is preserved: `stakeOutput.tokens(1)._1 == SELF.tokens(1)._1`

3. **Stake Key Distribution**:
   - Extract stake key from updated stake box (R5)
   - Mint/send exactly 1 stake key NFT to user output
   - Lock user output to user's original `propositionBytes` (from R5)

4. **Value Distribution**:
   - Route `toStakingIncentive` to staking incentive contract (validated via `blake2b256` hash)
   - Send `executorReward` to off-chain executor (bot/relayer)
   - Reserve `minerFee` for network miners
   - Enforce exactly 6 outputs (atomic completion)

### **Refund Transaction Path** (`refundTx`)

1. Return all tokens to user unchanged
2. Return ERG minus 1,000,000 nanoERG (standard storage rent)
3. Allow a second output (presumed for miner fee)
4. Unlock via user's original `propositionBytes`

### **Authorization**
Requires valid Sigma proof from the proposer (either path may be executed if signature is provided).

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | `stakeTime` — timestamp when stake was initiated (read-only, passed in constants) |
| **R5** | `Coll[Byte]` | **User's proposition bytes** — ErgoTree of the user's wallet; used to lock refund/stake key outputs back to the user |

*Note: Stake output box (OUTPUTS(1)) also sets R5 with the stake key identifier for future state transitions.*

---

## Tokens

### **State NFT** (`stakeStateNFT`)
- **Type**: Native token (NFT, quantity = 1)
- **Role**: Singleton token identifying the active staking state box
- **Location**: INPUTS(0).tokens(0)
- **Purpose**: Prevents double-spending of staking state; ensures only one valid staking pool exists

### **Stake Tokens** (`SELF.tokens(1)` and `stakeOutput.tokens(1)`)
- **Type**: Native token (fungible, any quantity)
- **Role**: The asset being staked (e.g., PAIDEIA governance token)
- **Purpose**: Accumulates user deposits; quantity increases by user's contribution

### **Stake Key** (`stakeKey`)
- **Type**: Native token (NFT, quantity = 1)
- **Role**: Proof of ownership and unlock key for the user's stake position
- **Location**: Extracted from updated stake box (R5), sent to user output
- **Purpose**: Allows user to later withdraw or claim rewards

---

## Integration Pattern

### Off-Chain Bot / Executor Responsibilities

1. **Monitor**: Watch for proxy boxes created by users (holding tokens + ERG at this contract's address).

2. **Validate Stake State**:
   - Fetch the current staking state box (holding `stakeStateNFT`)
   - Read staking parameters: incentive address, executor reward, miner fee from state or oracle

3. **Construct Transaction**:
   - Build INPUTS: proxy box + staking state box
   - Build OUTPUTS (6 boxes):
     - Advanced staking state box (incremented token count)
     - Updated stake box
     - User output (locked to user's `propositionBytes`, holding stake key)
     - Incentive contract output
     - Executor payment output
     - Miner fee output
   - Ensure all tokens and value balance correctly

4. **Sign & Submit**:
   - Sign SELF input with user's private key (via context extension or wallet)
   - Submit transaction to network

### Refund Path (User-Initiated)
- User can directly sign SELF and create a simple 2-output refund transaction
- No off-chain coordination needed (direct exit)

---

## Related Contracts

### **Staking Incentive Contract** (`