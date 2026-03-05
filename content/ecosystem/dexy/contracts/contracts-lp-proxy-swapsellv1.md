---
title: kushti/dexy-stable — SwapSellV1.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapSellV1.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapSellV1.es
project: kushti-dexy-stable
---
# SwapSellV1 Contract Analysis

## Purpose

This contract validates a **Token-to-Token swap transaction** in a liquidity pool (LP), ensuring that a seller receives a fair quote price after DEX fees are deducted. It is adapted from the Spectrum Finance AMM CFMM (Constant Function Market Maker) v1 implementation and acts as a **proxy validator** within the Dexy stable protocol's swap execution pipeline.

## Inputs / Outputs

### Inputs
- **INPUTS(0)** — `poolIn`: The active liquidity pool box, containing:
  - Pool NFT (tokens(0)) — identifies the pool singleton
  - Pool reserve asset X (value field)
  - Pool reserve asset Y (tokens(2)) — the quote asset reserves
  
- **INPUTS(1)** — (implied) User's input box with the asset to swap (BaseAmount)

- **INPUTS(2+)** — Additional boxes (script does not validate beyond index 0)

### Outputs
- **OUTPUTS(2)** — `rewardBox`: The settlement/reward box produced by the transaction, containing:
  - Quote asset token received by the swapper (tokens(0))
  - ERG value representing the DEX fee component

The transaction must have **minimum 3 inputs** and the pool must contain **exactly 3 tokens**.

## Key Logic

### Preconditions
1. **Pool existence**: INPUTS must have ≥3 boxes; poolIn must hold exactly 3 tokens
2. **Pool identification**: First token in poolIn matches the embedded `$lpNFT` constant (Singleton / State NFT)

### Validation Rules

#### Fair DEX Fee
```
rewardBox.value >= SELF.value - (quoteAmount × DexFeePerTokenNum / DexFeePerTokenDenom) - BaseAmount
```
- Ensures the reward box receives sufficient ERG to cover the DEX fee cut (1% of quote)
- DEX retains `10/100000` = **0.01%** of quote token amount as protocol fee
- Subtracts the fixed `BaseAmount` (1200 nanoERG minimum box value)

#### Fair Price (Spot Price Check)
```
poolReservesY × BaseAmount × FeeNum ≤ relaxedOutput × (poolReservesX × FeeDenom + BaseAmount × FeeNum)
```
- **Constant product formula** with AMM slippage tolerance
- `FeeNum = 997`, `FeeDenom = 1000` → 0.3% **swap fee** retained by pool
- `relaxedOutput = quoteAmount + 1` — accounts for **rounding loss** (1 unit tolerance)
- Ensures the quote received respects the CFMM invariant: `X × Y = k`
- Prevents front-running and sandwich attacks by validating the exchange rate

### Disabled Checks (Commented Out)
- `validMinerFee` — miner fee validation (commented, likely handled elsewhere)
- `rewardBox.propositionBytes == Pk.propBytes` — recipient authorization (commented)
- `quoteAsset._1 == QuoteId` — quote asset identity (commented, likely parameterized off-chain)
- `quoteAmount >= MinQuoteAmount` — minimum quote threshold (commented)

## Registers Used

**None explicitly declared or read** (`R4`–`R9`).

This contract operates solely on:
- **Box fields**: `value`, `tokens`, `propositionBytes`
- **Context objects**: `INPUTS`, `OUTPUTS`, `SELF`
- **Constants**: Embedded parameters (`$lpNFT` base64, fee ratios)

## Tokens

| Token | Role | Source | Purpose |
|-------|------|--------|---------|
| **Pool NFT** (`$lpNFT`) | Singleton identifier | INPUTS(0).tokens(0) | Authenticates the liquidity pool (State NFT pattern) |
| **Pool Reserve Y** | Quote asset | INPUTS(0).tokens(2) | The asset being sold/quoted in the swap |
| **Quote Asset** | Output token | OUTPUTS(2).tokens(0) | The swapped asset delivered to the user |

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Pool Discovery**: Locate a pool box (UTXO) with the embedded `$lpNFT` NFT
2. **Reserve Inspection**: Read `poolReservesX` (ERG in pool value) and `poolReservesY` (token reserves)
3. **Quote Calculation**: Compute fair output given user's `BaseAmount` input:
   ```
   quoteAmount = (poolReservesY × BaseAmount × FeeNum) / (poolReservesX × FeeDenom + BaseAmount × FeeNum)
   ```
4. **DEX Fee Deduction**: Calculate protocol fee:
   ```
   dexFee = quoteAmount × 10 / 100000
   ```
5. **Reward Box Construction**: Create OUTPUTS(2) with:
   - Quote asset amount: `quoteAmount`
   - ERG value: `SELF.value - dexFee - BaseAmount` (ensure fairDexFee condition is met)
6. **Transaction Signing**: Sign the swap transaction with the user's private key (Sigma protocol)
7. **Broadcast**: Submit the signed transaction to the Ergo network

### Contract Verification Flow
The ergoScript context validates:
- Pool NFT presence (anti-replay)
- Constant product formula holds
- Fees are correctly deducted
- **Does NOT verify**: user signature, quote asset identity, or minimum quote threshold (by design, commented out)

## Related Contracts

### Inferred Relationships (from dexy-stable topology)

1. **LiquidityPool / Pool Contract** — The counterparty contract locking the pool reserves; must accept this swap and update reserves atomically
2. **SwapProxy / Swap Router** — Likely the parent contract that routes swaps (this is `SwapSellV1`, implying `SwapBuyV1` exists)
3. **StableCoin / Dexy Core** — The protocol may interact with SigmaUSD-like mechanisms for collateral or reserve backing
4. **Fee Accumulator / Treasury Box** — Off-chain logic must