---
title: kushti/dexy-stable — SwapBuyV2.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapBuyV2.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapBuyV2.es
project: kushti-dexy-stable
---
# SwapBuyV2.es Contract Analysis

## Purpose

This contract executes a **Token-to-ERG atomic swap** on the Dexy liquidity pool, validating that a user receives fair market price when selling a token for nanoErgs. It enforces DEX fee constraints and ensures the pool's pricing invariant is maintained via the Constant Function Market Maker (CFMM) formula.

---

## Inputs / Outputs

### Inputs
1. **INPUTS(0)** – Pool Box (eUTXO)
   - Contains Pool NFT (authentication token)
   - Holds X reserves (nanoErgs) in box value
   - Holds Y reserves (third token) as native token

2. **SELF** – Swap Proxy Box (this contract)
   - Holds the input token amount in `SELF.tokens(0)._2`
   - Carries nanoErgs for transaction fees

3. **INPUTS(2)** (implied) – User's input box or additional context

### Outputs
1. **OUTPUTS(0)** – Pool Box (updated reserves after swap)
2. **OUTPUTS(1)** – Action/State Box (Dexy protocol mechanics)
3. **OUTPUTS(2)** (rewardBox) – User's reward box
   - Receives delta nanoErgs (`rewardBox.value - SELF.value`)
   - Must be spendable by `RedeemerPropBytes` (user's address)

4. **Additional outputs** – May include miner fee box

---

## Key Logic

### Validation Conditions (in execution order)

1. **Structural Validity**
   ```
   INPUTS.size == 3 && poolIn.tokens.size == 3
   ```
   - Exactly 3 inputs and pool must hold exactly 3 tokens (NFT + base asset + quote asset)

2. **Pool Authentication**
   ```
   poolNFT == PoolNFT
   ```
   - First token in pool input matches the Dexy pool NFT singleton identifier

3. **Quote Amount Calculation** (inverse fee math)
   ```
   deltaNErgs = rewardBox.value - SELF.value
   quoteAmount = deltaNErgs * DexFeePerTokenDenom / (DexFeePerTokenDenom - DexFeePerTokenNum)
                = deltaNErgs * 10 / (10 - 1)
                = deltaNErgs * 10 / 9
   ```
   - Back-calculates the gross quote before DEX fee was deducted
   - Accounts for the 1/10 DEX fee structure

4. **Fair Price Validation** (CFMM invariant)
   ```
   poolReservesX * baseAmount * FeeNum 
   <= 
   relaxedOutput * (poolReservesY * FeeDenom + baseAmount * FeeNum)
   ```
   - Substituting constants: `X × baseAmount × 996 ≤ relaxedOutput × (Y × 1000 + baseAmount × 996)`
   - Ensures: `k' ≥ k` (product of reserves increases or stays equal)
   - Relaxed by +1 to handle rounding losses
   - Prevents arbitrage and enforces fair swap pricing

5. **Minimum Quote Protection**
   ```
   quoteAmount >= MinQuoteAmount (800L nanoErgs)
   ```
   - Prevents dust-value swaps

6. **Output Destination**
   ```
   rewardBox.propositionBytes == RedeemerPropBytes
   ```
   - Ensures quote amount goes to authorized redeemer (user)

7. **Miner Fee Constraint**
   ```
   sum(minerFee boxes) <= MaxMinerFee
   ```
   - Prevents excessive transaction fees

---

## Registers Used

**None explicitly referenced** (R0-R3 are implicit in Box context).

- **Implicit**: Box value (stored implicitly, accessed via `.value`)
- **Implicit**: Token list (accessed via `.tokens(index)`)

This is a **stateless validator** contract; complex state lives in the **Pool Box** (separate contract) and **Action Box** (Dexy protocol).

---

## Tokens

### Native Tokens Used

1. **Pool NFT** (`poolIn.tokens(0)._1`)
   - **Purpose**: Singleton identifier for the pool eUTXO
   - **Type**: Single-instance NFT (token quantity = 1)
   - **Validation**: `poolNFT == PoolNFT` (constant)

2. **Base Asset** (`SELF.tokens(0)._2`)
   - **Purpose**: Token being sold in swap
   - **Type**: Quantity stored; token ID implicitly identified by position

3. **Quote Asset** (`poolIn.tokens(2)._2`)
   - **Purpose**: Pool's Y-asset reserve (the token being bought is ERG, so this is Y reserve)
   - **Type**: Balance tracked for pricing curve

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Box Selection**
   - Select pool eUTXO with valid Pool NFT
   - Select user's input token box

2. **Quote Calculation** (off-chain)
   ```
   userBaseAmount = selected input token quantity
   poolX = poolBox.value (nanoErgs)
   poolY = poolBox.tokens(2)._2
   
   // Compute quote using CFMM: out = Δx × X × fee / (Y + Δx × fee)
   quoteGross = (userBaseAmount * poolX * 996) / (poolY * 1000 + userBaseAmount * 996)
   quoteNet = quoteGross * 9 / 10  // subtract 1/10 DEX fee
   ```

3. **Transaction Construction**
   - **Input 0**: Pool box
   - **Input 1**: User's token box (amount = `userBaseAmount`)
   - **Input 2**: User's nanoErg box (for fees)
   - **Output 0**: Pool box (updated reserves)
   - **Output 1**: Action box (Dexy protocol state)
   - **Output 2**: Reward box