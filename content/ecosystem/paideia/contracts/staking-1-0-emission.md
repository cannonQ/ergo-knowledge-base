---
title: paideiadao/paideia-contracts — emission.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.0/emission.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.0/emission.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: Emission

## Purpose

This contract governs the emission and distribution of DAO tokens to stakers in a multi-stage staking system. It manages two critical transactions: (1) **Emit Tx**, which withdraws daily allocations from a stake pool into an emission box, and (2) **Compound Tx**, which distributes those emissions to individual stake boxes based on their staked amounts and checkpoint timing.

## Inputs / Outputs

### Emit Transaction

**Inputs:**
- `INPUTS(0)`: Stake State Box — contains total staked amount, checkpoint, staker count, and cycle duration
- `INPUTS(1)`: Stake Pool Box — holds the DAO token reserves and emission rate (in R4)
- `INPUTS(2)`: Emission Box (SELF) — the current emission state box

**Outputs:**
- `OUTPUTS(0)`: New Stake State Box — updated state with fresh checkpoint
- `OUTPUTS(1)`: New Stake Pool Box — depleted reserve after emission withdrawal
- `OUTPUTS(2)`: New Emission Box — receives allocated tokens for distribution
- `OUTPUTS(3+)`: Fee/operator outputs — treasury and transaction operator compensation

### Compound Transaction

**Inputs:**
- `INPUTS(0)`: Emission Box (SELF) — source of tokens to distribute
- `INPUTS(1..n)`: Stake Boxes — user staking positions with checkpoint matching the emission box

**Outputs:**
- `OUTPUTS(0)`: New Emission Box — updated with remaining tokens after distribution
- `OUTPUTS(1..n)`: New Stake Boxes — user positions with accrued rewards compounded
- `OUTPUTS(n+1+)`: Operator/fee outputs

## Key Logic

### Emit Transaction Validation

1. **Input Verification:**
   - First input must hold the Stake State NFT (singleton pattern for state machine)
   - Third input must be SELF (the current emission box, verified via box ID)

2. **New Emission Box Constraints:**
   - Preserves the same eUTXO value (minimum box value conservation)
   - Maintains identical ErgoTree (propositionBytes), enforcing continuation of the same contract logic
   - Copies Total Amount Staked, Checkpoint, and Staker count from stake state box (first 3 elements of R4)
   - **Emission amount calculation:** `99%` of the stake pool's designated emission (R4(0)) OR remaining balance, whichever is smaller (the 1% fee goes to treasury)
   - DAO token quantity in new emission box must exactly equal the calculated emission amount (invariant: `tokens(1)._2 == R4(3)`)
   - Preserves emission NFT (tokens(0)) and DAO token ID (tokens(1)._1)

### Compound Transaction Validation

1. **Input Filtering:**
   - Dynamically filters INPUTS to find all stake boxes matching:
     - Token(0) = Stake Token ID (proves box legitimacy via token authentication)
     - R4(0) (checkpoint) = SELF.R4(1) (emission box checkpoint) — ensures only synchronized stakes receive distribution

2. **Distribution Invariant (truncated in excerpt):**
   - Validates that emission tokens distributed equals `SELF.R4(3)` (the emission amount)
   - Ensures no token leakage via BigInt arithmetic to prevent rounding attacks
   - New emission box retains remaining dust tokens

## Registers Used

| Register | Type | Purpose | Used In |
|----------|------|---------|---------|
| **R4** | `Coll[Long]` | **Emission/State Data** |  |
| R4(0) | Long | Total Amount Staked | Emit (copied to new state); Compound (sum validation) |
| R4(1) | Long | Checkpoint ID | Emit (checkpoint marker); Compound (filter stake boxes by matching checkpoint) |
| R4(2) | Long | Number of Stakers | Emit (copied to new state); Compound (count validation) |
| R4(3) | Long | Emission Amount (tokens to distribute) | Emit (calculated as 99% of pool); Compound (total distributed must equal this) |
| **R5** (Stake Pool) | `Coll[Long]` or not present | Stake Pool emission rate designation | Emit (R4(0) read as emission allotment) |
| **R5** (Stake Box) | `Coll[Byte]` | Stake Key ID | Off-chain: used to identify which key authorized unstaking |
| **R4** (Stake Box) | `Coll[Long]` | Staking metadata |  |
| R4(0) | Long | Checkpoint (must match emission checkpoint) | Compound (filter by checkpoint value) |
| R4(1) | Long | Staking Time | Off-chain: used for lock-up validation |

## Tokens

### Token Authentication (NFTs)

| Token | Purpose | Quantity | Box Type |
|-------|---------|----------|----------|
| **Stake State NFT** (`_stakeStateNFT`) | Singleton identifier for the Stake State Box (state machine marker) | 1 | Stake State |
| **Emission NFT** (`SELF.tokens(0)._1`) | Singleton identifier for the Emission Box (state machine marker) | 1 | Emission |
| **Stake Pool NFT** | Singleton identifier for the Stake Pool Box | 1 | Stake Pool |
| **Stake Token** (`_stakeTokenID`) | Proof of valid stake box creation; filters legitimate stake boxes in Compound Tx | ≤ 1 Billion | Stake |

### Value Tokens

| Token | Purpose | Amount Constraint | Box Type |
|-------|---------|-------------------|----------|
| **DAO Token** (`_stakedTokenID`) | Emitted by DAO; distributed to stakers | ≤ Total DAO allocation | Emission + Stake Pool |
| **DAO Token** (in Stake boxes) | User-staked DAO tokens earning rewards | > 0 | Stake |

## Integration Pattern

### Off-Chain Bot Requirements

1. **Emit Transaction Construction:**
   - Watch for time-based trigger (e.g., once per day, derived from block