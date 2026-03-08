---
title: ergoplatform/ergo-node-interface-rust — Overview
description: Rust library for interacting with Ergo Node — scanning, submitting txs, querying state (EMURGO/Ergo Platform)
tags: [ergoplatform, ergo-node-interface-rust, sdk, rust]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repo: "https://github.com/ergoplatform/ergo-node-interface-rust"
project: ergoplatform-ergo-node-interface-rust
group: sdk
priority: high
languages: [rust]
contract_count: 0
pattern_match_count: 7
---
# Ergo Node Interface (Rust) — Developer Overview

---

## Overview

`ergo-node-interface-rust` is a Rust library that provides a structured, developer-friendly abstraction over the Ergo Node's HTTP API. Rather than requiring developers to manually construct REST calls and parse raw JSON responses, the library exposes a typed `NodeInterface` struct whose methods map directly to node endpoints and common off-chain dApp workflows. Its primary audience is Rust developers building off-chain bots, headless dApps, oracle operators, and tooling that must read blockchain state, scan the UTXO set, construct transactions, and submit them to the network.

The library sits at the boundary between raw node JSON and the strongly-typed Ergo domain model supplied by **ergo-lib** (the Rust port of the Ergo SDK, formerly sigma-rust). Raw node responses — including serialized `ErgoBox` data, `ErgoTree` representations, native token balances, register contents, and transaction structures — are deserialized through ergo-lib types, giving callers access to the full eUTXO data model without writing any parsing code themselves. This means a consuming crate can immediately inspect `Registers`, `Token ID`s, `ErgoTree` bytes, or box values without intermediate transformation layers.

Within the broader Ergo ecosystem the library fills a specific niche: it is the idiomatic Rust foundation for off-chain logic in the same way that `appkit` serves the JVM ecosystem. Projects such as oracle-core and other headless dApp implementations in Rust depend on it to read UTXO-set state, select input boxes, and submit signed transactions, making it a core dependency in the Ergo off-chain infrastructure layer.

---

## Architecture

The library is organized into four focused modules, each with a single responsibility. Data flows from the Ergo Node's REST API inward through `NodeInterface`, gets parsed by ergo-lib, and is handed to higher-level abstractions (`Scan`, wallet helpers) for use by application logic.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application / dApp                         │
└────────────┬────────────────────┬────────────────────┬──────────┘
             │                    │                    │
     ┌───────▼──────┐   ┌─────────▼──────┐   ┌────────▼────────┐
     │   scanning   │   │   transactions │   │     wallet      │
     │  (Scan struct│   │  (tx submit,   │   │  (box selection,│
     │   UTXO scan  │   │   sign helpers)│   │   NanoErg util) │
     │   register)  │   └─────────┬──────┘   └────────┬────────┘
     └───────┬──────┘             │                    │
             └────────────────────┼────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │       node_interface        │
                    │   (NodeInterface struct,    │
                    │    HTTP client, endpoints,  │
                    │    ErgoStateContext builder) │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │       local_config          │
                    │  (node-interface.yaml I/O,  │
                    │   NodeInterface factory)    │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  ergo-lib (sigma-rust)      │
                    │  ErgoBox, ErgoTree, Token,  │
                    │  Transaction, Registers,    │
                    │  ErgoStateContext, NanoErg  │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │       Ergo Node REST API    │
                    │  /wallet, /scan, /utxo,     │
                    │  /transactions, /blocks     │
                    └────────────────────────────┘
```

### `node_interface` module

The `NodeInterface` struct is the central object. It is constructed with a node IP, port, and API key and owns the HTTP client. All node endpoint methods — block height queries, mempool inspection, UTXO lookups, state context retrieval — are implemented as methods on this struct. The `get_state_context() -> Result<ErgoStateContext>` helper is particularly important: it assembles the `ErgoStateContext` required by ergo-lib's transaction building and proof-verification pipeline from live chain data, bridging the gap between raw node responses and the cryptographic context needed by Sigma protocols.

### `scanning` module

The `Scan` struct wraps the Ergo Node's UTXO-set scanning subsystem. A scan is registered on the node with a JSON predicate (e.g., `containsAsset` for tracking a **Singleton / State NFT**, `equals` for matching an `ErgoTree`, or compound predicates for multi-condition matching). Once registered, the node continuously tracks matching boxes across new blocks and reorganizations. The `Scan` struct provides methods to retrieve matching `ErgoBox` instances or their serialized forms, and persists scan IDs to a local file so that registration survives application restarts. Scans are node-scoped: each `Scan` holds a reference to the `NodeInterface` it was registered against, reflecting the fact that scan state lives inside a specific node instance.

### `wallet` module

This module provides box-selection helpers above the raw wallet endpoints. The primary utility is `unspent_boxes_with_min_total(total: NanoErg) -> Result<Vec<ErgoBox>>`, which implements a largest-first selection strategy to cover a required NanoErg value — a prerequisite step before constructing any transaction that requires ERG inputs. This strategy intentionally keeps the selection simple to minimize UTXO fragmentation and reduce the probability of exceeding the **Minimum box value** constraint on change outputs.

### `transactions` module

Contains helpers for serializing, submitting, and broadcasting signed transactions to the network via the node's `/transactions` endpoint. Callers are expected to construct and sign transactions using ergo-lib primitives; this module handles the serialization boundary and HTTP dispatch.

### `local_config` module

Reads and writes a `node-interface.yaml` file containing node connection parameters. `new_interface_from_local_config()` is the standard factory entry point for CLI tools and long-running bots, removing boilerplate configuration management from application code.

---

## Smart Contracts

This library does **not** define or deploy any ErgoScript contracts itself. It is purely an off-chain interface layer. However, it is designed to interact with contracts whose boxes are tracked via UTXO-set scans:

- **Scan predicates** can target boxes by `ErgoTree` hash, allowing an off-chain bot to monitor the output of any ErgoScript contract by its compiled tree.
- **`containsAsset` predicates** are the canonical pattern for tracking boxes guarded by contracts that use a **Singleton / State NFT** (Token ID rule) as their uniqueness invariant — common in oracle pools, SigmaUSD vaults, AMM pools, and other **multi-stage contracts**.
- **Register inspection** is available on retrieved `ErgoBox` objects through ergo-lib, enabling off-chain logic to read `R4`–`R9` values (e.g., oracle data points stored in registers, SigmaUSD parameters, or Dexy state) without any additional parsing layer.

Applications consuming this library are responsible for the ErgoScript contract logic itself; this crate handles only the retrieval and submission side.

---

## Integration Guide

### Installation

Add the crate to `Cargo.toml`:

```toml
[dependencies]
ergo-node-interface = { git = "https://github.com/ergoplatform/ergo-node-interface-rust" }
```

### Connecting to a Node

```rust
use ergo_node_interface::NodeInterface;

// Direct construction
let node = NodeInterface::new("your_api_key", "127.0.0.1",