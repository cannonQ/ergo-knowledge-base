---
title: Headless dApp pattern
description: Headless dApp pattern — pure protocol logic separated from UI, composable and testable
tags: [headless-dapp, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [DjedAlliance/Djed-Ergo, StabilityNexus/Gluon-Ergo-SDK]
---
# Headless dApp Pattern: Developer Guide

## Overview

The **headless dApp pattern** is an architectural approach where all protocol logic — transaction construction, Box validation, state machine transitions, and business rule enforcement — is encapsulated in a pure, UI-agnostic library. The "headless" refers to the absence of any frontend coupling: the same core library can be consumed by a CLI tool, a web wallet, a mobile app, a bot, or an automated testing harness without modification.

### Why It Exists

Ergo's eUTXO model presents unique challenges that make this separation especially valuable:

1. **Transaction construction is non-trivial.** Every Ergo Transaction must satisfy ErgoTree spending conditions, fund Storage rent, meet the Minimum box value per output Box, and include the Minimum transaction fee. This logic is complex enough to warrant isolation.

2. **Protocol state is on-chain.** Multi-stage contracts maintain state across a sequence of Boxes. A Singleton / State NFT (a Token with supply exactly 1, enforced by the Token ID rule — the token ID equals the ID of the Box in which it was first minted) anchors the canonical state Box. Finding that Box, reading its Registers, and producing a valid successor Box requires precise, repeatable logic that must not diverge between UI implementations.

3. **Composability and auditability.** Because ErgoScript is Turing-incomplete at the per-script level (all loops must terminate), protocol invariants that span multiple transactions must be enforced in the off-chain layer. A headless library makes those invariants explicit, testable, and auditable by any integrator.

4. **Multiple frontends, one protocol.** Djed (AgeUSD), SigmaUSD, Gluon, and similar protocols need CLI tooling, web UIs, and third-party integrations to behave identically. A shared headless core guarantees that.

### When to Use It

| Situation | Use Headless Pattern? |
|---|---|
| Multi-stage contract with shared state (Singleton NFT) | ✅ Yes |
| Protocol with multiple independent frontend implementations | ✅ Yes |
| dApp requiring automated / bot interaction | ✅ Yes |
| Pure ErgoScript contract with no off-chain state | ⚠️ Optional |
| Single-page toy dApp with no reuse intent | ❌ Probably not |

---

## How It Works

The pattern decomposes into five distinct layers, each with a single responsibility.

### Layer 1: Protocol Parameters

Immutable constants embedded at compile time: Token IDs (enforced by the Token ID rule), ErgoTree hashes, fee percentages, reserve ratio bounds, and height-based guards (e.g., `COOLING_OFF_HEIGHT`). These are never derived at runtime from user input.

### Layer 2: Box Specifications (`BoxSpec`)

A `BoxSpec` declaratively describes what a valid Box looks like: its ErgoTree (P2S address), required Tokens with `TokenSpec` constraints, and Register layouts. The specification is used both for *finding* Boxes (via Explorer or node scan) and for *validating* Boxes before they are used in transaction construction.

### Layer 3: Wrapped Boxes (`WrappedBox` / `SpecifiedBox`)

A raw `ErgoBox` is deserialized and wrapped in a typed struct that exposes decoded Register values as strongly-typed fields. All decoding errors are surfaced here, before any transaction logic runs. The wrapper enforces that a Box matching the spec is in fact the protocol Box it claims to be.

### Layer 4: Protocol Actions (Transaction Builders)

Pure functions that accept Wrapped Boxes (and optionally Data inputs — read-only Boxes that provide context without being spent) and return `ErgoBoxCandidate` output collections or unsigned `Transaction` objects. No network I/O occurs here. This is where:

- Reserve ratio equations are evaluated
- Minting/redemption amounts are calculated
- Output Register values are set
- Fee Boxes are constructed to the Minimum box value

### Layer 5: Integration Adapters

Thin, environment-specific adapters that perform I/O:
- **Node adapter**: Registers node Scans, submits transactions via `NodeInterface`
- **Explorer adapter**: Calls the Explorer API endpoint derived from a `BoxSpec`
- **WASM adapter**: Exposes the library to JavaScript via `wasm-bindgen`

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend / CLI / Bot                  │
└───────────────────────┬─────────────────────────────────┘
                        │ calls
┌───────────────────────▼─────────────────────────────────┐
│              Integration Adapter (Layer 5)               │
│         (Node scan, Explorer fetch, WASM bridge)        │
└───────────────────────┬─────────────────────────────────┘
                        │ produces typed Boxes
┌───────────────────────▼─────────────────────────────────┐
│           WrappedBox / SpecifiedBox (Layer 3)            │
│         (Register decoding, Token validation)           │
└──────────┬────────────────────────────┬─────────────────┘
           │                            │ reads
┌──────────▼──────────┐    ┌────────────▼────────────────┐
│  BoxSpec (Layer 2)  │    │  Protocol Equations (Layer 4)│
│  (find & validate)  │    │  (pure business logic)       │
└──────────┬──────────┘    └────────────┬────────────────┘
           │                            │
┌──────────▼────────────────────────────▼────────────────┐
│              Protocol Parameters (Layer 1)              │
│    (Token IDs, fee %, reserve bounds, height guards)    │
└─────────────────────────────────────────────────────────┘
```

### Data Flow for a Mint Operation

```
1. Adapter fetches BankBox    ─→  BoxSpec.explorer_endpoint() → HTTP GET
2. Adapter fetches OracleBox  ─→  same mechanism (Data input — not spent)
3. Adapter fetches ERG input  ─→  user's ErgsBox
4. Validate all three         ─→  WrappedBox::try_from(raw_box)?
5. Compute oracle rate        ─→  OraclePoolBox.datapoint_in_cents()
6. Compute reserve ratio      ─→  equations::reserve_ratio(reserves, circ_sc, rate)
7. Check protocol guard       ─→  ratio >= MIN_RESERVE_RATIO?
8. Build output BankBox       ─→  create_candidate(new_registers, new_tokens)
9. Build output user Box      ─→  create_candidate(minted_tokens, change_value)
10. Assemble Transaction      ─→  unsigned_tx with Data input = OracleBox
11. Adapter signs & submits   ─→  NodeInterface.sign_and_submit(unsigned_tx)
```

The Oracle Box is included as a **Data input**: it provides the ERG/USD rate to the ErgoScript context without being spent, which means the Oracle pool's contract is not involved in this transaction at all — a key eUTXO composability feature.

---

## Implementation

### Layer 1: Protocol Parameters (Rust)

```rust
// ageusd_headless/src/parameters.rs
// These constants are derived from on-chain bootstrap transactions.
// The BANK_NFT_ID equals the Box ID of the genesis Bank Box (Token ID rule).
// Once set, they are immutable for the lifetime of the protocol.

pub const BANK_NFT_ID: &str =
    "7d672d1def471720ca5782fd6473e47e796d9ac0c138d9911346f118b2f6d9d";

pub const STABLECOIN_TOKEN_ID: &str =
    "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04";

pub const RESERVECOIN_TOKEN_ID: &str =
    "003bd19d0187117f130b62e1bcab0939929ff5c7709f843c5c4dd158949285d0";

/// Minimum nanoERG value any Box must hold to avoid Storage rent reclamation.
/// Storage rent charges ~0.13 ERG per 4 years per box; this floor ensures
/// boxes remain economically viable. See EIP-0002.
pub const MIN_BOX_VALUE: u64 = 1_000_000; // 0.001 ERG in nanoERGs

/// Basis-point fee charged on each mint/redeem action.
/// 200 = 2.00%. Applied to base reserves delta.
pub const FEE_PERCENT: u64 = 200;

/// Secondary fee routed to the protocol implementor.
pub const IMPLEMENTOR_FEE_PERCENT: u64 = 20; // 0.20%

/// Height below which the protocol is in cooling-off mode.
/// Prevents manipulation attacks in the first N blocks after launch.
pub const COOLING_OFF_HEIGHT: u64 = 460_000;

pub const MIN_RESERVE_RATIO: u64 = 400; // 400%
pub const MAX_RESERVE_RATIO: u64 = 800; // 800%

/// Default price for ReserveCoin when no stablecoins are in circulation.
pub const RESERVECOIN_DEFAULT_PRICE: u64 = 1_000_000; // 1 milliERG
```

### Layer 2: Box Specifications (Rust)

```rust
// ageusd_headless/src/bank.rs (simplified and annotated)
use ergo_headless_dapp_framework::{
    BoxSpec, TokenSpec, SpecifiedBox, WrapBox, WrappedBox,
    BlockHeight, NanoErg, P2SAddressString,
};
use crate::parameters::*;

/// The BankBox is the Singleton state box for the AgeUSD protocol.
/// It is identified by the BANK_NFT_ID (Token ID rule: minted in genesis Box).
///