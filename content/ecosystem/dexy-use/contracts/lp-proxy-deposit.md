---
title: kushti/dexy-stable — Deposit.es
description: "ErgoScript contract analysis: contracts/lp/proxy/Deposit.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/Deposit.es
project: dexy-use
---
# ErgoScript Contract Analysis: Deposit (Dexy CFMM n2t Pool)

## Purpose

This contract validates deposits into a Constant Function Market Maker (CFMM) pool that trades native token (n) for token 2 (t) in the Dexy protocol. When a user deposits assets into the pool, this contract ensures the transaction correctly mints LP (liquidity provider) tokens and handles any excess reserves or change according to CFMM invariants.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Pool box (eUTXO) containing:
  - Pool NFT (authentication token)
  - LP token (representing pool share)
  - Token Y reserves with amount
  - Native ERG reserves (box value)
- **INPUTS(1+)**: User deposit box (SELF) containing:
  - Token X (user's deposit asset) in tokens(0)
  - Excess ERG for fees and minimum box value
- **Data inputs**: None explicitly referenced (but may exist for oracle/price feeds)

### Outputs
- **OUTPUTS(0)**: Updated pool box (created by previous transaction)
- **OUTPUTS(1)**: Action box (created by pool contract)
- **OUTPUTS(2)**: Reward box sent to user's public key address containing:
  - Minted LP tokens (amount ≥ minimalReward)
  - Change token Y (if minByX < minByY)
  - Minimum box value in ERG
- **OUTPUTS(n)**: Miner fee box (identified by MinerPropBytes)

## Key Logic

The contract validates a valid deposit through these conditions:

1. **Structural Requirements**:
   - Transaction has at least 2 inputs
   - Pool input has exactly 3 tokens (NFT, LP token, Token Y)

2. **LP Calculation** (proportional shares):
   - Calculates LP reward by two routes:
     - **minByX**: `depositX × (totalLP / reservesX)`
     - **minByY**: `depositY × (totalLP / reservesY)`
   - **minimalReward** = minimum of the two (determines limiting asset)

3. **Excess Handling**:
   - If minByX < minByY (Token X is limiting):
     - Excess Token Y calculated: `(minByY - minByX) × reservesY / totalLP`
     - Reward box must return this excess as Token Y change
     - Reward box value validates: `value ≥ SELF.value - DexFee - depositX`
   - If minByX ≥ minByY (Token Y is limiting):
     - Excess ERG calculated: `(minByX - minByY) × reservesX / totalLP`
     - Reward box value validates: `value ≥ SELF.value - DexFee - (depositX - excessX)`

4. **Security Checks**:
   - Pool NFT in output matches input (state machine integrity)
   - LP tokens in output ≥ minimalReward (slippage protection)
   - Miner fee ≤ MaxMinerFee (prevents fee manipulation)
   - Reward box belongs to Pk (user authorization)

5. **Signature Authorization**:
   - Either signed by Pk (owner can withdraw) **OR** validDeposit logic passes

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| R4-R9 | Not explicitly used | Contract may use constants via Constant segregation |
| Pool box R4 | Implicit | May contain additional pool metadata |
| SELF tokens | Token array | Holds deposited Token X |
| SELF value | Long | ERG amount for fees and output |

**Constants (hardcoded or compile-time)**:
- `PoolNFT`: Token ID of pool authentication NFT
- `Pk`: Depositor's public key (sigma protocol)
- `DexFee`: Protocol fee in nanoERG
- `MaxMinerFee`: Maximum allowable miner fee
- `MinerPropBytes`: Serialized proposition bytes identifying miner payment box
- `SelfX`: Amount of Token X in SELF (likely a constant reference)

## Tokens

1. **Pool NFT** (poolIn.tokens(0)._1):
   - Singleton identifying the specific pool
   - Validates pool authenticity on state transitions

2. **LP Token** (poolIn.tokens(1)):
   - Represents fractional ownership of pool reserves
   - Amount decreases from `InitiallyLockedLP` (0x7FFF...FFFF) as LP is minted
   - `supplyLP = InitiallyLockedLP - poolLP._2` (burned supply model)

3. **Token Y** (poolIn.tokens(2)):
   - Secondary reserve asset
   - Tracked by amount in pool box

4. **Mined LP Reward** (rewardOut.tokens(0)):
   - Minted LP sent to user (quantity ≥ minimalReward)

5. **Change Token Y** (rewardOut.tokens(1) - conditional):
   - Returned if Token Y is in excess

## Integration Pattern

### Off-Chain Bot / Headless dApp Requirements

1. **Pool State Observation**:
   - Read INPUTS(0) to extract current reserves (X, Y) and LP supply
   - Calculate `supplyLP = InitiallyLockedLP - lpTokenAmount`

2. **Deposit Construction**:
   - User provides deposit amount in Token X (and optionally Token Y)
   - Bot calculates:
     ```
     minByX = depositX × supplyLP / reservesX
     minByY = depositY × supplyLP / reservesY
     minimalReward = min(minByX, minByY)
     ```

3. **Output Creation**:
   - Create reward box with:
     - LP tokens (minted amount ≥ minimalReward)
     - Excess token (if applicable) with correct amount
     - Sufficient ERG: `depositERG - DexFee`
     - Send to user's Pk
   - Ensure miner fee ≤ MaxMinerFee

4. **Validation**:
   - Verify pool NFT preserved in output