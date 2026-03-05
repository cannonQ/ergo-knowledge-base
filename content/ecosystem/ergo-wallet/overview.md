---
title: ergoplatform/ergo-wallet-app — Overview
description: Official Ergo Android/iOS wallet — key management, mobile wallet patterns
tags: [ergoplatform, ergo-wallet-app, infrastructure, kotlin]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergoplatform/ergo-wallet-app"
project: ergoplatform-ergo-wallet-app
group: infrastructure
priority: medium
languages: [kotlin]
contract_count: 0
pattern_match_count: 0
---
# Developer Overview: ergoplatform/ergo-wallet-app

---

## Overview

The **ergo-wallet-app** is the official lightweight mobile and desktop wallet for the Ergo blockchain, available on Android, iOS, and desktop (JVM). Written primarily in Kotlin with a shared multiplatform core, it serves as the reference implementation of key management and transaction construction patterns for Ergo end-users. Rather than running a full node, it operates as a lightweight SPV-style client, querying public explorer and node APIs to fetch Box data, UTXOs, and mempool state — making it suitable for resource-constrained mobile environments while preserving the full eUTXO spending capability of the Ergo protocol.

Within the Ergo ecosystem, the wallet occupies a critical role as the primary end-user interface to the eUTXO model. It demonstrates canonical patterns for deriving keys (BIP-32/BIP-39 compatible with Yoroi and the Ergo reference node), constructing Transactions from Boxes (including Token handling with correct Token ID rule enforcement and Minimum box value management), and signing via Sigma protocols locally on-device. The app also functions as a consumer of higher-level Ergo standards: it implements **ErgoPay** (EIP-20) for dApp-to-wallet transaction handoff and **ErgoAuth** (EIP-28) for dApp authentication flows, making it the canonical mobile counterpart to EIP-12 browser connector wallets like Nautilus.

The wallet supports **cold wallet** operation — a security-critical pattern where a read-only (watch-only) wallet prepares an unsigned Transaction, which is then transferred to an air-gapped device (running the same app in signing mode) via QR code. The signed Transaction is returned over QR and broadcast by the online device, meaning private keys never touch a network-connected device. This makes ergo-wallet-app a direct reference for developers building custody, signing, or cold-storage infrastructure on Ergo.

---

## Architecture

The codebase is structured as a **Kotlin Multiplatform (KMP)**-style project with a shared `common` module and platform-specific modules for Android, iOS, and Desktop.

```
ergo-wallet-app/
├── common/          # Shared business logic, data models, API clients
├── android/         # Android UI (Fragments, ViewModels, Jetpack)
├── ios/             # iOS UI bridging (Swift/SwiftUI consuming Kotlin)
├── desktop/         # JVM desktop UI (Compose Desktop or Swing)
└── sigma-rust-lib/  # JNI/FFI bindings to sigma-rust for crypto
```

### Key Components

**1. Key Management Layer (`common/src/.../wallet`)**
- Handles BIP-39 mnemonic generation and restoration.
- Derives Ergo addresses using the standard `m/44'/429'/0'/0/n` path, compatible with Yoroi and the Ergo node's own wallet.
- Private keys and mnemonics are encrypted at rest using AES with a user-supplied password or biometric-protected keystore entry.
- Produces `ErgoProver` instances (via sigma-rust or AppKit) capable of signing Transactions using Schnorr-based Sigma protocols.

**2. Transaction Construction Layer**
- Fetches unspent Boxes for an address from the Ergo explorer or node REST API.
- Implements coin selection (box selection) respecting **Minimum box value** (currently 0.001 ERG per Box) and **Minimum transaction fee** rules.
- Constructs output Boxes with correct value, `ErgoTree` (derived from recipient P2PK address), and Token lists — enforcing the **Token ID rule** (token IDs inherited from input Boxes).
- Handles **Storage rent** awareness: the wallet avoids accidentally creating Boxes that would be swept by storage rent before the user can spend them.
- Native token (fungible and NFT) display and sending is fully supported, with Token IDs resolved against the explorer's token registry.

**3. Signing Engine**
- Delegates actual cryptographic operations to **sigma-rust** via JNI bindings (`sigma-rust-lib` module), or alternatively to **ergo-appkit** on the JVM desktop target.
- Signing produces a complete `ProofBytes` field in each `Input`, satisfying the Sigma protocol proof required to spend a P2PK-guarded Box.
- For cold wallet flows, the unsigned Transaction JSON is serialized and encoded as a QR payload, then the signed result is deserialized and broadcast.

**4. ErgoPay / ErgoAuth Protocol Handlers**
- **ErgoPay (EIP-20):** Handles `ergopay://` deep links. The wallet fetches an unsigned `ReducedTransaction` (containing the `ErgoScript` context already reduced to Sigma propositions) from a dApp backend URL, presents it for user confirmation, signs it, and broadcasts.
- **ErgoAuth (EIP-28):** Handles `ergoauth://` deep links. The wallet signs a challenge with the user's private key to prove ownership of an Ergo address to a dApp — enabling authentication without tokens or passwords.

**5. API / Network Layer (`common/.../api`)**
- Abstracts over Ergo Explorer API and Ergo Node REST API.
- Fetches confirmed and unconfirmed Boxes, transaction history, token metadata, and current network parameters (e.g., current height for `Context` construction).
- Balance tracking is done by aggregating all unspent Boxes owned by the wallet's derived addresses.

**6. Persistence Layer**
- Uses SQLDelight (shared KMP) or Room (Android) for local storage of wallet metadata, address book, and cached transaction history.
- Encrypted key material is stored separately in platform secure storage (Android Keystore, iOS Secure Enclave).

### Data Flow

```
User Action
    │
    ▼
UI Layer (Android Fragment / iOS SwiftUI / Desktop Compose)
    │
    ▼
ViewModel / Presenter (common business logic)
    │
    ├──► API Client ──► Explorer/Node REST API ──► Unspent Boxes, Token metadata
    │
    ├──► Key Manager ──► Encrypted Keystore
    │
    ├──► TX Builder ──► Box selection + Output construction + Fee calculation
    │
    └──► Signing Engine (sigma-rust JNI) ──► Signed Transaction JSON
                                                    │
                                                    ▼
                                            Network broadcast (Node API /transactions)
```

For **ErgoPay** flows, the `ReducedTransaction` arrives pre-built from the dApp backend, bypassing the TX Builder — the wallet only signs and broadcasts.

---

## Smart Contracts

The ergo-wallet-app itself does not deploy or own ErgoScript smart contracts on-chain. It operates exclusively with **P2PK (Pay-to-Public-Key)** Boxes, whose `ErgoTree` is a simple Sigma protocol proposition (`proveDlog(pubkey)`) requiring a single Schnorr signature.

However, the wallet is designed to be **contract-aware** in the following ways:

- **ErgoPay integration** allows arbitrary `ErgoTree` contracts to appear in the `ReducedTransaction` output Boxes. The wallet displays and signs these without needing to interpret the contract logic — the dApp backend is responsible for ErgoScript context reduction.
- **Token display**: NFTs whose minting Box Registers (R4–R9) conform to EIP-4 (NFT standard) are rendered with metadata (name, description, artwork), demonstrating Register-aware Box parsing without on-chain contract execution.
- **Cold wallet multi-Box flows**: When constructing transactions that interact with dApp contracts (e.g., a DEX order Box), the wallet can include **Data inputs** — read-only Boxes referenced for their Register contents but not spent — as part of the ErgoPay-provided `ReducedTransaction`.

Developers building ErgoScript contracts who want wallet support should target ErgoPay (EIP-20) as the integration point: reduce the contract's spending conditions server-side and deliver a `ReducedTransaction` to the wallet for signing.

---

## Integration Guide

### Integrating with ErgoPay (EIP-20)

ErgoPay is the primary off-chain integration pattern. Your dApp backend constructs a Transaction, reduces ErgoScript contexts to Sigma propositions, and exposes it at a URL. The wallet fetches, displays, signs, and broadcasts