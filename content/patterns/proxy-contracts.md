---
title: Proxy contracts
description: Proxy contracts — user-facing entry points with refund paths, deadline guards, and forwarding to protocol contracts
tags: [proxy-contracts, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [kushti/dexy-stable, paideiadao/paideia-contracts, duckpools/lend-protocol-contracts]
---
# Proxy Contracts: Developer Guide for Ergo Integration

## Overview

### What Is This Pattern?

A **proxy contract** in Ergo is a user-facing eUTXO script that acts as an intermediary holding layer between a user's wallet and a core protocol contract (such as an AMM pool, lending vault, or staking state box). The user locks funds into the proxy box first; an off-chain agent (bot, relayer, or the user themselves) then consumes that proxy box in a transaction that also interacts with the protocol contract.

The pattern emerged directly from Ergo's eUTXO model, where **the spending transaction's shape must be known at signing time**. Because on-chain state (pool reserves, oracle prices, interest rates) changes between blocks, users cannot atomically sign a transaction against a moving target. The proxy contract absorbs this uncertainty by:

1. **Holding the user's funds safely** under a script that enforces their intent.
2. **Allowing a relayer** to assemble the final transaction when conditions are favorable.
3. **Guaranteeing a refund path** so funds are never permanently locked if the operation fails or expires.

### Why It Exists

| Ergo Constraint | How Proxy Contracts Solve It |
|---|---|
| Wallet must sign a fully-formed transaction | User signs once to deposit into proxy; relayer assembles protocol tx later |
| Pool/state box is a shared resource (singleton) | Proxy decouples user deposit timing from contention on the State NFT box |
| No miner-extractable value mitigation at the script layer | Deadline guards + minimum-output checks prevent sandwich attacks |
| Storage rent (0.13 ERG/4 years per byte) punishes dust boxes | Proxy boxes carry enough ERG and have short deadlines to avoid rent traps |

### When to Use It

- **AMM swaps** where the pool box reserve ratio changes every block (Dexy LP, Spectrum Finance).
- **Staking entry/exit** where a singleton State NFT box must be updated atomically (Paideia).
- **Lending operations** where interest accrual between signing and execution would break fixed-rate assumptions (Duckpools).
- **Any multi-party protocol** where one party's box must be assembled together with a protocol box by a third-party relayer.

Do **not** use proxy contracts when:
- The user can sign against a stable, non-contested box (simple P2PK payments).
- The operation is fully self-contained (no shared state box required).
- Latency requirements demand single-block settlement (use direct spending with pre-computed context instead).

---

## How It Works

### Canonical Flow

```
Block N:  User signs Tx_deposit
          Input:  User wallet box (ERG + optional tokens)
          Output: Proxy box (locked under ProxyErgoTree)
                  ├─ R4: user P2PK refund address (SigmaProp)
                  ├─ R5: deadline height (Int)
                  ├─ R6: min output tokens expected (Long)
                  └─ R7: protocol-specific parameters

Block N+k (k ≥ 0, k < deadline):
          Relayer assembles Tx_execute
          Inputs:  [0] Protocol State box (singleton / State NFT)
                   [1] Proxy box
          Outputs: [0] Updated protocol State box
                   [1] User output box (tokens received)
                   [2] Fee box (relayer reward, optional)
          DataInputs: [0] Oracle box (price feed, if needed)

Block N+deadline (if Tx_execute never landed):
          User (or anyone) submits Tx_refund
          Input:  Proxy box
          Output: User wallet (full refund)
```

### Step-by-Step Breakdown

#### Step 1 — User Deposits into Proxy

The user's wallet constructs a **deposit transaction** spending their own box and producing a proxy box. The proxy box's **ErgoTree** encodes:

- The user's refund `SigmaProp` (stored in **R4**).
- A block-height deadline (stored in **R5**).
- Expected minimum output (stored in **R6**) — the slippage guard.
- The target protocol contract address (hardcoded in the ErgoScript or stored in **R7**).

The user signs this transaction with their private key. At this point, **no interaction with the protocol contract is required**; the proxy box is self-contained.

#### Step 2 — Relayer Monitors the Chain

An off-chain service indexes all UTXOs matching the proxy ErgoTree. When protocol conditions satisfy the user's parameters (price within slippage, pool has sufficient liquidity), the relayer:

1. Fetches the **singleton/State NFT box** (the protocol's shared state).
2. Fetches any required **Data Input boxes** (oracle price boxes — these are read-only and do not need to be spent).
3. Assembles `Tx_execute` with the proxy box as one of the inputs.

#### Step 3 — On-chain Validation (ErgoScript)

The proxy's ErgoScript validates every output of `Tx_execute`. Specifically, it checks:

- `HEIGHT < deadline` — the operation is still valid.
- `OUTPUTS(1).propositionBytes == userPK.propBytes` — output goes to the user.
- `OUTPUTS(1).tokens(0)._2 >= minExpectedTokens` — slippage guard met.
- `OUTPUTS(0).tokens` contains the State NFT — the protocol box is preserved.
- The relayer fee (if any) does not exceed a hardcoded cap.

If all checks pass, the proxy box is consumed and the operation executes atomically.

#### Step 4 — Refund Path

If the deadline block has passed and `Tx_execute` was never mined, the proxy script exposes the **refund branch**:

```
HEIGHT >= deadline  =>  userPK  (user's SigmaProp)
```

Only the user (holder of the private key corresponding to `userPK`) can sign the refund transaction. This ensures **no relayer can steal funds** by simply waiting for the deadline.

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Block N                                                    │
│                                                             │
│  [User Wallet Box]                                          │
│       │  Tx_deposit (signed by user)                        │
│       ▼                                                     │
│  [Proxy Box]                                                │
│    ErgoTree: ProxyScript                                    │
│    Value:    100 ERG                                        │
│    R4:       userSigmaProp                                  │
│    R5:       N + 30  (deadline)                             │
│    R6:       minDexyOut (1000 DEXY)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┴──────────────┐
           │  Relayer monitors UTXOs  │
           └───────────┬──────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Block N+k (k < 30)                                         │
│                                                             │
│  DataInputs: [Oracle Box (price feed)]                      │
│  Inputs:     [0] LP Pool Box  (State NFT present)           │
│              [1] Proxy Box                                  │
│  Outputs:    [0] Updated LP Pool Box                        │
│              [1] User Box (≥ minDexyOut DEXY tokens)        │
│              [2] Relayer Fee Box (optional, capped)         │
└─────────────────────────────────────────────────────────────┘

   OR (if deadline passed):

┌──────────────────────────────────────────────────────────────┐
│  Block N+30 (or later)                                      │
│                                                             │
│  Input:  [Proxy Box]                                        │
│  Output: [User Wallet Box]  (full refund)                   │
│  Signed: userPrivateKey                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation

### 1. Core Proxy ErgoScript

The following is a generalized proxy contract modeled on Dexy's `SwapBuyV1.es` and Spectrum Finance's redeem proxy pattern. It handles ERG→Token swaps against an n2t (native-to-token) CFMM pool.

```scala
// File: lp/proxy/SwapBuyV1.es
// Pattern: Proxy contract for ERG-to-Token swap via n2t CFMM pool
//
// Registers expected in this proxy box:
//   R4: SigmaProp  — user's refund public key
//   R5: Int        — deadline block height
//   R6: Long       — minimum token output (slippage guard)
//   R7: Coll[Byte] — expected pool NFT Token ID (authenticates the pool box)
//
// Context:
//   INPUTS(0): LP Pool box (must contain pool NFT)
//   INPUTS(1): This proxy box
//   OUTPUTS(0): Updated LP Pool box
//   OUTPUTS(1): User output box (receives tokens)
//   OUTPUTS(2): (optional) Relayer fee box

{
  // ── Registers ──────────────────────────────────────────────────────────────
  val userPK          = SELF.R4[SigmaProp].get
  val deadline        = SELF.R5[Int].get
  val minTokenOut     = SELF.R6[Long].get
  val expectedPoolNFT = SELF.R7[Coll[Byte]].get

  // ── Constants ──────────────────────────────────────────────────────────────
  // Maximum ERG the relayer may take as a fee (0.002 ERG = 2_000_000 nanoERG)
  val MaxRelayerFee   = 2000000L