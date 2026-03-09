---
title: ErgoAuth (EIP-28)
description: ErgoAuth (EIP-28) — user authentication via SigmaProp signature, challenge-response flow
tags: [ergoauth, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [paideiadao/paideia-app]
---
# ErgoAuth (EIP-28) Developer Guide

## Overview

ErgoAuth is a challenge-response authentication protocol defined in [EIP-28](https://github.com/ergoplatform/eips/blob/master/eip-0028.md) that allows a web application or service to verify that a user controls a specific Ergo address **without requiring an on-chain transaction**. Instead of signing a blockchain transaction, the user signs an arbitrary challenge message using the private key corresponding to their wallet's `SigmaProp` (a Sigma protocol proposition). The wallet software handles the cryptographic signing, and the server verifies the resulting proof.

### Why It Exists

Ergo's security model is built on **Sigma protocols** — composable, zero-knowledge proof systems that underpin `ErgoScript`. Every Ergo address encodes an `ErgoTree`, which is ultimately a `SigmaProp` — a proposition that must be satisfied by a valid proof (signature). ErgoAuth leverages this existing cryptographic infrastructure to provide:

- **Trustless identity**: No password database, no OAuth middleman, no on-chain fee.
- **Wallet-native UX**: Any EIP-28-compliant wallet (Nautilus, SAFEW, Terminus) can respond to auth requests automatically via deep link or QR code.
- **Composability**: Because the underlying primitive is a `SigmaProp`, future extensions can support multi-sig (`THRESHOLD`), ring signatures, or any `ErgoScript`-expressible authorization policy.

### When to Use It

| Use Case | ErgoAuth? |
|---|---|
| "Sign in with Ergo wallet" | ✅ Yes |
| Proving ownership of an address to claim an airdrop | ✅ Yes |
| Authorizing a server action tied to a wallet | ✅ Yes |
| Proving ownership of a specific Box or NFT | ⚠️ Use ErgoAuth + server-side UTXO lookup |
| Moving funds or interacting with a smart contract | ❌ Use a full Transaction |

---

## How It Works

The flow follows a standard **challenge-response** pattern, adapted to Ergo's Sigma protocol signature scheme.

```
┌─────────┐          ┌──────────────┐          ┌────────────┐
│  Client │          │ Your Backend │          │   Wallet   │
└────┬────┘          └──────┬───────┘          └─────┬──────┘
     │  1. POST /login      │                        │
     │  { address }         │                        │
     │─────────────────────>│                        │
     │                      │ 2. Generate nonce /    │
     │                      │    signingMessage      │
     │  3. ErgoAuthRequest  │                        │
     │<─────────────────────│                        │
     │                      │                        │
     │  4. Deep link / QR   │                        │
     │─────────────────────────────────────────────> │
     │                      │                        │ 5. User approves,
     │                      │                        │    wallet signs
     │                      │  6. POST /verify       │
     │                      │  { proof, signedMsg }  │
     │                      │<───────────────────────│
     │                      │ 7. Verify SigmaProp    │
     │                      │    signature           │
     │  8. Session / JWT    │                        │
     │<─────────────────────│                        │
└────┴────┘          └──────┴───────┘          └─────┴──────┘
```

### Step-by-Step

**Step 1 — Client initiates login**  
The frontend sends the user's Ergo address (Base58-encoded P2PK or P2S) to your backend.

**Step 2 — Backend generates a challenge**  
The server creates a cryptographically unpredictable `signingMessage` (nonce). This prevents replay attacks. The nonce must be stored server-side (database or cache) and tied to the address, with a short TTL.

**Step 3 — Server returns an `ErgoAuthRequest` object**  
This is the EIP-28 data structure:

```typescript
interface ErgoAuthRequest {
  address: string;          // The address being authenticated
  signingMessage: string;   // The challenge (nonce + optional context)
  sigmaBoolean: string;     // Base64/hex-encoded SigmaProp of the address
  userMessage: string;      // Human-readable message shown in wallet UI
  messageSeverity: "INFORMATION" | "WARNING";
  replyTo: string;          // Callback URL the wallet POSTs the proof to
}
```

**Step 4 — Wallet receives the request**  
The client app encodes the `ErgoAuthRequest` as a deep link (`ergoauth://...`) or QR code. EIP-28-compliant wallets parse this and display the `userMessage` to the user.

**Step 5 — Wallet signs the challenge**  
The wallet computes a Sigma protocol proof over `signingMessage` using the private key for `address`. This is **not** a transaction signature — it is a standalone `SigmaProp` proof (specifically, a Schnorr signature over the challenge bytes in the P2PK case).

**Step 6 — Wallet POSTs the proof**  
The wallet calls `replyTo` with:

```json
{
  "proof": "<hex-encoded sigma proof bytes>",
  "signedMessage": "<the original signingMessage>"
}
```

**Step 7 — Backend verifies the proof**  
Using `ergo-lib` (JVM, WASM, or Python bindings), the server reconstructs the `SigmaProp` from the address's `ErgoTree`, then calls the library's proof verification function against the signed message and proof bytes.

**Step 8 — Session established**  
On successful verification, the server issues a session cookie or JWT.

---

## Implementation

### Backend: Challenge Generation (`request.ts` — adapted from Paideia)

```typescript
// server/api/auth/request.ts
import { NextApiRequest, NextApiResponse } from "next";
import { Address } from "ergo-lib-wasm-nodejs";
import { prisma } from "@server/prisma";
import { UserLoginStatus } from "@prisma/client";
import crypto from "crypto";

interface ErgoAuthRequest {
  address: string;
  signingMessage: string;
  sigmaBoolean: string;
  userMessage: string;
  messageSeverity: "INFORMATION" | "WARNING";
  replyTo: string;
}

/**
 * Derives the sigmaBoolean (serialized SigmaProp) from a Base58 Ergo address.
 * The Address object encodes an ErgoTree; for P2PK addresses this is
 * directly a ProveDlog SigmaProp over the public key point.
 */
function getSigmaBoolean(address: string): string {
  const addr = Address.from_mainnet_str(address);
  // ErgoTree bytes contain the SigmaProp; EIP-28 wants the proposition bytes.
  // ergo-lib exposes address_type_prefix + content bytes.
  const ergoTree = addr.to_ergo_tree();
  // sigmaBoolean is the hex of the serialized sigma proposition
  return Buffer.from(ergoTree.sigma_serialize_bytes()).toString("hex");
}

/**
 * Generates a secure random nonce and stores a pending login record.
 * The nonce TTL prevents replay attacks — expire it after 5 minutes.
 */
async function generateChallenge(address: string): Promise<string> {
  const nonce = crypto.randomBytes(32).toString("hex");

  // Upsert: one pending challenge per address at a time
  await prisma.userLogin.upsert({
    where: { address },
    update: {
      nonce,
      status: UserLoginStatus.PENDING,
      expiresAt: new Date(Date.now() + 5 * 60 * 1000), // 5 min TTL
    },
    create: {
      address,
      nonce,
      status: UserLoginStatus.PENDING,
      expiresAt: new Date(Date.now() + 5 * 60 * 1000),
    },
  });

  return nonce;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { address } = req.body as { address: string };

  if (!address) {
    return res.status(400).json({ error: "Address is required" });
  }

  // Validate that address is a legitimate Ergo address (mainnet P2PK or P2S)
  let sigmaBoolean: string;
  try {
    sigmaBoolean = getSigmaBoolean(address);
  } catch {
    return res.status(400).json({ error: "Invalid Ergo address" });
  }

  const nonce = await generateChallenge(address);

  // The signingMessage is what the wallet will sign.
  // Including a domain prefix prevents cross-site signature reuse.
  const signingMessage = `paideia-authenticate-${nonce}`;

  const ergoAuthRequest: ErgoAuthRequest = {
    address,
    signingMessage,
    sigmaBoolean,
    userMessage: "Sign in to Paideia DAO",
    messageSeverity: "INFORMATION",
    // replyTo must be a publicly reachable HTTPS endpoint
    replyTo: `${process.env.NEXT_PUBLIC_API_URL}/api/auth/verify`,
  };

  return res.status(200).json(ergoAuthRequest);
}
```

---

### Backend: Proof Verification (`verify.ts`)

```typescript
// server/api/auth/verify.ts
import { NextApiRequest, NextApiResponse } from "next";
import { Address, Wallet, ErgoBoxes } from "er