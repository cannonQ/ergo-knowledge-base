---
title: Proxy contracts
description: Proxy contracts — user-facing entry points with refund paths, deadline guards, and forwarding to protocol contracts
tags: [proxy-contracts, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [kushti/dexy-stable, paideiadao/paideia-contracts, duckpools/lend-protocol-contracts]
---
# Proxy Contracts on Ergo: A Comprehensive Developer Guide

## Table of Contents
1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Implementation](#implementation)
4. [Common Pitfalls](#common-pitfalls)
5. [References](#references)

---

## Overview

### What Is a Proxy Contract?

A **proxy contract** is a user-facing eUTXO box whose ErgoTree encodes three fundamental guarantees:

| Guarantee | Description |
|-----------|-------------|
| **Forwarding** | Under nominal conditions, the box's ERG and/or Native tokens are forwarded to a protocol contract in a single atomic transaction. |
| **Refund path** | If the protocol cannot or does not execute within a deadline, the user can reclaim the box contents. |
| **Deadline guard** | A block-height condition prevents the protocol from consuming the box after expiry, forcing the refund path. |

### Why Does This Pattern Exist?

Ergo's eUTXO model requires that **every spending condition be encoded in the box's ErgoTree at creation time**. There is no `msg.sender` as in Ethereum's account model. Consequently:

- Users cannot simply "call" a protocol function — they must *place a box* that the protocol's off-chain bots (or any willing executor) can consume.
- The box must protect against:
  - **Executor front-running** — consuming the box but sending funds to the wrong place.
  - **Executor liveness failure** — the executor never acts, locking the user's funds indefinitely.
  - **Fee extraction** — the executor taking more than the agreed execution bounty.

The proxy contract pattern solves all three problems simultaneously.

### When to Use It

Use proxy contracts when:
- Your protocol uses **Multi-stage contracts** where a singleton / State NFT box must be updated in the same transaction as user funds.
- You need **asynchronous execution** — users submit intent boxes that bots later fulfill.
- The protocol contract is a **Singleton / State NFT** that can only be spent once per block, creating a queue of pending user requests.
- You are building AMM swaps, lending operations, staking deposits, or any operation that requires atomic coordination with a shared state box.

Do **not** use proxy contracts when a direct P2PK signature can safely encode the spending condition without a queuing mechanism.

---

## How It Works

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTENT PHASE                        │
│                                                                 │
│  User constructs Proxy Box with:                                │
│    • ERG / tokens to spend                                      │
│    • ErgoTree = proxy script (compiled ErgoScript)              │
│    • R4 = user's refund P2PK address (SigmaProp)               │
│    • R5 = deadline (Int block height)                           │
│    • R6 = min output / slippage tolerance                       │
│    • R7 = execution bounty (Long nanoERG)                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │  User broadcasts TX_0
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PROXY BOX ON CHAIN                         │
│                                                                 │
│  Box is publicly visible in the UTXO set.                       │
│  Off-chain executor bots monitor the mempool / chain.           │
└──────────┬──────────────────────────────────────┬───────────────┘
           │  HEIGHT < deadline                   │  HEIGHT >= deadline
           ▼                                      ▼
┌──────────────────────────┐          ┌───────────────────────────┐
│    EXECUTION PATH        │          │      REFUND PATH          │
│                          │          │                           │
│  TX_1 spends:            │          │  TX_1 spends:             │
│  • Proxy Box (input 0)   │          │  • Proxy Box (input 0)    │
│  • State NFT Box         │          │                           │
│    (input 1 or           │          │  Output 0 → user's P2PK  │
│     Data input)          │          │  (full value minus fee)   │
│                          │          │                           │
│  Outputs:                │          │  Validated by:            │
│  • Updated State Box     │          │  CONTEXT.HEIGHT >= R5     │
│  • User result box       │          │  & output.propBytes ==    │
│  • Executor bounty box   │          │    R4 (SigmaProp)         │
└──────────────────────────┘          └───────────────────────────┘
```

### Step-by-Step Execution

**Step 1 — User creates the proxy box**

The user (or a dApp frontend) constructs a transaction whose output `i` has:
- `value` = amount to swap/stake/lend plus execution bounty plus Minimum box value overhead
- `ergoTree` = compiled proxy ErgoScript
- `R4` = `SigmaProp` — the user's public key for refunds
- `R5` = `Int` — deadline block height
- `R6` = `Long` — minimum acceptable output (slippage guard)
- `R7` = `Long` — execution bounty in nanoERG

**Step 2 — Executor bot detects the box**

A bot scans the UTXO set (via the Ergo node REST API or an indexer) for boxes matching the proxy contract ErgoTree template hash.

**Step 3 — Executor constructs the fulfillment transaction**

The executor builds a transaction that:
1. Spends the proxy box as `INPUTS(0)`.
2. Spends or reads (as a **Data input**) the protocol's State NFT box.
3. Produces the correct output boxes verified by both the proxy script and the protocol script.
4. Claims the execution bounty.

**Step 4 — Proxy script validation**

During transaction validation, the Ergo node evaluates the proxy box's ErgoScript against the **ErgoScript context**. The script checks:
- `HEIGHT < deadline` (execution path is open)
- Output `0` goes to the protocol contract with correct value
- Output `1` (user result) meets minimum acceptable output (`R6`)
- Output `2` (executor bounty) does not exceed `R7`

**Step 5 — Refund (if deadline exceeded)**

If `HEIGHT >= R5`, the refund branch activates. Only the user (`R4`) can sign a refund transaction. The script reduces to the user's `SigmaProp`, which is a standard Sigma protocol provable by the user's private key.

---

## Implementation

### 1. Core Proxy ErgoScript

Below is a production-ready proxy script modeled on the patterns from Dexy and Paideia. It handles a generic "deposit into protocol" action.

```scala
// File: proxy/DepositProxy.es
// Proxy contract for depositing ERG into a protocol pool.
// Registers:
//   R4: SigmaProp  — user refund address
//   R5: Int        — deadline (block height)
//   R6: Long       — minimum LP tokens or output tokens expected
//   R7: Long       — executor bounty in nanoERG

{
  // ===== Context Extraction ===== //

  // User's refund key — a Sigma protocol (Schnorr proof over secp256k1)
  val userPk            = SELF.R4[SigmaProp].get

  // Deadline guard: block height after which only refund is valid
  val deadline          = SELF.R5[Int].get

  // Slippage guard: minimum output tokens the user must receive
  val minOutputTokens   = SELF.R6[Long].get

  // Execution bounty claimed by the off-chain executor bot
  val executorBounty    = SELF.R7[Long].get

  // ===== Box References ===== //

  // The protocol pool box must be INPUTS(1).
  // It carries a Singleton / State NFT identified by a known Token ID.
  val poolBox           = INPUTS(1)

  // The pool's State NFT Token ID — hardcoded at compile time.
  // This is the Token ID rule: a box is authentic iff it carries this NFT.
  val poolNFT           = fromBase64("POOL_NFT_TOKEN_ID_BASE64_HERE")

  // ===== Output Box References ===== //
  val poolOutBox        = OUTPUTS(0)   // Updated pool state
  val userOutBox        = OUTPUTS(1)   // User receives LP tokens or result
  val executorBox       = OUTPUTS(2)   // Executor bounty box

  // ===== Validity Predicates ===== //

  // 1. Authenticate the pool box via its State NFT.
  //    Without this check, an attacker could substitute a fake pool box.
  val validPoolInput    = poolBox.tokens(0)._1 == poolNFT

  // 2. The pool output must preserve the State NFT.
  val validPoolOutput   = poolOutBox.tokens(0)._1 == poolNFT

  // 3. User output must carry at least minOutputTokens of the result token.
  //    This enforces slippage tolerance in a trustless manner.
  val userReceivesEnough = userOutBox.tokens(0)._2 >= minOutputTokens

  // 4. User output must go to the correct address (validated by ErgoTree hash).
  //    We compare propBytes to prevent redirecting user funds.
  val userOutputToUser  = userOutBox.propositionBytes == userPk.propBytes

  // 5. Executor bounty must not exceed what the user agreed to pay.
  val validBounty       = executorBox.value <= executorBounty

  // 6. Executor box can go to any address (executor chooses their own P2PK).
  //    The cap