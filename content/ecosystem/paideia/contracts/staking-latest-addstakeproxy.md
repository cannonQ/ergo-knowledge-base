---
title: paideiadao/paideia-contracts — addStakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/latest/addStakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/latest/addStakeProxy.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: addStakeProxy.es

## Purpose

This contract serves as a **proxy entry point** for users to add stake to a staking pool. It validates two mutually exclusive transaction paths: either a valid stake addition that routes funds to a staking incentive contract with proper fee distribution, or a refund transaction that returns the user's assets minus a storage rent fee.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: State box holding the `stakeStateNFT` (Singleton / State NFT) — validates transaction legitimacy
- **INPUTS(1)**: Existing stake box containing accumulated staked tokens
- **SELF**: Proxy box containing user's tokens to be staked and user's proposition bytes in R5

### Outputs (addStakeTx path)
0. *Implicit* — typically governance/protocol output
1. **OUTPUTS(1)**: Updated stake box with aggregated token amounts
2. **OUTPUTS(2)**: User output returning the stake key NFT to user's address
3. **OUTPUTS(3)**: Incentive contract box receiving `toStakingIncentive` ergs
4. **OUTPUTS(4)**: Executor reward box (off-chain bot compensation)
5. **OUTPUTS(5)**: Miner fee box

### Outputs (refundTx path)
0. **OUTPUTS(0)**: User output with original tokens minus 1 erg (storage rent)
1. **OUTPUTS(1)**: *Implicit* — typically miner fee output

## Key Logic

### addStakeTx Validation
The transaction is valid if:
1. **State verification**: INPUTS(0) contains the `stakeStateNFT`, proving the transaction references the correct protocol state
2. **Token aggregation**: Staked token amount in OUTPUTS(1) equals prior stake amount plus new stake amount (SELF.tokens(1)._2)
3. **Token ID preservation**: Token type (ID) remains unchanged during consolidation
4. **Stake key distribution**: User receives exactly one stake key NFT (OUTPUTS(2)) with the correct key ID from R5 of the stake output
5. **User recovery**: User output has the correct proposition bytes (ErgoTree), recovering their address
6. **Incentive routing**: Incentive output's script hash (blake2b256) matches the staking incentive contract constant
7. **Fee distribution**: 
   - Incentive contract receives `toStakingIncentive` ergs
   - Executor receives `executorReward` ergs
   - Miner receives `minerFee` ergs
8. **Transaction structure**: Exactly 6 outputs are produced (strict box count invariant)

### refundTx Validation
Simple exit path allowing the user to recover their stake with minimal loss:
1. User output proposition bytes match stored user proposition
2. User receives all original tokens unchanged
3. User loses exactly 1 erg (0.001 ERG) to cover storage rent
4. Exactly 2 outputs produced (user output + implicit miner fee)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | **Unused** — intended for stake time tracking (documented but not read) |
| **R5** | `Coll[Byte]` | **User's ErgoTree** — stores the proposition bytes of the user's address for output recovery |

## Tokens

### Stake State NFT
- **ID**: `_stakeStateNFT` (injected constant)
- **Purpose**: Singleton token ensuring only one canonical staking state box exists per protocol
- **Role**: Guards against double-spending and replay attacks by anchoring the transaction to verified protocol state

### Stake Key NFT
- **ID**: Derived from stake box's R5 register
- **Purpose**: Authorization token returned to user proving their stake contribution
- **Quantity**: Exactly 1 per user per stake operation

### Staked Tokens
- **ID**: `_stakeTokens` (inferred from SELF.tokens(1)._1 preservation rule)
- **Quantity**: Accumulated across operations (OUTPUTS(1).tokens(1)._2 increases with each addStake)
- **Purpose**: The actual economic value locked in the staking pool

## Integration Pattern

### Off-chain Bot / Headless dApp Responsibilities

1. **State Query**: Fetch the current staking state box by scanning for UTXO containing `stakeStateNFT`

2. **Proxy Construction**: 
   - Create a proxy box at this contract's address containing:
     - User's staked token amount
     - User's ErgoTree (serialized) in R5
     - Adequate ergs to cover transaction fees

3. **Transaction Assembly**: 
   - **Path A (addStake)**: Build 6-output transaction routing:
     - Aggregated stake to stake box
     - Stake key NFT to user address
     - Incentives to staking contract
     - Executor compensation
     - Miner fee
   - **Path B (Refund)**: Build 2-output transaction returning tokens to user

4. **Constant Injection**: Populate contract template constants:
   ```
   _stakeStateNFT        // State box singleton identifier
   _stakingIncentiveContract  // Blake2b256 hash of incentive contract ErgoTree
   _toStakingIncentive        // Erg amount for protocol
   _executorReward            // Off-chain executor compensation
   _minerFee                  // Network transaction fee
   ```

5. **Proof of Execution**: Sign transaction with user's private key matching the proposition bytes stored in R5

6. **Atomic Swap Pattern**: This proxy implements the first stage of a **multi-stage contract** where:
   - Stage 1 (this box): User deposits tokens via proxy
   - Stage 2 (staking incentive contract): Lockup and reward distribution

## Related Contracts

### staking/ergoscript/latest/stakingIncentive.es
- **Composition**: addStakeProxy routes staked tokens and fees to this contract
- **Interface**: Receives ergs via `incentiveOutput` (OUTPUTS(3))
- **Invariant**: Script hash (blake2b256) must match `_stakingIncentiveContract` constant

### staking/ergoscript/latest/[stakeBox