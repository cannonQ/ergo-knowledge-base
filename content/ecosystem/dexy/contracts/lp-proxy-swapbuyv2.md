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
project: kushti-dexy-stable
---
# SwapBuyV2 Contract Analysis

## Purpose

This contract implements a **liquidity pool swap proxy** that facilitates **Token → ERG exchanges** within the Dexy stable protocol. It validates fair pricing against an AMM pool reserves, enforces fee constraints, and ensures the transaction either executes a valid trade or permits refunds—enabling trustless token-for-nanoErg atomic swaps.

---

## Inputs / Outputs

### Inputs
| Position | Role | Purpose |
|----------|------|---------|
| `INPUTS(0)` | **Pool Box** | The AMM pool UTXO holding reserves: nanoErgs (X asset), Pool NFT, and Y token reserves |
| `INPUTS(1)` | **Self (Proxy Box)** | The contract instance; holds the base asset tokens being swapped |
| `INPUTS(2+)` | *Optional* | Additional inputs (not validated here) |

### Outputs
| Position | Role | Purpose |
|----------|------|---------|
| `OUTPUTS(0)` | Pool Box | Updated pool state after swap (implicitly returned) |
| `OUTPUTS(1)` | Action Box | State machine marker for Dexy action sequencing |
| `OUTPUTS(2)` | **Reward Box** | Receives quote amount (ERG proceeds from swap); must match `RedeemerPropBytes` |
| `OUTPUTS(3+)` | Miner Fee | Must be paid to `MinerPropBytes` address; validated ≤ `MaxMinerFee` |

---

## Key Logic

### Validation Flow

The contract enforces **`sigmaProp(RefundProp || validTrade)`**, meaning:
- **Refund path**: Anyone holding `RefundProp` can reclaim the proxy box
- **Trade path**: Strict conditions must all pass:

### Trade Validation Conditions

1. **Structural Requirements**
   - `INPUTS.size == 3`: Exactly 3 inputs (Pool, Self, one more)
   - `poolIn.tokens.size == 3`: Pool holds 3 tokens (NFT + two reserves)

2. **Pool Authentication**
   - `poolNFT == PoolNFT`: First token in pool must match expected Singleton NFT
   - Ensures this is the intended liquidity pool, not a fake

3. **Fair Price Validation** (Core AMM Logic)
   ```
   fairPrice = poolReservesX * baseAmount * FeeNum 
             ≤ relaxedOutput * (poolReservesY * FeeDenom + baseAmount * FeeNum)
   ```
   - Computes **quote amount** from output nanoErgs, accounting for Dexy fees:
     ```
     quoteAmount = deltaNErgs * DexFeePerTokenDenom 
                   / (DexFeePerTokenDenom - DexFeePerTokenNum)
                 = deltaNErgs * 10 / 9
     ```
   - Adds relaxation (+1) for rounding loss tolerance
   - Validates the swap ratio respects CFMM invariant: **x·y = k** with 0.4% protocol fee (`FeeNum = 996/1000`)

4. **Quote Bounds**
   - `quoteAmount >= MinQuoteAmount`: Minimum output (800 nanoErgs) to prevent dust

5. **Output Routing**
   - `rewardBox.propositionBytes == RedeemerPropBytes`: Quote must go to authorized redeemer
   - Prevents fund misdirection

6. **Fee Compliance**
   - `validMinerFee`: Sum of all outputs to miner (identified by `MinerPropBytes`) ≤ `MaxMinerFee`
   - Enforces **minimum transaction fee** rule per Ergo blockchain

---

## Registers Used

**No R4–R9 registers are read or written.** This is a **stateless validation contract**:
- State transitions are managed by the **Pool Box** (modified in external outputs)
- Configuration (NFT IDs, addresses) is **hard-coded as constants**

| Constant | Value | Purpose |
|----------|-------|---------|
| `FeeDenom` | 1000 | Denominator for AMM fee ratio |
| `FeeNum` | 996 | Numerator: 996/1000 = 0.4% fee |
| `DexFeePerTokenNum` | 1 | Dexy protocol fee numerator |
| `DexFeePerTokenDenom` | 10 | Dexy protocol fee denominator (1/10 = 10%) |
| `MinQuoteAmount` | 800L nanoErgs | Dust prevention threshold |
| `PoolNFT` | *(injected constant)* | Singleton NFT identifying the pool |
| `MinerPropBytes` | *(injected constant)* | Serialized Sigma proposition for miner address |
| `RedeemerPropBytes` | *(injected constant)* | Serialized Sigma proposition for reward recipient |
| `MaxMinerFee` | *(injected constant)* | Maximum allowed miner fee in nanoErgs |
| `RefundProp` | *(injected constant)* | Sigma protocol allowing refunds (e.g., multisig) |

---

## Tokens

| Token Type | Role | Location |
|------------|------|----------|
| **Pool NFT** | State machine identifier | `poolIn.tokens(0)._1` |
| **Base Asset** | Input token being sold | `SELF.tokens(0)._2` (amount in proxy box) |
| **Quote Asset (ERG)** | Received from pool | `rewardBox.value` (nanoErgs) |
| **Y Reserve Token** | Liquidity pool reserve | `poolIn.tokens(2)._2` (pool's Y-side liquidity) |

---

## Integration Pattern

### Off-Chain Responsibilities

1. **Transaction Construction** (Off-chain bot / Headless dApp)
   - Fetch pool box from blockchain
   - Calculate fair quote using CFMM formula:
     ```
     quote = poolReservesX * baseAmount / (poolReservesY + baseAmount) * 996/1000