---
title: paideiadao/paideia-contracts — stakePool.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.1/stakePool.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.1/stakePool.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: stakePool.es

## Purpose

The **stakePool** contract governs a Singleton State NFT box that manages DAO token emission and distribution within a staking protocol. It validates two critical transaction types: **Emit Tx** (daily emission snapshots that move tokens from the stake pool to an emission box for distribution) and **Remove Funds Tx** (administrative withdrawals). The contract enforces invariants around token conservation, fee deduction (1% emission fee), and state machine transitions across interconnected boxes.

---

## Inputs / Outputs

### Emit Tx

**Inputs:**
1. **StakeStateBox** – INPUTS(0): State NFT box tracking cumulative staking metrics (total staked, checkpoint, staker count, cycle duration)
2. **StakePoolBox** – INPUTS(1): SELF (the current contract box holding DAO tokens for emission)
3. **EmissionBox** – INPUTS(2): Box holding tokens awaiting distribution; may contain dust (leftover tokens from prior cycles)
4. **StakingIncentiveBox** – INPUTS(3): ERG value to cover transaction fees and off-chain bot execution costs

**Data Inputs:** None

**Outputs:**
1. **NewStakeStateBox** – OUTPUTS(0): Updated state box with recalculated staking totals
2. **NewStakePoolBox** – OUTPUTS(1): Stake pool box with reduced DAO token balance (after emission withdrawal)
3. **NewEmissionBox** – OUTPUTS(2): Emission box with freshly allocated tokens for distribution
4. **EmissionFeeBox** – OUTPUTS(3): Dedicated box receiving 1% fee (sent to `_emissionFeeAddress`)
5. **StakingIncentiveBox** – OUTPUTS(4): Refund of unused ERG to the incentive provider
6. **TxOperatorOutput** – OUTPUTS(5): Operator fee or change output

### Remove Funds Tx

**Inputs:**
1. **StakePoolBox** – INPUTS(0): SELF (the contract box)
2. **StakingIncentiveBox** – INPUTS(1): ERG for transaction costs

**Outputs:**
- Any box(es) containing the **Stake Pool Key** (from R5) as a token
- Arbitrary secondary outputs (allows flexible fund withdrawal)

---

## Key Logic

### Emit Tx Validation

The contract enforces a multi-stage validation pipeline:

1. **Valid Emit Inputs Check:**
   - INPUTS(0) must hold the **Stake State NFT** token (identified by `StakeStateNFT` constant)
   - INPUTS(1) must be SELF (the current stake pool box, verified via box ID equality)

2. **Token Conservation & Emission Calculation:**
   - Reads `emissionAmount` from SELF.R4 (the per-cycle allocation quota)
   - Calculates `emissionDust` from the current emission box (leftover tokens from prior cycles)
   - Total available tokens = `SELF.tokens(1)._2 + emissionDust`
   - Deducts **1% emission fee**: `emissionFeeAmount = emissionAmount / 100`
   - New stake pool balance = `remainingStakePoolTokensAndEmissionDust - emissionAmount`

3. **New Stake Pool Box Validation:**
   - **Value Preservation:** `newStakePoolBox.value == SELF.value` (ERG value unchanged)
   - **Contract Integrity:** `newStakePoolBox.propositionBytes == SELF.propositionBytes` (script remains identical)
   - **Token Identity:** Stake Pool NFT (token 0) remains constant
   - **Emission Register:** R4 (emission amount quota) unchanged
   - **Stake Key Register:** R5 (stake key ID) unchanged
   - **Token Amount Logic:**
     - If sufficient tokens remain: decrement DAO token count by `emissionAmount`
     - If insufficient: reduce token array to single NFT (no DAO tokens left)

4. **Stake State Update:**
   - New total staked = `(old totalAmountStaked) + (emissionAmount - emissionFeeAmount) - emissionDust`
   - Accounts for fee removal and prior-cycle dust cleanup

5. **Emission Fee Box Validation** (conditional):
   - Only created if emission tokens remain post-allocation
   - Recipient address: `_emissionFeeAddress` (hard-coded constant)
   - DAO token amount: exactly `emissionFeeAmount`

6. **New Emission Box Validation:**
   - Receives `emissionAmount` DAO tokens
   - Preserves emission NFT identifier
   - Updates R4 registers with fresh snapshot (total staked, checkpoint, staker count, new emission amount)

### Remove Funds Tx Validation

- **Minimal enforcement:** Validates only that SELF (stake pool box) is present as INPUTS(0)
- **Flexible output structure:** Any output configuration is permitted, provided it includes the **Stake Pool Key** token
- **Authorization:** Relies on off-chain bot or governance to ensure legitimate withdrawal

---

## Registers Used

| Register | Type | Source Box | Purpose |
|----------|------|-----------|---------|
| **R4** | `Coll[Long]` (array of 4 elements) | StakeStateBox | Stores: [totalAmountStaked, checkpoint, stakerCount, lastCheckpointTimestamp, cycleDuration] |
| **R4** | `Long` | StakePoolBox (SELF) | Stores: emissionAmount (per-cycle DAO token allocation quota) |
| **R4** | `Coll[Long]` (array of 4 elements) | EmissionBox | Stores: [totalAmountStaked, checkpoint, stakerCount, emissionAmount] (snapshot for distribution logic) |
| **R4** | `Coll[Long]` | NewStakeStateBox | Updated: recalculated totalAmountStaked post-emission |
| **R5** | `Coll[Byte]` | StakePoolBox (SELF) | Stores: Stake Pool Key (administrative identifier for fund withdrawal) |
| **R5** | `Coll[Byte]` | NewStakePoolBox | Preserved: same Stake