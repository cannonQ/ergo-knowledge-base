---
title: ErgoPay (EIP-20)
description: ErgoPay (EIP-20) — mobile signing, URI scheme, dynamic vs static requests, desktop↔mobile flow
tags: [ergopay-signing, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [arkadianet/citadel, nautls/nautilus-wallet]
---
# ErgoPay (EIP-20) Developer Integration Guide

## Overview

ErgoPay is a standardized protocol defined in [EIP-20](https://github.com/ergoplatform/eips/blob/master/eip-0020.md) that enables secure transaction signing between dApps and Ergo wallets — most commonly mobile wallets such as Ergo Wallet App — without the dApp ever having custody of the user's private keys. It is the canonical answer to the question: *how does a web or desktop application get a user to sign an Ergo transaction?*

### Why It Exists

Ergo's eUTXO model means a transaction must be fully formed — with real Box inputs, correct ErgoTree guards, proper Registers, Token IDs, minimum box values, and an adequate minimum transaction fee — before it can be signed. The wallet must receive the *complete* unsigned transaction and return a signed one. ErgoPay defines a URI scheme and an HTTP polling contract so that:

- The dApp constructs and hosts the unsigned transaction.
- A QR code or deep-link carries a lightweight URI to the wallet.
- The wallet fetches, presents, and signs the transaction.
- The dApp polls for the signed result and broadcasts it.

No private keys, mnemonics, or seed phrases ever leave the wallet.

### When to Use It

| Scenario | Use ErgoPay? |
|---|---|
| Web dApp → mobile wallet signing | ✅ Primary use case |
| Desktop app → mobile wallet (Citadel pattern) | ✅ Yes |
| Desktop app with embedded wallet | ❌ Use direct signing API |
| Server-side batch transactions | ❌ Use node wallet or fleet-sdk |
| Browser extension wallet (Nautilus) | ❌ Use EIP-12 dApp connector |

ErgoPay is the right choice whenever the signing party is a mobile wallet and the transaction-building party is anything else.

---

## How It Works

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  dApp / Backend                    Mobile Wallet               │
│  ─────────────                     ─────────────               │
│                                                                 │
│  1. Build unsigned TX              4. Scan QR / tap link       │
│  2. Store TX on server             5. Fetch TX from server     │
│  3. Generate ErgoPay URI ──QR──▶   6. Display TX summary       │
│                                    7. User approves            │
│                                    8. Wallet signs TX          │
│  10. Receive signed TX  ◀──────    9. POST signed TX           │
│  11. Broadcast via node                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Breakdown

#### Step 1 — Construct the Unsigned Transaction

The dApp builds a fully valid unsigned transaction. Every input Box must exist on-chain (or in the mempool), every output Box must satisfy:

- A valid **ErgoTree** (compiled from ErgoScript)
- **Minimum box value** (currently 0.001 ERG per box; enforced by miners and nodes)
- Correct **Registers** (R4–R9) if the contract requires them
- Correct **Token ID** assignments following the **Token ID rule** (first input box ID for newly minted tokens)
- A miner fee output (minimum transaction fee box)

Storage rent implications must be considered: boxes that have existed for more than 4 years are subject to storage rent deduction, which can make their effective value lower than their nominal value.

#### Step 2 — Host the Transaction

The server stores the unsigned transaction and assigns it a unique session ID. This endpoint will be polled by both the wallet (to fetch the TX) and the dApp frontend (to check for the signed result).

#### Step 3 — Generate the ErgoPay URI

The URI scheme has two forms:

**Static (single use, TX embedded or at fixed URL):**
```
ergopay://<server-address>/api/ergo-pay/<session-id>
```

**Dynamic (wallet-address-aware, server tailors TX to the user's address):**
```
ergopay://<server-address>/api/ergo-pay/<session-id>?p2pk=<wallet-address>
```

The `ergopay://` scheme replaces `https://`. The wallet substitutes `ergopay://` with `https://` when making the actual HTTP request, so your server must serve TLS in production.

#### Step 4–5 — Wallet Fetches the Request

The wallet app resolves the URI and makes a GET request to the HTTPS endpoint. The server responds with an `ErgopayRequest` JSON object:

```json
{
  "reducedTx": "<base64-encoded reduced transaction>",
  "senderAddress": "<P2PK address of expected signer>",
  "replyTo": "https://<server>/api/ergo-pay/<session-id>/signed",
  "message": "Swap 10 ERG for 500 SigUSD",
  "messageSeverity": "INFORMATION"
}
```

The `reducedTx` is the unsigned transaction serialized as a **reduced transaction** (a compact format where each input's spending proof context is pre-reduced, leaving only the sigma proposition to be signed). This is the format Ergo wallets expect.

#### Step 6–8 — User Signs in Wallet

The wallet decodes the reduced transaction, displays a human-readable summary (addresses, amounts, tokens), and waits for user approval. On approval, the wallet produces a **signed transaction** using the user's private key via **Sigma protocols** (specifically Schnorr signatures on the secp256k1 curve, as defined by Autolykos-compatible key derivation).

#### Step 9 — Wallet POSTs the Signed Transaction

The wallet sends the signed transaction to the `replyTo` endpoint as a JSON body.

#### Step 10–11 — dApp Polls and Broadcasts

The dApp frontend polls its own backend for the signed transaction. Once received, the backend (or the wallet itself, depending on configuration) broadcasts to the Ergo network via a node's `/transactions` endpoint.

---

## Implementation

### 1. Server: TypeScript / Node.js (Express)

This is a complete ErgoPay server implementation covering session management, the ErgoPay endpoint, and the polling/reply endpoints.

```typescript
// ergo-pay-server.ts
import express, { Request, Response } from "express";
import { v4 as uuidv4 } from "uuid";
import {
  ErgoBoxes,
  UnsignedTransaction,
  ReducedTransaction,
  BlockHeaders,
  PreHeader,
  ErgoStateContext,
} from "ergo-lib-wasm-nodejs";

const app = express();
app.use(express.json());

// ─── Types ────────────────────────────────────────────────────────────────────

interface ErgopayRequest {
  reducedTx: string;          // base64url-encoded reduced transaction
  senderAddress?: string;     // P2PK address; wallet validates ownership
  replyTo: string;            // POST endpoint for signed TX
  message?: string;           // Human-readable description shown in wallet UI
  messageSeverity?: "INFORMATION" | "WARNING" | "ERROR";
}

interface Session {
  id: string;
  unsignedTx: object;         // raw unsigned TX JSON (fleet-sdk or sigma-rust format)
  reducedTx: string;          // base64url reduced TX for the wallet
  senderAddress?: string;
  message: string;
  signedTx?: object;          // populated by the wallet's POST
  status: "PENDING" | "SIGNED" | "BROADCAST" | "FAILED";
  createdAt: number;
}

// ─── In-memory session store (use Redis in production) ────────────────────────

const sessions = new Map<string, Session>();

// ─── Helper: reduce unsigned TX to ReducedTransaction ─────────────────────────
//
// A ReducedTransaction strips the full blockchain context down to just the
// sigma propositions that need signing. The wallet only needs to produce
// Schnorr proofs; it does not re-execute the ErgoScript context.

async function reduceTransaction(
  unsignedTxJson: object,
  boxesToSpendJson: object[],
  dataInputBoxesJson: object[],
  blockHeadersJson: object[],   // last 10 block headers from the node
  currentHeight: number
): Promise<string> {
  // Deserialize inputs
  const unsignedTx = UnsignedTransaction.from_json(
    JSON.stringify(unsignedTxJson)
  );

  const boxesToSpend = ErgoBoxes.from_boxes_json(
    boxesToSpendJson.map((b) => JSON.stringify(b))
  );

  const dataInputBoxes = ErgoBoxes.from_boxes_json(
    dataInputBoxesJson.map((b) => JSON.stringify(b))
  );

  // Build ErgoStateContext from the last 10 block headers.
  // This is required to evaluate ErgoScript context variables such as
  // HEIGHT, SELF, INPUTS, OUTPUTS, and any Context extension fields.
  const blockHeaders = BlockHeaders.from_json(
    blockHeadersJson.map((h) => JSON.stringify(h))
  );
  const preHeader = PreHeader.from_block_header(blockHeaders.get(0));
  const stateContext = new ErgoStateContext(preHeader, blockHeaders);

  // Reduce: evaluate all ErgoScript guards down to sigma propositions
  const reducedTx = UnsignedTransaction.from_json(
    JSON.stringify(unsignedTxJson)
  );

  // ergo-lib-wasm exposes reduce via the tx_reduce function
  const reduced = reducedTx.reduce(
    stateContext,
    boxesToSpend,
    dataInputBoxes
  );

  // Serialize to base64url for the ErgopayRequest payload
  return Buffer.from(reduced.sigma_serialize_bytes()).toString("base64url");
}

//