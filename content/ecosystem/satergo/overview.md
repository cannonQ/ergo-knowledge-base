---
title: Satergo/Satergo — Overview
description: Satergo — Java desktop wallet for Ergo with full node support, Ledger integration
tags: [satergo, satergo, infrastructure, java]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/Satergo/Satergo"
project: satergo-satergo
group: infrastructure
priority: medium
languages: [java]
contract_count: 0
pattern_match_count: 0
---
# Satergo Developer Overview

## Overview

Satergo is a Java-based desktop wallet for the Ergo blockchain that combines a full-featured user interface with an optionally embedded Ergo full node. Unlike thin client or web-based wallets, Satergo is designed to run entirely on the user's machine — encrypted key storage, local transaction construction, and an optionally self-hosted node all operate without reliance on third-party infrastructure. This makes Satergo a trust-minimized entry point into the Ergo eUTXO model, where users retain full custody of keys and can independently verify chain state through their own node.

Within the Ergo ecosystem, Satergo fills the role of a production-grade end-user wallet that also functions as a developer and power-user tool. It surfaces Ergo-native primitives — Boxes, Registers, Native tokens, Token IDs, and Storage rent mechanics — through a cross-platform GUI built with JavaFX. Its Ledger hardware wallet integration means that transaction signing can be delegated to a hardware security module, validating that constructed transactions respect proper ErgoTree spending conditions before any secrets are exposed. Satergo targets all major desktop platforms (Windows x64, Linux x64/aarch64, macOS x64/aarch64) and ships with a self-contained JVM runtime, requiring no pre-installed Java dependency from end users.

Satergo also serves a secondary role as a reference implementation for how a desktop application should interact with the Ergo node API and construct valid eUTXO transactions on the JVM. Developers building off-chain bots, headless dApps, or integration tooling can study Satergo's patterns for box selection, transaction fee handling (Minimum transaction fee, Minimum box value enforcement), and Ledger device communication within a real-world, maintained codebase.

---

## Architecture

Satergo is structured as a Gradle-based Java application with a JavaFX frontend. The major architectural layers are:

### 1. Node Integration Layer
Satergo can operate in two modes:
- **Embedded node mode**: Launches and manages a local Ergo full node process (downloading the Ergo node JAR, managing its lifecycle, and communicating with it over localhost). The node runs as a managed subprocess. This gives the wallet access to NiPoPoW-validated chain state and the full Ergo node REST API.
- **Remote node mode**: Connects to a user-specified external node endpoint via the same Ergo node REST API surface.

Data flows from the node REST API → Satergo's service layer → UI components. Blockchain data (Box UTXOs, transaction history, mempool state) is fetched on demand or via polling; there is no persistent local UTXO database beyond what the node itself maintains.

### 2. Wallet / Key Management Layer
- Mnemonic phrases are generated and encrypted at rest using AES. The encrypted seed is stored in a local wallet file on disk.
- Ergo extended public/private key derivation (BIP-32-compatible, Ergo-flavored) is performed in-process to derive addresses and signing keys.
- **Ledger integration**: When a Ledger hardware wallet is connected, the private key never enters application memory. Transaction signing requests are serialized and dispatched to the Ledger device via USB/HID; the device validates the ErgoTree spending path and returns the Sigma protocol proof (signature).

### 3. Transaction Construction Layer
This layer is responsible for building valid Ergo transactions:
- **Box selection**: Implements coin selection logic over the wallet's unspent Boxes, respecting Minimum box value constraints and Storage rent implications.
- **Transaction assembly**: Constructs `UnsignedTransaction` objects with proper inputs, data inputs (read-only Boxes used as Data inputs), outputs with correct Registers, and ErgoTree locking scripts.
- **Fee handling**: Enforces the Minimum transaction fee and ensures change outputs meet the Minimum box value threshold.
- Signing is dispatched either to the local key material (software wallet) or the Ledger device.

### 4. Token / Asset Layer
- Native tokens are represented by their Token ID (following the Token ID rule: a token's ID equals the Box ID of the UTXO in which it was first minted).
- The UI exposes token balances, allows token transfers, and handles the eUTXO constraint that tokens must be explicitly routed to output Boxes or they are burned.

### 5. UI Layer (JavaFX)
- Screens include: wallet setup/unlock, address management, send/receive, transaction history, embedded node management, and Ledger device pairing.
- Internationalization is handled via `Lang.properties` files, with an `index.json` registry of supported locales.
- Resource loading, icon licensing, and platform detection are all managed through classpath resources.

```
[ Ergo Node (embedded or remote) ]
           |  REST API (HTTP/JSON)
           v
[ Node Service Layer ]  <-->  [ Box / UTXO Cache ]
           |
           v
[ Transaction Builder ]  <-->  [ Key Manager / Ledger HID ]
           |
           v
[ JavaFX UI Screens ]
```

---

## Smart Contracts

Satergo is a wallet application and does not deploy or maintain its own ErgoScript contracts. However, it interacts with ErgoScript at several points:

- **P2PK locking scripts**: Standard outputs are locked with Pay-to-Public-Key ErgoTrees derived from the wallet's key hierarchy. These are the canonical single-signature Sigma protocol spending conditions.
- **ErgoTree interpretation for display**: When displaying transaction details, Satergo may decode and present ErgoTree scripts associated with incoming Boxes, helping users understand what spending conditions apply to funds they are receiving.
- **Ledger ErgoTree validation**: The Ledger integration path requires that the ErgoTree of each input Box being signed is communicated to the device, which validates it against the signing key before producing a Sigma proof. This is a critical security path — the hardware device verifies the spending condition is a P2PK script for the device's own key before signing.
- **Token minting**: Satergo supports token minting, which involves constructing a transaction where a new token is created. The Token ID rule is enforced: the first input Box's ID becomes the Token ID of the newly minted asset, and the minting output Box carries the token quantity in its value along with optional metadata in Registers (R4–R9).

Developers wishing to use Satergo to interact with Multi-stage contracts, Singleton/State NFT state machines, or dApp contracts (e.g., SigmaUSD, Dexy) would need to manually construct the appropriate spending transactions with correct Data inputs and Context extension values using the node API or an external SDK.

---

## Integration Guide

### Node REST API
Satergo communicates with the Ergo node exclusively through the **Ergo node REST API** (default port 9053 for mainnet). Developers integrating with Satergo's node instance (embedded or remote) can use this same API surface:

- `GET /wallet/boxes/unspent` — fetch unspent Boxes for the wallet
- `GET /wallet/transactions` — transaction history
- `POST /wallet/transaction/send` — broadcast a signed transaction
- `GET /blockchain/box/byId/{boxId}` — fetch a specific Box by ID, including all Registers
- `POST /transactions` — submit a raw signed transaction directly

### Wallet File Format
The encrypted wallet file is stored locally. It is not directly accessible as an API. Developers should not attempt to parse this file; instead, interact via the running Satergo instance's node.

### Building from Source for Integration Testing
```bash
# Run from source (requires JDK 25+)
./gradlew run

# Build a portable runtime for a target platform
./gradlew satergoRuntime -Pplatform=linux

# Build all platform runtimes
./build-all-runtimes.sh
```

### Ledger Integration
Satergo communicates with Ledger devices via USB/HID (Java HID API library). The Ledger Ergo app must be installed on the device. The integration:
1. Detects connected Ledger devices.
2. Serializes the unsigned transaction (inputs with ErgoTree, output Boxes, token lists, Register contents).
3. Streams the transaction to the device in chunks.
4. Collects Sigma protocol proof bytes (Schnorr signature) from the device.
5. Assembles the signed transaction for broadcast.

Developers building their own Led