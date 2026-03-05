---
title: paideiadao/paideia-contracts — emission.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/latest/emission.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/latest/emission.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: `emission.es`

## Purpose

This contract governs the **emission and distribution cycle** for a staking protocol within the Paideia DAO ecosystem. It manages two critical transactions: **(1) Emit Tx** — which withdraws allocations from a stake pool into an emission box once per cycle, and **(2) Compound Tx** — which distributes accrued emissions from the emission box to individual stake boxes proportional to their stake amount and duration.

## Inputs / Outputs

### Emit Transaction

**Inputs:**
- `INPUTS(0)`: Stake State Box — holds aggregated staking metrics (total staked, checkpoint, staker count, cycle duration)
- `INPUTS(1)`: Stake Pool Box — reserve of DAO tokens available for emission
- `INPUTS(2)`: Emission Box (SELF) — current emission state box
- `INPUTS(3+)`: Staking Incentive Box — ERG for transaction execution and mining fees

**Outputs:**
- `OUTPUTS(0)`: New Stake State Box — updated state propagated forward
- `OUTPUTS(1)`: New Stake Pool Box — reduced token reserve after withdrawal
- `OUTPUTS(2)`: New Emission Box — populated with freshly allocated tokens for distribution
- `OUTPUTS(3+)`: Emission Fee Box & Operator Boxes — treasury cut (1%) and bot incentive

### Compound Transaction

**Inputs:**
- `INPUTS(0)`: Emission Box (SELF) — current distribution pool
- `INPUTS(1..n)`: Stake Boxes — individual user stakes (filtered by checkpoint matching and Stake Token ID)
- `INPUTS(n+1)`: Staking Incentive Box — ERG for transaction fees

**Outputs:**
- `OUTPUTS(0)`: New Emission Box — reduced by distributed amounts
- `OUTPUTS(1..n)`: New Stake Boxes — compounded rewards added to user holdings
- `OUTPUTS(n+1+)`: Operator Box — transaction fee payment

---

## Key Logic

### Emit Transaction Validation (`validEmitTx`)

1. **Input Authenticity**: Verifies the first input holds the **Stake State NFT** singleton and the third input is SELF (current emission box by box ID).

2. **Emission Allocation Calculation**:
   - Computes total available tokens: `stakePoolBox.tokens(1)._2 + SELF.tokens(1)._2` (current reserve + any dust from prior cycle)
   - Emits **99% of the designated pool amount** (1% treasury fee retained)
   - If pool is depleted, emits all remaining tokens

3. **Box Invariants**:
   - New emission box has identical **ERG value** (storage rent preservation)
   - Governed by **identical ErgoTree** (same contract)
   - Inherits first 3 elements of **R4** from stake state (Total Staked, Checkpoint, Stakers count)
   - New **R4[3]** (emission amount) = 99% of stake pool allocation
   - Token distribution matches: **DAO Token amount in new emission box = R4[3]**

4. **NFT/Token Preservation**: Confirms emission NFT and DAO token IDs are maintained in new box.

### Compound Transaction Validation (`validCompoundTx`)

1. **Input Filtering**: Extracts all stake boxes from inputs where:
   - Token(0) matches **StakeTokenID** (stake proof token)
   - R4[0] (checkpoint) matches SELF.R4[1] (emission box checkpoint)

2. **Distribution Accuracy**:
   - For each stake box: `rewardAmount = emissionAmount × (stakeAmount / totalStaked) × (stakingDuration / cycleLength)`
   - Validates **no tokens are lost**: sum of output token amounts ≤ emission box input amount

3. **Dust Handling**: Accumulates rounding errors in output emission box for next cycle.

4. **Emission Box State**:
   - Remaining tokens = input tokens − (sum of distributed rewards)
   - Same NFT and DAO token ID preserved
   - Box value and ErgoTree unchanged (state machine invariant)

---

## Registers Used

| Register | Type | Purpose | Transaction(s) |
|----------|------|---------|-----------------|
| **R4** | `Coll[Long]` | Multi-field state vector | Both |
| **R4[0]** | Long | Total Amount Staked (wei equivalent) | Emit (read from stake state) |
| **R4[1]** | Long | Checkpoint timestamp / cycle marker | Both (emit writes, compound filters) |
| **R4[2]** | Long | Staker count | Emit (propagated) |
| **R4[3]** | Long | Emission Amount (tokens to distribute) | Both (emit calculates, compound subtracts) |
| **R5** | `Coll[Byte]` | Stake Pool Key (in stake pool box only) | Not used in emission contract |

---

## Tokens

### Token(0) — Singleton NFTs

| Box Type | Token Purpose | Amount | Constraint |
|----------|---------------|--------|-----------|
| **Emission Box** | Emission NFT (state identifier) | 1 | Immutable singleton (preserved across both Tx types) |
| **Stake State Box** | Stake State NFT (state identifier) | 1 | Single authority token |
| **Stake Pool Box** | Stake Pool NFT (state identifier) | 1 | Distinguishes active pool |
| **Stake Box** | Stake Token ID (proof of valid stake) | 1 | Proves box created by legitimate staking contract |

### Token(1) — Value Tokens

| Box Type | Token | Amount | Constraints |
|----------|-------|--------|-----------|
| **Emission Box** | DAO Token (e.g., staking reward token) | ≤ Designated Emission Amount | Must equal R4[3] in new emission box |
| **Stake Pool Box** | DAO Token | ≤ Total Reserve | Decreases by emission amount after Emit Tx |
| **Stake Box** | DAO Token (user stake) | > 0 |