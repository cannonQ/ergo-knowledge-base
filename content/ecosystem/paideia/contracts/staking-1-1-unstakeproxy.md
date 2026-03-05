---
title: paideiadao/paideia-contracts — unstakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.1/unstakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.1/unstakeProxy.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: unstakeProxy.es

## Purpose

This contract serves as a **proxy for unstaking requests** in the Paideia DAO staking system. It validates that a user's unstake request is either processed correctly by the staking incentive contract (distributing rewards and returning stake tokens) or refunded to the user if processing fails. The contract acts as an intermediary that ensures atomic, validated transitions between the user's unstake intent and the final settlement.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: The stake state box (identified by `stakeStateNFT` token), providing authoritative staking state
- **INPUTS(1)**: The user's stake box, holding stake tokens and tracking staked amounts
- **SELF**: The unstake proxy box itself, containing:
  - The amount to unstake (R4)
  - The user's ergo tree / proposition bytes (R5)
  - The stake key token (for return to user)

### Outputs (on successful unstake path)

| Index | Purpose | Validates |
|-------|---------|-----------|
| 0 | (change/reserved) | — |
| 1 | **User output** | Receives unstaked ERG + optionally returned stake key token |
| 2 or 3 | **Incentive contract output** | Receives ERG for staking incentive protocol |
| 3 or 4 | **Executor reward** | Compensates transaction operator (off-chain bot) |
| 4 or 5 | **Miner fee** | Network mining fee |

**Output count varies:** `5 + stakeBoxOutput` (5 if stake box stays, 6 if stake box is closed)

### Outputs (on refund path)

| Index | Purpose |
|-------|---------|
| 0 | User refund box (ERG - 1M nanoERG storage rent) |
| 1 | (likely change output) |

---

## Key Logic

### Validation Flow

The contract enforces **two mutually exclusive transaction paths**, confirmed by the final `sigmaProp(unstakeTx || refundTx)`:

#### **Path 1: Successful Unstake (unstakeTx)**

1. **Precondition**: INPUTS(0) must hold the `stakeStateNFT` token (state machine singleton)
   - Ensures the transaction is authorized by the staking state contract

2. **Conditional output indexing**: 
   - If remaining stake in INPUTS(1) > amount to unstake → stake box continues (stakeBoxOutput = 1)
   - If stake is fully withdrawn → stake box closes (stakeBoxOutput = 0)
   - Output indices shift dynamically based on this condition

3. **User output (OUTPUTS(1)) validation**:
   - Must match the user's proposition bytes (from R5)
   - Must receive exactly `amountToUnstake` in tokens(0)
   - If stake box continues, tokens(1) must be the stake key token
   - If stake box closes, no stake key requirement

4. **Incentive contract output**:
   - BlakeTwo256 hash of its proposition bytes must equal `stakingIncentiveContract`
   - Must receive exactly `toStakingIncentive` ERG

5. **Fee distribution**:
   - Executor (off-chain operator) receives `executorReward` ERG
   - Miner receives `minerFee` ERG

6. **Transaction structure**:
   - Output count must match expected size (5 or 6 boxes)
   - All conditions in `allOf(Coll(...))` must pass

#### **Path 2: Refund (refundTx)**

Triggered only if `unstakeTx` is false.

1. **User output (OUTPUTS(0))**:
   - Must match user's proposition bytes (R5)
   - Receives `SELF.value - 1000000` (net ERG after 1M nanoERG storage rent burn)
   - Receives all tokens from SELF unchanged

2. **Transaction size**:
   - Exactly 2 outputs (user refund + miner fee/change)

### Invariants

- **Mutual exclusivity**: `unstakeTx` and `refundTx` cannot both be true
- **Stake key token preservation**: Either returned to user or implicitly handled by state transition
- **Non-fungible state**: The `stakeStateNFT` ensures only one valid staking state per epoch/context
- **Storage rent**: Refund path deducts 1M nanoERG (minimum box value) from user recovery

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | **amountToUnstake** — The quantity of stake tokens user requests to withdraw |
| **R5** | `Coll[Byte]` | **userPropositionBytes** — The user's ergo tree (contract) to receive unstaked funds |

**R0–R3**: Standard (value, tokens, ID, creationInfo) — not custom-used.  
**R6–R9**: Unused in this contract.

---

## Tokens

### Token Types

| Token | ID Source | Role |
|-------|-----------|------|
| **Stake State NFT** | Constant `_stakeStateNFT` | **Singleton / State NFT** — Identifies the authoritative staking state box. Only one INPUTS(0) with this token can appear, enforcing single-state-machine rule per transaction. |
| **Stake Key** | `SELF.tokens(0)` | **Authentication token** — Represents the user's stake position. Returned to user on successful unstake if partial stake remains; burned/consumed if full unstake. |

### Token Flow

- **Input**: Stake key held in SELF (unstake proxy box)
- **Output**: 
  - Returned to user (OUTPUTS(1).tokens(1)) if stake box persists
  - Implicitly cleared if stake fully withdrawn (stakeBoxOutput = 0)

---

## Integration Pattern

### Off-Chain Bot Responsibilities

The **off-chain executor (Headless dApp / Off-chain bot)** must:

1. **Monitor** unstake proxy boxes created by