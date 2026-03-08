---
title: ErgoPay (EIP-20)
description: ErgoPay (EIP-20) — mobile signing, URI scheme, dynamic vs static requests, desktop↔mobile flow
tags: [ergopay-signing, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [arkadianet/citadel, nautls/nautilus-wallet]
---
# ErgoPay (EIP-20) Developer Integration Guide

---

## Overview

**ErgoPay** is the standardized protocol defined in [EIP-20](https://github.com/ergoplatform/eips/blob/master/eip-0020.md) for requesting transaction signing from an Ergo wallet — most commonly a mobile wallet such as Ergo Wallet App — without that wallet being directly connected to the dApp or service initiating the request. It exists because Ergo's eUTXO model separates transaction *construction* from transaction *signing*: a server or desktop application builds an unsigned transaction referencing specific Boxes (inputs, outputs, Data inputs), and the user's wallet — which holds the private keys — signs it independently.

### Why ErgoPay Exists

| Problem | ErgoPay Solution |
|---|---|
| Private keys should never leave the mobile wallet | Wallet only receives an unsigned tx, signs locally, broadcasts |
| dApp servers don't know the user's UTXOs at build time | Dynamic requests let the server fetch UTXOs on demand using the wallet address supplied at scan time |
| Desktop dApps need mobile signing (air-gapped or convenience) | URI scheme bridges desktop ↔ mobile via QR code or deep link |
| Stateless one-shot transactions (faucets, NFT claims) | Static requests embed the full unsigned tx in the URI |

### When to Use ErgoPay

- **Mobile-first dApps** where the user's wallet is their phone
- **Desktop dApps** that need to delegate signing to a paired mobile wallet (desktop ↔ mobile flow)
- **Server-rendered transactions** where the backend constructs the full unsigned transaction and the user merely approves
- **Batch or protocol operations** (AMM swaps, bridge locks, token burns, hodlcoin interactions) where complex ErgoScript contract logic must be verified before signing — exactly the pattern used in Citadel
- Anywhere you want to avoid embedding signing logic in the frontend

### When *Not* to Use ErgoPay

- When you need synchronous in-page signing (use EIP-12 dApp connector / Nautilus instead)
- When the user is already on desktop with a browser wallet injected

---

## How It Works

ErgoPay defines two request modes and a single URI scheme. The full flow has five actors: **dApp/server**, **QR code / deep link**, **mobile wallet**, **Ergo node / Explorer**, and **user**.

### URI Scheme

```
ergopay://<host>/<path>[?<query>]
ergopay://<host>/<path>#P2PK_ADDRESS
```

- The scheme is always `ergopay://` (not `https://`). Wallets intercept this scheme.
- The `#P2PK_ADDRESS` fragment is appended by the wallet *after* the user consents to share their address (only for dynamic requests that need it).
- Static requests embed everything in the URI body (no server required).

---

### Flow A — Static Request (no server)

A static request is a self-contained URI where the unsigned transaction is Base64url-encoded directly in the path or as a query parameter. No callback is needed.

```
ergopay:?request=<base64url-encoded-ReducedTransaction>
```

```
┌─────────┐   generates URI    ┌──────────────┐
│  dApp   │ ─────────────────► │   QR Code /  │
│ (server │                    │  Deep Link   │
│  or     │                    └──────┬───────┘
│ static) │                           │ user scans
└─────────┘                    ┌──────▼───────┐
                                │ Mobile Wallet│
                                │  - decode tx │
                                │  - show UI   │
                                │  - sign      │
                                │  - broadcast │
                                └──────────────┘
```

**Key constraint:** The transaction must be fully formed. All input Boxes must be resolved (their `ergoTree`, `value`, `assets`, `additionalRegisters`). The wallet cannot fill in any unknowns.

---

### Flow B — Dynamic Request (server-side, with address)

The dynamic flow is the production pattern for dApps. The URI points to a server endpoint. The wallet GETs that endpoint, supplies its P2PK address in the fragment (which becomes a query param server-side), and the server builds a transaction tailored to *that specific address and its current UTXOs*.

```
ergopay://api.mydapp.io/ergopay/swap#P2PK_ADDRESS
         └─────────────────────────┘└────────────┘
              server endpoint         wallet appends
```

**Step-by-step:**

1. **dApp generates** an `ergopay://` URI pointing to its backend endpoint
2. **URI is displayed** as a QR code on desktop, or as a tappable deep link on mobile
3. **User opens** their Ergo wallet (e.g., Ergo Wallet App) and scans/taps
4. **Wallet resolves** the URI; because it contains a `#`, the wallet knows it must substitute the user's P2PK address
5. **Wallet sends GET** to `https://api.mydapp.io/ergopay/swap?address=<P2PK_ADDRESS>`
6. **Server fetches** UTXOs for that address from an Ergo node or Explorer API
7. **Server constructs** an `UnsignedTransaction` (inputs, data inputs, outputs) using those UTXOs
8. **Server serializes** the transaction as a `ReducedTransaction` (all inputs reduced using the blockchain context) and wraps it in an `ErgopaySigningRequest` JSON response
9. **Wallet receives** the JSON, deserializes the `ReducedTransaction`, displays a human-readable summary
10. **User approves**; wallet signs each input using the appropriate Sigma protocol proof
11. **Wallet broadcasts** the signed transaction to the Ergo node mempool
12. **Wallet polls** (optionally) the server's status endpoint for confirmation

---

### Desktop ↔ Mobile Flow

This is the pattern Citadel uses. The desktop app (Tauri/Rust) builds transactions but delegates signing to the user's mobile wallet:

```
┌─────────────────────────┐         ┌──────────────────────┐
│   Desktop App (Citadel) │         │   Mobile Wallet      │
│                         │         │   (Ergo Wallet App)  │
│  1. Build unsigned tx   │         │                      │
│  2. POST to local/      │         │                      │
│     remote ergopay srv  │         │                      │
│  3. Display QR code     │──scan──►│  4. GET request URL  │
│                         │         │  5. Deserialize tx   │
│  6. Poll status endpoint│◄────────│  6. Show tx summary  │
│  7. Confirm broadcast   │         │  7. User signs       │
│                         │         │  8. Broadcast        │
└─────────────────────────┘         └──────────────────────┘
```

---

### ErgopaySigningRequest JSON Schema

The server must respond with this exact structure:

```json
{
  "reducedTx": "<base64url-encoded ReducedTransaction bytes>",
  "senderAddress": "<optional P2PK address of expected signer>",
  "replyTo": "<optional URL for wallet to POST signed tx>",
  "message": "Swap 10 ERG for 500 SigUSD",
  "messageSeverity": "INFORMATION"
}
```

| Field | Required | Description |
|---|---|---|
| `reducedTx` | Yes | Base64url-encoded `ReducedTransaction` (ergo-lib serialization) |
| `senderAddress` | No | If set, wallet must sign with matching key |
| `replyTo` | No | Wallet POSTs `SignedTransaction` here instead of broadcasting itself |
| `message` | No | Human-readable description shown to user |
| `messageSeverity` | No | `INFORMATION`, `WARNING`, or `ERROR` |

---

## Implementation

### 1. Server Endpoint (TypeScript / Node.js)

A production-grade dynamic ErgoPay endpoint using `@fleet-sdk/core` and `ergo-lib-wasm-nodejs`:

```typescript
import express, { Request, Response } from "express";
import {
  ErgoAddress,
  Network,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
  TransactionBuilder,
} from "@fleet-sdk/core";
import * as ergo from "ergo-lib-wasm-nodejs";

const app = express();
app.use(express.json());

// ── Types ────────────────────────────────────────────────────────────────────

interface ErgopaySigningRequest {
  reducedTx: string;          // base64url ReducedTransaction
  senderAddress?: string;
  replyTo?: string;
  message?: string;
  messageSeverity?: "INFORMATION" | "WARNING" | "ERROR";
}

interface ErgoBox {
  boxId: string;
  value: string;              // nanoERG as string (Explorer API)
  ergoTree: string;
  assets: { tokenId: string; amount: string }[];
  additionalRegisters: Record<string, string>;
  creationHeight: number;
  transactionId: string;
  index: number;
}

// ── Explorer helpers ─────────────────────────────────────────────────────────

const EXPLORER_API = "https://api.ergoplatform.com/api/v1";

async function fetchUTXOs(address: string): Promise<ErgoBox[]> {
  const res = await fetch(
    `${EXPLORER_API}/boxes/unspent/byAddress/${address}?limit=50`
  );
  if (!res.ok) throw new Error(`Explorer error: ${res.status}`);
  const data = await res.json();
  return data.items as ErgoBox[];
}

async function fetchCurrentHeight(): Promise<number> {
  const res = await fetch(`${