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

ErgoAuth is a standardized authentication protocol for the Ergo blockchain, defined in [EIP-28](https://github.com/ergoplatform/eips/blob/master/eip-0028.md). It enables decentralized, wallet-native user authentication without passwords, sessions cookies baked into centralized servers, or custodial key management. Instead, ErgoAuth leverages **Sigma protocols** — the cryptographic foundation of Ergo's **ErgoScript** — to prove ownership of a wallet address through a challenge-response signature flow.

### Why It Exists

Traditional web authentication (username/password, OAuth) requires a trusted third party or a server-side secret store. On Ergo, every address is derived from a **SigmaProp** (a Sigma protocol proposition, typically `proveDlog(pk)` for a standard P2PK address). ErgoAuth exploits this: if you can produce a valid Sigma proof for a SigmaProp, you *are* the owner of that address — no password required.

This fits naturally into Ergo's **eUTXO** model, where identity and authorization are cryptographic rather than administrative.

### When to Use It

| Use Case | Use ErgoAuth? |
|---|---|
| "Sign in with Ergo wallet" for a dApp | ✅ Yes |
| Proving address ownership before whitelisting | ✅ Yes |
| Authorizing off-chain actions tied to an on-chain identity | ✅ Yes |
| Signing an on-chain **Transaction** | ❌ Use standard tx signing |
| Anonymous credential proofs (Ring signatures) | ❌ Separate pattern |

ErgoAuth is used in production by [Paideia DAO](https://github.com/paideiadao/paideia-app), Ergopad, and other ecosystem projects as the canonical "Sign In with Ergo" mechanism.

---

## How It Works

ErgoAuth follows a classic **challenge-response** protocol, but the "response" is a Sigma protocol proof rather than a simple HMAC or JWT signature.

```
┌─────────┐          ┌──────────────┐          ┌────────────────┐
│  User   │          │  dApp/Server │          │  Ergo Wallet   │
│ Browser │          │  (Verifier)  │          │  (Prover)      │
└────┬────┘          └──────┬───────┘          └───────┬────────┘
     │                      │                          │
     │  1. "Login" click     │                          │
     │─────────────────────>│                          │
     │                      │                          │
     │  2. ErgoAuth request  │                          │
     │     URI / QR code     │                          │
     │<─────────────────────│                          │
     │                      │                          │
     │  3. Open in wallet    │                          │
     │─────────────────────────────────────────────────>
     │                      │                          │
     │                      │                          │ 4. Wallet fetches
     │                      │                          │    request from
     │                      │<─────────────────────────│    replyTo URL
     │                      │                          │
     │                      │  5. Return challenge     │
     │                      │─────────────────────────>│
     │                      │                          │
     │                      │                          │ 6. User confirms;
     │                      │                          │    wallet signs
     │                      │                          │    sigmaBoolean with
     │                      │                          │    secret key (dlog proof)
     │                      │                          │
     │                      │  7. POST signed proof    │
     │                      │<─────────────────────────│
     │                      │                          │
     │                      │ 8. Server verifies       │
     │                      │    SigmaProp proof       │
     │                      │                          │
     │  9. Auth token / JWT  │                          │
     │<─────────────────────│                          │
     │                      │                          │
```

### Step-by-Step Breakdown

**Step 1 — User initiates login**  
The user clicks "Connect Wallet" in the dApp frontend.

**Step 2 — Server generates an ErgoAuth Request**  
The server constructs an `ErgoAuthRequest` object containing:
- `address` — the Ergo address whose ownership must be proved
- `signingMessage` — a unique, server-generated challenge string (e.g., a nonce or UUID)
- `sigmaBoolean` — the **SigmaProp** (serialized as Base16 ErgoTree bytes) that corresponds to the address; the wallet must produce a valid proof for this proposition
- `userMessage` — a human-readable message shown in the wallet UI
- `messageSeverity` — display hint (`"INFORMATION"`, `"WARNING"`)
- `replyTo` — the callback URL where the wallet POSTs the signed proof

The request is encoded as an `ergoauth://` URI (or a QR code for mobile wallets).

**Step 3–5 — Wallet fetches the challenge**  
The wallet parses the URI, fetches the full request JSON from `replyTo`, and displays `userMessage` to the user.

**Step 6 — Wallet produces a Sigma proof**  
The wallet uses the user's secret key to produce a **Schnorr signature** (a non-interactive Sigma protocol proof via Fiat-Shamir transform) over a hash of `signingMessage`. This proves knowledge of the discrete logarithm corresponding to the public key embedded in the `sigmaBoolean` ErgoTree — without revealing the secret key.

**Step 7 — Wallet POSTs the proof**  
The wallet sends back:
```json
{
  "proof": "<base16-encoded sigma proof bytes>",
  "pk": "<base16-encoded public key>"
}
```

**Step 8 — Server verifies**  
The server reconstructs the challenge bytes, verifies the Sigma proof against the `sigmaBoolean`, and checks that the proved public key matches the claimed address. This uses `ergo-lib` (Rust/JVM/WASM).

**Step 9 — Session established**  
On success, the server creates a session (JWT, database session, etc.) tied to the verified address.

---

## Implementation

### Prerequisites

```bash
# Node.js / TypeScript
npm install ergo-lib-wasm-nodejs @prisma/client

# Scala (sbt)
# "org.ergoplatform" %% "ergo-appkit" % "5.0.4"

# Python
pip install ergpy
```

---

### 1. Server: Generate the ErgoAuth Request (TypeScript / Next.js)

This is the endpoint the wallet fetches to receive its challenge. Drawn from the Paideia pattern in `request.ts`:

```typescript
// pages/api/auth/ergo/request.ts
import { NextApiRequest, NextApiResponse } from "next";
import { Address } from "ergo-lib-wasm-nodejs";
import { prisma } from "@server/prisma";
import { UserLoginStatus } from "@prisma/client";
import { v4 as uuidv4 } from "uuid";

/**
 * EIP-28 ErgoAuth request shape.
 * The wallet will GET this endpoint to receive the challenge,
 * then POST the signed proof back to `replyTo`.
 */
interface ErgoAuthRequest {
  address: string;          // Ergo address to authenticate
  signingMessage: string;   // Server-generated nonce / challenge
  sigmaBoolean: string;     // Base16 ErgoTree of the address's SigmaProp
  userMessage: string;      // Human-readable text shown in wallet
  messageSeverity: "INFORMATION" | "WARNING";
  replyTo: string;          // Where wallet POSTs the proof
}

/**
 * Derive the sigmaBoolean (ErgoTree hex) from an Ergo address.
 *
 * For a standard P2PK address, the ErgoTree encodes:
 *   proveDlog(pk)
 * where pk is the compressed SEC public key.
 * ergo-lib handles the derivation automatically.
 */
function getSigmaBoolean(address: string): string {
  // Address.from_mainnet_str parses the Base58Check address
  // and exposes the underlying ErgoTree
  const addr = Address.from_mainnet_str(address);
  // to_ergo_tree() returns the ErgoTree; script_hex() gives Base16 bytes
  return Buffer.from(addr.to_ergo_tree().sigma_serialize_bytes()).toString("hex");
}

/**
 * GET /api/auth/ergo/request?address=<ergo_address>
 *
 * Returns an EIP-28 ErgoAuthRequest JSON.
 * The wallet scans a QR / follows an ergoauth:// URI that points here.
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ErgoAuthRequest | { error: string }>
) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { address } = req.query;

  if (!address || typeof address !== "string") {
    return res.status(400).json({ error: "Missing address parameter" });
  }

  // Validate the address is a legitimate Ergo address
  let sigmaBoolean: string;
  try {
    sigmaBoolean = getSigmaBoolean(address);
  } catch {
    return res.status(400).json({ error: "Invalid Ergo address" });
  }

  // Generate a cryptographically unique nonce as the challenge.
  // This MUST be stored server-side and validated on reply — never trust
  // a nonce sent by the client.
  const nonce = uuidv4();
  const signingMessage = `paideia-login-${nonce}`;

  // Persist pending login state so we can verify the