---
title: paideiadao/paideia-contracts — stakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/latest/stakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/latest/stakeProxy.es
project: paideiadao-paideia-contracts
---
# StakeProxy Contract Analysis

## Purpose

This contract acts as a **proxy/intermediary box** in a staking workflow that validates either a successful staking transaction or a refund. It guards user funds temporarily during stake initiation and ensures they are either properly forwarded to the staking incentive contract with correct companion outputs, or refunded to the user if the staking state is unavailable.

## Inputs / Outputs

### Inputs
- **SELF (StakeProxy Box)**: Contains user's ErgoTree in R5 and stake time in R4. Must have native tokens to stake.
- **INPUTS(0)**: Must be a box holding the `stakeStateNFT` token (validates the staking system is operational).

### Outputs

**For Valid Stake Transaction (6 outputs required):**
1. **OUTPUTS(0)**: Not specified in contract (typically change or state box)
2. **OUTPUTS(1)** - Stake Output Box: 
   - Holds the stake's companion token (from SELF.tokens(0))
   - R4 contains array where index [1] equals original stakeTime
   - R5 contains `stakeKey` (the user's derived stake NFT identifier)
3. **OUTPUTS(2)** - User Output Box: 
   - Locked to user's original ErgoTree (from SELF.R5)
   - Contains `stakeKey` token (quantity: 1L) as proof of ownership
4. **OUTPUTS(3)** - Incentive Output Box: 
   - Locked to `stakingIncentiveContract` (validated by blake2b256 hash)
   - Value: exactly `toStakingIncentive` ERG
   - No tokens
5. **OUTPUTS(4)** - Executor Reward: Value = `executorReward` ERG, no tokens
6. **OUTPUTS(5)** - Miner Fee: Value = `minerFee` ERG, no tokens

**For Refund Transaction (2 outputs required):**
1. **OUTPUTS(0)** - User Refund Box: 
   - Locked to user's original ErgoTree (SELF.R5)
   - Value: SELF.value - 1,000,000 nanoERG (storage rent)
   - Contains all original tokens from SELF
2. **OUTPUTS(1)**: Not specified in contract (typically miner fee)

## Key Logic

### Validation Conditions

**Primary Guard (Mutually Exclusive Paths):**
```
sigmaProp(stakeTx || refundTx)
```

**Stake Transaction Path (`stakeTx`):**
- ✓ INPUTS(0) must hold the `stakeStateNFT` token (state machine validation)
- ✓ Stake output's companion token must match SELF's first token (token preservation)
- ✓ Stake output's R4[1] must equal the original stakeTime (immutable timestamp)
- ✓ User output must be locked to the original user ErgoTree (user control)
- ✓ User output must contain exactly 1 `stakeKey` token (stake proof/NFT)
- ✓ Incentive output must hash to the staking incentive contract (correct routing)
- ✓ Incentive output receives exactly `toStakingIncentive` ERG (proper funding)
- ✓ All fee outputs (incentive, executor, miner) must have no tokens
- ✓ Transaction must produce exactly 6 outputs (rigid structure)

**Refund Path (`refundTx`):**
- ✓ INPUTS(0) must **NOT** hold `stakeStateNFT` (system offline/unavailable)
- ✓ User output must be locked to original ErgoTree (user reclaims control)
- ✓ User output value = SELF.value - 1,000,000 nanoERG (storage rent deducted)
- ✓ All tokens returned to user intact (no loss of assets)
- ✓ Transaction must produce exactly 2 outputs

## Registers Used

| Register | Type | Purpose | Accessed By |
|----------|------|---------|------------|
| **R4** | `Coll[Long]` | Array where [0] = stakeTime (when stake became active) | SELF reads [0]; stakeOutput validated for [1] equality |
| **R5** | `Coll[Byte]` | User's ErgoTree (original address/script) | SELF reads to validate user outputs locked to this tree |

**Derived Register Usage:**
- Stake Output **R5**: Contains `stakeKey` (Coll[Byte]) - the NFT token ID identifying this stake

## Tokens

### Token Roles

1. **`stakeStateNFT`** (Constant)
   - Type: Singleton/State NFT
   - Purpose: Guards the validity path; INPUTS(0) must hold this to proceed with staking
   - Authenticates that the staking system's state box is available
   - Acts as a gatekeeper for state machine progression

2. **`stakeKey`** (Generated/Derived)
   - Type: Native Token (1 unit)
   - Purpose: Minted in OUTPUTS(2) as proof of stake ownership
   - User receives this token to prove they own the corresponding stake
   - Enables later unstaking or governance rights

3. **SELF.tokens(0)** (Input Companion Token)
   - Type: Native Token
   - Purpose: Forwarded to stakeOutput (OUTPUTS(1))
   - Maintains the user's staked asset throughout the transaction

**Token ID Rule Implication:**
- The contract assumes tokens are identified by their unique ID (blake2b256 hash of minting transaction)
- `stakeKey` likely derives its ID from the minting box in the same transaction

## Integration Pattern

### Off-Chain Flow (Expected Bot/dApp Behavior)

1. **Monitor User Deposit**: 
   - User creates StakeProxy box with value ERG + tokens in R4/R5
   - Off-chain service detects this UTXO

2. **Check System State**:
   - Query the staking state box (holder of `stakeStateNFT`)
   - If available → proceed to stake path; if unavailable →