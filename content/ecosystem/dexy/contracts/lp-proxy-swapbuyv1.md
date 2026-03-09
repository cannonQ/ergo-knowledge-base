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
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: SwapBuyV1

## Purpose

This contract validates a **Token → ERG swap** transaction in a Constant Function Market Maker (CFMM) liquidity pool with a 1:1 token-to-nanoErg trading pair (n2t). It ensures the user receives a fair market price according to the Automated Market Maker (AMM) invariant, enforcing DEX fees and minimum quote constraints.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)** — Pool Box: Contains the liquidity pool state
  - **tokens(0)**: LP NFT (identifier for pool validity)
  - **tokens(2)**: Y-reserve (token asset amount)
  - **value**: X-reserve (nanoErg amount)
- **SELF** — Swap Request Box: The user's swap input
  - **tokens(0)**: Base amount (the token being sold)
- **INPUTS(2+)** — Supporting boxes (at least 3 total inputs required)

### Outputs
- **OUTPUTS(2)** — Reward Box: The user's output receiving exchanged ERGs
  - **value**: Net nanoErgs after fee deduction

---

## Key Logic

The contract validates a swap through **five critical conditions**:

1. **Structural Validation**: 
   - Minimum 3 inputs must exist
   - Pool box must contain exactly 3 tokens (NFT, reserve token, fee token/other)

2. **Pool Authentication**:
   - First token in pool (NFT) must match the hardcoded `$lpNFT` constant
   - Prevents swaps against unauthorized or spoofed pools

3. **Fee Calculation** (DEX fee extraction):
   - Observed ERG delta: `deltaNErgs = rewardBox.value - SELF.value`
   - Derives true quote amount: `quoteAmount = deltaNErgs × 1000 / (1000 - 5)`
   - This reverses the fee formula: `netErg = quoteAmount × 0.995`
   - Tolerance of `+1` nanoErg handles rounding loss

4. **Minimum Output Guard**:
   - `quoteAmount >= 100L` — prevents dust swaps and griefing attacks

5. **Fair Price Validation** (CFMM Invariant):
   - Core AMM equation: 
     ```
     poolReservesX × baseAmount × (1000 - 997) 
     ≤ 
     relaxedOutput × (poolReservesY × 1000 + baseAmount × 3)
     ```
   - Enforces constant product invariant: `(X + Δx) × (Y - Δy) ≥ X × Y`
   - Fee factor (997/1000 = 0.3% taker fee) reduces effective input
   - Ensures user cannot extract more value than the AMM curve permits

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **None explicitly** | — | This contract uses only **Input/Output boxes** and **box fields** (tokens, value). No R4-R9 data registers are accessed. Pool state is read from the pool box's **tokens** and **value** fields, not register storage. |

---

## Tokens

### NFT (Pool Identifier)
- **Token ID**: `$lpNFT` (injected as constant at compile time)
- **Purpose**: Uniquely identifies the legitimate pool for this swap pair
- **Rule**: Must be the **first token** in the pool box (`poolIn.tokens(0)._1`)
- **Mechanism**: Prevents replay attacks and pool spoofing

### Base Token
- **Location**: `SELF.tokens(0)._2` (amount)
- **Purpose**: The input token being swapped to ERG
- **Authentication**: Held in the user's input box; no explicit ID validation in this contract

### Y-Reserve Token
- **Location**: `poolIn.tokens(2)._2` (amount in pool)
- **Purpose**: Tracks the pool's token liquidity; used in AMM invariant calculation

---

## Integration Pattern

### Off-Chain Bot Responsibilities

1. **Box Construction**:
   - Select a valid pool box by its LP NFT
   - Read current pool reserves (X nanoErgs, Y tokens)
   - Calculate minimum quote: `quote = baseAmount × (reservesX / reservesY) × 0.997`
   - Build reward box with quote amount minus fee

2. **Transaction Assembly**:
   ```
   INPUTS:  [PoolBox, ..., UserSwapBox, ...]  (≥3 inputs)
   OUTPUTS: [ModifiedPoolBox, ?, RewardBox, ...]
   ```
   - Modify pool box: increment Y-reserve by `baseAmount`, decrement X-reserve (nanoErgs)
   - Construct reward box with calculated ERG amount
   - Set `rewardBox.value = quoteAmount × 0.995`

3. **Sigma Proof Construction**:
   - Currently contract expects **only** `validTrade` logic (line commented: `sigmaProp(Pk || validTrade)`)
   - Off-chain must ensure transaction satisfies all five validation conditions above

4. **Verification Responsibility**:
   - Verify pool NFT matches hardcoded constant
   - Calculate fair price locally before submission
   - Monitor slippage and mempool congestion

---

## Related Contracts

### Likely Dependencies
- **Pool Contract** (not shown): 
  - The box at `INPUTS(0)` with NFT `$lpNFT`
  - Likely manages pool state transitions and fee accumulation
  - Must validate that modified pool reserves preserve invariant

- **Spectrum Finance CFMM v1** (upstream reference):
  - Code sourced from `spectrum-finance/ergo-dex` repository
  - This is a **Dexy** project adaptation; original n2t swap logic reused

### Design Pattern
- **Multi-stage contract**: This is the **swap validation stage**; the pool contract is a separate stage managing liquidity state
- **State machine pattern**: Pool acts as singleton (NFT-locked); each swap is a stateless validation layer

---

## Security Notes & Observations