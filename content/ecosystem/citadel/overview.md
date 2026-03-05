---
title: arkadianet/citadel — Overview
description: "Gold mine: one crate per protocol (AMM, Dexy, HodlCoin, Duckpools, Rosen, SigmaFi, SigmaUSD). Shows EIP-12 tx building, box selection, sigma encoding, ErgoPay signing flow, node API client with capability detection. Single repo demonstrating nearly every major Ergo protocol interaction.\n"
tags: [arkadianet, citadel, reference, rust, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/arkadianet/citadel"
project: arkadianet-citadel
group: reference
priority: high
languages: [rust, typescript]
contract_count: 0
pattern_match_count: 11
---
# Citadel — Developer Overview

## Overview

Citadel (**Client Interface To Access DeFi on Ergo Ledger**) is a local-first desktop application that provides a unified interface for interacting with the major DeFi protocols on the Ergo blockchain. Rather than routing user interactions through cloud APIs or centralized relayers, Citadel communicates directly with a user-operated Ergo full node, preserving the eUTXO model's trustless guarantees end to end. The application covers SigmaUSD (AgeUSD stablecoin), Dexy (oracle-pegged stablecoins including DexyUSD and DexyGold), Spectrum AMM (N2T token swaps), Duckpools (supply/borrow lending), Phoenix HodlCoin (mint/burn with on-chain bank discovery), Rosen Bridge (cross-chain transfers to Cardano and Bitcoin), SigmaFi (P2P bond lending), and MewLock (time-locked UTXOs).

From an ecosystem perspective, Citadel functions as a **reference implementation** demonstrating how a production-grade headless dApp frontend consumes nearly every category of Ergo protocol. Each protocol is isolated in its own Rust crate, making the repository a practical study in eUTXO transaction construction: EIP-12 transaction building, Box selection heuristics, Sigma protocol encoding, Registers, Data inputs, Singleton/State NFT discovery, and multi-stage contract interactions are all represented in concrete, runnable code. Developers building their own integrations can study any single protocol crate independently without needing to understand the full application.

Citadel is built on Tauri v2, pairing a Rust workspace backend with a React/TypeScript frontend. IPC between the two layers uses Tauri's typed `invoke` mechanism, giving the project the additional property of demonstrating how to expose Ergo protocol logic through a strongly-typed command boundary—a pattern directly transferable to other desktop or CLI tools in the ecosystem.

---

## Architecture

### High-Level Layers

```
┌──────────────────────────────────────────────────────┐
│  React / TypeScript Frontend  (frontend/src/)         │
│  Tauri invoke wrappers · UI components · API types   │
└────────────────────┬─────────────────────────────────┘
                     │ Tauri IPC (invoke / commands)
┌────────────────────▼─────────────────────────────────┐
│  Tauri Shell  (app/)                                  │
│  Command handlers per protocol · AppState            │
└──┬──────────────┬──────────────────┬─────────────────┘
   │              │                  │
┌──▼──┐  ┌───────▼──────┐  ┌────────▼────────┐
│ergo-│  │ Protocol     │  │ ergopay-core /  │
│node-│  │ Crates       │  │ ergopay-server  │
│clie-│  │ (one per     │  │ (tx reduction + │
│nt/  │  │  protocol)   │  │  signing relay) │
└──┬──┘  └───────┬──────┘  └────────┬────────┘
   │              │                  │
┌──▼──────────────▼──────────────────▼────────┐
│  ergo-tx  (EIP-12 building, box selection,  │
│           sigma encoding)                   │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  citadel-core  (shared types, errors,       │
│                config, ERG constants)       │
└─────────────────────────────────────────────┘
```

### Crate Responsibilities

| Crate | Responsibility |
|---|---|
| `citadel-core` | Canonical types (`NanoErg`, `TokenId`, `BoxId`), error hierarchy, configuration, shared constants (minimum box value, minimum transaction fee, storage rent parameters) |
| `ergo-node-client` | Typed HTTP client against the Ergo node REST API; capability detection (e.g., `extraIndex` availability, node version); methods for UTXO retrieval, Box lookup by ID, transaction broadcast, mempool inspection |
| `ergo-tx` | EIP-12 unsigned transaction construction, coin-selection / Box selection algorithms, context extension encoding, Sigma protocol value serialization, fee Box creation |
| `ergopay-core` | Transaction reduction: takes an unsigned EIP-12 transaction and reduces it to the form Nautilus wallet expects for signing (ErgoTree evaluation context, context variables) |
| `ergopay-server` | Local HTTP server that implements the ErgoPay signing flow; Nautilus connects to it to retrieve the reduced transaction and post the signed result back |
| `protocols/amm` | Spectrum N2T AMM: pool graph construction, route finding, `quote_route`, circular arbitrage detection (`find_cycles`, `find_circular_arbs`, ternary-search profit optimization, reverse-tighten precision pass) |
| `protocols/dexy` | Dexy oracle-pegged stablecoin: bank Box discovery via Singleton/State NFT, LP rate comparison, mint/redeem transaction building |
| `protocols/hodlcoin` | Phoenix HodlCoin: on-chain bank discovery, mint/burn invariant calculations, fee extraction |
| `protocols/lending` | Duckpools: supply, borrow, withdraw, repay transaction construction against lending pool Boxes |
| `protocols/mewlock` | MewLock: on-chain timelock discovery, lock/unlock transaction building using lock expiry Registers |
| `protocols/rosen` | Rosen Bridge: cross-chain transfer to Cardano/Bitcoin, watcher collateral encoding, guard set selection |
| `protocols/sigmafi` | SigmaFi: P2P bond order discovery, collateral posting, bond fill, repay, liquidation logic |
| `protocols/sigmausd` | AgeUSD: SigUSD and SigRSV mint/redeem, bank Singleton/State NFT tracking, oracle Data input attachment, reserve ratio invariant enforcement |

### Data Flow: Typical Transaction

```
User action (React UI)
  → Tauri invoke (e.g., `amm::swap`)
    → protocol crate builds unsigned EIP-12 tx
        ergo-node-client: fetch wallet UTXOs, protocol Boxes, oracle Data inputs
        ergo-tx: select input Boxes, compute output Boxes, encode Registers,
                 attach context extensions, set fee Box
    → ergopay-core: reduce unsigned tx for signing
    → ergopay-server: serve reduced tx on local HTTP endpoint
    → Nautilus wallet: signs via ErgoPay flow
    → app command: broadcast signed tx via ergo-node-client
  → Frontend: display TxId
```

---

## Smart Contracts

Citadel is an **off-chain client**; it does not deploy new ErgoScript contracts. It interacts with already-deployed protocol contracts by constructing transactions that satisfy their spending conditions. The relevant contract semantics reflected in the off-chain code are:

**SigmaUSD / AgeUSD Bank Contract** — A multi-stage contract guarding the bank Singleton Box (tracked by a State NFT). The off-chain code enforces the reserve ratio invariant (minimum 400% collateral for SigUSD, adjustable for SigRSV), computes mint/redeem prices from the oracle Data input (attached as a read-only Data input, never consumed), and builds output Boxes with correct updated Register values (`R4`–`R7` carry circulating supply counters).

**Dexy Bank and LP Contracts** — Oracle-pegged stablecoin contracts where the peg is enforced by comparing the LP pool price against the oracle price. Off-chain code performs the rate comparison and routes through the appropriate intervention contract path.

**Spectrum AMM Pool Contract** — Constant-product invariant (`x * y = k`) enforced on-chain. The `protocols/amm` crate computes `calculate_output` and `calculate_input` using integer arithmetic matching the Ergo