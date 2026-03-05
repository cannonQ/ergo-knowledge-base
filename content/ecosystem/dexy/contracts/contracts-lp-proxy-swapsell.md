---
title: kushti/dexy-stable — SwapSell.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapSell.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapSell.es
project: kushti-dexy-stable
---
# SwapSell Contract Analysis
**From:** kushti/dexy-stable project (LP Proxy)

---

## Purpose

This contract implements a **sell-side atomic swap** that exchanges ERG (nanoErgs) for a quote token in a liquidity pool. It validates that the trade price is fair according to CFMM (Constant Function Market Maker) math, collects dex fees, and ensures the miner fee is within acceptable bounds. The contract acts as a **proxy validator** within a multi-stage swap transaction orchestrated by an off-chain bot.

---

## Inputs / Outputs

### Expected Inputs
1. **INPUTS(0)** — Pool Box
   - Contains 3 tokens: [PoolNFT, PoolX (implicit in nanoErgs), PoolY (token reserves)]
   - nanoErg value = poolReservesX (ERG side of pool)

2. **INPUTS(1+)** — Other boxes (e.g., action box, user input)
   - Not directly validated in this script

3. **SELF** — This proxy box (context box)
   - Contains ERG to be swapped (BaseAmount + fee allocations)

### Expected Outputs
1. **OUTPUTS(0)** — Updated Pool Box (implicit in validation context)
2. **OUTPUTS(1)** — Action Box (implicit, "first two outputs occupied with pool box & action box")
3. **OUTPUTS(2)** — Reward/Redeemer Box
   - Must contain quote token (QuoteId)
   - Must have QuoteAmount ≥ MinQuoteAmount
   - propositionBytes must equal RedeemerPropBytes
   - nanoErg value ≥ fair dex fee + BaseAmount

4. **OUTPUTS(n)** — Miner fee box
   - Identified by MinerPropBytes
   - Total across all such boxes ≤ MaxMinerFee

---

## Key Logic

### Structural Validation
```
INPUTS.size == 3 && poolIn.tokens.size == 3
```
Ensures exactly 3 inputs and pool box has exactly 3 token slots (NFT + 2 token types).

### Pool Authentication
```
poolNFT == PoolNFT
```
Verifies the first input's leading token is the canonical Pool NFT (singleton identity).

### Quote Token & Amount Validation
```
quoteAsset._1 == QuoteId && quoteAmount >= MinQuoteAmount
```
Ensures output token is the correct quote asset and meets minimum trade size.

### Fair Price Validation (CFMM Invariant)
```
poolReservesY * BaseAmount * FeeNum <= relaxedOutput * (poolReservesX * FeeDenom + BaseAmount * FeeNum)
```
**Rearranged CFMM formula:**
- `relaxedOutput = quoteAmount + 1` (handles rounding error tolerance)
- Verifies: `(X + ΔX) × (Y - ΔY) ≥ X × Y` with 0.4% fee (FeeNum=996, FeeDenom=1000)
- Constants indicate Spectrum Finance's CFMM v2 n2t (native-to-token) implementation

### Fair Dex Fee Validation
```
rewardBox.value >= SELF.value - quoteAmount * DexFeePerTokenNum / DexFeePerTokenDenom - BaseAmount
```
Ensures the redeemer receives enough nanoErgs to cover:
- Dex fee: 0.2 nanoErgs per token (2/10 ratio)
- BaseAmount: 1200 nanoErgs (minimum box value + protocol overhead)

### Miner Fee Cap
```
validMinerFee = OUTPUTS.fold(...) <= MaxMinerFee
```
Prevents transaction fee from exceeding MaxMinerFee constant.

### Refund Path
```
sigmaProp(RefundProp || validTrade)
```
Provides **emergency escape hatch**: if RefundProp is satisfied (typically a timeout or user signature), the box can be refunded without validating the trade.

---

## Registers Used

**None explicitly used in this contract.**

All state is derived from:
- Input/output box structure (INPUTS, OUTPUTS, SELF)
- Native token arrays and nanoErg balances
- Constant pool identifiers (PoolNFT, QuoteId)

*Note:* R4–R9 may be used by the **pool box** (INPUTS(0)) and **redeemer box** (OUTPUTS(2)) in their own contracts, but this proxy doesn't read them.

---

## Tokens

### PoolNFT (Singleton)
- **Role:** Uniquely identifies the liquidity pool
- **Read from:** INPUTS(0).tokens(0)._1
- **Validation:** Must equal the compile-time constant PoolNFT

### PoolX & PoolY (Liquidity Reserves)
- **PoolX:** Stored implicitly as nanoErg value of pool box
- **PoolY:** INPUTS(0).tokens(2) — the quote token reserve
- **Type:** Long (quantity in atomic units)

### QuoteId (Output Token)
- **Role:** The token users receive in the swap
- **Read from:** OUTPUTS(2).tokens(0)._1
- **Validation:** Must equal compile-time constant QuoteId

### Miner Fee Token
- **Role:** Native transaction fee (measured in nanoErgs)
- **Identified by:** box.propositionBytes == MinerPropBytes
- **Capped at:** MaxMinerFee

---

## Integration Pattern

### Off-Chain Bot Responsibilities

1. **Construct Transaction**
   - Read current pool state from blockchain (INPUTS(0))
   - Calculate fair output amount using CFMM formula:
     ```
     quotedAmount = (poolReservesY * baseAmount * FeeNum) / (poolReservesX * FeeDenom + baseAmount * FeeNum)
     ```
   - Build action box (OUTPUTS(1)) with execution parameters

2. **Fee Calculation**
   - Dex fee: `quoteAmount * 0.02` nanoErgs
   - Miner