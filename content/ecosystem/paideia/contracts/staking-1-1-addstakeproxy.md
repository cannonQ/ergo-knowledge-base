---
title: paideiadao/paideia-contracts — addStakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.1/addStakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.1/addStakeProxy.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: addStakeProxy

## Purpose

This contract acts as a **proxy input box** that facilitates the addition of stake tokens to an existing staking position. It validates either a successful stake accumulation transaction (where tokens are deposited into a staking contract) or a refund transaction that returns assets to the user minus a small storage rent fee.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: State box holding the **stakeStateNFT** (Singleton / State NFT) — authenticates the staking system
- **INPUTS(1)**: Existing staking position box containing accumulated stake tokens
- **SELF**: Proxy box (this contract) holding user's additional stake tokens to be added, plus a stake key NFT

### Outputs (Add Stake Path)
- **OUTPUTS(0)**: (implicit, not checked — may contain change or other value)
- **OUTPUTS(1)**: Updated staking position box with increased token balance
- **OUTPUTS(2)**: User output box, receives the stake key NFT as proof of ownership
- **OUTPUTS(3)**: Staking incentive contract box (receives protocol reward)
- **OUTPUTS(4)**: Executor reward box (compensates off-chain transaction orchestrator)
- **OUTPUTS(5)**: Miner fee box (pays Ergo network)

### Outputs (Refund Path)
- **OUTPUTS(0)**: User output box, receives all assets minus 1 erg (storage rent)
- **OUTPUTS(1)**: Miner fee box

## Key Logic

### Add Stake Transaction (`addStakeTx`)

The contract validates a staking operation through three layers:

1. **State Authentication**: INPUTS(0) must contain the stakeStateNFT, confirming the transaction is part of an authorized staking protocol action.

2. **Token Accumulation**:
   - Stake token quantity in OUTPUTS(1) equals prior quantity (INPUTS(1)) plus user's contribution (SELF.tokens(1)._2)
   - Stake token ID remains unchanged (immutability constraint)

3. **Ownership & Incentive Distribution**:
   - User receives a stake key NFT (OUTPUTS(2)), a Singleton token proving their staking position ownership
   - Staking incentive contract receives exact protocol-defined value (`toStakingIncentive`)
   - Transaction executor compensated with `executorReward`
   - Miner receives `minerFee` for network inclusion
   - Output structure is exactly 6 boxes (strict invariant)

4. **User Authentication**: Propositions bytes (ErgoTree script) in OUTPUTS(2) match the user's stored proposition (R5), ensuring refund and withdrawal operations can only be executed by the rightful owner.

### Refund Transaction (`refundTx`)

Allows the user to abort the staking operation:
- User receives all assets in SELF minus 1 erg (storage rent for blockchain maintenance)
- Tokens returned intact
- Exactly 2 outputs (user box + implied miner fee or change)
- User's proposition bytes enforced

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | (Not used in this contract) | Reserved for stakeTime in the staking state machine |
| **R5** | `Coll[Byte]` | **User's proposition bytes** (ErgoTree) — stored in SELF, used to authorize the user output in add-stake or refund paths |
| **R5 (OUTPUTS(1))** | `Coll[Byte]` | **Stake key** — NFT identifier extracted from updated staking position, sent to user as proof |

## Tokens

1. **Stake State NFT** (`stakeStateNFT`): 
   - Singleton token in INPUTS(0)
   - Authenticates the staking system state
   - Prevents unauthorized or duplicate staking operations

2. **Stake Key NFT** (`stakeKey`):
   - Retrieved from `OUTPUTS(1).R5`
   - Sent to user in `OUTPUTS(2)` with quantity exactly `1L`
   - Represents ownership of the staking position
   - Enables later withdrawal or modification operations

3. **Stake Tokens** (`SELF.tokens(1)`):
   - User's contribution to accumulate in the staking position
   - Token ID must match existing staking position token ID (immutability)
   - Quantity added to staking output

## Integration Pattern

### Off-Chain Bot / Executor Responsibilities

1. **Monitor**: Watch for proxy boxes (SELF) created by users containing stake tokens and the stake key NFT.

2. **Fetch State**: 
   - Retrieve the current staking state box (holding stakeStateNFT)
   - Retrieve the user's existing staking position box (INPUTS(1))

3. **Construct Transaction**:
   - **Input**: Proxy box (SELF) + staking state box (INPUTS(0)) + staking position box (INPUTS(1))
   - **Output**: 6 boxes exactly:
     - Updated staking position (with accumulated tokens and preserved stake key in R5)
     - User box (with stake key NFT, user's proposition)
     - Incentive contract box (value = `toStakingIncentive`)
     - Executor reward box (value = `executorReward`)
     - Miner fee box (value = `minerFee`)
   - **Context Extension**: Provide constants: `_stakeStateNFT`, `_stakingIncentiveContract`, `_toStakingIncentive`, `_executorReward`, `_minerFee`

4. **Sign**: Use the executor's key to satisfy the Sigma protocol on other inputs if needed.

5. **Refund Path** (if staking fails or is cancelled):
   - Construct simpler 2-output transaction
   - Return user's assets minus 1 erg to their address
   - User must provide signature (propositionBytes in R5)

### Validation Guarantees

- **Atomic state transition**: Staking position is updated only if all output constraints are met; no partial execution possible.
- **Minimum box value**: Ensures all outputs meet the eUTXO minimum value requirement (implicitly via executor reward and miner fee).
- **Storage rent