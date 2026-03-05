---
title: paideiadao/paideia-contracts — stakePool.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/latest/stakePool.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/latest/stakePool.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: stakePool.es

## Purpose

The **stakePool** contract governs the core state machine for a DAO staking emission mechanism. It manages two primary transaction types: (1) **Emit Tx**, which periodically withdraws DAO tokens from the stake pool into an emission box for distribution to stakers (deducting a 1% fee), and (2) **Remove Funds Tx**, which allows authorized parties to withdraw remaining funds from the stake pool using a Stake Pool Key.

## Inputs / Outputs

### Emit Transaction
**Inputs (Data):**
- `INPUTS(0)`: Stake State Box — holds total staked amount, checkpoint, staker count, and cycle duration
- `INPUTS(1)`: Stake Pool Box (SELF) — the contract box being spent
- `INPUTS(2)`: Emission Box — accumulates tokens for distribution
- `INPUTS(3)`: Staking Incentive Box — funds for transaction execution bot and mining fees

**Outputs:**
- `OUTPUTS(0)`: New Stake State Box — updated with post-emission staking totals
- `OUTPUTS(1)`: New Stake Pool Box — reduced DAO token holdings after emission withdrawal
- `OUTPUTS(2)`: New Emission Box — updated with newly emitted tokens
- `OUTPUTS(3)`: Emission Fee Box — receives 1% fee from emission
- `OUTPUTS(4)`: Staking Incentive Box — refunded to execution bot
- `OUTPUTS(5)`: TxOperator Output — bot operator reward

### Remove Funds Transaction
**Inputs:**
- `INPUTS(0)`: Stake Pool Box (SELF)
- `INPUTS(1)`: Staking Incentive Box

**Outputs:**
- A box containing the Stake Pool Key (as a native token)
- Any other authorized output box

---

## Key Logic

### Emit Transaction Validation

The contract enforces the following invariants:

1. **Input Box Validation:**
   - `INPUTS(0)` must hold the Stake State NFT token (immutable identifier)
   - `INPUTS(1)` must be SELF (the stake pool box itself) via box ID comparison

2. **Emission Amount Calculation:**
   - Reads `SELF.R4` (emission amount per cycle)
   - Calculates **emission dust** from remaining DAO tokens in the current emission box: `emissionDust = INPUTS(2).tokens(1)._2 if present else 0`
   - Total available tokens for next emission: `remainingStakePoolTokensAndEmissionDust = SELF.tokens(1)._2 + emissionDust`

3. **Fee Deduction:**
   - **Emission fee = emissionAmount / 100** (1% of allocated emission)
   - Fee box created only if non-zero fee exists
   - Remaining stake pool tokens: `remainingStakePoolTokensAndEmissionDust - emissionAmount`

4. **New Stake Pool Box Constraints:**
   - **Value preservation:** `newStakePoolBox.value == SELF.value` (ERG amount unchanged)
   - **Contract identity:** `newStakePoolBox.propositionBytes == SELF.propositionBytes` (same ErgoTree)
   - **NFT token:** Stake Pool NFT preserved in `tokens(0)`
   - **Register invariants:**
     - `R4` (emission amount) unchanged
     - `R5` (Stake Pool Key) unchanged
   - **Token accounting:** If tokens remain after emission, `newStakePoolBox.tokens(1)._2 == remainingStakePoolTokensAndEmissionDust - emissionAmount`; otherwise only NFT remains
   - **Stake State update:** Emission tokens (minus 1% fee) added to total staked: `newStakeStateBox.R4[Coll[Long]].get(0) == totalAmountStaked + (emissionAmount - emissionFeeAmount) - emissionDust`

5. **New Emission Box Constraints:**
   - Emission NFT preserved
   - Receives newly emitted tokens: `newEmissionBox.tokens(1)._2 == emissionAmount`
   - Register data updated with checkpoint and emission amount

6. **Emission Fee Box Constraints:**
   - Created only if `emissionFeeAmount > 0`
   - Receives 1% of emission: `emissionFeeBox.tokens(0)._2 == emissionFeeAmount`
   - Sent to hardcoded `EmissionFeeAddress`

7. **Staking Incentive Box Refund:**
   - Staking incentive box must appear in outputs with sufficient value for next cycle's execution and mining fees

### Remove Funds Transaction Validation

The contract validates that:
- Stake Pool Key (as a Singleton / State token) is extracted into an output
- Allows removal of remaining DAO tokens or ERG from the pool
- Requires authorization via the Staking Incentive Box mechanism

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|-----------|
| **R4** | `Coll[Long]` | Emission amount (index 0); read-only constant per cycle | Preserved in new stake pool |
| **R5** | `Coll[Byte]` | Stake Pool Key (binary identifier for withdrawal authorization) | Preserved in new stake pool |

**Stake State Box Registers (referenced, not written by this contract):**
- **R4[0]**: Total amount staked
- **R4[1]**: Checkpoint (snapshot index for reward calculations)
- **R4[2]**: Staker count
- **R4[3]**: Last checkpoint timestamp
- **R4[4]**: Cycle duration

---

## Tokens

### Stake Pool Box (SELF)
- **Token 0:** Stake Pool NFT (`_stakeStateNFT` hardcoded)
  - Amount: 1 (Singleton / State NFT for box identification)
  - Purpose: Immutable identifier preventing confusion with other boxes
- **Token 1:** DAO Token ID (issued by DAO governance)
  - Amount: ≤ Total DAO tokens allocated to staking
  - Purpose: Value being distributed to stakers over time

### Stake State Box (