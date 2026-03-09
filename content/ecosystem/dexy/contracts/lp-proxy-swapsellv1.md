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
project: kushti-dexy-stable
---
# SwapSellV1 Contract Analysis

## Purpose

This contract validates a token swap transaction on the Dexy/Spectrum Finance AMM (Automated Market Maker), specifically a **sell operation** where a user swaps a base asset for a quote asset through a liquidity pool. It ensures the trade respects the constant product formula (CFMM), fair pricing, and protocol fees before allowing the swap to settle.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)** – Pool Box (the AMM liquidity pool state box)
  - Must contain 3 tokens: [Pool NFT, Pool X reserve, Pool Y reserve]
  - Holds native ERG value representing poolReservesX
  
- **INPUTS(1+)** – User/Swap Box(es) (inferred, not directly validated in this contract)
  - Supplies the BaseAmount (1200 nanoERG equivalent) being sold

### Outputs
- **OUTPUTS(2)** – Reward/Settlement Box
  - Contains the quoted asset tokens received by the user
  - Holds ERG value for fee settlement
  - Must satisfy fairDexFee and fairPrice invariants

---

## Key Logic

### 1. **Pool Validation**
```
validPoolIn: poolNFT == fromBase64("$lpNFT")
```
Verifies the input box contains the correct LP Pool NFT (injected as constant `$lpNFT`), ensuring atomic binding to the intended liquidity pool.

### 2. **Fair Dex Fee**
```
fairDexFee = rewardBox.value >= SELF.value - (quoteAmount * DexFeePerTokenNum / DexFeePerTokenDenom) - BaseAmount
```
- Dexy protocol charges a **1% fee per token** (10/100000 = 0.01% per token, scaled)
- Fee is deducted from the reward box's ERG value
- Ensures sufficient ERG remains after fee and base amount deduction
- Implements **state rent** compliance by maintaining minimum box value

### 3. **Fair Price (Constant Product Formula)**
```
poolReservesY * BaseAmount * FeeNum <= relaxedOutput * (poolReservesX * FeeDenom + BaseAmount * FeeNum)
```
Enforces the **CFMM invariant** with **Spectrum's 0.3% swap fee** (FeeNum=997, FeeDenom=1000):
- **Left side**: `y * Δx * (1 - fee)` – expected output without fee impact
- **Right side**: `relaxedOutput * (x + Δx * (1 - fee))` – ensures new reserve product ≥ old reserve product
- `relaxedOutput + 1` tolerates **rounding loss** from fixed-precision arithmetic
- Prevents arbitrage and maintains pool solvency

### 4. **Transaction Structure Validation**
```
INPUTS.size >= 3 && poolIn.tokens.size == 3
```
Requires at least 3 inputs (pool, user swap box, and likely a fee collector) and confirms pool carries exactly 3 tokens.

---

## Registers Used

**None explicitly accessed** in this contract.

- The script reads only **box values** (`value`), **box tokens** (`tokens`), and **context fields** (`INPUTS`, `OUTPUTS`, `SELF`).
- Pool state is encoded in tokens and ERG value, not in R4–R9 registers.
- **Implication**: This is a **stateless validator contract**; pool state mutations are managed externally by the off-chain bot.

---

## Tokens

### Pool NFT (Singleton)
- **Token ID**: `$lpNFT` (base64-encoded constant)
- **Role**: Authenticates the liquidity pool box; ensures swaps execute against the correct pool
- **Quantity**: 1 (Ergo's "Token ID rule" – only one NFT per token class in a box)

### Pool Reserves
- **poolIn.tokens(1)** – Base asset reserve (X)
  - Encoded in token quantity or pool box ERG value
- **poolIn.tokens(2)** – Quote asset reserve (Y)
  - Token ID and amount `poolY._2` represent liquidity in quote asset

### Output Quote Token
- **quoteAsset = rewardBox.tokens(0)**
  - The asset the user receives post-swap
  - Amount validated against fair price logic

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Box Construction**
   - Assemble INPUTS: pool box (from chain state), user swap box, and additional boxes for fees/outputs
   - Calculate fair price given current `poolReservesX`, `poolReservesY`, and user's `BaseAmount`
   - Compute `quoteAmount` such that fairPrice condition holds

2. **Parameter Injection**
   - Replace `$lpNFT` constant with the actual pool NFT token ID before deployment

3. **Output Assembly**
   - Create OUTPUTS(2) with:
     - `value >= SELF.value - (quoteAmount * 10 / 100000) - 1200` (ERG)
     - `tokens(0) = (quoteAssetId, quoteAmount)` (quoted tokens)
   - Ensure output box respects Ergo's **minimum box value** (4.8 ERG default for most boxes)

4. **Transaction Signing**
   - After script validation passes, append a valid **Sigma protocol signature** (P2PK) to authorize spending

### Context Extension
- None required; all validation happens on-chain against current box state

---

## Related Contracts

### Spectrum Finance (Ergo-Dex)
- **SwapSell.sc** (referenced in comment)
  - Original Spectrum AMM swap validator
  - This Dexy contract adapts Spectrum's logic with modified fee structure

### Inferred Dexy Contracts (from project structure)
- **Pool Contract** (`contracts/lp/pool/...`)
  - Manages the liquidity pool state and reserve updates
  - Must preserve reserves across swaps following CFMM invariant
  
- **LP Proxy Container** (`contracts/lp/proxy/...`)
  - Likely orchestrates multi-