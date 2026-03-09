---
title: kushti/dexy-stable — SwapBuyV2.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapBuyV2.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapBuyV2.es
project: dexy-use
---
# SwapBuyV2 Contract Analysis

## Purpose

This contract facilitates **Token → ERG swaps** in the Dexy liquidity pool (LP) proxy system, derived from Spectrum Finance's AMM design. It validates that a user trading tokens for nanoErgs receives a fair price based on constant function market maker (CFMM) math, while protecting against excessive miner fees and ensuring proper output routing.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Pool box containing:
  - NFT (token at index 0) identifying the pool
  - nanoErgs (X reserve, priced asset)
  - Y-asset tokens (at index 2)
- **SELF**: User's swap request box holding:
  - Input tokens (baseAmount) to trade away
- **INPUTS(2)** (implicit via data input context): May reference additional state

### Outputs
- **OUTPUTS(0)**: Pool box (state updated post-swap)
- **OUTPUTS(1)**: Action/state tracking box in Dexy protocol
- **OUTPUTS(2) / rewardBox**: User's reward output containing nanoErgs received, with proposition matching `RedeemerPropBytes`
- **Miner fee output**: Any box with `MinerPropBytes` proposition (implicit in fold validation)

## Key Logic

1. **Input Structure Validation**
   - Exactly 3 inputs required (`INPUTS.size == 3`)
   - Pool input has exactly 3 tokens (NFT + X reserve + Y reserve)

2. **Pool Authentication**
   - First token of pool input must match `PoolNFT` singleton identifier
   - Ensures transaction only executes against authorized pool

3. **Fair Price Computation (CFMM)**
   - **User receives**: `deltaNErgs` = `rewardBox.value - SELF.value` (nanoErgs delta)
   - **Quote amount (gross)**: `deltaNErgs × DexFeePerTokenDenom / (DexFeePerTokenDenom - DexFeePerTokenNum)`
     - Backs out the dex fee (1/10 = 10% margin between net/gross)
   - **Price curve validation**:
     ```
     poolReservesX × baseAmount × 996 ≤ (quoteAmount + 1) × (poolReservesY × 1000 + baseAmount × 996)
     ```
     - Left side: ERG reserves × input tokens × fee ratio (996/1000)
     - Right side: output nanoErgs × (token reserves × fee denominator + input × fee ratio)
     - This is the CFMM invariant: `k = x × y` must not decrease, adjusted for fees
     - `+ 1` relaxation handles rounding loss

4. **Output Validation**
   - Reward box must be spendable by `RedeemerPropBytes` (user's address or contract)
   - Output amount must exceed `MinQuoteAmount` (800 nanoErgs minimum)

5. **Miner Fee Cap**
   - Sum of all outputs with `MinerPropBytes` ≤ `MaxMinerFee`
   - Prevents miner fee exploitation

6. **Refund Path**
   - **OR condition**: Transaction is valid if `RefundProp` holds OR `validTrade` conditions pass
   - Allows emergency/cancellation paths without trade validation

## Registers Used

**None explicitly read/written** (R0–R3 implicit):
- `SELF.value`: nanoErg balance of swap request box
- `SELF.tokens(0)._2`: Quantity of input tokens
- `INPUTS(0).value`: Pool's nanoErg reserves (X asset)
- `INPUTS(0).tokens(n)._1`, `._2`: Token IDs and amounts

**No R4–R9 data registers** accessed, indicating this is a **simple stateless swap validator** without complex state machine logic.

## Tokens

| Token | Role | Usage |
|-------|------|-------|
| **PoolNFT** | Pool singleton identifier | Authenticates which pool CFMM is applied to |
| **baseAmount** (SELF.tokens(0)) | Input token for swap | Quantity determines quote via CFMM curve |
| **poolReservesY** (INPUTS(0).tokens(2)) | Y-asset reserve | Used in pricing formula alongside X reserve (nanoErgs) |

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Construct swap request box** (SELF):
   - Fund with tokens to swap: `SELF.tokens(0) = (tokenId, baseAmount)`
   - Fund with nanoErgs for transaction fees

2. **Fetch pool state**:
   - Read current pool box (INPUTS(0))
   - Extract reserves: `poolReservesX` (nanoErgs), `poolReservesY` (tokens)

3. **Compute fair output**:
   - Apply CFMM formula: `quoteAmount = poolReservesX × baseAmount × FeeNum / (poolReservesY × FeeDenom + baseAmount × FeeNum)`
   - Account for dex fee margin when constructing rewardBox

4. **Build transaction**:
   - Ensure exactly 3 inputs (pool + request + optional data input)
   - Route nanoErg output to `rewardBox` with `RedeemerPropBytes` address
   - Construct miner fee output ≤ `MaxMinerFee`
   - Verify `rewardBox.value - SELF.value ≥ MinQuoteAmount`

5. **Verify before signing**:
   - Simulate fairPrice condition: confirm reserves × baseAmount × 996 satisfies CFMM inequality
   - Check miner fee sum

## Related Contracts

- **Pool contract** (referenced as `INPUTS(0)`): Manages reserves and LP state; must validate its own spending rules
- **Dexy action/state box** (`OUTPUTS(1)`): Part of Dexy protocol's state machine (likely tracks swaps, fees, or protocol parameters)
- **Spectrum Finance `SwapBuy.sc`** (original source): This is a **specialized fork** for Dexy LP integration, adding