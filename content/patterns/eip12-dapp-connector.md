---
title: EIP-12 dApp Connector
description: EIP-12 dApp Connector — connection API, context API, multi-wallet detection, TypeScript types
tags: [eip12-dapp-connector, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [nautls/nautilus-wallet, ThierryM1212/SAFEW, fleet-sdk/fleet]
---
# EIP-12 dApp Connector — Developer Guide

## Overview

EIP-12 (Ergo Improvement Proposal 12) defines the standard interface between browser-based dApps and Ergo wallet extensions. It specifies two distinct API surfaces injected into the `window` object: an **Auth API** (sometimes called the Connection API) used to request wallet access, and a **Context API** (the `ergo` object) used to interact with the wallet once access is granted.

### Why It Exists

Ergo's eUTXO model requires dApps to construct transactions client-side — collecting Boxes, assembling inputs, setting Registers, specifying ErgoScript guards — before asking the wallet to sign. Without a standard interface, every dApp would need bespoke integrations for every wallet. EIP-12 creates a contract that any compliant wallet (Nautilus, SAFEW, Minotaur, etc.) must fulfill, letting dApp developers write once and support multiple wallets.

### When to Use It

- You are building a browser-based dApp that needs to read wallet state (balances, UTXOs, addresses) or request transaction signatures.
- You need to support multiple wallets without forking your integration code.
- You are building a wallet extension and need to understand what surface area to expose.

**Do not use EIP-12 for:**
- Server-side signing (use `ergo-lib` directly).
- Mobile apps (no `window` object; use deep-link or SDK-specific approaches instead).
- Read-only blockchain queries that do not require user identity (use a node/explorer REST API).

---

## How It Works

The flow has four distinct phases:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 1: Discovery          Phase 2: Connection                    │
│                                                                     │
│  window.ergoConnector        ergoConnector.nautilus.connect()       │
│  ├─ nautilus ──────────────► Auth API call                          │
│  ├─ safew                    Wallet prompts user                    │
│  └─ [others]                 Returns Promise<boolean>               │
│                                                                     │
│  Phase 3: Context Acquisition   Phase 4: Usage                      │
│                                                                     │
│  ergoConnector.nautilus         ergo.get_balance()                  │
│    .getContext()            ──► ergo.get_utxos()                    │
│  Resolves to ergo object        ergo.sign_tx()                      │
│                                 ergo.submit_tx()                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Phase 1 — Wallet Discovery

When the browser loads your page, each installed wallet extension runs a content script that injects its API stub into `window.ergoConnector`. Multiple wallets coexist by adding a named key:

```
window.ergoConnector = {
  nautilus: NautilusAuthApi,
  safew:    SafewAuthApi,
  // ...
}
```

The `window.ergo` object may also be pre-populated by a legacy API (`ergo_request_read_access` / `ergo_check_read_access`), but EIP-12 supersedes this.

### Phase 2 — Connection Request

Your dApp calls `ergoConnector.<walletName>.connect()`. The wallet extension intercepts this, shows a permission dialog to the user, and resolves the promise with `true` (granted) or `false` (denied).

### Phase 3 — Context Acquisition

After connection, call `ergoConnector.<walletName>.getContext()`. This resolves to a **Context API object** — conventionally stored as `ergo` — which is the live interface to that wallet.

### Phase 4 — Context API Usage

The `ergo` object exposes read and write methods. Read methods query wallet state. Write methods (`sign_tx`, `submit_tx`) construct a signing request, route it through the extension's background service worker, and return signed data or a transaction ID.

```
dApp                    Content Script           Background SW          User
 │                           │                        │                  │
 │──sign_tx(unsignedTx)──►   │                        │                  │
 │                           │──RPC message──────►    │                  │
 │                           │                        │──prompt user──►  │
 │                           │                        │◄─approve/reject─ │
 │                           │◄──signed tx / error─── │                  │
 │◄──Promise resolves────────│                        │                  │
```

The RPC bridge between content script and background service worker is an internal implementation detail; EIP-12 only standardises what the dApp sees.

---

## Implementation

### 1. TypeScript Type Definitions

Define the full EIP-12 surface before writing any integration code. These types serve as living documentation and catch errors at compile time.

```typescript
// eip12.types.ts

/**
 * A serialised Ergo Box as returned by the wallet context API.
 * Registers R4–R9 are optional and encoded as hex-serialised
 * Sigma types (same encoding used in node REST API responses).
 */
export interface ErgoBox {
  boxId: string;
  transactionId: string;
  blockId?: string;
  value: string;           // nanoERG, as string to avoid JS BigInt issues
  index: number;
  globalIndex?: number;
  creationHeight: number;
  settlementHeight?: number;
  ergoTree: string;        // hex-encoded ErgoTree bytes
  address?: string;        // base58-encoded P2PK or P2S address
  assets: Asset[];
  additionalRegisters: Registers;
  spentTransactionId?: string | null;
  mainChain?: boolean;
}

export interface Asset {
  tokenId: string;         // Token ID = first input Box's ID at minting tx
  index?: number;
  amount: string;          // token quantity as string
  name?: string;
  decimals?: number;
  type?: string;
}

/**
 * Registers R4–R9. Values are hex-encoded serialised Sigma types.
 * An empty object means no registers are set beyond R0–R3.
 */
export interface Registers {
  R4?: string;
  R5?: string;
  R6?: string;
  R7?: string;
  R8?: string;
  R9?: string;
}

/**
 * Pagination descriptor accepted by methods that may return
 * large result sets. EIP-12 defines this but some wallets
 * (notably Nautilus) return an error if paginate is supplied —
 * always check wallet behaviour before using.
 */
export interface PaginateOptions {
  page: number;
  limit: number;
}

export type TokenId = string;  // "ERG" literal or a 32-byte hex token ID

// ─── Unsigned Transaction (what your dApp constructs) ──────────────────────

export interface UnsignedInput {
  boxId: string;
  transactionId?: string;
  index?: number;
  ergoTree: string;
  creationHeight: number;
  value: string;
  assets: Asset[];
  additionalRegisters: Registers;
  /** Context extension for scripts that read ContextVar. Key = var index. */
  extension?: Record<string, string>;
}

export interface UnsignedDataInput {
  boxId: string;
}

export interface UnsignedOutput {
  ergoTree: string;
  creationHeight: number;
  value: string;           // nanoERG
  assets: Asset[];
  additionalRegisters: Registers;
}

/**
 * The unsigned transaction structure passed to sign_tx / sign_tx_input.
 * Mirrors the Ergo node's /transactions/check endpoint body.
 */
export interface UnsignedTransaction {
  id?: string;
  inputs: UnsignedInput[];
  dataInputs: UnsignedDataInput[];   // Data inputs are read-only; not spent
  outputs: UnsignedOutput[];
}

// ─── Signed artefacts ──────────────────────────────────────────────────────

export interface SpendingProof {
  proofBytes: string;         // hex-encoded Sigma proof bytes
  extension: Record<string, string>;
}

export interface SignedInput {
  boxId: string;
  spendingProof: SpendingProof;
}

export interface SignedTransaction {
  id: string;
  inputs: SignedInput[];
  dataInputs: UnsignedDataInput[];
  outputs: ErgoBox[];
}

// ─── Error types ───────────────────────────────────────────────────────────

export enum APIErrorCode {
  InvalidRequest  = -32600,
  MethodNotFound  = -32601,
  InvalidParams   = -32602,
  InternalError   = -32603,
  Refused         = -32604,  // User rejected
  AccountChange   = -32605,  // Active account changed mid-session
}

export interface APIError {
  code: APIErrorCode;
  info: string;
}

// ─── Auth API (one per wallet, lives on ergoConnector) ────────────────────

export interface EIP12AuthApi {
  /**
   * Request the user to grant this origin read access to their wallet.
   * Returns true if granted, false if denied.
   * Must be called before getContext().
   */
  connect(options?: { createErgoObject?: boolean }): Promise<boolean>;

  /** Returns true if this origin already has a live connection. */
  isConnected(): Promise<boolean>;

  /**
   * Disconnect this origin. After this call, getContext() will reject
   * until connect() is called again.
   */
  disconnect(): Promise<boolean>;

  /**
   * Resolve to the live Context API object for this wallet.
   * Rejects if connect() has not been called or access was denied.
   */
  getContext(): Promise<EIP12ContextApi>;
}

// ─── Context API (the `ergo` object) ──────