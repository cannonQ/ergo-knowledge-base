---
title: minotaur-ergo/minotaur-wallet — Overview
description: Minotaur — multi-platform Ergo wallet with multi-sig support, dApp connector, ErgoPay
tags: [minotaur-ergo, minotaur-wallet, infrastructure, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/minotaur-ergo/minotaur-wallet"
project: minotaur-ergo-minotaur-wallet
group: infrastructure
priority: medium
languages: [typescript]
contract_count: 0
pattern_match_count: 0
---
# Minotaur Wallet — Developer-Focused Overview

---

## Overview

Minotaur is an open-source, multi-platform Ergo wallet built with TypeScript and the Capacitor framework, targeting Android, iOS, Windows, macOS, and Linux from a single codebase. It functions as a full-featured eUTXO wallet — managing Boxes, Native tokens (including NFTs conforming to EIP-04 metadata), and Transaction construction and signing — while also exposing a dApp hosting layer that embeds mini-applications directly into the wallet UI. In the Ergo ecosystem, Minotaur occupies the role of a user-controlled signing environment: it holds keys, constructs and signs Transactions (or partially signs them in multi-sig flows), and bridges end-users to on-chain protocols without delegating custody to a third party.

Beyond basic key management, Minotaur implements several Ergo-specific interaction patterns: ErgoPay (EIP-20) for QR-code-driven Transaction requests from external services, cold wallet support for fully air-gapped signing via animated QR codes, read-only wallet mode using public keys only, and a dApp connector interface compatible with EIP-12. These features make it a practical reference implementation for wallet-level integration of Sigma protocols, since each signed Transaction must satisfy the ErgoTree conditions of the input Boxes — including threshold Sigma protocols for multi-sig. The project is a first-class citizen of the Ergo infrastructure layer: dApp developers, protocol designers, and tooling authors all interact with it either as an end-user signing surface or as an EIP-12-compliant connector target.

The wallet's built-in dApp ecosystem currently includes SigmaUSD, token issuance, token burn, and Box consolidation. Each of these operates by constructing an unsigned Transaction client-side using the eUTXO model — selecting input Boxes, computing change Boxes, respecting the Minimum box value and Minimum transaction fee constraints, and then submitting signed Transactions to an Ergo node or public API. The roadmap includes dynamic dApp loading (so new protocols can be added without a wallet binary update) and a browser extension connector for Chrome and Firefox.

---

## Architecture

### High-Level Component Map

```
┌──────────────────────────────────────────────────────────┐
│                  Capacitor Shell                          │
│  (Android / iOS / Electron / Web)                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │              React / Vue UI Layer                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │  │
│  │  │  Wallet UI   │  │  dApp Host   │  │ErgoPay  │  │  │
│  │  │  (accounts,  │  │  (embedded   │  │Handler  │  │  │
│  │  │   history,   │  │   dApps)     │  │(EIP-20) │  │  │
│  │  │   tokens)    │  └──────┬───────┘  └────┬────┘  │  │
│  │  └──────┬───────┘         │               │        │  │
│  └─────────┼─────────────────┼───────────────┼────────┘  │
│            │                 │               │            │
│  ┌─────────▼─────────────────▼───────────────▼────────┐  │
│  │              Core Wallet Library                    │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  │  │
│  │  │ Key Manager │  │ TX Builder   │  │ Signer   │  │  │
│  │  │ (BIP-32/39  │  │ (Box select, │  │ (Sigma   │  │  │
│  │  │  derivation)│  │  fee, change)│  │  proofs) │  │  │
│  │  └──────┬──────┘  └──────┬───────┘  └────┬─────┘  │  │
│  │         │                │               │         │  │
│  │  ┌──────▼────────────────▼───────────────▼─────┐  │  │
│  │  │           ergo-lib-wasm (Rust bindings)      │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          Persistence Layer (SQLite / IndexedDB)      │  │
│  │  Encrypted key material, wallet metadata, TX cache  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          Network Layer                               │  │
│  │  Ergo Node REST API / Explorer API                  │  │
│  │  (Box fetch, TX broadcast, NiPoPoW headers)         │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Component Descriptions

**Capacitor Shell** — The cross-platform runtime bridges the web application to native device APIs (camera for QR scanning, secure storage, filesystem). Electron provides the desktop equivalent. Platform-specific subdirectories (`android/`, `ios/`, `electron/`) contain the native project skeletons that Capacitor syncs into.

**UI Layer** — Presents wallet accounts, Box balances (ERG + Native tokens), Transaction history, and the embedded dApp host. The dApp host renders each mini-dApp (SigmaUSD, token issuance, etc.) within the wallet context, giving dApps direct access to signing primitives without requiring an external browser connector.

**Core Wallet Library** — Handles all cryptographic and eUTXO logic:
- *Key Manager*: BIP-39 mnemonic generation (12–24 words) and BIP-32 hierarchical deterministic key derivation, compatible with Yoroi and the official Ergo node wallet derivation path. Secrets are encrypted with a user password before persistence.
- *TX Builder*: Coin selection over available Boxes (respecting Minimum box value per Box and the Minimum transaction fee), construction of output Boxes with correct Registers, token amounts, and ErgoTree targets.
- *Signer*: Delegates proof generation to `ergo-lib-wasm`, producing Sigma protocol proofs (including threshold/multi-sig `k-of-n` proofs) for each input Box's ErgoTree.

**ergo-lib-wasm** — The Rust `sigma-rust` library compiled to WebAssembly. This is the cryptographic and ErgoScript evaluation core: it constructs `UnsignedTransaction` objects, verifies ErgoTree conditions, and generates Sigma proofs. All low-level Box serialisation and ErgoScript context evaluation happens here.

**Persistence Layer** — SQLite (mobile/desktop) or IndexedDB (web) stores encrypted key material, derived address metadata, and a local Transaction cache. The wallet never stores unencrypted private keys at rest.

**Network Layer** — Communicates with an Ergo full node (REST) or public Explorer API to fetch unspent Boxes by address, retrieve Transaction history, and broadcast signed Transactions. ErgoPay endpoints are also resolved through this layer.

### Data Flow — Sending a Transaction

```
User Input (amount, recipient)
    │
    ▼
TX Builder: fetch unspent Boxes from Network Layer
    │  apply Box selection, compute Minimum box value for change Box
    ▼
UnsignedTransaction (via ergo-lib-wasm)
    │  displayed to user for confirmation (ErgoTree, Registers, tokens shown)
    