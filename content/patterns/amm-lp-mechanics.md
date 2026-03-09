---
title: AMM / LP mechanics
description: AMM / LP mechanics — swap math, liquidity provision, LP token minting, fee extraction, pool state boxes
tags: [amm-lp-mechanics, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [spectrum-finance/ergo-dex, kushti/dexy-stable]
---
# Ergo AMM / LP Mechanics: Comprehensive Developer Guide

## Overview

Automated Market Makers (AMMs) on Ergo implement Constant Function Market Maker (CFMM) pools using the eUTXO model. Unlike account-based AMMs (Uniswap v2), Ergo's eUTXO architecture encodes all pool state directly inside **Boxes** — each Box carrying token reserves, LP supply, and fee parameters in its value fields and **Registers**.

### Why This Pattern Exists

Ergo has no mutable contract storage. Every "state update" is a transaction that **consumes** the current pool Box and **creates** a successor Box with updated reserves. This creates a clean, auditable state machine:

```
Pool Box (state N) ──→ Transaction ──→ Pool Box (state N+1)
                              ↑
                    Swap / Deposit / Redeem Box
```

The pattern exists because:
- **Native tokens** in Ergo are first-class citizens tracked by **Token ID** — LP tokens are real tokens, not phantom accounting entries
- **Storage rent** (after ~4 years of inactivity, miners can reclaim boxes) means pool boxes must stay active and must hold minimum ERG
- **Multi-stage contracts** allow deposit/redeem orders to sit in mempool boxes until an off-chain operator (bot) batches them against the pool
- The **Singleton / State NFT** pattern ensures only one canonical pool box exists at any time

### When to Use

| Scenario | Use AMM/LP Pattern? |
|----------|-------------------|
| Token-to-token swaps | ✅ Yes |
| Liquidity bootstrapping | ✅ Yes |
| Stable-price swaps (StableSwap) | ✅ Yes (variant) |
| Order-book DEX | ❌ No — use grid/limit order boxes |
| Single-asset yield | ⚠️ Only with custom farm contracts |

---

## How It Works

### 1. Pool State Box Structure

A CFMM pool is represented by a single **Box** protected by the pool's **ErgoTree**. Its structure:

```
Pool Box {
  value:     ERG (≥ minBoxValue, covers storage rent)
  tokens[0]: (Pool NFT / Singleton Token, 1)      ← unique pool identifier
  tokens[1]: (LP Token ID, remaining_supply)       ← unminted LP tokens
  tokens[2]: (Token X, reserveX)                   ← asset X reserve
  tokens[3]: (Token Y, reserveY)                   ← asset Y reserve
  R4: Int    ← feeNum   (e.g. 995 for 0.5% fee)
  R5: Int    ← feeDenom (e.g. 1000)
}
```

The **Pool NFT** (a token with supply = 1 enforced by the **Token ID rule** — a token's ID equals the ID of the UTXO that minted it, making re-creation impossible) acts as a **Singleton** guaranteeing uniqueness. Any transaction claiming to update pool state must carry this NFT in `OUTPUTS(0)`.

### 2. Constant Product Formula

The invariant is:

```
x * y = k
```

For a swap of `Δx` input tokens (fee-adjusted):

```
Δy = (y * Δx * feeNum) / (x * feeDenom + Δx * feeNum)
```

Where:
- `feeNum = 995`, `feeDenom = 1000` → 0.5% fee
- The fee stays **inside the pool**, increasing `k` over time (accruing to LPs)

### 3. LP Token Minting (Deposit Flow)

```
Step 1: User creates a Deposit Order Box
        - Contains inputX tokens, inputY tokens, ERG for fees
        - Protected by DepositContract (refundable if not executed)

Step 2: Off-chain executor (bot) reads pool state (reserveX, reserveY, supplyLP)

Step 3: Bot calculates LP tokens to mint:
        lpByX = inputX * supplyLP / reserveX
        lpByY = inputY * supplyLP / reserveY
        lpOut = min(lpByX, lpByY)          ← conservative: use limiting asset
        change = excess of the non-limiting asset

Step 4: Bot constructs Transaction:
        INPUTS:  [PoolBox, DepositOrderBox]
        OUTPUTS: [PoolBox', UserBox(lpOut LP tokens), ChangeBox]

Step 5: ErgoScript on PoolBox validates:
        - Pool NFT preserved in OUTPUTS(0)
        - New reserveX = old reserveX + inputX
        - New reserveY = old reserveY + inputY  
        - LP tokens emitted = old_lp_reserve - new_lp_reserve = lpOut
        - k invariant satisfied (for swaps)
```

### 4. Swap Flow

```
Step 1: User creates Swap Order Box
        - Contains inputX (or inputY), specifies minOutput
        - Contains Pool NFT reference as Data Input (for price discovery)

Step 2: Bot calculates output:
        outputY = (reserveY * inputX * feeNum) / 
                  (reserveX * feeDenom + inputX * feeNum)

Step 3: Transaction:
        INPUTS:  [PoolBox, SwapOrderBox]
        OUTPUTS: [PoolBox', UserBox(outputY)]

Step 4: ErgoScript validates:
        - outputY ≥ minOutput (slippage protection)
        - x' * y' ≥ x * y   (k non-decreasing)
        - Pool NFT preserved
```

### 5. Redeem (Remove Liquidity)

```
lpIn / supplyLP = share of pool

outputX = lpIn * reserveX / supplyLP
outputY = lpIn * reserveY / supplyLP

LP tokens are sent back to tokens[1] in PoolBox' (increasing remaining supply)
```

### 6. Fee Extraction

Fees are **implicit** — they accumulate in reserves. There is no explicit fee extraction per-swap. When an LP redeems, they receive proportionally more than they deposited (the growth in k). Protocol fees (if any) are encoded as an additional output to a fee address, validated by the pool ErgoScript.

---

## Implementation

### 2.1 Core Pool Math (Scala — from `spectrum-finance/ergo-dex`)

```scala
// CfmmPool.scala — core state model
package io.ergodex.core.cfmm

final case class PoolConfig(
  feeNum: Int,
  feeDenom: Int,
  emissionLP: Long,   // total LP tokens ever minted (fixed at pool creation)
  burnLP: Long,       // LP tokens burned at init to prevent 0-liquidity attacks
  minInitialDeposit: Long
)

final case class CfmmPool(x: Long, y: Long, lp: Long, config: PoolConfig) {

  // LP tokens currently in circulation (held by LPs)
  val supplyLP: Long = config.emissionLP - lp

  /** Deposit: add x and y, receive LP tokens
   *  Returns updated pool state after deposit
   */
  def deposit(inX: Long, inY: Long): CfmmPool = {
    // How many LP tokens each input entitles the depositor to
    val byX = inX * supplyLP / x
    val byY = inY * supplyLP / y
    // Conservative: use the minimum (the limiting asset determines LP issued)
    val unlocked = math.min(byX, byY)
    // New pool: reserves increase, LP reserve decreases (tokens leave pool to user)
    CfmmPool(x + inX, y + inY, lp - unlocked, config)
  }

  /** Swap inputAmount of `token` ("x" or "y"), return new pool state */
  def swap(token: String, inputAmount: Long): CfmmPool =
    token match {
      case "x" =>
        // dy = (y * dx * feeNum) / (x * feeDenom + dx * feeNum)
        val dy = (BigInt(y) * inputAmount * config.feeNum) /
                 (BigInt(x) * config.feeDenom + BigInt(inputAmount) * config.feeNum)
        CfmmPool(x + inputAmount, y - dy.toLong, lp, config)
      case "y" =>
        val dx = (BigInt(x) * inputAmount * config.feeNum) /
                 (BigInt(y) * config.feeDenom + BigInt(inputAmount) * config.feeNum)
        CfmmPool(x - dx.toLong, y + inputAmount, lp, config)
    }

  /** Redeem lpAmount LP tokens, receive x and y proportionally */
  def redeem(lpAmount: Long): (Long, Long, CfmmPool) = {
    val outX = lpAmount * x / supplyLP
    val outY = lpAmount * y / supplyLP
    (outX, outY, CfmmPool(x - outX, y - outY, lp + lpAmount, config))
  }

  /** How much input X is needed to get exactly `output` units of Y */
  def inputAmount(token: String, output: Long): Long =
    token match {
      case "x" =>
        // Invert swap formula: dx = (x * dy * feeDenom) / ((y - dy) * feeNum) + 1
        val dx = (BigInt(x) * output * config.feeDenom) /
                 (BigInt(y - output) * config.feeNum) + 1
        dx.toLong
      case "y" =>
        val dy = (BigInt(y) * output * config.feeDenom) /
                 (BigInt(x - output) * config.feeNum) + 1
        dy.toLong
    }
}

object CfmmPool {
  /** Initialize a new pool from initial deposits.
   *  burnLP tokens are locked forever to prevent the pool ever reaching 