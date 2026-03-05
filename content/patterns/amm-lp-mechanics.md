---
title: AMM / LP mechanics
description: AMM / LP mechanics — swap math, liquidity provision, LP token minting, fee extraction, pool state boxes
tags: [amm-lp-mechanics, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [spectrum-finance/ergo-dex, kushti/dexy-stable]
---
# Developer Guide: AMM / LP Mechanics on Ergo

## Overview

Automated Market Makers (AMMs) on Ergo implement Constant Function Market Maker (CFMM) logic — most commonly the constant product formula `x * y = k` — using the eUTXO model. Unlike account-based AMMs (e.g., Uniswap on Ethereum), Ergo's AMM encodes all pool state directly in **Boxes**, with invariants enforced by **ErgoScript** contracts rather than mutable storage.

This pattern exists because:

- Ergo has no mutable global state; all state lives in UTXO boxes
- ErgoScript's Sigma protocols enable trustless, non-custodial pool logic
- Native tokens (Token ID rule) allow LP tokens to be first-class assets minted and burned on-chain
- The eUTXO model enables atomic, composable multi-step swaps and deposits in a single transaction

**Use this pattern when you are building:**
- DEX swap interfaces
- Liquidity provision and withdrawal flows
- LP token-based yield protocols
- On-chain price oracles derived from pool state
- Multi-hop routing across pool boxes

**Canonical implementation:** [Spectrum Finance (formerly ErgoDex)](https://github.com/spectrum-finance/ergo-dex)

---

## How It Works

### 1. Pool State Box

The entire AMM pool is represented as a single **pool state box** — a singleton box identified by a **Singleton / State NFT** (a token with a supply of exactly 1). The box holds:

| Location | Content |
|---|---|
| `SELF.tokens(0)` | Pool NFT (1 token, unique pool identity) |
| `SELF.tokens(1)` | LP token reserves (unminted LP tokens) |
| `SELF.tokens(2)` | Token X reserves |
| `SELF.tokens(3)` | Token Y reserves (or ERG value in ERG/token pools) |
| `R4` | Fee numerator |
| `R5` | Fee denominator |

The pool NFT enforces **singleton** identity: only one UTXO in the blockchain can hold this NFT at any time. Scripts reference `SELF.tokens(0)._1` as the canonical pool ID.

### 2. LP Token Minting and the Emission Model

LP tokens represent proportional ownership of the pool. Spectrum Finance uses a **burn model**:

- `emissionLP` = `Long.MaxValue` — the total possible LP supply
- At pool creation, `burnLP` tokens are permanently destroyed (sent to a provably unspendable address), preventing the pool from ever being fully drained
- `supplyLP = emissionLP - lockedLP` — tokens currently circulating with LPs
- Unminted LP tokens sit **inside** the pool box as `tokens(1)`

This means LP tokens are not minted in the traditional sense; they are pre-minted at pool genesis and **released** from the pool box when liquidity is added, or **recollected** by the pool when liquidity is removed.

### 3. Constant Product Swap Math

For a swap of `Δx` input tokens X:

```
feeAmount = Δx * feeNum / feeDenom
effectiveInput = Δx - feeAmount  (fee stays in pool, growing reserves)
Δy = (effectiveInput * y) / (x + effectiveInput)
```

Where `x`, `y` are current pool reserves. The invariant after the swap:

```
(x + Δx) * (y - Δy) >= x * y
```

The strict inequality captures the fee: fees accrue to LPs by growing the pool reserves relative to outstanding LP supply.

In Spectrum's implementation, fee is applied as:

```
(x + Δx * feeNum / feeDenom) * (y - Δy) = x * y
→ Δy = y * Δx * feeNum / (x * feeDenom + Δx * feeNum)
```

### 4. Liquidity Deposit Flow

```
User sends:
  DepositBox { tokenX: inX, tokenY: inY, R4: refundPK, R5: poolNFT }
  PoolBox(t)  { nft, lpTokens: lp, tokenX: x, tokenY: y }

Transaction produces:
  PoolBox(t+1) { nft, lpTokens: lp - mintedLP, tokenX: x + inX, tokenY: y + inY }
  RewardBox    { lpTokens: mintedLP → user }
  ChangeBox    { excess tokenX or tokenY → user }
```

The minted LP amount is the minimum of the two proportional contributions:

```
mintedLP = min(inX * supplyLP / x,  inY * supplyLP / y)
```

The `min` enforces that the user deposits in the correct ratio; the excess of whichever token is oversupplied is returned as change.

### 5. Liquidity Withdrawal Flow

```
User sends:
  RedeemBox  { lpTokens: inLP, R4: refundPK, R5: poolNFT }
  PoolBox(t) { nft, lpTokens: lp, tokenX: x, tokenY: y }

Transaction produces:
  PoolBox(t+1) { nft, lpTokens: lp + inLP, tokenX: x - outX, tokenY: y - outY }
  UserBox      { tokenX: outX, tokenY: outY }
```

Withdrawal amounts:

```
outX = inLP * x / supplyLP
outY = inLP * y / supplyLP
```

### 6. Order Box Pattern

Because Ergo transactions are assembled off-chain, users do not interact with the pool directly. Instead they submit **order boxes** (Deposit, Swap, Redeem) that sit in the mempool or on-chain. An off-chain **executor** (bot) assembles the transaction combining the order box and pool box, collecting a small **execution fee** for their service. The ErgoScript in both the order box and the pool box must simultaneously validate.

### 7. Fee Extraction

Protocol fees are not extracted per-transaction. They accumulate as reserve growth. Separate **fee boxes** can be defined in the protocol for treasury extraction, validated by the pool script checking that output reserves satisfy a modified invariant that permits a small protocol cut.

---

## Implementation

### Scala: Core CFMM Pool Model

```scala
// spectrum-finance/ergo-dex: CfmmPool.scala
package io.ergodex.core.cfmm

final case class PoolConfig(
  feeNum: Int,
  feeDenom: Int,
  emissionLP: Long,
  burnLP: Long,
  minInitialDeposit: Long
)

final case class CfmmPool(x: Long, y: Long, lp: Long, config: PoolConfig) {

  // LP tokens currently held by liquidity providers
  val supplyLP: Long = config.emissionLP - lp

  /** Deposit inX of token X and inY of token Y.
   *  Returns updated pool state and the LP tokens minted.
   */
  def deposit(inX: Long, inY: Long): CfmmPool = {
    // LP minted is bounded by whichever token is the limiting factor
    val unlocked = math.min(
      inX * supplyLP / x,
      inY * supplyLP / y
    )
    CfmmPool(x + inX, y + inY, lp - unlocked, config)
  }

  /** Redeem inLP LP tokens for underlying X and Y. */
  def redeem(inLP: Long): (Long, Long, CfmmPool) = {
    val outX = inLP * x / supplyLP
    val outY = inLP * y / supplyLP
    (outX, outY, CfmmPool(x - outX, y - outY, lp + inLP, config))
  }

  /** Swap `input` amount of `token` ("x" or "y"), return output amount. */
  def swap(token: String, input: Long): CfmmPool = {
    token match {
      case "x" =>
        val dy = outputAmount(x, y, input)
        CfmmPool(x + input, y - dy, lp, config)
      case "y" =>
        val dx = outputAmount(y, x, input)
        CfmmPool(x - dx, y + input, lp, config)
    }
  }

  /** Output amount for a given input, applying the fee. */
  def outputAmount(reserveIn: Long, reserveOut: Long, input: Long): Long = {
    val feeNum   = config.feeNum
    val feeDenom = config.feeDenom
    // Δout = reserveOut * input * feeNum / (reserveIn * feeDenom + input * feeNum)
    val numerator   = BigInt(reserveOut) * input * feeNum
    val denominator = BigInt(reserveIn) * feeDenom + BigInt(input) * feeNum
    (numerator / denominator).toLong
  }

  /** Minimum input needed to receive at least `output` of the other token. */
  def inputAmount(token: String, output: Long): Long = {
    val (reserveIn, reserveOut) = if (token == "x") (x, y) else (y, x)
    val feeNum   = config.feeNum
    val feeDenom = config.feeDenom
    // Δin = reserveIn * output * feeDenom / ((reserveOut - output) * feeNum) + 1
    val numerator   = BigInt(reserveIn) * output * feeDenom
    val denominator = BigInt(reserveOut - output) * feeNum
    (numerator / denominator + 1).toLong
  }
}

object CfmmPool {
  def init(inX: Long, inY: Long, config: PoolConfig): CfmmPool = {
    require(inX >= config.minInitialDeposit && inY >= config.minInitialDeposit)
    val initialLP = math.min(
      inX * (config.em