---
title: ErgoAuth (EIP-28)
description: ErgoAuth (EIP-28) — user authentication via SigmaProp signature, challenge-response flow
tags: [ergoauth, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [paideiadao/paideia-app]
---
# ErgoAuth (EIP-28) Developer Guide

## Overview

**ErgoAuth** is a wallet-authentication protocol defined in [EIP-28](https://github.com/ergoplatform/eips/blob/master/eip-0028.md) that enables decentralized, stateless user authentication by leveraging Ergo's native **Sigma protocols**. Instead of passwords or OAuth tokens, a user proves ownership of an address by signing a server-issued challenge with the private key whose corresponding `SigmaProp` (public key, encoded as an `ErgoTree`) is locked to that address.

### Why It Exists

Ergo's eUTXO model makes every address the hash of an `ErgoTree`. That tree is a Sigma-protocol statement — most commonly `proveDlog(pk)` for a P2PK address. Because Sigma protocols are *composable* (supporting AND, OR, threshold, **Ring signatures**, etc.), ErgoAuth generalises beyond simple key ownership to arbitrarily complex spending conditions *without touching the chain*.

### When to Use It

| Scenario | ErgoAuth | Alternative |
|---|---|---|
| Web2-style "Sign in with wallet" | ✅ | — |
| Prove membership of a multisig group | ✅ (threshold SigmaProp) | — |
| On-chain gating that mutates state | ❌ | Smart contract TX |
| Anonymous credential presentation | ✅ (Ring signature) | — |
| Time-locked access | ❌ | Multi-stage contract |

ErgoAuth is **off-chain** and **free** — no transaction, no storage rent, no minimum box value is consumed.

---

## How It Works

The protocol is a three-party **challenge-response** flow involving a **dApp server**, a **wallet** (e.g., Nautilus, Terminus), and optionally a **verification backend**.

```
┌─────────┐   1. Login request      ┌──────────────┐
│  User   │ ──────────────────────► │  dApp Server │
│ Browser │                         │              │
│         │ ◄────────────────────── │  2. Issues   │
│         │   ErgoAuthRequest URI   │  challenge   │
│         │                         └──────────────┘
│         │   3. Deep-links to wallet
│         │ ──────────────────────► ┌──────────────┐
│         │                         │    Wallet    │
│         │ ◄────────────────────── │  Signs msg  │
│         │   4. Signed response    │  with sk     │
└─────────┘                         └──────────────┘
     │
     │  5. POST signature + address to replyTo endpoint
     ▼
┌──────────────┐
│  dApp Server │  6. Verify SigmaProp proof → grant session
└──────────────┘
```

### Step-by-Step

#### Step 1 — User initiates login
The browser sends the wallet address it wants to authenticate.

#### Step 2 — Server creates an `ErgoAuthRequest`
The server constructs a JSON object containing:

| Field | Type | Description |
|---|---|---|
| `address` | `String` | The Ergo address to authenticate |
| `signingMessage` | `String` | The **challenge** — a random nonce or structured string the server will verify |
| `sigmaBoolean` | `String` | Base64-encoded serialised `SigmaProp` (the `ErgoTree` of the address, first byte stripped) |
| `userMessage` | `String` | Human-readable prompt shown in the wallet UI |
| `messageSeverity` | `"INFORMATION" \| "WARNING"` | UI severity hint |
| `replyTo` | `String` | HTTPS URL the wallet POSTs the signature to |

The server also exposes this object at a well-known URL and constructs a deep-link URI:

```
ergoauth://<host>/api/ergoauth/<requestId>
```

#### Step 3 — Wallet fetches and displays the request
EIP-28-compatible wallets (Nautilus, Terminus, SAFEW) detect the `ergoauth://` scheme, fetch the `ErgoAuthRequest` JSON, and present `userMessage` to the user.

#### Step 4 — Wallet signs
The wallet computes:

```
signature = sign(signingMessage, privateKey)
```

Using the **Schnorr/Sigma protocol** proof that corresponds to the `SigmaProp` in the request. The proof is serialised as a byte array.

#### Step 5 — Wallet POSTs to `replyTo`
```json
{
  "address": "9f...",
  "signedMessage": "<signingMessage>",
  "proof": "<base64-encoded proof bytes>"
}
```

#### Step 6 — Server verifies
The server reconstructs the expected `SigmaProp` from the address, then uses `ergo-lib` to verify the proof against the signing message. On success, a session is created.

---

## Implementation

### 1. Server-Side: Issuing the Challenge (TypeScript / Next.js)

This pattern mirrors the production code in `paideiadao/paideia-app`.

```typescript
// lib/ergoauth/challenge.ts
import crypto from "crypto";
import { Address, ErgoTree } from "ergo-lib-wasm-nodejs";

/**
 * Derive the base64-encoded SigmaProp (sigma boolean) from an Ergo address.
 * ErgoTree bytes: [0x00, 0x08, 0xcd, ...33-byte compressed pk]
 * The SigmaProp serialisation strips the leading ErgoTree version/type bytes.
 */
export function sigmaProofFromAddress(address: string): string {
  const ergoAddress = Address.from_mainnet_str(address); // throws on invalid
  const ergoTree: ErgoTree = ergoAddress.to_ergo_tree();
  // ErgoTree bytes for P2PK: 0x0008cd<33-byte pk>
  const treeBytes = Buffer.from(ergoTree.to_base16_bytes(), "hex");
  // EIP-28: sigmaBoolean is the ErgoTree bytes, base64-encoded
  return treeBytes.toString("base64");
}

export function generateChallenge(): string {
  // 32 bytes of entropy — never reuse a challenge
  return crypto.randomBytes(32).toString("hex");
}

export interface ErgoAuthRequest {
  address: string;
  signingMessage: string;
  sigmaBoolean: string;
  userMessage: string;
  messageSeverity: "INFORMATION" | "WARNING";
  replyTo: string;
}

/**
 * Build a fully-formed ErgoAuthRequest.
 * Store (address, signingMessage) in your session/DB to verify later.
 */
export function buildErgoAuthRequest(
  address: string,
  requestId: string,
  baseUrl: string
): ErgoAuthRequest {
  const signingMessage = generateChallenge();
  const sigmaBoolean = sigmaProofFromAddress(address);

  return {
    address,
    signingMessage,
    sigmaBoolean,
    userMessage: "Sign to authenticate with Paideia. No tokens will be spent.",
    messageSeverity: "INFORMATION",
    replyTo: `${baseUrl}/api/ergoauth/${requestId}/verify`,
  };
}
```

### 2. API Route: Serving the Request (Next.js)

```typescript
// pages/api/ergoauth/[requestId]/index.ts
import type { NextApiRequest, NextApiResponse } from "next";
import { prisma } from "@server/prisma";
import { buildErgoAuthRequest } from "@lib/ergoauth/challenge";
import { UserLoginStatus } from "@prisma/client";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "GET") return res.status(405).end();

  const { requestId } = req.query as { requestId: string };

  const pending = await prisma.ergoAuthRequest.findUnique({
    where: { id: requestId },
  });

  if (!pending || pending.status !== UserLoginStatus.PENDING) {
    return res.status(404).json({ error: "Request not found or expired" });
  }

  // Return the ErgoAuthRequest JSON — wallet fetches this via ergoauth:// URI
  return res.status(200).json({
    address: pending.address,
    signingMessage: pending.challenge,       // stored at request creation time
    sigmaBoolean: pending.sigmaBoolean,
    userMessage: "Authenticate with Paideia DAO",
    messageSeverity: "INFORMATION",
    replyTo: `${process.env.NEXT_PUBLIC_URL}/api/ergoauth/${requestId}/verify`,
  } satisfies import("@lib/ergoauth/challenge").ErgoAuthRequest);
}
```

### 3. API Route: Verifying the Proof (TypeScript)

This is the core of the real `request.ts` from `paideiadao/paideia-app`, extended with full verification logic.

```typescript
// pages/api/ergoauth/[requestId]/verify.ts
import type { NextApiRequest, NextApiResponse } from "next";
import {
  Address,
  ErgoTree,
  verify_signature,          // ergo-lib-wasm-nodejs ≥ 0.24
} from "ergo-lib-wasm-nodejs";
import { prisma } from "@server/prisma";
import { UserLoginStatus } from "@prisma/client";
import { deleteEmptyUser } from "@server/services/user";

interface WalletReply {
  address: string;
  signedMessage: string;   // must match the stored challenge exactly
  proof: string;           // base64-encoded Sigma proof bytes
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") return res