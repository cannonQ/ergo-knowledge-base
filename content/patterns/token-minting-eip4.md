---
title: Token minting (EIP-4)
description: Token minting (EIP-4) — NFT and fungible token issuance, metadata registers, Token ID rule
tags: [token-minting-eip4, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repos: [fleet-sdk/fleet, fleet-sdk/fleet-by-example, arkadianet/citadel, LiliumErgo/scala-api]
---
# Ergo Token Minting (EIP-4) Developer Guide

## Overview

Token minting in Ergo follows the **EIP-4 (Ergo Application Level Standard for Tokens)** specification, which defines how both **fungible tokens** (FTs) and **non-fungible tokens** (NFTs) are issued, described, and identified on-chain. This pattern governs how native tokens come into existence within the eUTXO model and establishes the metadata register layout that wallets, DEXes, and frontends rely on.

### Why This Pattern Exists

Ergo's eUTXO model treats tokens as **first-class citizens** at the protocol level — every Box can carry an arbitrary number of `(TokenId, Amount)` pairs as native tokens, with no need for smart contracts to simulate token logic. However, the protocol itself imposes no semantic constraints on what a token *means*. EIP-4 fills that gap by:

- Establishing the canonical **Token ID rule** (issuance box constraint)
- Defining which **Registers** carry which metadata fields
- Distinguishing NFTs (amount = 1) from fungible tokens (amount > 1)
- Enabling off-chain tooling to discover and display token metadata deterministically

### When to Use This Pattern

| Use Case | Token Type |
|---|---|
| Artwork, collectibles, certificates | NFT (amount = 1) |
| Governance tokens, stablecoins, utility tokens | Fungible token |
| Singleton / State NFT for multi-stage contracts | NFT (amount = 1) |
| Liquidity pool shares | Fungible token |
| Bootstrap box for protocol initialization | NFT (amount = 1) |

---

## How It Works

### The Token ID Rule

The most critical invariant in Ergo token minting is the **Token ID rule**: the Token ID of a newly minted token **must equal the Box ID of the first input box** in the minting transaction.

```
TokenId = BoxId(inputs[0])
```

This rule is enforced at the **consensus layer** (node validation), not by a smart contract. It guarantees:

1. **Global uniqueness** — Box IDs are cryptographic hashes of box contents + context, making collisions computationally infeasible.
2. **One-time issuance** — A Box can only be spent once, so its ID can only ever seed one token.
3. **No registry required** — Any node can verify a token's origin without consulting external state.

### Minting Transaction Structure

```
Minting Transaction
├── Inputs
│   └── [0] Funding Box  ← BoxId becomes the new TokenId
│       (must cover: ERG for outputs + minimum box value + tx fee)
│
└── Outputs
    └── [0] Issuance Box (contains the newly minted tokens)
        ├── value:    ≥ MinBoxValue (0.001 ERG)
        ├── tokens:   [(TokenId = inputs[0].id, amount)]
        ├── R4:       token name         (Coll[Byte] / UTF-8)
        ├── R5:       token description  (Coll[Byte] / UTF-8)
        ├── R6:       number of decimals (Coll[Byte] / UTF-8 encoded integer)
        ├── R7:       [NFT only] asset type
        ├── R8:       [NFT only] content hash (SHA-256)
        └── R9:       [NFT only] link to content (IPFS / URL)
```

### Register Layout (EIP-4)

Registers must be **densely packed** — you cannot skip R5 if you want to set R6. The eUTXO model enforces this at the Box serialization level.

| Register | Type | Content | Required |
|---|---|---|---|
| R4 | `Coll[Byte]` | Token name (UTF-8) | Yes |
| R5 | `Coll[Byte]` | Token description (UTF-8) | Yes |
| R6 | `Coll[Byte]` | Decimals as UTF-8 string (e.g., `"2"`) | Yes |
| R7 | `Coll[Byte]` | Asset type (NFT subtype) | NFT only |
| R8 | `Coll[Byte]` | Content hash (SHA-256, 32 bytes) | NFT only |
| R9 | `Coll[Byte]` | Link/URI to content | NFT only |

**Asset type values for R7:**

| Value | Meaning |
|---|---|
| `0x01` | Picture (JPEG, PNG, etc.) |
| `0x02` | Audio |
| `0x03` | Video |
| `0x04` | Custom / other |

### Step-by-Step Flow

```
1. SELECT a UTXO to spend as inputs[0]
        │
        ▼
2. DERIVE TokenId = BoxId(inputs[0])
        │
        ▼
3. ENCODE metadata into R4–R6 (and R7–R9 for NFTs)
        │
        ▼
4. BUILD issuance output box
   - Set token amount (1 for NFT, N for FT)
   - Pack registers densely (R4, R5, R6 must all be present)
        │
        ▼
5. SIGN and SUBMIT transaction
        │
        ▼
6. NODE VALIDATES Token ID rule:
   tokens[0].id == inputs[0].boxId  ✓
        │
        ▼
7. TOKEN EXISTS — can be transferred, locked in contracts,
   used as Singleton/State NFT, etc.
```

---

## Implementation

### TypeScript — Fungible Token with Fleet SDK

The Fleet SDK's `OutputBuilder.mintToken()` method implements the complete EIP-4 minting pattern. It automatically encodes metadata registers and wires up the Token ID.

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
  ErgoAddress,
} from "@fleet-sdk/core";

// Types from fleet-sdk/fleet token.ts
// NewToken allows omitting tokenId — Fleet derives it from inputs[0]
import type { NewToken } from "@fleet-sdk/core";

async function mintFungibleToken(
  utxos: Box<bigint>[],           // Wallet UTXOs; utxos[0].boxId becomes TokenId
  recipientAddress: string,
  creatorAddress: string,
  currentHeight: number
): Promise<SignedTransaction> {

  // Define the new token — tokenId intentionally omitted here;
  // Fleet resolves it to inputs[0].boxId during build()
  const newToken: NewToken<bigint> = {
    amount: 1_000_000n,     // Total supply (in minimal units, no decimals applied)
    name: "MyToken",
    decimals: 2,            // Stored in R6 as UTF-8 "2"
    description: "A fungible token following EIP-4",
  };

  const unsignedTx = new TransactionBuilder(currentHeight)
    .from(utxos)                    // utxos[0] determines the Token ID
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, recipientAddress)
        .mintToken(newToken)        // Encodes R4, R5, R6; attaches token to box
    )
    .sendChangeTo(creatorAddress)
    .payMinFee()                    // Adds RECOMMENDED_MIN_FEE_VALUE output
    .build();

  // unsignedTx.inputs[0].boxId === the minted token's TokenId
  console.log(
    "Minted Token ID:",
    unsignedTx.inputs[0].boxId
  );

  return unsignedTx;
}
```

### TypeScript — NFT Minting with Content Hash

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  ErgoAddress,
} from "@fleet-sdk/core";
import { Blake2b256 } from "@fleet-sdk/crypto"; // or use noble-hashes

async function mintNFT(
  utxos: Box<bigint>[],
  ownerAddress: string,
  currentHeight: number,
  artworkUrl: string,
  artworkBytes: Uint8Array   // The raw artwork content to hash
): Promise<UnsignedTransaction> {

  // EIP-4: R8 must be SHA-256 of the content, not the URL
  const contentHash = sha256(artworkBytes); // 32-byte Uint8Array

  const unsignedTx = new TransactionBuilder(currentHeight)
    .from(utxos)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, ownerAddress)
        .mintToken({
          amount: 1n,                          // NFT: exactly 1
          name: "My Artwork NFT",
          decimals: 0,                         // NFTs always 0 decimals
          description: "An on-chain NFT following EIP-4",
        })
        // EIP-4 NFT registers: R7, R8, R9
        // These must be set AFTER mintToken() to avoid being overwritten
        .setAdditionalRegisters({
          R7: "0e0101",          // Coll[Byte] encoding of 0x01 = picture type
          R8: encodeHex(contentHash),  // 0e + length + sha256(content)
          R9: encodeString(artworkUrl),
        })
    )
    .sendChangeTo(ownerAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}

// Helper: encode a UTF-8 string as an EIP-4 register value
function encodeString(s: string): string {
  const bytes = new TextEncoder().encode(s);
  // Sigma type prefix: 0e = Coll[Byte],
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
