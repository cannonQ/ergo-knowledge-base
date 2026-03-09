---
title: kushti/dexy-stable — SwapSell.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapSell.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapSell.es
project: dexy-use
---
# SwapSell Contract Analysis
## Purpose

This contract validates ERG-to-Token swaps within the Dexy liquidity pool system. It acts as a proxy that ensures trades execute at fair prices, that fees are correctly allocated, and that the pool state transitions correctly—preventing arbitrage and protecting liquidity providers.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Pool box containing:
  - 3 tokens: Pool NFT (singleton), secondary token, quote asset Y reserve
  - ERG value: Pool X reserve (native currency)
- **INPUTS(1)** (implicit): Typically the action/swap request box
- **INPUTS(2)** (implicit): May contain additional context

### Outputs
- **OUTPUTS(0)**: Updated pool box (reconstructed by off-chain bot)
- **OUTPUTS(1)**: Action/reward distribution box
- **OUTPUTS(2)**: Reward box containing:
  - Quote asset tokens (the output from swap)
  - ERG value covering dex fees
- **Additional outputs**: Miner fee box (identified by `MinerPropBytes`)

## Key Logic

The contract validates a swap through six atomic conditions (all must pass):

1. **Input Structure**: Exactly 3 inputs exist, and the pool box contains exactly 3 tokens.

2. **Pool Integrity**: The first token in the pool box matches `PoolNFT` (State NFT / singleton), proving this is the authentic pool.

3. **Output Routing**: The reward box (OUTPUTS(2)) has propositionBytes matching `RedeemerPropBytes`, ensuring the quote asset reaches the intended recipient.

4. **Quote Asset Verification**: The reward box's first token has ID `QuoteId`, confirming the correct output asset is being paid.

5. **Minimum Output Protection**: `quoteAmount >= MinQuoteAmount` ensures the user receives at least a threshold amount (800 tokens by default).

6. **Fair Price Check** (Core AMM Logic):
   ```
   poolReservesY * BaseAmount * FeeNum ≤ relaxedOutput * (poolReservesX * FeeDenom + BaseAmount * FeeNum)
   ```
   - Uses CFMM (Constant Function Market Maker) formula
   - `FeeNum/FeeDenom = 996/1000` (0.4% swap fee retained in pool)
   - `relaxedOutput = quoteAmount + 1` handles rounding losses
   - Ensures the trader receives at least the AMM-calculated fair value

7. **Dex Fee Collection**: `fairDexFee` verifies the reward box holds sufficient ERG to cover:
   - Protocol fee: `quoteAmount * 2 / 10` (0.2% per token)
   - Base overhead: 1200 nanoERG
   - Subtracted from the ERG value returned to the user

8. **Miner Fee Ceiling**: Total miner fees across all outputs do not exceed `MaxMinerFee`, preventing DOS via excessive transaction fees.

9. **Refund Path**: `sigmaProp(RefundProp || validTrade)` allows either:
   - A valid trade execution, OR
   - A refund if `RefundProp` (off-chain signature/condition) is satisfied

## Registers Used

**None explicitly read/written in this contract.** 

- Register operations are delegated to the pool box (INPUTS(0)) and reward box (OUTPUTS(2)), which may use R4-R9 for pool metadata or liquidity provider tracking (not visible in this contract's logic).
- This contract is **stateless** and acts as a pure validation filter.

## Tokens

1. **Pool NFT** (`PoolNFT` constant):
   - **Role**: State NFT / singleton token
   - **Purpose**: Proves INPUTS(0) is the authoritative pool box
   - **Implementation**: Checked via `poolNFT == PoolNFT`

2. **Quote Asset** (`QuoteId` constant):
   - **Role**: The output token being swapped for (e.g., USDC, USDT)
   - **Purpose**: Identifies the token paid to the user
   - **Implementation**: Verified in reward box: `quoteAsset._1 == QuoteId`

3. **Pool Reserves**:
   - **Token at index 2** (`poolY`): Y reserve (quote asset reserve in the pool)
   - **ERG value**: X reserve (native currency reserve)

## Integration Pattern

### Off-Chain Bot Responsibilities

1. **Construct Transaction**:
   - Select the pool box (INPUTS(0)) as the current state
   - Build a swap request box or combine with action box
   - Calculate fair quote amount using AMM formula: `quoteAmount = poolReservesY * BaseAmount * FeeNum / (poolReservesX * FeeDenom + BaseAmount * FeeNum)`
   - Subtract dex fee: `rewardBoxERG = inputERG - (quoteAmount * 2 / 10) - 1200`

2. **Construct Outputs**:
   - **OUTPUTS(0)**: New pool box with updated reserves:
     - X reserve: `poolReservesX + BaseAmount`
     - Y reserve: `poolReservesY - quoteAmount`
     - Pool NFT preserved
   - **OUTPUTS(1)**: Action/admin box (format depends on Dexy spec)
   - **OUTPUTS(2)**: Reward box with:
     - `quoteAsset` tokens: `(QuoteId, quoteAmount)`
     - ERG: `rewardBoxERG`
   - **Final output**: Miner fee box with `<= MaxMinerFee`

3. **Verify Constraints Pre-Submission**:
   - Check `quoteAmount >= 800`
   - Ensure `poolReservesY >= quoteAmount` (pool has sufficient reserves)
   - Verify total transaction value balances: inputs = outputs + miner fee

4. **Signature Handling**:
   - For valid trades: prove the trade math via contract validation (no additional signature required)
   - For refunds: provide `RefundProp` signature (off-chain authorization) if trade cannot be executed

### Context Extension
- Not used in this contract; all parameters are constants or derived from boxes.

##