---
title: ErgoAuth (EIP-28)
description: ErgoAuth (EIP-28) — user authentication via SigmaProp signature, challenge-response flow
tags: [ergoauth, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [paideiadao/paideia-app]
---
# ErgoAuth (EIP-28) Developer Guide

## Overview

ErgoAuth is a challenge-response authentication protocol defined in [EIP-28](https://github.com/ergoplatform/eips/blob/master/eip-0028.md) that enables dApps to verify ownership of an Ergo address without requiring the user to submit an on-chain transaction. Instead of spending a Box or paying a fee, the user proves control of a **SigmaProp** (a Sigma protocol statement) by signing a server-issued challenge message with their wallet's private key.

### Why It Exists

Traditional blockchain authentication forces users to pay a **Minimum transaction fee** (currently 0.001 ERG) every time they log in — an unnecessary cost for off-chain identity verification. ErgoAuth solves this by leveraging Ergo's native **Sigma protocols** (specifically Schnorr signatures over the secp256k1 curve) purely at the cryptographic layer, with no eUTXO interaction required.

### When to Use ErgoAuth

| Use Case | ErgoAuth? |
|---|---|
| Gating a dApp dashboard behind wallet ownership | ✅ Yes |
| Signing into a DAO governance portal (e.g., Paideia) | ✅ Yes |
| Authorizing a multi-stage contract transaction | ❌ Use ErgoScript guards instead |
| Proving ownership of a **Native token** / NFT for off-chain perks | ✅ Yes |
| On-chain access control | ❌ Use SigmaProp in ErgoTree |

ErgoAuth is the correct pattern whenever you need **off-chain proof of key ownership** tied to an Ergo address, without touching the eUTXO ledger.

---

## How It Works

ErgoAuth follows a classic challenge-response flow, but the "response" is a **Sigma protocol proof** — the same cryptographic primitive that guards Boxes on-chain via **ErgoTree**.

```
┌────────┐        1. Auth Request URL          ┌──────────┐
│        │ ◄─────────────────────────────────── │          │
│ Wallet │                                      │  Server  │
│  App   │  2. GET /ergoauth/request/{address}  │  (dApp)  │
│        │ ─────────────────────────────────── ► │          │
│        │                                      │          │
│        │  3. ErgoAuthRequest JSON response    │          │
│        │ ◄─────────────────────────────────── │          │
│        │                                      │          │
│        │  4. User signs challenge locally     │          │
│        │     (Schnorr sig over SigmaProp)     │          │
│        │                                      │          │
│        │  5. POST proof to replyTo endpoint   │          │
│        │ ─────────────────────────────────── ► │          │
│        │                                      │          │
│        │  6. Server verifies, returns token   │          │
│        │ ◄─────────────────────────────────── │          │
└────────┘                                      └──────────┘
```

### Step-by-Step Breakdown

**Step 1 — Initiate: dApp generates a deep-link or QR code**

The dApp constructs a URI of the form:
```
ergoauth://<host>/api/ergoauth/request/<address>
```
This URI is handed to a compatible wallet (Nautilus, SAFEW, Ergo Wallet App). The `address` segment tells the wallet which key to use.

**Step 2 — Request: Wallet GETs the challenge**

The wallet HTTP-GETs the URL, substituting `ergoauth://` with `https://` (or `http://` for localhost). The server receives the user's Ergo address and generates a fresh, time-limited challenge.

**Step 3 — Challenge: Server returns `ErgoAuthRequest`**

The server responds with a JSON object conforming to the EIP-28 schema:

```jsonc
{
  "address": "9f...",                        // P2PK address (Base58)
  "signingMessage": "paideia-auth-<nonce>",  // The challenge string
  "sigmaBoolean": "0008cd<pubkey-hex>",      // Serialised SigmaProp (ErgoTree prefix)
  "userMessage": "Sign in to Paideia DAO",   // Displayed to user in wallet UI
  "messageSeverity": "INFORMATION",          // UI hint
  "replyTo": "https://app.paideia.im/api/ergoauth/verify"
}
```

The `sigmaBoolean` field is critical: it is the **serialised SigmaProp** corresponding to the address. For a standard P2PK address this is `0008cd` followed by the compressed public key bytes. The wallet uses this to know *which* Sigma protocol statement to prove.

**Step 4 — Sign: Wallet creates a Sigma proof**

The wallet signs `signingMessage` using the private key that satisfies `sigmaBoolean`. For a P2PK address this is a standard Schnorr signature. For more complex **ErgoTree** guards (e.g., threshold multisig using **Ring signatures**), the wallet produces the appropriate Sigma proof tree. No transaction is created; no Box is consumed.

**Step 5 — Reply: Wallet POSTs the proof**

```jsonc
{
  "address": "9f...",
  "signingMessage": "paideia-auth-<nonce>",
  "proof": "<base64-encoded-sigma-proof>"
}
```

**Step 6 — Verify: Server checks the proof**

The server reconstructs the `sigmaBoolean`, verifies the Sigma proof against the challenge bytes, and — if valid — issues a session token (JWT, cookie, etc.).

---

## Implementation

### Server Side — TypeScript / Next.js

The following is drawn from the Paideia DAO application:

#### `request.ts` — Issue the Challenge

```typescript
// api/ergoauth/request.ts
import { UserLoginStatus } from "@prisma/client";
import { prisma } from "@server/prisma";
import { deleteEmptyUser } from "@server/services/user";
import { Address } from "ergo-lib-wasm-nodejs";
import { NextApiRequest, NextApiResponse } from "next";
import crypto from "crypto";

interface ErgoAuthRequest {
  address: string;
  signingMessage: string;
  sigmaBoolean: string;
  userMessage: string;
  messageSeverity: "INFORMATION" | "WARNING" | "ERROR";
  replyTo: string;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { address } = req.query as { address: string };

  if (!address) {
    return res.status(400).json({ error: "Address is required" });
  }

  try {
    // Validate the address is a legitimate Ergo P2PK address.
    // ergo-lib-wasm will throw if the address is malformed or
    // belongs to the wrong network (mainnet vs testnet).
    const ergAddress = Address.from_base58(address);

    // Derive the sigmaBoolean (serialised SigmaProp) directly from
    // the address. For P2PK this produces the "0008cd<pubkey>" hex
    // that the wallet needs to construct its Sigma proof.
    const ergoTree = ergAddress.to_ergo_tree();
    const sigmaBoolean = Buffer.from(ergoTree.sigma_serialize_bytes()).toString("hex");

    // Generate a cryptographically random nonce and persist it so
    // we can replay-check it during verification. Store with a TTL.
    const nonce = crypto.randomBytes(32).toString("hex");
    const signingMessage = `paideia-auth-${nonce}`;
    const expiresAt = new Date(Date.now() + 5 * 60 * 1000); // 5 minutes

    // Upsert a pending auth record. If the user already has a
    // UserLoginStatus.PENDING row from a previous attempt, reset it.
    await prisma.ergoAuthChallenge.upsert({
      where: { address },
      create: { address, nonce, signingMessage, expiresAt },
      update: { nonce, signingMessage, expiresAt,
                status: UserLoginStatus.PENDING },
    });

    const authRequest: ErgoAuthRequest = {
      address,
      signingMessage,
      sigmaBoolean,
      userMessage: "Sign in to Paideia DAO — no transaction required.",
      messageSeverity: "INFORMATION",
      // The wallet will POST the signed proof to this URL.
      replyTo: `${process.env.NEXT_PUBLIC_API_URL}/api/ergoauth/verify`,
    };

    return res.status(200).json(authRequest);
  } catch (err) {
    console.error("[ErgoAuth] Request error:", err);
    return res.status(400).json({ error: "Invalid Ergo address" });
  }
}
```

#### `verify.ts` — Validate the Sigma Proof

```typescript
// api/ergoauth/verify.ts
import { Address, ErgoStateContext, Wallet } from "ergo-lib-wasm-nodejs";
import { prisma } from "@server/prisma";
import { NextApiRequest, NextApiResponse } from "next";
import { signJwt } from "@server/auth/jwt";

interface ErgoAuthProof {
  address: string;
  signingMessage: string;
  proof: string; // Base64-encoded serialised Sigma proof bytes
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed"