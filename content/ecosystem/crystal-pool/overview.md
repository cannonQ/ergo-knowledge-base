---
title: SavonarolaLabs/crystal-pool — Overview
description: Crystal Pool — real-time order-based L1 exchange on Ergo, order-book contract architecture
tags: [savonarolalabs, crystal-pool, defi, typescript, svelte]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/SavonarolaLabs/crystal-pool"
project: savonarolalabs-crystal-pool
group: defi
priority: medium
languages: [typescript, svelte]
contract_count: 5
pattern_match_count: 12
---
# CrystalPool: Developer Overview

---

## Overview

CrystalPool is a self-custodial, real-time, order-book-based exchange operating entirely on Ergo Layer 1 (L1). Rather than routing trades through an automated market maker (AMM), it implements a classical limit-order-book model where each open order is a live eUTXO locked by an ErgoScript contract. Orders for Deposit, Buy, Sell, and Swap operations exist as individual Boxes on-chain, and the pool service continuously aggregates, matches, and chains these Boxes into a growing tree of signed-but-unsubmitted transactions that are flushed to the mempool asynchronously. This design delivers a user experience comparable to a centralized exchange while preserving full on-chain settlement and self-custody.

The exchange's trustless properties are enforced at the contract level through time-limited 2-of-2 Sigma protocol multisig: before a configurable `unlockHeight`, both `userPK` and `poolPK` must co-sign any action. After `unlockHeight` expires, the user's key gains unilateral spending authority, making it impossible for a rogue pool operator to permanently freeze user funds. This mechanism, embedded in every contract's R4 (`Coll[SigmaProp]`) and R5 (`Int` unlock height), is the core security invariant of the protocol. CrystalPool was built as a proof-of-concept at ErgohackVIII and represents a notable architectural pattern for real-time L1 trading that avoids off-chain custody entirely.

Within the Ergo ecosystem, CrystalPool occupies a niche distinct from AMM-style DEXes such as Spectrum Finance. Its order-book model is closer in spirit to the ErgoDEX order-book design, but it introduces a novel transaction-tree mechanism that pre-chains signed transactions client-side, giving users instant local state updates before any transaction is confirmed. This positions it as a research-grade reference implementation for headless dApp patterns, off-chain bot architecture, and multi-stage contract composition using the eUTXO model.

---

## Architecture

CrystalPool separates concerns cleanly into three layers: the smart contract layer (ErgoScript), an off-chain pool service (TypeScript backend), and a rich client UI (Svelte + TypeScript). Data flows in a directed cycle among these layers.

```
┌─────────────────────────────────────────────────────┐
│                   Ergo L1 Node                      │
│  (confirmed Boxes, mempool, transaction submission) │
└───────────────────────┬─────────────────────────────┘
                        │ REST / Node API
         ┌──────────────▼──────────────┐
         │        Pool Service          │
         │  ┌──────────────────────┐   │
         │  │  SQLite3 UTXO Store  │   │  ← canonical unconfirmed UTXO set
         │  └──────────┬───────────┘   │
         │  ┌──────────▼───────────┐   │
         │  │  Transaction Builder │   │  ← constructs & signs tx trees
         │  └──────────┬───────────┘   │
         │  ┌──────────▼───────────┐   │
         │  │  WebSocket Broadcaster│  │  ← real-time orderbook / trade events
         │  └──────────┬───────────┘   │
         │  ┌──────────▼───────────┐   │
         │  │  Public REST API      │  │  ← latest UTXO set for clients
         │  └──────────────────────┘   │
         └──────────────┬──────────────┘
                        │ WS + REST
         ┌──────────────▼──────────────┐
         │       Svelte Web UI          │
         │  ┌──────────────────────┐   │
         │  │  Built-in Wallet     │   │  ← key management, background signing
         │  └──────────────────────┘   │
         │  ┌──────────────────────┐   │
         │  │  Orderbook View      │   │  ← real-time updates via WebSocket
         │  └──────────────────────┘   │
         │  ┌──────────────────────┐   │
         │  │  Trade Execution UI  │   │  ← creates deposit/swap/buy/sell intents
         │  └──────────────────────┘   │
         └─────────────────────────────┘
```

**Data Flow — Happy Path:**

1. User initiates a trade action in the Svelte UI (e.g., create a Swap order).
2. The built-in wallet constructs a transaction spending the user's DEPOSIT Box and producing a SWAP Box; the user signs (background signing via `userPK`).
3. The signed transaction is sent to the Pool Service, which co-signs with `poolPK`, stores the resulting Box in SQLite3 as the new canonical unconfirmed UTXO, and chains the next transaction off the new Box's output.
4. The Pool Service broadcasts the updated orderbook state over WebSocket to all connected clients.
5. Asynchronously, the Pool Service submits the root of the transaction tree to the Ergo node mempool. As blocks confirm, spent Boxes are pruned and the SQLite3 UTXO set is reconciled against on-chain state.
6. If a counterparty's order matches, the Pool Service constructs and signs a SWAP transaction consuming both parties' order Boxes and producing updated DEPOSIT Boxes for each; both parties receive real-time balance updates via WebSocket.

**Key Architectural Decision — Transaction Tree:**
Rather than submitting each transaction immediately, the Pool Service maintains a *chain of unsubmitted signed transactions* in memory / SQLite3. Each transaction in the tree spends the output of the previous one, building a dependency graph. This allows the UI to reflect instant state changes while actual L1 settlement happens asynchronously. The risk is that if the mempool is congested and transaction fees are too low, the tree root may not confirm before `unlockHeight`, exposing unsubmitted transactions to expiry.

---

## Smart Contracts

All contracts are written in ErgoScript and share a common structural skeleton: Registers R4–R8 encode immutable order parameters, and the spending condition is a height-gated Sigma protocol expression. No Singleton / State NFT is used; state coherence is achieved through register-matching invariants enforced in-script across all inputs and outputs of a single transaction.

### `deposit.es` — Deposit Contract

Holds user funds in escrow pending trading activity.

| Register | Type | Purpose |
|----------|------|---------|
| R4 | `Coll[SigmaProp]` | `[sellerPk, poolPk]` |
| R5 | `Int` | `unlockHeight` |

**Guard condition (intended):**
```ergoscript
if (HEIGHT > unlockHeight(SELF)) {
  getSellerPk(SELF)                        // unilateral withdrawal post-expiry
} else {
  getSellerPk(SELF) && getPoolPk(SELF)     // 2-of-2 multisig pre-expiry
}
```
> ⚠️ **Known issue:** The current source has the `&& getPoolPk(SELF)` clause commented out, making the time-lock non-functional. Both branches resolve to `getSellerPk(SELF)`, meaning the seller can spend at any time. This must be fixed before mainnet deployment.

The contract carries Native tokens (ERG and arbitrary fungible tokens) but performs no token-specific validation; that responsibility is delegated to the spending transaction constructed off-chain.

---

### `buy-token-for-erg.es` — Buy Order Contract

Locks ERG committed by a buyer waiting to acquire a specific token at a fixed rate.

| Register | Type | Purpose |
|----------|------|---------|
| R4 | `Coll[SigmaProp]` | `[buyerPk, poolPk]` |
| R5 | `Int` | `unlockHeight` |
|