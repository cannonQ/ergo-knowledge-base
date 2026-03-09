---
title: kushti/dexy-stable — SwapSellV1.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapSellV1.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapSellV1.es
project: dexy-use
---
# SwapSellV1 Contract Analysis

## Purpose

This contract validates a **token swap transaction** in a liquidity pool (LP) where a user sells a base asset and receives a quote asset in return. It enforces fair pricing based on the Constant Function Market Maker (CFMM) formula and validates that the DEX fee is correctly collected, preventing front-running and arbitrage attacks on swaps.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)** — Pool Box (the liquidity pool state machine box)
  - Must contain 3 tokens: Pool NFT, base asset reserve, quote asset reserve
  - Holds the current reserve amounts (`poolReservesX`, `poolReservesY`)
- **INPUTS(1+)** — User input box(es) (implicit; not directly validated here)
- **SELF** — This contract's box being spent (contains base tokens being swapped)

### Outputs
- **OUTPUTS(2)** — Reward/Swap Output Box
  - Receives the quote asset tokens (payment to user)
  - Must hold the correct DEX fee in ERG value
  - Expected to be sent to user's address (commented-out validation for `Pk.propBytes`)

---

## Key Logic

The contract enforces three critical conditions:

### 1. **Pool Structure Validation** (`validPoolIn`)
```
poolNFT == fromBase64("$lpNFT")
```
- Verifies that INPUTS(0) contains the correct Pool NFT (Singleton token)
- Prevents swapping against fraudulent or wrong pools
- The `$lpNFT` is a **constant segregation** placeholder injected off-chain

### 2. **Fair Price Validation** (`fairPrice`)
```
poolReservesY * BaseAmount * FeeNum <= relaxedOutput * (poolReservesX * FeeDenom + BaseAmount * FeeNum)
```
- Applies the **CFMM invariant** (x·y = k, with fee adjustment)
- Constants:
  - `FeeNum = 997`, `FeeDenom = 1000` → 0.3% DEX fee
  - `BaseAmount = 1200L` → hardcoded swap amount (base asset quantity)
  - `relaxedOutput = quoteAmount + 1` → handles rounding loss (allows ±1 precision)
- Ensures user receives **at least fair market price** after fee deduction
- Prevents the pool from being drained below fair exchange rates

### 3. **DEX Fee Collection** (`fairDexFee`)
```
rewardBox.value >= SELF.value - quoteAmount * DexFeePerTokenNum / DexFeePerTokenDenom - BaseAmount
```
- Verifies ERG fee is collected from the reward box
- Fee calculation: `quoteAmount * (10 / 100000)` = 0.01% per token
- Compensates the protocol for liquidity provision and DEX infrastructure

---

## Registers Used

**None explicitly used in this contract.**

- The contract relies entirely on **Box value and tokens** (implicit UTXO fields)
- Pool state is encoded in **poolIn.tokens** (NFT and reserve amounts)
- No R4-R9 registers are read or written

---

## Tokens

### Pool NFT (Singleton)
- **Token ID**: `fromBase64("$lpNFT")` — injected as constant via **Context extension**
- **Purpose**: Identifies the correct liquidity pool to prevent swap routing attacks
- **Location**: `poolIn.tokens(0)._1`

### Base Asset
- **Quantity**: Implied to be `BaseAmount = 1200L` (hardcoded)
- **Location**: SELF box (the spending box)

### Quote Asset
- **Token ID**: Returned from pool, stored in `rewardBox.tokens(0)._1`
- **Quantity**: `quoteAsset._2` — dynamically calculated by CFMM formula
- **Location**: OUTPUTS(2)

---

## Integration Pattern

### Off-Chain Bot / Dapp Responsibilities

1. **Inject Pool NFT Constant**
   - Compile contract with `$lpNFT` substituted with actual pool NFT ID via **constant segregation**

2. **Construct Transaction**
   - **INPUTS(0)**: Retrieve and spend the current pool box
   - **INPUTS(1)**: User's box containing base asset tokens
   - **OUTPUTS(0)**: New pool box with updated reserves
   - **OUTPUTS(2)**: Reward box with quote tokens + DEX fee in ERG

3. **Calculate Quote Amount**
   ```
   quoteAmount = (poolReservesY * BaseAmount * FeeNum) / (poolReservesX * FeeDenom + BaseAmount * FeeNum)
   ```
   - Off-chain pre-calculates expected output before signing

4. **Sign Transaction**
   - User must sign with **Sigma protocol** to authorize spending their base asset box
   - Pool NFT constant must match on-chain pool state (no replay)

5. **Fee Deduction**
   - Ensure `rewardBox.value >= (SELF.value - dexFee - BaseAmount)`
   - This enforces fee extraction from user's ERG balance

### Validation Flow
```
User sends Tx → Bot constructs INPUTS(0,1) + OUTPUTS → 
Contract verifies pool NFT + fair price + fee → 
Tx settles on-chain
```

---

## Related Contracts

### Inferred Composition
1. **Pool Contract** — The contract protecting the pool box (INPUTS(0))
   - Must validate that reserves are updated correctly
   - Enforces the invariant `(X + baseAmount * FeeNum) * (Y - quoteAmount) >= X * Y`

2. **User Authorization** — External contract or P2PK signature
   - User's input box (INPUTS(1)) must be spent with valid signature
   - Not enforced in this contract (typical for **composable eUTXO** design)

### Design Pattern
This is part of a **multi-stage swap contract** system:
- **SwapSellV1** ← validates swap execution (this contract)
- **Pool Contract** ← protects liquidity reserves
- **Off-chain