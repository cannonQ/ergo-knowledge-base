---
title: Headless dApp pattern
description: Headless dApp pattern — pure protocol logic separated from UI, composable and testable
tags: [headless-dapp, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [DjedAlliance/Djed-Ergo, StabilityNexus/Gluon-Ergo-SDK]
---
# Headless dApp Pattern: Developer Guide

## Overview

### What Is the Headless dApp Pattern?

The **headless dApp pattern** is an architectural approach that separates pure protocol logic from all user interface concerns. In the Ergo ecosystem, this means encoding all on-chain interaction rules — Box validation, Transaction construction, Sigma protocol verification, token arithmetic — into a standalone library that has no dependency on any frontend framework, wallet UI, or rendering layer.

The pattern takes its name from "headless" browsers: the core logic runs without a "head" (UI). What remains is a composable, deterministic, and independently testable protocol engine.

### Why It Exists

Ergo's eUTXO model makes protocol logic unusually rich and stateful compared to account-based chains. A single protocol action might require:

- Locating specific Boxes by ErgoTree or Token ID
- Reading Registers (R4–R9) on those Boxes
- Evaluating reserve ratios, emission curves, or oracle rates
- Constructing multi-input Transactions with precise output Box candidates
- Enforcing Minimum box value and Minimum transaction fee constraints
- Handling Storage rent implications across long-lived Singleton / State NFT boxes

Embedding all of this inside a React component or a CLI handler produces untestable, non-reusable, and fragile code. The headless pattern isolates this logic so it can be:

- **Unit tested** against mock Boxes without a running node
- **Reused** across CLI tools, web frontends, mobile apps, and bots
- **Composed** — one headless library can be imported by another
- **Audited** independently of any UI

### When to Use It

| Situation | Use Headless Pattern? |
|---|---|
| Protocol with non-trivial Box selection rules | ✅ Yes |
| Multi-stage contracts with chained Transactions | ✅ Yes |
| Shared protocol used by multiple frontends | ✅ Yes |
| Simple single-action script with one UI | ⚠️ Optional |
| Pure ErgoScript with no off-chain logic | ❌ Not applicable |

The pattern is especially well-suited to Ergo because eUTXO protocols are inherently **stateless at the call site** — given the same Box set and parameters, the same Transaction must be produced every time. This determinism makes headless libraries natural.

---

## How It Works

The headless dApp pattern decomposes a protocol into five distinct layers. Each layer has a single responsibility and a well-defined interface to its neighbors.

### Layer 1: Box Specifications (`BoxSpec`)

Each logical Box in the protocol — Bank box, Oracle pool box, Ballot box, Vault box — is described by a **`BoxSpec`**: a declarative schema that captures:

- The expected ErgoTree (compiled ErgoScript contract address)
- Required Token IDs and quantities (`TokenSpec`)
- Required Register types at R4–R9
- Value constraints (minimum nanoERG held)

This specification is the single source of truth for what a valid Box looks like. It is used both for **validation** (does this Box satisfy the spec?) and **discovery** (find me all Boxes matching this spec).

### Layer 2: Wrapped Boxes (`WrappedBox` / `SpecifiedBox`)

A raw `ErgoBox` from the node or explorer is wrapped in a typed struct — `BankBox`, `ReserveCoinBox`, `OraclePoolBox` — that:

- Validates the raw Box against its `BoxSpec` at construction time
- Exposes typed accessor methods (`fn base_reserves() -> NanoErg`, `fn circulating_stablecoins() -> u64`)
- Prevents invalid Boxes from propagating into transaction logic

This is the protocol's **domain model**. All downstream logic works with wrapped types, never raw `ErgoBox` values.

### Layer 3: Protocol Equations

Pure functions that implement the mathematical invariants of the protocol. They take primitive values — nanoERG amounts, token counts, oracle rates — and return computed values or errors. They have **no I/O and no Box dependencies**.

Examples: reserve ratio calculation, stablecoin mint price, ReserveCoin redemption value.

### Layer 4: Action Functions (Transaction Builders)

Functions that accept wrapped Boxes and user parameters, apply protocol equations, enforce all constraints, and return an `UnsignedTransaction` (or a list of `ErgoBoxCandidate` outputs). These are the protocol's **verbs**: `mint_stablecoin`, `redeem_reservecoin`, `update_bank_box`.

Action functions never sign transactions and never submit them. Signing is a UI-layer concern.

### Layer 5: Box Finders (Node / Explorer Integration)

Thin adapters that use `BoxSpec` to query:

- A local **Ergo node** via registered **Scans** (node wallet scan API)
- The **Ergo Explorer** REST API

These finders return wrapped Boxes ready for use in action functions. They are the only layer that performs I/O and the only layer that changes between deployment environments.

### End-to-End Flow

```
User Intent (e.g., "mint 100 SigUSD")
        │
        ▼
┌─────────────────────┐
│  Box Finder Layer   │  ← queries node scans or Explorer API
│  (fetch_boxes.rs)   │
└────────┬────────────┘
         │  BankBox, OraclePoolBox, ErgsBox
         ▼
┌─────────────────────┐
│  Wrapped Box Layer  │  ← validates, exposes typed accessors
│  (bank.rs, etc.)    │
└────────┬────────────┘
         │  base_reserves(), oracle_rate(), etc.
         ▼
┌─────────────────────┐
│  Equations Layer    │  ← pure math, no I/O
│  (equations.rs)     │
└────────┬────────────┘
         │  mint_price, reserve_ratio, fees
         ▼
┌─────────────────────┐
│  Action Layer       │  ← builds UnsignedTransaction
│  (bank.rs actions)  │
└────────┬────────────┘
         │  UnsignedTransaction
         ▼
┌─────────────────────┐
│  UI / CLI Layer     │  ← signs, submits, displays result
│  (main.rs)          │
└─────────────────────┘
```

The transaction is signed and submitted **outside** the headless library. The library's job ends at producing a valid unsigned transaction.

---

## Implementation

The following examples are drawn from the Djed/AgeUSD implementation in `DjedAlliance/Djed-Ergo` and structured to show each layer concretely.

### 1. Defining a `BoxSpec` — The Bank Box

The `BoxSpec` encodes what a valid Bank Box must contain. In the AgeUSD protocol, the Bank Box holds the protocol's reserve and carries a **Singleton / State NFT** (the `BANK_NFT_ID`) that makes it uniquely identifiable on-chain.

```rust
// From: ageusd_headless/src/bank.rs
// Adapted from DjedAlliance/Djed-Ergo

use ergo_headless_dapp_framework::{
    BoxSpec, SpecifiedBox, TokenSpec, WrapBox, WrappedBox,
};
use ergo_headless_dapp_framework::{BlockHeight, NanoErg, P2SAddressString};
use ergo_lib::chain::ergo_box::ErgoBox;
use crate::parameters::{
    BANK_NFT_ID,
    RESERVECOIN_TOKEN_ID,
    STABLECOIN_TOKEN_ID,
    MIN_BOX_VALUE,
};

/// A `BankBox` wraps a raw ErgoBox that has been validated against
/// the Bank Box specification. It holds the protocol's ERG reserves
/// and tracks circulating token supplies via Registers.
///
/// Register layout:
///   R4 (Long) : circulating supply of StableCoin
///   R5 (Long) : circulating supply of ReserveCoin
#[derive(Debug, Clone, WrapBox, SpecBox)]
pub struct BankBox(ErgoBox);

impl SpecifiedBox for BankBox {
    /// Returns the BoxSpec that every valid Bank Box must satisfy.
    /// The framework uses this spec for both validation and Box discovery.
    fn box_spec() -> BoxSpec {
        // The Bank Box must hold exactly 1 unit of the Bank NFT.
        // This is the Singleton / State NFT pattern: one token per
        // contract instance, making the box globally unique and
        // unforgeable without the token.
        let bank_nft_spec = TokenSpec::new(
            1..=1,                         // exactly 1 NFT unit
            BANK_NFT_ID,                   // the Token ID (Blake2b hash of
                                           // the first input of the minting tx)
        );

        // The box may hold a variable quantity of StableCoins and
        // ReserveCoins (the unminted/unissued supply held in reserve).
        let stablecoin_spec = TokenSpec::new(
            0..=u64::MAX,
            STABLECOIN_TOKEN_ID,
        );
        let reservecoin_spec = TokenSpec::new(
            0..=u64::MAX,
            RESERVECOIN_TOKEN_ID,
        );

        BoxSpec::new(
            None,                          // address checked via ErgoTree at runtime
            Some(MIN_BOX_VALUE..=u64::MAX),// must hold at least MIN_BOX_VALUE nanoERG
            vec![],                        // no Register constraints in spec
                                           // (validated in accessor methods)
            vec![
                Some(bank_nft_spec),
                Some(stablecoin_spec),
                Some(reservecoin_spec),
            ],
        )
    }
}

impl BankBox {
    /// Returns the total ERG reserves held in the Bank Box, in nanoERG.
    /// This is the raw Box value — the protocol treats the entire value
    /// as the reserve base.
    pub fn base_reserves(&self) -> NanoErg {
        self.0.value.as_u