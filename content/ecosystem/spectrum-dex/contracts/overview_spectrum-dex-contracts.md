---
title: spectrum-finance/ergo-dex — Overview
description: Spectrum DEX (formerly ErgoDEX) — AMM pools, order-book, atomic swaps, LP mechanics
tags: [spectrum-finance, ergo-dex, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/spectrum-finance/ergo-dex"
project: spectrum-finance-ergo-dex
group: defi
priority: high
languages: [ergoscript, scala]
contract_count: 0
pattern_match_count: 0
---
# Developer Overview: spectrum-finance/ergo-dex

## Overview

Spectrum DEX (formerly ErgoDEX) is a decentralized exchange protocol built natively on the Ergo blockchain, implementing both an order-book DEX and an Automated Market Maker (AMM) DEX within the eUTXO model. The protocol supports atomic swaps, partial limit orders, Constant Function Market Makers (CFMMs) using the `x*y=c` invariant, and concentrated liquidity pools (CLPs) that allow liquidity providers to target specific price ranges. By leveraging ErgoScript's expressive smart contract capabilities, ErgoDEX achieves composable, trustless exchange mechanics without requiring a centralized intermediary or mutable global state.

A defining architectural advantage of ErgoDEX arises directly from Ergo's eUTXO model: liquidity pool contracts and order contracts are composable at the protocol level, enabling shared liquidity between the AMM and order-book execution paths. This was not achievable in account-based DeFi models. Each pool or order is represented as a Box carrying tokens, ERG value, and contract logic encoded as an ErgoTree, with state encoded in Registers. Pool state transitions (swaps, deposits, redemptions) are validated entirely on-chain by ErgoScript while the computational work of constructing valid transactions is delegated to off-chain bots.

The project plays a foundational role in the Ergo DeFi ecosystem, serving as the primary on-chain liquidity venue for ERG and native tokens. Its tokenomics model distributes execution fees across miners, UI providers, off-chain executors, and liquidity providers (LPs), creating aligned incentives for each class of participant. The protocol is designed to be permissionlessly executable — anyone may run an off-chain bot, submit valid transactions, and earn execution fees, reinforcing decentralization at the infrastructure layer.

---

## Architecture

ErgoDEX is structured as a two-layer system: an **on-chain contract layer** (ErgoScript validation logic embedded in Boxes) and an **off-chain execution layer** (Scala-based bots and SDKs that construct and submit transactions).

### On-Chain Components

| Component | Description |
|---|---|
| **CFMM Pool Box** | Holds reserves of two assets, a Singleton/State NFT identifying the pool, and LP tokens. The ErgoTree enforces the `x*y=c` invariant on every swap. |
| **Concentrated Liquidity Pool (CLP) Box** | An extension of CFMM restricted to a price range; maintains virtual reserves and tracks active/inactive positions. |
| **Swap Order Box** | Created by a trader; holds input assets and encodes execution parameters (minOutput, fee, refund address) in Registers. |
| **Deposit Order Box** | Encodes a request to add liquidity proportional to pool reserves; redeemed by the executor who mints LP tokens. |
| **Redeem Order Box** | Encodes a request to burn LP tokens and withdraw a proportional share of pool reserves. |
| **LP Token Box** | Minted as a native token during deposits; Token ID is derived deterministically from the pool's State NFT, enforcing the Token ID rule. |

### State NFT / Singleton Pattern

Each AMM pool is uniquely identified by a **Singleton NFT** (a native token with supply of 1) held in the Pool Box. This NFT acts as the pool's identity across all state transitions — the ErgoScript in the Pool Box requires this NFT to be present in the self output, preventing pool duplication and ensuring the correct pool Box is consumed in any given transaction.

### Data Flow

```
Trader / LP
    │
    ▼
[Order Box created on-chain]  ← eUTXO holding assets + Registers (params)
    │
    ▼
Off-Chain Bot
    │  reads UTXOs, constructs Transaction
    ▼
[Pool Box (input)] + [Order Box (input)]
    │  ErgoScript validates invariant, fee, min output
    ▼
[Pool Box (output)] + [Return Box to trader] + [Executor fee Box]
```

The off-chain bot acts as the **executor**: it scans the mempool and UTXO set, selects compatible order boxes and pool boxes, builds a balanced transaction satisfying all ErgoScript conditions, and submits it. The on-chain scripts perform all correctness enforcement — the bot cannot steal funds or violate the invariant because any such transaction would be rejected by the network.

### Order-Book Path

For the order-book DEX, atomic limit orders and partial limit orders are stored as Boxes. Partial orders carry remaining-fill state in Registers and are consumed/re-created by the bot across multiple partial fills. ErgoDEX bots aggregate these orders, match compatible pairs, and construct multi-input transactions that satisfy both orders' ErgoScript conditions simultaneously — a form of atomic swap at the transaction level.

---

## Smart Contracts

All contracts are written in **ErgoScript** and compiled to **ErgoTree** bytecode stored in the `propositionBytes` of each Box. The contracts rely on ErgoScript context variables (`SELF`, `INPUTS`, `OUTPUTS`, `HEIGHT`) and Registers (`R4`–`R9`) to encode state and enforce transitions.

### CFMM Pool Contract

**Responsibility:** Enforce the constant product invariant `x * y = k` across swap operations and validate deposit/redeem mechanics.

**Key enforcement points:**
- Output pool Box must contain the Singleton State NFT (pool identity check).
- For swaps: `reservesX_out * reservesY_out >= reservesX_in * reservesY_in` (after fee deduction), enforcing the invariant.
- Fee rate is encoded in a Register (e.g., `R4`) and applied as `amountIn * (feeNumerator / feeDenominator)` before invariant check.
- Minimum output amount (`minOutput`) is read from the swap order Box's Register and validated against actual output sent to the trader.
- Storage rent compliance: output Boxes must meet **minimum box value** thresholds in ERG.

### Deposit Contract

**Responsibility:** Validate that LP tokens are minted proportionally to the deposited asset amounts relative to current pool reserves.

**Key enforcement points:**
- LP token minting amount must satisfy `lpMinted / totalLpSupply = depositX / reservesX = depositY / reservesY`.
- LP Token ID is verified against the pool's State NFT-derived token identifier.
- Refund path: if the order is not executed within a time window (`HEIGHT > deadline` encoded in Register), the depositor can reclaim their Box via a `proveDLog` spending path.

### Redeem Contract

**Responsibility:** Validate proportional withdrawal of pool reserves against LP tokens burned.

**Key enforcement points:**
- `withdrawnX / reservesX = withdrawnY / reservesY = lpBurned / totalLpSupply`.
- LP tokens in the input must be destroyed (supply decremented).

### Swap Order Contract (Order-Book)

**Responsibility:** Allow a swap to execute only if the trader receives at least `minQuoteAmount` of the desired asset, otherwise allow the trader to cancel.

**Key enforcement points:**
- `OUTPUTS(0).tokens` must include at least `minQuoteAmount` of target Token ID sent to `rewardAddress` (stored in `R4`).
- Cancellation path: `proveDLog(rewardPk)` where `rewardPk` is stored in a Register.
- Execution fee (in ERG) released to executor Box validated by amount check.

### Concentrated Liquidity Contracts

**Responsibility:** Extend CFMM logic with price-range bounds (`sqrtPriceLower`, `sqrtPriceUpper` stored in Registers). Liquidity only accumulates fees while the active price is within the position's range. Out-of-range positions hold only one asset, behaving like a limit order.

**Context Extensions:** Used in some contracts to pass off-chain computed values (e.g., square root prices) into the ErgoScript evaluation context without storing them on-chain, keeping Box size minimal.

---

## Integration Guide

### Reading Pool State

Pool Boxes are identifiable by their Singleton State NFT. Query the Ergo node or an explorer API for UTXOs containing a known pool NFT Token ID:

```
GET /api/v1/boxes/unspent/byTokenId/{poolNftTokenId}
```

Pool reserves are read directly from the Box