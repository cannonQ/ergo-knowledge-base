---
title: paideiadao/paideia-contracts — unstakeProxy.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.0/unstakeProxy.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.0/unstakeProxy.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: `unstakeProxy.es`

## Purpose

This contract acts as an **unstaking proxy** that facilitates the withdrawal of staked tokens from a staking protocol. It validates that unstaking transactions properly distribute tokens to the user, forward incentives to a staking contract, and compensate the transaction executor and miner. If unstaking conditions cannot be met, it allows a refund of the original staked assets back to the user.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: A box containing the **Stake State NFT** (identified by token ID `_stakeStateNFT`); validates that the unstaking state machine is properly initialized.
- **INPUTS(1)**: A box holding remaining stake tokens; used to determine if a new stake box must be created in the output set.
- **SELF**: The proxy box itself, holding:
  - Stake key token (to be returned to user or carried forward)
  - ERG value (minus fees)
  - R4: Amount to unstake (as `Coll[Long]`)
  - R5: User's proposition bytes (ergo tree for refund destination)

### Outputs
**Two possible transaction structures:**

#### Path A: Successful Unstaking (5 or 6 boxes depending on stake remainder)
- **OUTPUTS(0)**: Unknown (not explicitly validated; may be a change box)
- **OUTPUTS(1)**: **User box** — receives unstaked ERG amount + stake key token (if applicable)
- **OUTPUTS(2 or 3)**: **Incentive box** — sent to staking incentive contract with fixed ERG value
- **OUTPUTS(3 or 4)**: **Executor reward box** — compensates off-chain transaction executor
- **OUTPUTS(4 or 5)**: **Miner fee box** — covers transaction fees
- **OUTPUTS(5)** *(conditional)*: Additional stake box (if `INPUTS(1)` has remaining stake)

#### Path B: Refund Transaction (2 boxes)
- **OUTPUTS(0)**: **User refund box** — returns all staked tokens + (value - 1 ERG in lovelace)
- **OUTPUTS(1)**: Unknown (likely miner fee or change)

## Key Logic

### Validation Conditions

1. **Stake State Verification**
   ```
   INPUTS(0).tokens(0)._1 == stakeStateNFT
   ```
   First input must hold the Stake State NFT; ensures this transaction is part of an authorized staking state machine.

2. **Stake Box Output Calculation**
   ```
   stakeBoxOutput = if (INPUTS(1).tokens(1)._2 > amountToUnstake) 1 else 0
   ```
   Determines whether a new stake box is needed in outputs:
   - If remaining stake > unstaked amount: create new stake box (stakeBoxOutput = 1)
   - Otherwise: no new stake box (stakeBoxOutput = 0)
   - This shifts subsequent output indices dynamically.

3. **User Output Validation** (Unstaking Path)
   - Must be sent to user's ergo tree (`userPropositionBytes` from R5)
   - Receives exact unstake amount in tokens(0)
   - Receives stake key token only if new stake box is created (stakeBoxOutput == 1)

4. **Incentive & Fee Distribution**
   - Incentive contract receives fixed ERG (`toStakingIncentive`) at script hash `_stakingIncentiveContract`
   - Executor receives fixed ERG reward (`executorReward`)
   - Miner receives fixed ERG fee (`minerFee`)

5. **Output Count**
   ```
   OUTPUTS.size == 5 + stakeBoxOutput
   ```
   Total outputs = 5 (base) + 1 (conditional stake box) = 5 or 6

### Refund Path Logic

If unstaking conditions fail, contract allows refund:
- User output must match original proposition bytes
- User receives `SELF.value - 1,000,000` lovelace (subtracts 1 ERG storage rent)
- All tokens returned unchanged to user
- Exactly 2 outputs required

**Core Logic Gate:**
```
sigmaProp(unstakeTx || refundTx)
```
Transaction is valid if **either** unstaking path succeeds **or** refund path succeeds (mutual exclusion via inverse conditions).

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | **Amount to unstake** — extracted as first element; determines token quantity returned to user |
| **R5** | `Coll[Byte]` | **User ergo tree** — proposition bytes for the user's wallet; used to validate refund/unstaking output destination |
| **R6–R9** | *Not used* | Available for future extensions |

## Tokens

### Stake Key Token
- **Type**: NFT or singleton token (held in `SELF.tokens(0)`)
- **Purpose**: Proof of staking position; conditionally returned to user based on whether remaining stake exists
- **Validation**: If `stakeBoxOutput == 1`, token transferred to user output; otherwise, implies this was final unstake

### Stake State NFT
- **Type**: Constant `_stakeStateNFT` (injected constant)
- **Purpose**: Authenticates that INPUTS(0) belongs to authorized staking state machine
- **Role**: Singleton pattern — ensures only one valid state progression

### Token ID Rule Implications
- Stake key token ID embedded in contract constants; prevents unstaking via unauthorized contracts
- State machine integrity enforced by Ergo's **native token ID rule** (token ID = creation tx ID)

## Integration Pattern

### Off-Chain Bot / Executor Requirements

1. **Monitor unstake requests**: Listen for boxes locked at this proxy contract with populated R4, R5

2. **Construct unstaking transaction**:
   - Input 0: Fetch box containing `stakeStateNFT` from the staking state machine
   - Input 1: Fetch latest stake position box (contains remaining stake tokens)
   - Input 2 (SELF): The proxy box with unstake request
   - Calculate `stakeBoxOutput` based