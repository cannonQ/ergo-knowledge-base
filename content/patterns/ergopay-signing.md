---
title: ErgoPay (EIP-20)
description: ErgoPay (EIP-20) — mobile signing, URI scheme, dynamic vs static requests, desktop↔mobile flow
tags: [ergopay-signing, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [arkadianet/citadel, nautls/nautilus-wallet]
---
# ErgoPay (EIP-20) Developer Integration Guide

---

## Overview

**ErgoPay** is the standard protocol defined in [EIP-20](https://github.com/ergoplatform/eips/blob/master/eip-0020.md) for requesting transaction signing from an Ergo wallet — most commonly a mobile wallet such as Ergo Wallet App — without ever exposing private keys to the dApp or service initiating the request.

### Why It Exists

Ergo's eUTXO model means a transaction spends specific Boxes and creates new ones, each Box potentially guarded by an ArgoTree (compiled ErgoScript). The signing process requires a wallet to prove it satisfies those guard conditions via **Sigma protocols** — zero-knowledge proofs that may involve standard P2PK proofs, threshold signatures, or even **Ring signatures**. Rather than building signing into every dApp directly, EIP-20 defines a clean separation:

- The **dApp/service** constructs the unsigned transaction and exposes it via a URI or HTTP endpoint.
- The **wallet** fetches, validates, presents to the user, and signs the transaction.
- The **dApp/service** receives the signed transaction back (or the wallet broadcasts it directly).

### When to Use It

| Use Case | Appropriate? |
|---|---|
| Mobile-first dApp where users sign on their phone | ✅ Primary use case |
| Desktop dApp with QR-code handoff to mobile | ✅ Classic desktop↔mobile flow |
| Signing arbitrary unsigned transactions in a Tauri/Electron app | ✅ As seen in Citadel |
| Server-side signing with known keys | ❌ Use node wallet API directly |
| Browser extension (Nautilus) dApp connector | ❌ Use EIP-12 dApp connector instead |

ErgoPay is appropriate any time you need **user-custody signing** without a browser extension being present.

---

## How It Works

### High-Level Flow

```
┌─────────────┐        1. Build unsigned TX         ┌──────────────────┐
│  dApp /     │ ─────────────────────────────────▶  │  Backend / Local  │
│  Frontend   │                                      │  TX Builder       │
└─────────────┘                                      └──────────────────┘
       │                                                      │
       │  2. Expose ergopay:// URI (static or dynamic)        │
       │◀─────────────────────────────────────────────────────┘
       │
       │  3. User scans QR or taps deep link
       ▼
┌─────────────┐   4. Wallet GETs unsigned TX (dynamic)  ┌──────────────────┐
│  Mobile     │ ──────────────────────────────────────▶ │  dApp Server /   │
│  Wallet     │                                          │  Local Endpoint  │
│  (Ergo      │ ◀────────────────────────────────────── │                  │
│  Wallet     │   5. Returns ErgoPay response JSON       └──────────────────┘
│  App)       │
│             │   6. Wallet validates, displays summary
│             │      (inputs, outputs, tokens, fees)
│             │
│             │   7. User approves → wallet signs
│             │      via Sigma protocol proofs
│             │
│             │   8a. Wallet submits TX to node/explorer
│             │   OR
│             │   8b. Wallet POSTs signed TX back to dApp
└─────────────┘
       │
       │  9. (Optional) dApp polls or receives webhook
       ▼
  TX confirmed on-chain
```

### Static vs Dynamic Requests

EIP-20 defines two request modes:

**Static Request** — The entire unsigned transaction is embedded directly in the URI or a static payload. Used for simple, pre-built transactions where no per-user Box selection is needed at request time.

```
ergopay:<base64url-encoded-unsigned-tx>
```

**Dynamic Request** — The URI contains an HTTPS endpoint URL. The wallet performs a GET request to that URL (optionally substituting `#P2PK_ADDRESS#` with the user's address) to fetch the current transaction. This is the recommended approach for production because:

- Input Boxes can be selected at request time against the current UTXO set.
- The transaction can be personalized per user (their address is injected).
- The unsigned transaction doesn't bloat the QR code.

```
ergopay:https://example.com/api/ergo-pay/swap?address=#P2PK_ADDRESS#
```

### The `#P2PK_ADDRESS#` Placeholder

When the wallet encounters `#P2PK_ADDRESS#` in a dynamic URL, it replaces it with the user's **P2PK address** (standard pay-to-public-key address) before making the GET request. This allows your server to:

1. Query the user's unspent Boxes from an explorer/node.
2. Select appropriate input Boxes for the transaction.
3. Build a valid unsigned transaction tailored to that user.

### ErgoPay Response Schema

The server responds with JSON conforming to the EIP-20 schema:

```json
{
  "reducedTx": "<base64url-encoded reduced transaction>",
  "sender": "9f...",
  "replyTo": "https://example.com/api/ergo-pay/result/{requestId}",
  "message": "Swap 10 ERG for 500 SigUSD",
  "messageSeverity": "INFORMATION"
}
```

| Field | Required | Description |
|---|---|---|
| `reducedTx` | ✅ | Base64URL-encoded **reduced transaction** (unsigned TX with context applied) |
| `sender` | ❌ | Expected sender P2PK address for wallet validation |
| `replyTo` | ❌ | URL where wallet POSTs the signed TX after user approves |
| `message` | ❌ | Human-readable description shown to user |
| `messageSeverity` | ❌ | `INFORMATION`, `WARNING`, or `ALERT` |

> **Critical:** The `reducedTx` field contains a **ReducedTransaction**, not a raw unsigned transaction. A ReducedTransaction has the spending context (block height, data inputs, etc.) already folded in, so the wallet only needs to provide the signature — it does not need access to the full node to validate inputs. This is what enables offline/mobile signing.

### Desktop↔Mobile Flow via QR Code

```
Desktop Browser                    Mobile Wallet
      │                                  │
      │  1. User initiates action         │
      │                                  │
      │  2. Backend builds ergopay:// URI │
      │                                  │
      │  3. Display QR code on screen     │
      │                                  │
      │                    4. User scans QR with wallet app
      │                                  │
      │                    5. Wallet parses URI, detects dynamic
      │                       → GET https://...?address=9f...
      │                                  │
      │  6. Server receives GET,          │
      │     sees address=9f...            │
      │     builds unsigned TX            │
      │     returns ErgoPay JSON          │
      │                                  │
      │                    7. Wallet shows TX summary
      │                       (Boxes consumed, created,
      │                        Native tokens, ERG delta)
      │                                  │
      │                    8. User taps "Sign & Send"
      │                       Sigma proof generated
      │                                  │
      │  9. (if replyTo set)              │
      │     Wallet POSTs signed TX ──────▶│
      │     Server broadcasts             │
      │                                  │
      │  10. Poll for TX confirmation     │
      ▼                                  ▼
```

---

## Implementation

### 1. TypeScript — Building and Serving a Dynamic ErgoPay Endpoint

This example shows a Next.js API route that handles the full dynamic ErgoPay flow, including Box selection, transaction building, and ReducedTransaction generation.

```typescript
// pages/api/ergo-pay/swap.ts
// Dynamic ErgoPay endpoint — receives wallet address, builds swap TX

import type { NextApiRequest, NextApiResponse } from 'next';
import {
  Address,
  ErgoBoxes,
  ReducedTransaction,
  UnsignedTransaction,
  ErgoBox,
  BoxValue,
  NetworkPrefix,
  Tokens,
  Token,
  TokenId,
  TokenAmount,
  I64,
} from 'ergo-lib-wasm-nodejs';

// Explorer API client (e.g., Ergo Platform Explorer v1)
import { ExplorerClient } from '../../../lib/explorer';

const EXPLORER = new ExplorerClient('https://api.ergoplatform.com');
const MINER_FEE = BigInt(1_100_000);        // Minimum transaction fee: 0.0011 ERG
const MIN_BOX_VALUE = BigInt(1_000_000);     // Minimum box value: 0.001 ERG
const NETWORK_PREFIX = NetworkPrefix.Mainnet;

export interface ErgoPayResponse {
  reducedTx: string;
  sender?: string;
  replyTo?: string;
  message?: string;
  messageSeverity?: 'INFORMATION' | 'WARNING' | 'ALERT';
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ErgoPayResponse | { error: string }>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // The wallet substitutes #P2PK_ADDRESS# before calling this endpoint
  const address = req.query.address as string;
  if (!address) {
    return res.status(400).json({ error: 'address parameter required' });
  }

  try {
    // 1. Validate the address
    const senderAddress = Address.from_mainnet_