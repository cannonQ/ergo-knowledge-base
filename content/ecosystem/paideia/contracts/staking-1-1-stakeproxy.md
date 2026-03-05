---
title: paideiadao/paideia-contracts — stakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.1/stakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.1/stakeProxy.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: stakeProxy.es

## Purpose

This contract acts as a **proxy/intermediary box** in a staking workflow that routes user stake requests to the staking incentive contract. It validates that either a properly formatted staking transaction executes (transferring stake tokens and distributing rewards) or refunds the user's assets if the staking operation fails.

## Inputs / Outputs

### Inputs
- **SELF (this box):** Contains user's staking request with:
  - R4: Staking metadata (stakeTime as array of Longs)
  - R5: User's ergo tree (proposition bytes for refund routing)
  - tokens(0): Stake token to be staked
  - value: ERG amount for transaction fees

- **INPUTS(0):** Must hold the **Singleton State NFT** (`stakeStateNFT`) to trigger staking path; absence triggers refund path

### Outputs (Staking Path - 6 outputs required)
1. **OUTPUTS(0):** (implied, not shown) — likely change/service box
2. **OUTPUTS(1):** Stake output box sent to staking contract with:
   - tokens(1): Original stake token from SELF
   - R4[1]: Original stakeTime value
   - R5: Stake key (public key for claim eligibility)
3. **OUTPUTS(2):** User output receiving stake key NFT (1 unit)
4. **OUTPUTS(3):** Incentive output to staking incentive contract (exact ERG value, no tokens)
5. **OUTPUTS(4):** Executor reward box (off-chain bot compensation)
6. **OUTPUTS(5):** Miner fee box

### Outputs (Refund Path - 2 outputs required)
1. **OUTPUTS(0):** User recovery box returning all tokens, minus 1 ERG (tx fee)
2. **OUTPUTS(1):** (implied) Miner fee box

## Key Logic

### Staking Transaction (`stakeTx`)

The contract validates a staking operation through these conditions:

1. **State verification:** INPUTS(0) must hold the `stakeStateNFT` (Singleton State NFT) to prove the staking contract authorized this request
2. **Stake preservation:** `stakeOutput.tokens(1)` must equal the original `SELF.tokens(0)` (same asset staked)
3. **Timestamp consistency:** The stake time in `stakeOutput.R4[1]` must match `SELF.R4[0]` (staking period integrity)
4. **User key recovery:** User receives a stake key NFT (1 unit) and output script must match their original proposition bytes
5. **Contract routing:** Incentive output's blake2b256 hash must match the `stakingIncentiveContract` constant
6. **Payment distribution:** 
   - Incentive box receives exactly `toStakingIncentive` ERGs
   - Executor receives exactly `executorReward` ERGs (off-chain bot payment)
   - Miner receives exactly `minerFee` ERGs
7. **Output count:** Exactly 6 outputs must exist (strict box count)

### Refund Transaction (`refundTx`)

Triggered when INPUTS(0) lacks the state NFT:

1. **User recovery:** Output script must match the original user's proposition bytes (SELF.R5)
2. **Fee deduction:** User receives `SELF.value - 1000000` (1 ERG deducted as minimal tx fee)
3. **Token preservation:** All tokens returned unchanged
4. **Output count:** Exactly 2 outputs (user recovery + miner fee implied)

### Guard Clause
The contract accepts either path: `sigmaProp(stakeTx || refundTx)` — requires a valid Sigma proof for one of the two branches.

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` (array) | Staking metadata; `R4(0)` = stakeTime (Unix timestamp or block height threshold) |
| **R5** | `Coll[Byte]` | User's ergo tree (proposition bytes) — used to validate refund outputs and ensure only the original user can recover funds |

## Tokens

| Token | Role | Authentication Mechanism |
|-------|------|--------------------------|
| **stakeStateNFT** (constant) | Singleton State NFT | Guards the staking path; must appear in INPUTS(0).tokens(0)._1. Proves the staking contract is ready to accept this stake request. Without it, refund path activates. |
| **SELF.tokens(0)** | Stake asset (e.g., PAO governance token) | Transferred to staking output; state machine verifies it matches `stakeOutput.tokens(1)` |
| **Stake key NFT** | User claim entitlement | 1 unit issued to user in OUTPUTS(2), derived from `stakeOutput.R5` (stake public key) for later unstaking |

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Construct staking transaction:**
   - Collect this proxy box (SELF) as input
   - Query blockchain to obtain the state NFT holder (INPUTS(0))
   - Build 6-output transaction with exact ERG allocations
   - Derive stake key from staking contract state and populate OUTPUTS(1).R5

2. **Construct refund transaction:**
   - Detect if state NFT unavailable (network outage, contract halt)
   - Route SELF back to user via OUTPUTS(0) with proposition bytes from SELF.R5
   - Deduct 1 ERG only (not configurable in refund path)

3. **Sign and submit:**
   - Sign with executor key (if OUTPUTS(4) present)
   - Cover miner fee via OUTPUTS(5)
   - Verify R4/R5 are present before box creation

### Verification Checklist

- [ ] State NFT present in INPUTS(0) before accepting staking
- [ ] All output indices correct (1–5 for staking; 0–1 for refund)
- [ ] blake2b256 hash of incentive contract matches constant