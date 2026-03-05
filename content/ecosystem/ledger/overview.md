---
title: ergoplatform/ledger-app-ergo — Overview
description: Ledger hardware wallet integration for Ergo
tags: [ergoplatform, ledger-app-ergo, infrastructure, c]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergoplatform/ledger-app-ergo"
project: ergoplatform-ledger-app-ergo
group: infrastructure
priority: low
languages: [c]
contract_count: 0
pattern_match_count: 0
---
# Developer Overview: ergoplatform/ledger-app-ergo

## Overview

The `ledger-app-ergo` project is a Ledger hardware wallet application that enables secure key management and transaction signing for the Ergo blockchain on Ledger Nano S+, X, Stax, and Flex devices. Written in C and running within the BOLOS (Blockchain Open Ledger Operating System) secure execution environment, the app exposes an APDU (Application Protocol Data Unit) command interface that allows host-side software to request cryptographic operations — most critically, the derivation of extended public keys and the blind signing of serialized Ergo Transactions — without the private key material ever leaving the secure element.

Within the Ergo ecosystem, this project occupies a critical trust boundary. Because Ergo uses the eUTXO model, a single transaction can consume multiple Boxes (each with its own value, Registers, Native tokens, and ErgoTree spending conditions governed by ErgoScript and Sigma protocols), and the app must parse and present all relevant Box fields to the user before authorizing a signature via the Autolykos-compatible secp256k1 curve. This means the app carries partial knowledge of Ergo's serialization format — including Token IDs, context extensions, and multi-input structures — directly in firmware, making it a security-critical component of the Ergo custody stack.

The project also serves as the canonical reference for how Ledger integration with Ergo should work, defining the APDU protocol that companion libraries (such as `ledgerjs-hw-app-ergo`) must implement. Any wallet or dApp front-end (e.g., Nautilus, SAFEW) that aims to support hardware wallet signing ultimately depends on the behavioral contract established here.

---

## Architecture

### High-Level Components

```
Host Machine                          Ledger Device (BOLOS)
─────────────────────────────         ──────────────────────────────────────
Wallet / SDK (JS/Python)              src/
  │                                     ├── main.c            (APDU dispatcher)
  │  USB/BLE APDU frames                ├── commands/         (per-command handlers)
  ▼                                     ├── ergo/             (Ergo-domain logic)
ledgerblue / Transport layer  ───────►  │   ├── tx/           (transaction parsing)
                                        │   ├── schnorr.c     (Sigma proof signing)
                                        │   └── tokens.c      (Native token handling)
                                        ├── crypto/           (key derivation, hashing)
                                        └── ui/               (display + user confirmation)
```

### Key Components

| Component | Responsibility |
|---|---|
| **APDU Dispatcher (`main.c`)** | Receives raw APDU frames, routes by `CLA`/`INS` byte pairs to command handlers, manages the multi-step streaming state machine for large payloads. |
| **Command Handlers (`commands/`)** | One handler per logical operation: `GET_VERSION`, `GET_EXTENDED_PUBLIC_KEY`, `SIGN_TX`, `ATTEST_INPUT`. Each handler owns its own context struct on the device stack. |
| **Transaction Parser (`ergo/tx/`)** | Stateful streaming parser for Ergo's binary transaction serialization. Consumes chunked APDU payloads, reconstructs Box inputs (with Token IDs, Registers, context extensions), outputs, and data inputs. Validates structural invariants (e.g., Minimum box value, token count limits) incrementally without buffering the full transaction. |
| **Crypto Layer (`crypto/`)** | Wraps BOLOS SDK calls for BIP32/BIP44 key derivation on secp256k1, Blake2b-256 hashing (Ergo's native hash), and the Schnorr signature primitive underpinning Sigma protocols. |
| **UI Layer (`ui/`)** | Renders human-readable summaries of transaction fields — ERG amounts, Token IDs, destination addresses — using Ledger's UX framework. Blocks execution until the user physically confirms or rejects. |
| **Attestation (`ATTEST_INPUT`)** | A distinct command flow that allows the host to prove to the device that a prior Box output (from a previous transaction) genuinely exists, enabling the device to trust input Box values when constructing the transaction digest. |

### Data Flow: Transaction Signing

```
1. Host serializes unsigned Ergo Transaction (inputs, data inputs, outputs)
2. Host streams transaction in APDU chunks → SIGN_TX command handler
3. Transaction Parser incrementally hashes each field (Blake2b-256)
4. For each output Box: UI displays ErgoTree/address, ERG value, Native tokens
5. User confirms on device
6. Crypto layer derives private key via BIP32 path, computes Schnorr signature
7. Device returns 64-byte signature over transaction id (Blake2b hash of serialized tx)
8. Host assembles final signed Transaction for broadcast
```

The device never holds the full transaction in RAM simultaneously — the streaming/chunking design is essential given BOLOS's constrained heap.

---

## Smart Contracts

This project does not define or deploy any ErgoScript contracts. It is purely infrastructure firmware. However, it is directly aware of ErgoScript and ErgoTree in the following ways:

- **ErgoTree display**: When signing, the app decodes recipient ErgoTree bytes into a P2PK address (or flags the output as a script hash) and presents this to the user for confirmation. Raw ErgoTree bytes for non-standard scripts are shown as hex to prevent spoofing.
- **Context extensions**: The transaction parser recognizes and skips serialized context extension fields (used by dApps to pass extra parameters into ErgoScript evaluation), ensuring correct cursor advancement through the binary format without needing to evaluate the script.
- **Registers**: The parser handles the serialized Register layout of output Boxes (R4–R9), advancing the streaming hash correctly even when Registers carry complex Sigma type descriptors, though their semantic content is not evaluated on-device.

Developers building Multi-stage contracts or State machine dApps that require hardware wallet signing must ensure their transaction construction respects the display and attestation constraints imposed by this app.

---

## Integration Guide

### Host-Side Interaction Model

All interaction with the device app goes through APDU command/response pairs over USB HID or BLE. In practice, JavaScript-based wallets use the `@ledgerhq/hw-transport-*` family, and the Ergo-specific APDU encoding is handled by the companion library **`ledgerjs-hw-app-ergo`** (see Related Projects).

### Key APDU Commands

| INS Byte | Command | Description |
|---|---|---|
| `0x01` | `GET_VERSION` | Returns app major/minor/patch version |
| `0x10` | `GET_EXTENDED_PUBLIC_KEY` | BIP32 derivation; returns compressed pubkey + chain code |
| `0x20` | `ATTEST_INPUT` | Attests a Box from a prior confirmed transaction for use as a trusted input |
| `0x21` | `SIGN_TX` | Streams unsigned transaction, collects user confirmation, returns Schnorr signature |

### Derivation Path Convention

Ergo follows BIP44 with coin type `429`:

```
m / 44' / 429' / account' / change / address_index
```

### Integration Patterns

**1. Address Generation (read-only)**
```
Transport → GET_EXTENDED_PUBLIC_KEY(path)
         ← xpub (pubkey + chain code)
Host derives P2PK ErgoTree: 0x0008cd ++ compressed_pubkey
Host encodes address = network_prefix ++ ergotree_hash ++ checksum
```

**2. Transaction Signing (full flow)**
```python
# Pseudocode — mirrors ledgerjs-hw-app-ergo behavior
transport.send(CLA, INS_SIGN_TX, chunk_index, total_chunks, tx_bytes_chunk)
# Repeat for each chunk; device hashes incrementally
# On final chunk: device prompts user
# On approval: device returns 64-byte Schnorr signature
```

**3. Trusted Input Attestation**

For each input Box being spent, the host must first call `ATTEST_INPUT` with the serialized output from the transaction that created that Box. The device signs a commitment to