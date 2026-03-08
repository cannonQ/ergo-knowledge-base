---
title: Headless dApp pattern
description: Headless dApp pattern — pure protocol logic separated from UI, composable and testable
tags: [headless-dapp, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [DjedAlliance/Djed-Ergo, StabilityNexus/Gluon-Ergo-SDK]
---
# Headless dApp Pattern — Developer Guide

## Overview

### What This Pattern Is

The **headless dApp pattern** separates pure protocol logic from any user interface layer, producing a self-contained library that encodes all the rules of an Ergo protocol — box validation, transaction construction, state transitions, and economic equations — without any dependency on a frontend, wallet UI, or rendering engine.

In Ergo's eUTXO model, a decentralized application is fundamentally a set of rules about:

- Which **Boxes** (eUTXOs) are valid inputs to a transaction
- What **ErgoScript** constraints those boxes encode in their **ErgoTree**
- How **Registers** (R4–R9), **Native tokens**, and **NanoErg** values must change between inputs and outputs
- What auxiliary boxes (**Data inputs**) must be present to provide read-only context

A headless dApp encodes all of these rules as a typed, composable Rust/Scala/TypeScript library. The UI — whether a CLI, web frontend, mobile app, or bot — becomes a thin consumer of this library, responsible only for fetching boxes and submitting signed transactions.

### Why It Exists

The eUTXO model is fundamentally different from account-based chains. There is no global mutable state: every action is a deterministic transformation from a set of input boxes to a set of output box candidates. This makes protocol logic naturally separable from presentation.

Without the headless pattern:

- Protocol rules get scattered across UI components
- The same validation logic is duplicated in every frontend
- Testing requires a running browser or wallet
- Third-party integrations (bots, aggregators, other dApps) must re-implement the protocol from scratch

With the headless pattern:

- A single canonical library defines the protocol
- Any interface — web, CLI, Telegram bot, on-chain composition — calls the same library
- Unit tests run against pure functions with no network dependencies
- **Multi-stage contracts** (sequences of dependent transactions) can be composed programmatically

### When to Use It

Use the headless dApp pattern when:

- Your protocol has non-trivial box-selection logic (e.g., reserve ratio constraints, cooling-off periods, oracle-dependent pricing)
- Multiple independent frontends or integration points need to interact with the same contracts
- You need deterministic, reproducible transaction construction for automated agents (arbitrage bots, liquidation keepers, governance voters)
- You want to publish an SDK that third parties can embed in their own dApps
- Your protocol uses **Singleton / State NFT** boxes whose state must be tracked and updated atomically

Canonical examples from the ecosystem: **AgeUSD (Djed)**, **SigmaUSD**, **Gluon Gold**, and **ErgoDEX** all expose headless libraries.

---

## How It Works

### Conceptual Flow

```
┌─────────────────────────────────────────────────────┐
│                   Protocol Library                   │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ BoxSpecs │  │Equations │  │  Action Functions  │ │
│  │(validation│  │(reserve  │  │(build tx candidate)│ │
│  │ rules)   │  │ ratio,   │  │                    │ │
│  └──────────┘  │ pricing) │  └────────────────────┘ │
│                └──────────┘                          │
└─────────────────────────────────────────────────────┘
         ▲                              │
         │  fetch boxes                 │  UnsignedTransaction
         │                              ▼
┌─────────────────────────────────────────────────────┐
│              Interface Layer (thin)                  │
│                                                      │
│  ┌──────────────┐   ┌───────────┐   ┌─────────────┐ │
│  │ Explorer API │   │ Node Scan │   │  Wallet /   │ │
│  │  (read UTXOs)│   │ (tracking)│   │  Signing    │ │
│  └──────────────┘   └───────────┘   └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Step-by-Step Flow

#### Step 1 — Define BoxSpecs

A `BoxSpec` declares the structural requirements for a box to be considered a valid participant in a protocol action. It encodes:

- The **ErgoTree** (P2S address) the box must be locked to
- Which **Registers** must be present and their types
- Which **Native tokens** (by **Token ID**) must be present, and in what quantity range
- The NanoErg value bounds

This is the runtime equivalent of the on-chain **ErgoScript** validation, expressed as a Rust/Scala type.

#### Step 2 — Wrap Boxes

Raw `ErgoBox` values from the node or Explorer API are **wrapped** in typed structs (`BankBox`, `ReserveCoinBox`, `OraclePoolBox`). Wrapping validates the box against its `BoxSpec` at construction time, preventing invalid boxes from propagating into transaction-building code.

#### Step 3 — Fetch Boxes

The interface layer fetches boxes from:

- **Explorer API**: Public REST endpoint, suitable for read-only frontend queries
- **Node Scans**: The Ergo node's `/scan` API registers tracking rules (e.g., "boxes containing asset `<BANK_NFT_ID>`"). Scans persist across blocks and return live UTXO sets — essential for **Singleton / State NFT** tracking

#### Step 4 — Execute Protocol Equations

Before building a transaction, the library evaluates protocol-level equations using the current box states. For AgeUSD/Djed these include:

- `reserve_ratio(base_reserves, circulating_stablecoins, oracle_rate)` → determines whether minting/redeeming is permitted
- `stablecoin_nominal_price(oracle_rate)` → price of one StableCoin in NanoErg
- `reservecoin_price(base_reserves, circulating_stablecoins, circulating_reservecoins, oracle_rate)` → price of one ReserveCoin

These equations are pure functions. They have no side effects and can be unit-tested exhaustively.

#### Step 5 — Build Output Box Candidates

An **action function** (e.g., `mint_stablecoin_tx`) takes:

- The validated, wrapped input boxes
- User-provided parameters (amount to mint, user address, implementor address)
- Current block height (for **Storage rent** and validity intervals)

It returns an `UnsignedTransaction` or a list of `ErgoBoxCandidate` output objects. Output candidates specify:

- NanoErg value (respecting **Minimum box value**)
- Tokens (via **Token ID rule** — token IDs in output must derive from input box IDs or existing input tokens)
- Register values (R4–R9)
- The ErgoTree (contract address) locking the output

The transaction also specifies the **Minimum transaction fee** as a dedicated fee output.

#### Step 6 — Sign and Submit

The interface layer passes the unsigned transaction to a wallet or node signing endpoint. The headless library has no opinion on how signing occurs — it works with Nautilus wallet, `ergo-wallet`, the Ergo node's `/wallet/transaction/send` endpoint, or an offline signer.

#### Step 7 — Verify On-Chain

After submission, the interface layer monitors the mempool or block confirmations. The headless library may provide utilities to re-fetch and re-wrap the updated boxes for subsequent actions.

---

## Implementation

### Project Structure

A well-structured headless dApp library looks like this:

```
protocol-headless/
├── src/
│   ├── lib.rs              # Public API re-exports
│   ├── parameters.rs       # Protocol constants (NFT IDs, ratios, fees)
│   ├── equations.rs        # Pure economic/protocol functions
│   ├── error.rs            # Typed error enum
│   ├── bank.rs             # BankBox spec, wrapping, and actions
│   ├── input_boxes.rs      # OraclePoolBox, ErgsBox, token box specs
│   └── actions/
│       ├── mint_stablecoin.rs
│       ├── redeem_stablecoin.rs
│       ├── mint_reservecoin.rs
│       └── redeem_reservecoin.rs
interface/
├── src/
│   ├── main.rs             # CLI entry point
│   ├── fetch_boxes.rs      # Explorer API fetching
│   └── scan.rs             # Node scan registration
```

### 1. Protocol Parameters (`parameters.rs`)

All contract constants live in one place. **Token IDs** are fixed at deployment and embedded here. Changing any of these changes the protocol identity.

```rust
// ageusd_headless/src/parameters.rs

/// The Token ID of the Bank's Singleton / State NFT.
/// This NFT uniquely identifies the canonical BankBox on-chain.
/// There is exactly one box holding this token at any time.
pub const BANK_NFT_ID: &str =
    "7d672d1def471720ca5782fd6473e47e796d9ac0c138d9911346f118b2f6d9d9";

/// The Token ID of the StableCoin (SigmaUSD).
pub const STABLECOIN_TOKEN_ID: &str =
    "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04";

/// The Token ID of the ReserveCoin (SigmaRSV).
pub const RESERVECOIN_TOKEN_ID: &str =
    "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0";

/// Minimum reserve ratio (400%) — below this, StableCoin redemption is blocked
/// and ReserveCoin minting is blocked.
pub const MIN_RESERVE_RATIO: u64