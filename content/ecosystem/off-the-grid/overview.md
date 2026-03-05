---
title: Telefragged/off-the-grid — Overview
description: Off the Grid — decentralized multi-grid order contract for token/ERG trading with ERG accumulation
tags: [telefragged, off-the-grid, defi, ergoscript, rust]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/Telefragged/off-the-grid"
project: telefragged-off-the-grid
group: defi
priority: medium
languages: [ergoscript, rust]
contract_count: 1
pattern_match_count: 0
---
# Off the Grid — Developer Overview

## Overview

Off the Grid is a decentralized grid trading application built on the Ergo blockchain that enables automated token/ERG trading through a multi-order contract architecture. Rather than submitting individual limit orders, users deploy a single **multi-grid Box** that encodes an entire ladder of buy and sell orders in its Registers, retaining self-custodial control at all times. The contract enforces that funds can only leave the Box if orders are correctly filled according to their encoded prices, or if the owner provides a valid Sigma-protocol signature — making the system non-custodial by construction.

The project's role in the Ergo ecosystem is to provide a permissionless, automated market-making primitive that operates against existing liquidity sources. The current implementation matches grid orders against **Spectrum Finance** AMM pools (N2T pools), with the off-chain matching bot identifying arbitrage opportunities between the grid's fixed prices and the AMM's spot price. Bot operators are incentivized through the spread between the liquidity source price and the grid order price, while grid order owners accumulate profits as ERG through repeated buy-low/sell-high cycles. This design demonstrates how eUTXO-native constructs — particularly multi-stage contracts and off-chain batcher patterns — can implement sophisticated DeFi primitives without centralized intermediaries.

Off the Grid is implemented in two layers: an **ErgoScript contract** that enforces all on-chain invariants for order state transitions and balance reconciliation, and a **Rust-based CLI and matching bot** that handles off-chain order construction, monitoring, and transaction submission via the Ergo node's HTTP API. The project is directly inspired by kushti's decentralized grid trading proposal on the Ergo Forum and serves as a concrete reference implementation of that design.

---

## Architecture

### Component Map

```
┌─────────────────────────────────────────────────────┐
│                  off-the-grid CLI                   │
│  grid create │ grid redeem │ grid list │ grid details│
└────────────────────────┬────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   Ergo Node HTTP API │  ◄── node_config.json
              │  (wallet, scans,    │
              │   tx broadcast)     │
              └──────────┬──────────┘
                         │
         ┌───────────────▼───────────────┐
         │        Node Wallet Scans       │
         │  scan_config.json (scan IDs)   │
         │  Tracks grid_multi Boxes       │
         └───────────────┬───────────────┘
                         │
    ┌────────────────────▼────────────────────┐
    │           MultiGrid Box (eUTXO)          │
    │  propositionBytes = grid_multi ErgoTree  │
    │  R4: GroupElement (owner pubkey)         │
    │  R5: Coll[((Long,Bool),(Long,Long))]     │
    │  R6: Coll[Byte] (Token ID)               │
    │  R7: Coll[Byte] (metadata, optional)     │
    │  value: ERG                              │
    │  tokens: [tokenId → amount]              │
    └────────────────────┬────────────────────┘
                         │
              ┌──────────▼──────────┐
              │    Matching Bot      │  ◄── matcher_config.json
              │  (off-chain batcher) │       MATCHER_REWARD_ADDRESS
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  Spectrum AMM Pools  │
              │  (N2T liquidity)     │
              └─────────────────────┘
```

### Data Flow

1. **Order Creation**: The CLI constructs a transaction spending from the user's wallet that produces a MultiGrid Box. The Box's R5 Register is populated with the full order ladder (buy/sell pairs, amounts, prices) computed from CLI parameters. The transaction is signed via the node wallet and broadcast.

2. **Scan Monitoring**: Node wallet scans (keyed by `scan_config.json`) track all live MultiGrid Boxes on-chain, enabling both the CLI and the matching bot to discover open orders without requiring a full indexer.

3. **Order Matching**: The matching bot continuously polls for MultiGrid Boxes and queries Spectrum AMM pool states. When a profitable match is found — a grid sell order priced above the AMM's effective buy price, or vice versa — the bot constructs a matching Transaction using the MultiGrid Box and the relevant AMM pool Box as inputs.

4. **State Transition**: The matching Transaction produces a recreated MultiGrid Box with updated R5 order states (BUY→SELL or SELL→BUY flips), updated token and ERG balances, and one or more fee Boxes satisfying the protocol's `MaxFee` constant. The on-chain contract validates all invariants atomically.

5. **Order Redemption**: The owner redeems remaining funds by signing with the private key corresponding to R4's `GroupElement`, bypassing the swap validation path entirely.

---

## Smart Contracts

### `contracts/grid_multi/contract.es`

This is the sole on-chain contract in the project. It implements a **multi-stage, self-recreating Box** that encodes an entire grid order book in a single eUTXO.

#### Validation Branches (OR composition)

The ErgoScript contract uses a top-level OR:

```
(proveDlog(ownerGroupElement)) || (all swap invariants hold)
```

**Branch 1 — Owner signature**: A standard `proveDlog` Sigma protocol over the `GroupElement` stored in R4. This permits the owner to redeem or modify the Box unconditionally by proving knowledge of the corresponding discrete logarithm.

**Branch 2 — Swap path**: A purely propositional (non-interactive) validation that enforces all of the following:

| Check | Description |
|---|---|
| **Box recreation** | `OUTPUTS(selfIndex).propositionBytes == SELF.propositionBytes` — the contract must recreate itself at a known output index |
| **Order fold** | A `fold` over zipped `(currentOrders, recreatedOrders)` pairs validates that `amount`, `buyPrice`, and `sellPrice` are immutable, while `isBuy` state may flip BUY↔SELL. Each flip accumulates `(tokenDelta, ergDelta)` |
| **Exchange consistency** | `tokenDiff` from order folds must equal `recreatedTokens - SELF.tokens`; `ergDiff` must equal `OUTPUTS(selfIndex).value - SELF.value`; both deltas must be non-zero |
| **Token ID invariant** | Output holds ≤ 1 native token; all tokens must match R6's Token ID (prevents **Token ID rule** injection attacks) |
| **Register immutability** | R4 (owner), R5 (order structure/size), R6 (token ID), R7 (metadata if present) are all preserved across the state transition |
| **Fee collection** | Sum of all output Boxes whose `propositionBytes == FeeProposition` must equal `MaxFee` (constant-segregated protocol fee) |

#### Register Layout

| Register | ErgoScript Type | Semantics |
|---|---|---|
| R4 | `GroupElement` | Owner's public key for `proveDlog` |
| R5 | `Coll[((Long, Boolean), (Long, Long))]` | Order ladder: `((amount, isBuy), (buyPrice, sellPrice))` per order slot |
| R6 | `Coll[Byte]` | Token ID of the traded asset (blake2b-256) |
| R7 | `Coll[Byte]` (optional) | Off-chain metadata: order grouping label, profit tracking |

#### Key Design Properties

- **No Singleton / State NFT**: Each MultiGrid Box is independent. The contract does not use a singleton NFT for global state coordination; multiple instances coexist with no on-chain coupling.
- **Constant segregation**: `MaxFee` and `FeeProposition` are compiled as constants into the ErgoTree,