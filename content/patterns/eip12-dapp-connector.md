---
title: EIP-12 dApp Connector
description: EIP-12 dApp Connector — connection API, context API, multi-wallet detection, TypeScript types
tags: [eip12-dapp-connector, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [nautls/nautilus-wallet, ThierryM1212/SAFEW, fleet-sdk/fleet]
---
# EIP-12 dApp Connector — Developer Guide

## Overview

### What Is EIP-12?

EIP-12 (Ergo Improvement Proposal 12) defines a standardized browser-based **dApp Connector API** — a JavaScript/TypeScript interface that wallet extensions inject into web pages, enabling decentralized applications to request wallet access, query blockchain state, and submit transactions without ever holding private keys.

EIP-12 is Ergo's equivalent of EIP-1193 in the Ethereum ecosystem, but designed from the ground up for the **eUTXO model**. Rather than account balances and nonces, EIP-12 exposes **Boxes**, **Registers**, **Data inputs**, **Native tokens**, and **ErgoScript**-aware signing flows.

### Why It Exists

The eUTXO model introduces complexities that account-based connector APIs cannot handle:

- **Boxes** carry value, **Native tokens**, and typed **Registers** — not just ERG balances
- Transactions may include **Data inputs** (read-only Boxes that provide context to **ErgoScript** without being consumed)
- **Multi-stage contracts** involving **Singleton / State NFT** boxes require precise UTXO selection
- **Context extension** variables must be injected at signing time for certain **Sigma protocols**
- **Storage rent** mechanics mean Box selection strategies must account for age and size

EIP-12 abstracts all of this behind a wallet-agnostic API so dApp developers write one integration and any conformant wallet — Nautilus, SAFEW, or future wallets — works without modification.

### When to Use It

| Scenario | Use EIP-12? |
|---|---|
| Browser dApp requiring user-held keys | ✅ Yes |
| Server-side transaction building | ❌ No — use Fleet SDK or AppKit directly |
| Read-only blockchain queries | ⚠️ Partial — use a node/explorer API instead |
| Multi-party **Atomic swaps** | ✅ Yes — wallet handles partial signing |
| dApp with **Ring signatures** | ✅ Yes — wallet prover handles Sigma logic |

---

## How It Works

### The Two-Phase Architecture

EIP-12 separates concerns into two distinct API surfaces:

```
┌─────────────────────────────────────────────────────────┐
│                    Browser Window                        │
│                                                          │
│  window.ergoConnector        window.ergo                │
│  ┌─────────────────┐         ┌──────────────────────┐   │
│  │   Auth API      │──────►  │    Context API        │   │
│  │ (NautilusAuthApi│connect()│  (NautilusErgoApi)    │   │
│  │  ErgoAPIini)    │         │  get_utxos()          │   │
│  └─────────────────┘         │  get_balance()        │   │
│                               │  sign_tx()            │   │
│  Phase 1: Permission          │  submit_tx()          │   │
│  Request                      └──────────────────────┘   │
│                               Phase 2: Wallet Operations  │
└─────────────────────────────────────────────────────────┘
```

### Step-by-Step Flow

#### Phase 1 — Connection and Permission

```
dApp                    Wallet Extension           User
 │                           │                      │
 │  ergoConnector.nautilus   │                      │
 │  .connect()               │                      │
 │──────────────────────────►│                      │
 │                           │  Show permission     │
 │                           │  popup ──────────────►│
 │                           │                      │ Approve/Deny
 │                           │◄─────────────────────│
 │◄──────────────────────────│                      │
 │  Promise<boolean>         │                      │
 │  (true = granted)         │                      │
```

1. The wallet extension injects `window.ergoConnector` at page load, populating it with one entry per installed wallet (e.g., `nautilus`, `safew`).
2. The dApp calls `ergoConnector.<walletName>.connect()`, which triggers a user-facing permission dialog.
3. On approval, the wallet populates `window.ergo` (or returns a context object) with the **Context API**.

#### Phase 2 — Context API Usage

```
dApp                         window.ergo (Context API)
 │                                    │
 │── get_balance("ERG") ─────────────►│
 │◄─ BigInt (nanoERG) ────────────────│
 │                                    │
 │── get_utxos(amount, tokenId) ─────►│  Wallet selects
 │◄─ ErgoBox[] ───────────────────────│  Boxes from eUTXO set
 │                                    │
 │── sign_tx(unsignedTx) ────────────►│  Wallet builds
 │                                    │  ErgoScript context,
 │                                    │  evaluates Sigma proofs
 │◄─ SignedTransaction ───────────────│
 │                                    │
 │── submit_tx(signedTx) ────────────►│  Broadcasts to
 │◄─ TxId (string) ───────────────────│  Ergo network
```

#### Signing Internals (Nautilus Prover)

When `sign_tx()` is called, the wallet's internal prover:

1. Reconstructs the **ErgoScript context** (current height, **SELF** box, **INPUTS**, **OUTPUTS**, **DATA_INPUTS**)
2. Evaluates each input's **ErgoTree** using the **ErgoScript** interpreter
3. Generates cryptographic proofs via **Sigma protocols** (Schnorr, **Ring signatures**, threshold)
4. Attaches `spendingProof` to each signed input
5. Optionally injects **Context extension** variables required by the script

---

## Implementation

### TypeScript Type Definitions

Start with the core types that mirror EIP-12's specification:

```typescript
// types/eip12.ts

/**
 * EIP-12 canonical type definitions.
 * These types describe the shape of objects flowing across the
 * dApp Connector boundary — from wallet to dApp and back.
 */

/** A Token ID follows the Token ID rule: the ID equals the Box ID
 *  of the transaction output that first minted the token. */
type TokenId = string; // 64-char hex

/** ERG amounts are always represented in nanoERG (1 ERG = 1_000_000_000 nanoERG).
 *  This avoids floating-point errors and matches the Minimum box value unit. */
type NanoErg = string; // bigint-safe string

/** A Box ID is the Blake2b-256 hash of the serialized Box content. */
type BoxId = string; // 64-char hex

/** A Transaction ID is the Blake2b-256 hash of the serialized transaction. */
type TxId = string; // 64-char hex

/** ErgoTree is the serialized P2S (pay-to-script) locking script, hex-encoded.
 *  It encodes the ErgoScript expression as a typed lambda calculus term. */
type ErgoTreeHex = string;

/** Registers R4–R9 hold typed ErgoScript values serialized as hex.
 *  R0–R3 are implicit (value, tokens, creationInfo, script). */
interface Registers {
  R4?: string;
  R5?: string;
  R6?: string;
  R7?: string;
  R8?: string;
  R9?: string;
}

/** A Native token attached to a Box. */
interface Token {
  tokenId: TokenId;
  amount: NanoErg;
}

/**
 * An EIP-12 ErgoBox — the fundamental eUTXO primitive.
 * Boxes are immutable once created; spending creates new Boxes.
 * Storage rent applies after ~4 years (1,051,200 blocks).
 */
interface ErgoBox {
  boxId: BoxId;
  value: NanoErg;           // nanoERG, must meet Minimum box value
  ergoTree: ErgoTreeHex;    // locking ErgoScript
  assets: Token[];          // Native tokens
  additionalRegisters: Registers;
  creationHeight: number;   // block height when Box was created
  transactionId: TxId;
  index: number;            // output index within creating transaction
}

/** Context extension variables injected at signing time.
 *  Used by ErgoScript via getVar[T](id) to access prover-supplied data. */
interface ContextExtension {
  [key: string]: string; // key: variable index (string), value: hex-encoded SigmaType
}

/** An unsigned transaction input referencing a Box to be spent. */
interface UnsignedInput {
  boxId: BoxId;
  extension: ContextExtension;
}

/** A Data input — a Box read by ErgoScript without being consumed.
 *  Enables stateful contracts to read oracle data, parameters, etc. */
interface DataInput {
  boxId: BoxId;
}

/** An output Box to be created by the transaction. */
interface ErgoBoxCandidate {
  value: NanoErg;
  ergoTree: ErgoTreeHex;
  assets: Token[];
  additionalRegisters: Registers;
  creationHeight: number;
}

/** A complete unsigned transaction ready for wallet signing. */
interface UnsignedTransaction {
  id?: TxId;
  inputs: UnsignedInput[];
  dataInputs: DataInput[];
  outputs: ErgoBoxCandidate[];
}

/** A spending proof produced by evaluating Sigma protocols. */
interface SpendingProof {
  proofBytes: string;        // hex-encoded proof (can be empty for proveDlog)
  extension: ContextExtension;
}

/** A signed input after the wallet prover has run. */