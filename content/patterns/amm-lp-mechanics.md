---
title: AMM / LP mechanics
description: AMM / LP mechanics — swap math, liquidity provision, LP token minting, fee extraction, pool state boxes
tags: [amm-lp-mechanics, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [spectrum-finance/ergo-dex, kushti/dexy-stable]
---
# Ergo AMM / LP Mechanics: Comprehensive Developer Guide

## Overview

### What This Pattern Is

Automated Market Maker (AMM) with Liquidity Provider (LP) mechanics is the foundational primitive of decentralized exchange on Ergo. Specifically, Ergo's ecosystem (led by Spectrum Finance, formerly ErgoDex) implements **Constant Function Market Maker (CFMM)** pools — most commonly the constant product formula `x * y = k` — entirely within Ergo's eUTXO model.

Unlike account-based AMMs (Uniswap on Ethereum), Ergo AMMs encode all pool state and invariants inside **Boxes** with **ErgoScript** guards, using **Registers** for auxiliary data and **Native tokens** for LP tokens and pool assets. Every interaction — swap, deposit, redeem — is an on-chain **Transaction** that must satisfy the pool's ErgoScript guard without any mutable state.

### Why It Exists

| Problem | CFMM Solution on Ergo |
|---|---|
| Trustless price discovery | Invariant enforced by ErgoScript; no admin keys |
| Permissionless liquidity | Anyone can deposit and receive LP tokens |
| No oracles required for basic swaps | Price emerges from reserve ratio |
| eUTXO statelessness | Pool state box acts as a **Singleton / State NFT** container |

### When to Use It

- Building a DEX, aggregator, or any protocol that needs on-chain price discovery
- Implementing yield strategies that interact with liquidity pools
- Writing off-chain order-matching bots that compose swap/deposit/redeem transactions
- Any multi-stage contract pattern where a pool box is consumed and recreated each block

---

## How It Works

### Core Concepts

#### The Pool State Box

Every CFMM pool is represented by a single **Box** (enforced as a singleton via a **State NFT** / pool NFT token) that holds:

| Slot | Contents |
|---|---|
| `value` (nanoERG) | Minimum box value + ERG reserve (if ERG/token pool) |
| `tokens[0]` | Pool NFT (Token ID rule: 1 token, quantity 1, proves singleton) |
| `tokens[1]` | LP token reserve (unissued LP tokens remaining) |
| `tokens[2]` | Asset X reserve |
| `tokens[3]` | Asset Y reserve (omitted for ERG/token pools) |
| `R4` | Fee numerator |
| `R5` | Fee denominator |

The pool's **ErgoTree** (compiled ErgoScript) is the immutable guard that validates every state transition.

#### The Constant Product Invariant

```
x * y = k
```

Where `x` and `y` are reserve amounts. The invariant after a swap with fee:

```
(x + dx * feeNum / feeDenom) * (y - dy) >= x * y
```

This means the protocol fee (`1 - feeNum/feeDenom`) stays in the pool, accruing to LPs.

### Step-by-Step Flow

#### Flow 1: Pool Initialization

```
1. Creator issues Pool NFT (1 token, guaranteed unique by Token ID rule: 
   NFT ID = first input box ID of the creation tx)
2. Creator issues LP token supply (e.g., Long.MaxValue = 9,223,372,036,854,775,807)
3. Initial deposit transaction:
   - Input:  [Creator box with X, Y, LP tokens, Pool NFT]
   - Output: [Pool state box], [Creator LP token reward box]
4. Pool box locks: NFT + remaining LP tokens + X reserves + Y reserves
5. burnLP tokens (e.g., 1000) are permanently locked — prevents zero-liquidity attacks
```

#### Flow 2: Swap (X → Y)

```
1. User submits an Order box (off-chain bot picks it up)
2. Off-chain executor (matcher) constructs a Transaction:
   - Input[0]: Pool state box  (consumed, recreated)
   - Input[1]: User order box  (contains dX amount of token X)
   - Output[0]: New pool state box (x' = x + dX_with_fee, y' = y - dY)
   - Output[1]: User reward box (receives dY of token Y)
   - Output[2]: Executor reward box (protocol/execution fee)
3. ErgoScript on pool box verifies:
   - Pool NFT preserved
   - x' * y' >= x * y  (invariant holds)
   - dY correctly computed from invariant
   - LP token count unchanged
```

#### Flow 3: Liquidity Deposit

```
1. User constructs a Deposit order box containing dX and dY
2. Executor constructs Transaction:
   - Input[0]: Pool state box
   - Input[1]: Deposit order box
   - Output[0]: New pool state box (reserves increased)
   - Output[1]: User LP token reward box
   - Output[2]: Change box (unused portion of smaller asset)
3. LP tokens minted to user = min(dX * supplyLP / x, dY * supplyLP / y)
4. ErgoScript verifies the LP amount is fair relative to pool ratio
```

#### Flow 4: Liquidity Redemption

```
1. User submits Redeem order box containing LP tokens
2. Executor constructs Transaction:
   - Input[0]: Pool state box
   - Input[1]: Redeem order box (contains LP tokens)
   - Output[0]: New pool state box (reserves decreased, LP tokens returned)
   - Output[1]: User reward box (proportional X and Y)
3. Returned amounts: dX = lpIn * x / supplyLP, dY = lpIn * y / supplyLP
```

#### Multi-Stage Contract Architecture

```
┌─────────────────────────────────────────────────────┐
│                   CFMM Transaction                   │
│                                                      │
│  Inputs:          Outputs:                           │
│  ┌──────────┐     ┌──────────┐                      │
│  │ Pool Box │────▶│ Pool Box │  (same ErgoTree,      │
│  │ (State)  │     │ (State') │   new reserves)       │
│  └──────────┘     └──────────┘                      │
│  ┌──────────┐     ┌──────────┐                      │
│  │  Order   │────▶│  User    │  (reward)             │
│  │  Box     │     │  Box     │                       │
│  └──────────┘     └──────────┘                      │
│                   ┌──────────┐                      │
│                   │ Executor │  (fee)                │
│                   │  Box     │                       │
│                   └──────────┘                      │
└─────────────────────────────────────────────────────┘
```

---

## Implementation

### Part 1: Core Pool Math (Scala — from Spectrum Finance)

```scala
// spectrum-finance/ergo-dex: CfmmPool.scala
package io.ergodex.core.cfmm

/**
 * PoolConfig encapsulates immutable pool parameters.
 *
 * @param feeNum           Fee numerator (e.g., 995 means 0.5% fee when denom=1000)
 * @param feeDenom         Fee denominator (e.g., 1000)
 * @param emissionLP       Total LP token supply ever emitted (Long.MaxValue typical)
 * @param burnLP           LP tokens permanently burned at init (prevents sqrt(0) attack)
 * @param minInitialDeposit Minimum initial liquidity required
 */
final case class PoolConfig(
  feeNum: Int,
  feeDenom: Int,
  emissionLP: Long,
  burnLP: Long,
  minInitialDeposit: Long
)

/**
 * CfmmPool is the pure functional model of pool state.
 * x, y  = current reserves of asset X and Y
 * lp    = LP tokens currently held IN the pool box (unissued)
 *
 * supplyLP = tokens already issued to liquidity providers
 *          = emissionLP - lp
 *
 * IMPORTANT: Use BigInt for intermediate calculations to avoid
 * Long overflow — reserves can be near Long.MaxValue.
 */
final case class CfmmPool(x: Long, y: Long, lp: Long, config: PoolConfig) {

  val supplyLP: Long = config.emissionLP - lp

  /**
   * Compute new pool state after a deposit of (inX, inY).
   * LP tokens issued = min(inX * supplyLP / x, inY * supplyLP / y)
   * This is the "minimum of two ratios" formula ensuring the pool
   * ratio is maintained — excess of the larger-ratio asset is returned
   * as change to the depositor.
   */
  def deposit(inX: Long, inY: Long): CfmmPool = {
    val unlocked = math.min(
      // Use BigInt to prevent overflow in multiplication
      (BigInt(inX) * supplyLP / x).toLong,
      (BigInt(inY) * supplyLP / y).toLong
    )
    // New reserves: full deposit amounts added (change handled in order contract)
    // New LP in pool: reduced by unlocked amount (those go to user)
    CfmmPool(x + inX, y + inY, lp - unlocked, config)
  }

  /**
   * Compute new pool state after redeeming lpIn LP tokens.
   * Returns proportional share: dX = lpIn * x / supplyLP
   *                             dY = lpIn * y / supplyLP
   */
  def redeem(lpIn: Long): CfmmPool = {
    val retX = (BigInt(lpIn) * x / supplyLP).toLong
    val retY = (BigInt(lpIn) * y / supplyLP).toLong
    CfmmPool(x - retX, y - retY, lp + lp