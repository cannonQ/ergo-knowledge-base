---
title: ErgoPay (EIP-20)
description: ErgoPay (EIP-20) — mobile signing, URI scheme, dynamic vs static requests, desktop↔mobile flow
tags: [ergopay-signing, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repos: [arkadianet/citadel, nautls/nautilus-wallet]
---
# ErgoPay (EIP-20) Developer Integration Guide

## Overview

ErgoPay is a standardized protocol defined in [EIP-20](https://github.com/ergoplatform/eips/blob/master/eip-0020.md) that enables dApps to request transaction signing from external wallets — primarily mobile wallets like Ergo Wallet App — without requiring the dApp to ever handle private keys. It exists because the eUTXO model requires precise Box construction (with correct values, Registers, ErgoTree, Native tokens, and minimum box values) before signing, and that construction is best done server-side or in a trusted dApp context while signing remains in the user's custody.

**When to use ErgoPay:**

| Scenario | Use ErgoPay? |
|---|---|
| Mobile-first dApp where users sign on phone | ✅ Yes |
| Desktop dApp with QR code handoff to mobile wallet | ✅ Yes |
| Server constructs unsigned TX, user signs externally | ✅ Yes |
| Browser extension wallet (Nautilus) is the only target | ❌ Use EIP-12 connector instead |
| Full in-browser signing with injected wallet | ❌ Use EIP-12 |
| Multi-stage contracts requiring sequential signing steps | ✅ Yes (dynamic requests) |

ErgoPay is **not** a signing library — it is a **handoff protocol**. The dApp builds a valid unsigned transaction (respecting minimum box value, minimum transaction fee, Storage rent implications, and correct ErgoTree encoding), then hands it to the wallet via a URI or HTTP endpoint.

---

## How It Works

### Core Concepts

ErgoPay operates in two modes:

1. **Static Request** — The entire unsigned transaction is embedded directly in the `ergopay:` URI. Suitable for simple, pre-built transactions where all inputs are known in advance.
2. **Dynamic Request** — The URI points to an HTTP endpoint. The wallet fetches the unsigned transaction at signing time, optionally sending the user's address(es) so the server can construct a transaction tailored to the user's actual UTXOs (Boxes).

### Protocol Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ErgoPay Full Flow                               │
│                                                                     │
│  dApp / Server          QR / Deeplink          Mobile Wallet        │
│  ─────────────         ─────────────          ─────────────         │
│                                                                     │
│  1. Build unsigned  ──► ergopay://URL ──────► Parse URI             │
│     transaction         or                    or scan QR            │
│     (eUTXO boxes,       ergopay:Base64                              │
│      ErgoTree,                                                      │
│      Registers,                                                     │
│      Native tokens)                                                 │
│                                                                     │
│  2. (Dynamic only)  ◄── GET /ergo-pay/…  ◄── Wallet GETs           │
│     Return                ?address=…          endpoint with         │
│     ErgoPay                                   user address          │
│     Response JSON                                                   │
│                                                                     │
│  3.                                           Wallet displays       │
│                                               TX summary to         │
│                                               user                  │
│                                                                     │
│  4.                                           User approves →       │
│                                               wallet signs TX       │
│                                               with private key      │
│                                               (Sigma protocols)     │
│                                                                     │
│  5. (Dynamic only)  ◄── POST signed TX   ◄── Wallet submits        │
│     Server may             (optional)         signed TX to node     │
│     verify / relay                            or posts to           │
│                                               reducedTx endpoint    │
│                                                                     │
│  6.                                           Wallet shows          │
│                                               success / TX ID       │
└─────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Breakdown

**Step 1 — Build the Unsigned Transaction**

The server or dApp constructs an `UnsignedTransaction` using the eUTXO model. Each output Box must specify:
- `value` (nanoERG, must satisfy minimum box value — typically `1000000` nanoERG)
- `ergoTree` (serialized ErgoScript compiled to ErgoTree bytes, Base16-encoded)
- `assets` (Native tokens as `[{tokenId, amount}]`)
- `additionalRegisters` (R4–R9, encoded as `SType` constant values)
- `creationHeight` (current block height)

Input Boxes are referenced by their Box ID (a hash of the Box contents). Data inputs (read-only Boxes used for oracle data, DEX pool state, etc.) are listed separately and are **not spent**.

**Step 2 — Encode as ErgoPay URI**

*Static:*
```
ergopay:<Base64url-encoded reduced transaction>
```

*Dynamic:*
```
ergopay://example.com/api/ergo-pay/request/<requestId>
ergopay://example.com/api/ergo-pay/swap?address=#P2PK_ADDRESS#
```

The placeholder `#P2PK_ADDRESS#` is replaced by the wallet with the user's P2PK address before making the request.

**Step 3 — Display QR Code or Trigger Deeplink**

On desktop, render the URI as a QR code. On mobile (same device), trigger as a deeplink that opens the wallet app directly.

**Step 4 — Wallet Fetches and Validates (Dynamic)**

The wallet sends a `GET` request to the resolved URL. The server responds with an `ErgoPay Response` JSON object (see Implementation section). The wallet validates:
- The transaction is well-formed
- Input Boxes exist on-chain and are unspent
- Output values satisfy minimum box value
- ErgoTree scripts are parseable
- The fee Box is present and meets minimum transaction fee

**Step 5 — User Signs**

The wallet executes Sigma protocols (Schnorr signatures, potentially Ring signatures for multi-sig) over the transaction's sigma-proposition derived from each input Box's ErgoTree. The result is a `SignedTransaction`.

**Step 6 — Submission**

The wallet submits directly to an Ergo node's `/transactions` endpoint, or (if the ErgoPay response specified a `replyTo` URL) POSTs the signed transaction back to the server.

---

## Implementation

### 1. ErgoPay Response Schema (Server-Side)

The server endpoint must return this JSON structure:

```typescript
// TypeScript — ErgoPay Response type (EIP-20 compliant)
interface ErgoPayResponse {
  // Base16-encoded serialized ReducedTransaction (NOT a full UnsignedTransaction).
  // A ReducedTransaction strips out Box contents, leaving only sigma propositions.
  reducedTx?: string;

  // Human-readable address for the wallet to verify P2PK ownership.
  // Must be a valid Ergo P2PK or P2S address.
  address?: string;

  // Wallet displays this message to the user before signing.
  message?: string;

  // Severity of the message: "information" | "warning" | "error"
  messageSeverity?: "information" | "warning" | "error";

  // If set, wallet POSTs the signed TX (Base16 JSON) here after signing.
  replyTo?: string;
}
```

> **Key distinction:** ErgoPay requires a `ReducedTransaction`, not a raw `UnsignedTransaction`. A `ReducedTransaction` contains pre-evaluated sigma propositions for each input — the wallet does not need to re-execute ErgoScript context evaluation. This is critical for contracts using Context extension variables or complex ErgoScript context.

### 2. Building and Reducing a Transaction (Scala / ergo-appkit)

```scala
import org.ergoplatform.appkit._
import org.ergoplatform.appkit.impl.ErgoTreeContract
import sigma.data.AvlTreeData

// Connect to a public node (or your own)
val nodeUrl    = "https://node.ergo.watch"
val networkType = NetworkType.MAINNET

ErgoClient.create(nodeUrl, networkType, "", Parameters.MainnetNetworkPrefix)
  .execute { ctx: BlockchainContext =>

    val txBuilder = ctx.newTxBuilder()

    // Fetch spendable input Boxes for the user address
    val inputBoxes: java.util.List[InputBox] =
      ctx.getUnspentBoxesFor(
        Address.create("9f...userAddress"),
        0,    // offset
        100   // limit
      )

    // Construct output Box
    // minimum box value = Parameters.MinChangeValue = 1_000_000 nanoERG
    val outputBox: OutBox = txBuilder.outBoxBuilder()
      .value(Parameters.MinChangeValue)
      .contract(
        // ErgoTree for a P2PK address
        ErgoTreeContract(
          Address.create("9g...recipientAddress").getErgoAddress.script,
          networkType
        )
      )
      // Attach a Native token — Token ID rule: first-spend minting
      .tokens(new ErgoToken("tokenId_hex_here", 100L))
      // R4 register: a Long constant (SLong)
      .registers(ErgoValue.of(42L))
      .build()

    // Minimum transaction fee (1_000_000 nanoERG on mainnet)
    val unsignedTx: UnsignedTransaction = txBuilder
      .boxesToSpend(inputBoxes)
      .outputs(outputBox)
      .fee(Parameters.MinFee)           // 1_000_000 nanoERG
      .sendChangeTo(Address.create("9f...userAddress"))
      .build()

    // ── Reduce to ReducedTransaction for ErgoPay ──────────────────────
    // Reduction evaluates ErgoScript context variables (height, self, inputs,
    // outputs, data
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
