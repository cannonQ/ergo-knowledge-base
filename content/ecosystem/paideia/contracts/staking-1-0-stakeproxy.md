---
title: paideiadao/paideia-contracts — stakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.0/stakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.0/stakeProxy.es
project: paideiadao-paideia-contracts
---
# StakeProxy Contract Analysis

## Purpose

This contract acts as a **proxy entry point for user staking operations** in the Paideia DAO staking system. It receives user funds and validates that they are properly routed to the staking incentive contract while distributing rewards to executors and miners. It also provides a refund mechanism if the staking state NFT is not present in the transaction input.

## Inputs / Outputs

### Inputs
- **SELF (INPUTS(0) in stake path)**: The StakeProxy box itself, containing:
  - Funds to be staked
  - Tokens associated with the user's stake
  - R4: Stake time (collection of longs)
  - R5: User's ergo tree (proposition bytes)
  
- **Data Input (conditional)**: Must include a Box with the Stake State NFT token (identified by `_stakeStateNFT`)

### Outputs

**Stake Transaction Path** (when Stake State NFT present):
- **OUTPUTS(0)**: Change or fee output (implicit)
- **OUTPUTS(1)**: Stake output to staking incentive contract (contains staking token and updated stake time)
- **OUTPUTS(2)**: User output (returns stake key token to user)
- **OUTPUTS(3)**: Incentive output (box funding the staking incentive contract)
- **OUTPUTS(4)**: Executor reward output (payment for transaction executor)
- **OUTPUTS(5)**: Miner fee output (payment for block inclusion)

**Refund Transaction Path** (when Stake State NFT absent):
- **OUTPUTS(0)**: User refund output (returns all tokens and value minus 1 ERG storage rent)
- **OUTPUTS(1)**: Miner fee output (implicit in size check)

## Key Logic

### Validation Conditions

**Stake Transaction (`stakeTx`)**:
1. **State NFT presence**: `INPUTS(0).tokens(0)._1 == stakeStateNFT` — confirms staking system is active
2. **Stake output integrity**: 
   - Contains the correct staking token (preserved from SELF)
   - Carries forward the stake time from R4
3. **Stake key issuance**: 
   - User receives exactly 1 Stake Key NFT token
   - Stake Key token ID matches the value in the stake output's R5
4. **User output correctness**: 
   - Sent to original user's proposition bytes (from SELF.R5)
   - Contains the stake key token
5. **Incentive routing**: 
   - Output #3 is a valid staking incentive box (blake2b256 hash of its script matches `_stakingIncentiveContract`)
   - Receives exactly `_toStakingIncentive` ERGs with no tokens
6. **Fee distribution**:
   - Executor receives exactly `_executorReward` ERGs
   - Miner receives exactly `_minerFee` ERGs
7. **Output count**: Exactly 6 outputs required (enforces strict transaction structure)

**Refund Transaction (`refundTx`)**:
1. **State NFT absence**: Triggered only if Stake State NFT is not in INPUTS(0)
2. **User recovery**:
   - Output sent to user's original address (from SELF.R5)
   - All tokens returned unchanged
   - Value returned minus 1 ERG (standard storage rent, ~0.001 ERG)
3. **Output count**: Exactly 2 outputs (user refund + miner fee implied)

### Control Flow
```
if (Stake State NFT in INPUTS(0))
  → Validate Stake Transaction (6 outputs, proper routing)
else
  → Validate Refund Transaction (2 outputs, user recovery)

Valid if (stakeTx OR refundTx)
```

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R4** | `Coll[Long]` | SELF | Stake time array; index 0 extracted as staking duration/timestamp |
| **R5** | `Coll[Byte]` | SELF | User's ergo tree (proposition bytes); used to route user output and validate refund destination |
| **R4** (output) | `Coll[Long]` | OUTPUTS(1) | Staking output register; index 1 must match original stake time |
| **R5** (output) | `Coll[Byte]` | OUTPUTS(1) | Stake output register; contains staking token ID (Stake Key reference) |

## Tokens

| Token | ID | Purpose | Usage |
|-------|----|---------|----|
| **Stake State NFT** | `_stakeStateNFT` (constant) | System authentication | Must appear in INPUTS(0) to enable staking; absence triggers refund path |
| **Staking Token** | `SELF.tokens(0)` | User stake representation | Preserved in OUTPUTS(1); tracks active stake amount |
| **Stake Key NFT** | Derived from stakeOutput.R5 | User proof of ownership | Issued to user in OUTPUTS(2); 1 unit minted to identify stake participation |

All tokens follow the **Token ID rule** (first 32 bytes of transaction ID for newly minted tokens).

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Stake Path Construction**:
   ```
   Construct TX:
   - Input: User's StakeProxy box
   - Data Input: Box with Stake State NFT
   - Output(1): StakeOutput → StakingIncentiveContract script
     * R4: [_, stakeTime]
     * R5: stakeKeyTokenId (Coll[Byte])
     * tokens: [stakeToken]
   - Output(2): UserOutput → userPropositionBytes
     * tokens: [stakeKeyNFT(qty=1)]
   - Output(3): IncentiveOutput → StakingIncentiveContract
     * value: _toStakingIncentive
   - Output(4): ExecutorReward → executor address
     * value: _executorReward
   - Output(5): MinerFee → miner address