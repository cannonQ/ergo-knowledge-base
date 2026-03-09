---
title: kushti/dexy-stable — SwapBuyV1.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapBuyV1.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapBuyV1.es
project: dexy-use
---
# SwapBuyV1 Contract Analysis

## Purpose

This contract validates a **Token → ERG swap** transaction in a Constant Function Market Maker (CFMM) liquidity pool with a 1-to-2 token pair (n2t: native token to ERG). It ensures the user receives fair market price according to the CFMM formula and that protocol fees are correctly applied before releasing the user's input tokens.

## Inputs / Outputs

### Inputs
- **INPUTS(0)** — The **Pool Box**: Contains the CFMM pool state with:
  - Pool NFT (first token, ID placeholder `$lpNFT`)
  - Liquidity provider LP tokens (second token)
  - Reserve tokens Y amount (third token)
  - Reserve ERGs (nanoErgs in box value)

- **INPUTS(1+)** — User's swap request box(es), including **SELF** (the current executing box):
  - SELF contains base tokens to be swapped (SELF.tokens(0)._2 = baseAmount)

### Outputs
- **OUTPUTS(2)** — **Reward Box**: Receives the net quote amount (ERGs after fee deduction)
  - Expected to be sent to the user or a reward collector

---

## Key Logic

The contract enforces three validation conditions:

1. **Structural Validity**
   ```
   INPUTS.size >= 3 AND poolIn.tokens.size == 3
   ```
   Ensures minimum transaction structure (pool + self + reward) and complete pool state.

2. **Pool Authentication**
   ```
   poolNFT == fromBase64("$lpNFT")
   ```
   Confirms the input pool is the correct Spectrum DEX pool via NFT singleton check.

3. **Fair Price Calculation** (Constant Product Formula)
   - Extract reserves: `X = poolReservesX` (ERGs), `Y = poolReservesY` (tokens)
   - User supplies: `baseAmount` (input tokens)
   - User receives: `deltaNErgs = rewardBox.value - SELF.value` (ERG delta after fee)
   - **Compute fair quote**: 
     ```
     quoteAmount = deltaNErgs × (DexFeePerTokenDenom) / (DexFeePerTokenDenom - DexFeePerTokenNum)
                 = deltaNErgs × 1000 / 995  [backs out the ~0.5% protocol fee]
     ```
   - **Enforce CFMM invariant** (with rounding tolerance):
     ```
     X × baseAmount × (1000 - 997) <= (quoteAmount + 1) × (Y × 1000 + baseAmount × 3)
     ⟺ X × baseAmount × 3 <= relaxedOutput × (Y × 1000 + baseAmount × 3)
     ```
     This is the constant-product check: `(X + Δx) × (Y - Δy) ≥ X × Y` (rearranged for slippage).

4. **Minimum Output Protection**
   ```
   quoteAmount >= MinQuoteAmount (100 nanoErgs)
   ```
   Prevents dust/spam transactions.

---

## Registers Used

**None explicitly used** (R4–R9 not referenced).

- Contract parameters are **hardcoded constants**:
  - `FeeDenom = 1000`, `FeeNum = 997` → 0.3% DEX fee
  - `DexFeePerTokenNum = 5`, `DexFeePerTokenDenom = 1000` → Additional 0.5% swap fee
  - `MinQuoteAmount = 100L` → Minimum output threshold
  - `$lpNFT` — Injected at compile time (pool NFT ID)

---

## Tokens

1. **Pool NFT** (`poolIn.tokens(0)._1`)
   - **Type**: Singleton State NFT
   - **Purpose**: Uniquely identifies this CFMM pool
   - **Value**: ID placeholder `$lpNFT`

2. **LP Tokens** (`poolIn.tokens(1)`)
   - **Type**: Native token (fungible)
   - **Purpose**: Represents liquidity provider shares (not validated here, but stored in pool state)

3. **Reserve Tokens Y** (`poolIn.tokens(2)._2`)
   - **Type**: Native token (fungible)
   - **Purpose**: One side of the liquidity pair; amount is used in CFMM formula

4. **User Input Tokens** (`SELF.tokens(0)._2`)
   - **Type**: Native token (fungible)
   - **Purpose**: Base asset being swapped; consumed as input

---

## Integration Pattern

### Off-chain Bot / Frontend Responsibilities

1. **Read Pool State**
   - Query the current pool box to fetch `X`, `Y` reserves and `poolNFT`

2. **Calculate Quote**
   - Compute expected `quoteAmount` given user's `baseAmount` input
   - Apply slippage tolerance (e.g., user sets max acceptable loss)
   - Back-calculate: `deltaNErgs = quoteAmount × (DexFeePerTokenDenom - DexFeePerTokenNum) / DexFeePerTokenDenom`

3. **Construct Transaction**
   - **Input 0**: Pool box (unspent, read-only reference)
   - **Input 1+**: User's box (SELF) containing base tokens
   - **Output 0/1**: Pool box output (updated reserves after swap)
   - **Output 2**: Reward box with `rewardBox.value = SELF.value + deltaNErgs` (net ERGs received)
   - Additional outputs: change, miner fee (not validated here)

4. **Sign & Submit**
   - User signs the transaction with private key
   - Contract validates fairness on-chain; if any condition fails → rejection

### Context Extension
- Not used in this contract (no `getVar` calls)

---

## Related Contracts

Based on naming and structure:

1. **SwapSellV1** — Mirror contract for ERG → Token swaps
   - Likely uses same CFMM formula with X/Y reversed