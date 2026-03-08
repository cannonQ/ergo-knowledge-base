---
title: Proxy contracts
description: Proxy contracts — user-facing entry points with refund paths, deadline guards, and forwarding to protocol contracts
tags: [proxy-contracts, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [kushti/dexy-stable, paideiadao/paideia-contracts, duckpools/lend-protocol-contracts]
---
# Proxy Contracts in Ergo: A Comprehensive Developer Guide

## Table of Contents
1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Implementation](#implementation)
4. [Common Pitfalls](#common-pitfalls)
5. [References](#references)

---

## Overview

### What Is the Proxy Contract Pattern?

A **proxy contract** in Ergo is a user-facing eUTXO Box whose ErgoScript guards an intermediate step between a user's intent and a protocol's core logic. Rather than having users interact directly with complex multi-stage protocol contracts (LP pools, staking state machines, lending vaults), a proxy contract acts as a **holding escrow** that:

1. **Receives** the user's funds and encodes their parameters (desired output, slippage tolerance, deadline) into Registers or Context extension variables
2. **Allows a permissionless executor** (off-chain bot, keeper) to compose the proxy Box as an input alongside the real protocol Boxes in a single atomic Transaction
3. **Enforces a refund path** so the user can reclaim funds if no executor services the request within a deadline

This pattern is pervasive across the Ergo ecosystem because of two fundamental eUTXO properties:

- **Boxes are stateless and immutable** — a Box's ErgoTree cannot distinguish *who* submitted the spending Transaction; it can only verify conditions on the Transaction's inputs, outputs, Data inputs, and context
- **Multi-input transactions are atomic** — an executor can safely compose the user's proxy Box with a DEX pool Box, check all invariants, and either the whole swap succeeds or nothing changes

### Why Does It Exist?

| Problem Without Proxy | How Proxy Solves It |
|---|---|
| Users must sign multi-step protocol Transactions directly, requiring wallet integration with full protocol knowledge | User signs one simple "deposit to proxy" Transaction; keepers handle protocol complexity |
| Race conditions: two users cannot safely submit to the same pool Box simultaneously | Each user's intent is isolated in their own proxy Box; the keeper serialises execution |
| No recourse if a keeper never executes | Deadline guard + self-refund path in the proxy ErgoTree |
| Front-running: miners can see user intent in mempool | Proxy Box parameters can be commit-reveal or use Sigma protocol blinding |
| Storage rent accumulation on long-lived Boxes | Deadline ensures the Box is either consumed or refunded before rent becomes material |

### When to Use It

Use the proxy pattern when:

- Users interact with a **Singleton / State NFT**-guarded protocol contract (DEX pool, lending vault, staking state box) that can only have one instance in a given Transaction
- Your protocol requires **off-chain keeper infrastructure** (Spectrum-style AMM bots, Dexy arbitrageurs, Paideia staking incentive bots)
- The protocol Transaction requires **multiple coordinated inputs** that a standard wallet cannot assemble alone
- You need **MEV-resistance** or **slippage protection** enforced on-chain rather than in UI code

Do **not** use a proxy when:
- The user can directly spend the protocol Box themselves (simple P2PK or threshold Sigma protocol suffices)
- The operation is idempotent and stateless (no shared state Box exists)

---

## How It Works

### High-Level Flow

```
User Wallet                 Proxy Box (on-chain)           Protocol Box (on-chain)
     │                            │                               │
     │──── Tx 1: deposit ────────►│                               │
     │      (ERG + tokens,        │  [waiting for keeper]         │
     │       params in R4–R7)     │                               │
     │                            │                               │
     │                     Keeper Bot                             │
     │                            │                               │
     │                            │◄─── Tx 2: execute ──────────►│
     │                            │     (proxy + protocol         │
     │                            │      + data inputs)           │
     │◄─── output Box ────────────┴───────────────────────────────┘
     │     (tokens / ERG to user)
     │
     │  [if deadline passes, no keeper:]
     │
     │──── Tx 3: refund ─────────►│ (user reclaims own Box)
```

### Step-by-Step Execution

#### Step 1 — User Deposits into Proxy Box

The user's wallet constructs a Transaction spending their own UTXOs and creating one **proxy Box**. The proxy Box contains:

| Field | Content |
|---|---|
| `value` | ERG to swap/stake/lend + `Minimum box value` for output + `Minimum transaction fee` |
| `tokens(0)` | (Optional) Native tokens being deposited |
| `R4` | User's refund address as `SigmaProp` (or `Coll[Byte]` ErgoTree) |
| `R5` | Minimum expected output amount (slippage guard) |
| `R6` | Deadline height (block number after which refund is valid) |
| `R7` | (Optional) Protocol-specific parameters (pool ID, token ID) |
| `ErgoTree` | The proxy contract script |

The user signs Tx 1 with their standard P2PK key. No protocol knowledge is required.

#### Step 2 — Keeper Discovers and Executes

An off-chain keeper scans the blockchain (via Ergo node REST API or explorer) for unspent proxy Boxes matching a known ErgoTree template. When found:

1. Keeper fetches the current **protocol Box** (identified by its Singleton / State NFT Token ID)
2. Keeper assembles Tx 2 with inputs: `[proxy Box, protocol Box]` and data inputs as needed
3. Keeper verifies the Transaction satisfies all ErgoScript guards (simulation via `ergo-appkit` or `sigma-rust`)
4. Keeper submits Tx 2; if successful, the user's output Box lands at the address encoded in `R4` (or derived from it)

The keeper is permissionless — anyone can do this. The proxy ErgoScript enforces correctness, not the keeper's identity.

#### Step 3 — Deadline Guard / Refund Path

If no keeper executes by block height `R6`, the user can self-spend the proxy Box back to their own wallet. The ErgoScript's refund branch verifies:

```
HEIGHT > deadlineHeight && userPk
```

Only the original user (whose `SigmaProp` is in `R4`) can trigger the refund, and only after the deadline.

### Transaction Anatomy (Tx 2 — Execute)

```
INPUTS:
  [0] proxy Box       (value=X ERG, tokens=[Y dexyUSD], R4=userPk, R5=minOut, R6=deadline)
  [1] LP Pool Box     (value=reservesX ERG, tokens=[LP token, reservesY dexyUSD], R4=..., R5=...)

DATA INPUTS:
  [0] Oracle Box      (value=..., R4=ERG/USD rate as Long)

OUTPUTS:
  [0] LP Pool Box'    (updated reserves, same ErgoTree as input[1])
  [1] User Output Box (value=userERGback, tokens=[swapOutput dexyUSD], propositionBytes=userPk.propBytes)
  [2] Miner Fee Box   (value=MinimumTransactionFee)
  [3] (Optional) Protocol fee Box
```

The proxy ErgoScript checks `OUTPUTS(1)` satisfies the user's minimum output requirement. The LP pool's own ErgoScript (the protocol contract) checks its own constant-product invariant independently.

---

## Implementation

### 1. ErgoScript — Core Proxy Contract Template

This template is generalised from the pattern seen in Dexy's `SwapBuyV1.es` and Spectrum's redeem proxy:

```scala
// proxy/SwapBuyV1.es
// User deposits ERG to buy Dexy tokens from the LP pool.
// Keeper executes; user can refund after deadline.
{
  // ===== Registers of THIS proxy Box ===== //
  // R4: SigmaProp  — user's refund/output public key
  // R5: Long       — minimum Dexy tokens user accepts (slippage guard)
  // R6: Int        — deadline block height for refund
  // R7: Coll[Byte] — expected LP pool ErgoTree hash (anti-substitution)

  // ===== Named extractions ===== //
  val userPk         : SigmaProp   = SELF.R4[SigmaProp].get
  val minOutputDexy  : Long        = SELF.R5[Long].get
  val deadlineHeight : Int         = SELF.R6[Int].get
  val expectedPoolTree: Coll[Byte] = SELF.R7[Coll[Byte]].get

  // ===== Output boxes ===== //
  // By convention, output[0] = updated pool, output[1] = user receipt
  val userOutput : Box = OUTPUTS(1)

  // ===== Pool input validation ===== //
  // Prevent pool-substitution attack: the LP pool box must have the known ErgoTree
  val poolInput  : Box = INPUTS(1)
  val poolTreeOk : Boolean = blake2b256(poolInput.propositionBytes) == expectedPoolTree

  // ===== Slippage guard ===== //
  // User's output box must carry at least minOutputDexy Dexy tokens (Token ID at index 0)
  val userDexyOut : Long =
    if (userOutput.tokens.size > 0) userOutput.tokens(0)._2
    else 0L
  val slippageOk  : Boolean = userDexyOut >= minOutputDexy

  // ===== Recipient guard ===== //
  // Output must go back to the user (their ErgoTree)
  val recipientOk : Boolean = userOutput.propositionBytes == userPk.propBytes

  // ===== Execute path ===== //
  val canExecute : Boolean = poolTreeOk && slippageOk && recipientOk

  // ===== Refund path ===== //
  // After