---
title: paideiadao/paideia-contracts — unstakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/latest/unstakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/latest/unstakeProxy.es
project: paideiadao-paideia-contracts
---
# UnstakeProxy Contract Analysis

## Purpose

This contract acts as a **proxy box** in a staking withdrawal flow, holding a user's unstaking request until it is processed by an off-chain executor. It validates either a successful unstake transaction (dispersing funds to the user, staking incentive pool, executor, and miner) or a refund transaction (returning assets to the user if the unstake fails to execute within a timeout window).

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Stake state NFT box — must contain the `stakeStateNFT` token in position 0 to authorize unstaking
- **INPUTS(1)**: Stake box — referenced to determine if a replacement stake box output is needed (compared against `amountToUnstake`)
- **SELF**: This proxy box, holding the user's stake tokens and unstake request metadata

### Outputs

**Success Case (unstakeTx):**
- **OUTPUTS(0)**: (Implicit; not validated here, likely change or intermediary)
- **OUTPUTS(1)**: User output — receives unstaked ERG and optionally the stake key token
- **OUTPUTS(2 or 3)**: Staking incentive contract box — receives protocol incentive fee
- **OUTPUTS(3 or 4)**: Transaction operator (executor) box — receives executor reward
- **OUTPUTS(4 or 5)**: Miner box — receives miner fee
- Total size: 5 or 6 boxes depending on `stakeBoxOutput`

**Refund Case (refundTx):**
- **OUTPUTS(0)**: User output — receives all proxy box value minus 1 ERG (storage rent), plus all original tokens
- **OUTPUTS(1)**: Likely miner fee output
- Total size: 2 boxes

## Key Logic

### Valid Unstake Transaction
1. **Stake state authorization**: `INPUTS(0)` must carry the `stakeStateNFT` token to authorize this unstaking action.
2. **Stake box presence check**: If the stake box at `INPUTS(1)` has remaining stake balance (`tokens(1)._2`) greater than the unstake amount, a replacement stake box output is created at `OUTPUTS(1+1)`; otherwise, no replacement (stake fully closed).
3. **User receives unstaked amount**: `OUTPUTS(1)` (the user output) must:
   - Match the user's original proposition bytes from `R5`
   - Contain the unstaked ERG amount from `R4[0]`
   - Receive the stake key token if and only if a replacement stake box is not being created
4. **Fee distribution**:
   - Staking incentive pool receives exactly `toStakingIncentive` nanoERG
   - Executor receives exactly `executorReward` nanoERG
   - Miner receives exactly `minerFee` nanoERG
5. **Output count validation**: Total outputs must equal 5 (or 6 if a replacement stake box is created)

### Refund Transaction
- Triggered if unstake validation fails
- User receives all proxy value minus 1 ERG (storage rent for the refund transaction itself)
- All tokens are returned to the user
- Exactly 2 outputs (user + miner fee)

### Transaction Flow
```
unstakeTx OR refundTx (exactly one must be true)
```

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Holds `[amountToUnstake]` — the quantity of stake tokens to withdraw |
| **R5** | `Coll[Byte]` | User's proposition bytes (ErgoTree) — specifies where refunded/unstaked ERG and tokens flow |

## Tokens

- **Stake key token** (`SELF.tokens(0)`): A native token held in this proxy box that may be returned to the user if the underlying stake position is fully closed (when no replacement stake box is created).
- **Stake state NFT** (`stakeStateNFT`): A singleton NFT in `INPUTS(0)` that gates authorization of the unstake transaction.

## Integration Pattern

### Off-Chain Executor Workflow

1. **Monitor**: Watch for proxy boxes with pending unstake requests (identified by stake key tokens and non-zero `R4` values).

2. **Construct Unstake Transaction**:
   - Gather the proxy box (`SELF`), the current stake state box, and the user's current stake position box
   - Retrieve `amountToUnstake` from `R4` and `userPropositionBytes` from `R5`
   - Determine if the stake position will be fully closed or partially reduced
   - Create output boxes in the correct order:
     - User output (with ERG + tokens per validation rules)
     - Staking incentive box (exactly `toStakingIncentive` nanoERG)
     - Executor box (exactly `executorReward` nanoERG)
     - Miner box (exactly `minerFee` nanoERG)
   - Ensure total output count is 5 or 6 depending on stake closure
   - Sign with the stake state NFT box holder's private key (via Sigma protocol)

3. **Fallback (Timeout/Error)**: If the executor does not process within a time window, the user (or any party) may construct a refund transaction:
   - Single user output receiving all proxy value minus storage rent
   - All tokens returned
   - Miner fee output

4. **Constants (hardcoded in ErgoTree via constant segregation)**:
   - `_stakeStateNFT`: Token ID of the stake state NFT
   - `_stakingIncentiveContract`: Blake2b256 hash of the staking incentive contract's ErgoTree
   - `_toStakingIncentive`: Fee amount (nanoERG) to the incentive pool
   - `_executorReward`: Executor's reward (nanoERG)
   - `_minerFee`: Network miner fee (nanoERG)

## Related Contracts

- **Stake State Box**: Referenced via `stakeStateNFT` — maintains the global staking state machine and guards unstake authorization.
- **Staking Incentive Contract**: The hash of its Ergo