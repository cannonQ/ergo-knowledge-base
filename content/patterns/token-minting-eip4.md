---
title: Token minting (EIP-4)
description: Token minting (EIP-4) — NFT and fungible token issuance, metadata registers, Token ID rule
tags: [token-minting-eip4, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [fleet-sdk/fleet, fleet-sdk/fleet-by-example, arkadianet/citadel, LiliumErgo/scala-api]
---
# Developer Guide: Token Minting with EIP-4 on Ergo

## Overview

EIP-4 (Ergo Improvement Proposal 4) defines the **Asset Standard** for Ergo — the canonical specification for issuing both **fungible tokens** (FTs) and **non-fungible tokens** (NFTs) on the Ergo blockchain. It standardises how token metadata is stored in box **Registers**, how tokens are identified, and how wallets and dApps interpret on-chain asset information.

### Why It Exists

Ergo supports **Native tokens** at the protocol level via the eUTXO model. Every **Box** can carry multiple token types, each identified by a unique **Token ID**. However, the base protocol says nothing about *names*, *decimals*, *artwork*, or *descriptions*. EIP-4 fills this gap, giving the ecosystem a shared schema so that wallets (Nautilus, SAFEW), explorers (explorer.ergoplatform.com), and dApps can display asset metadata consistently without relying on off-chain registries.

### The Token ID Rule

The **Token ID rule** is a core protocol invariant: **a token's ID is always equal to the Box ID of the first input box in the minting transaction.** This is enforced at the consensus layer — you cannot fabricate a Token ID. Because a Box ID is a hash of the box's content and its creation context, Token IDs are globally unique and unforgeable. This is the mechanism that underpins NFT uniqueness on Ergo without requiring any additional smart-contract logic.

### When to Use This Pattern

| Scenario | Use EIP-4? |
|---|---|
| Launching a fungible token (DAO governance, reward token) | ✅ |
| Minting a unique NFT (art, game item, identity) | ✅ |
| Creating a **Singleton / State NFT** to guard a multi-stage contract | ✅ |
| Transferring existing tokens between boxes | ❌ (no minting involved) |
| Wrapping a native token with extra on-chain logic | Partial — mint first, then lock |

---

## How It Works

### 1. Understand the eUTXO Minting Invariant

In Ergo's eUTXO model, tokens are created according to a strict ledger rule:

> For every token that appears in the **outputs** of a transaction but not in the **inputs**, the token's ID **must equal the Box ID of the first input**.

This means:
- Only **one new token type** can be minted per transaction.
- The **amount** minted can be any value from `1` to `Long.MaxValue` (`9,223,372,036,854,775,807`).
- For an NFT, you mint exactly `1` unit.

### 2. Prepare the Metadata Registers

EIP-4 allocates the **non-mandatory Registers** R4–R8 on the minting output box for metadata:

| Register | Type | Content |
|---|---|---|
| **R4** | `Coll[Byte]` | Token name (UTF-8 encoded) |
| **R5** | `Coll[Byte]` | Token description (UTF-8 encoded) |
| **R6** | `Coll[Byte]` | Number of decimals (UTF-8 string of an integer, e.g. `"2"`) |
| **R7** | `Coll[Byte]` | *(NFT only)* Asset type tag |
| **R8** | `Coll[Byte]` | *(NFT only)* Checksum / content hash of the off-chain asset |

> **Registers must be densely packed.** You cannot set R6 without setting R4 and R5. The protocol rejects transactions where registers have gaps (e.g., R4 set but R5 skipped, then R6 set).

### 3. Build the Minting Output Box

The output box that receives the new tokens must:
1. Carry the full minted supply in its token list.
2. Hold at least the **Minimum box value** in nanoERG (currently `0.001 ERG` = `1,000,000` nanoERG) to be protected from **Storage rent** eviction.
3. Have its Registers set according to EIP-4.
4. Be assigned to the recipient's **ErgoTree** (the compiled guard script).

### 4. Select the First Input

Because the **Token ID** will equal the first input's Box ID, you must be deliberate about which UTxO occupies `input[0]`. Typically this is simply the largest available UTXO in the user's wallet, but in programmatic minting (e.g., a launchpad contract) you may need to pin a specific box.

### 5. Sign and Submit

The transaction is signed with the Sigma protocol proof for the input guards (usually a simple **proveDlog** / P2PK guard) and submitted to a node or via the Ergo Transaction API.

### Flow Diagram

```
Wallet UTxOs
     │
     ▼
[Input Box 0]  ← Box ID becomes Token ID
[Input Box 1]  (optional, for fee coverage)
     │
     │  Transaction
     ▼
[Output Box 0] ← minting box
  value: ≥ minBoxValue nanoERG
  tokens: [(newTokenId, amount)]
  R4: name bytes
  R5: description bytes
  R6: decimals bytes
  R7: asset type (NFT only)
  R8: content hash (NFT only)
[Output Box 1] ← change box (ERG remainder)
```

---

## Implementation

### TypeScript — Fleet SDK

Fleet SDK (`@fleet-sdk/core`) is the primary TypeScript/JavaScript library for building Ergo transactions. Its `OutputBuilder` has first-class support for EIP-4 minting via the `.mintToken()` method.

#### Installation

```bash
npm install @fleet-sdk/core
# or
yarn add @fleet-sdk/core
```

#### Fungible Token Minting

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
  SConstant,
  SColl,
  SByte
} from "@fleet-sdk/core";

/**
 * Mint a fungible EIP-4 token.
 *
 * @param inputs       - UTxOs owned by the sender (first input provides the Token ID)
 * @param recipientErgoTree - ErgoTree hex of the recipient
 * @param creationHeight - Current blockchain height
 */
function mintFungibleToken(
  inputs: Array<{ boxId: string; value: bigint; ergoTree: string }>,
  recipientErgoTree: string,
  creationHeight: number
) {
  // ── 1. Describe the new token ────────────────────────────────────────────
  //
  // NewToken<bigint> from fleet's token.ts:
  //   tokenId?    – omit here; Fleet derives it from inputs[0].boxId
  //   name?       – UTF-8 display name
  //   decimals?   – number of decimal places for UI display
  //   description?– human-readable description
  //
  const mintingBox = new OutputBuilder(
    SAFE_MIN_BOX_VALUE, // minimum nanoERG to prevent Storage rent eviction
    recipientErgoTree,
    creationHeight
  ).mintToken({
    amount: 1_000_000n,      // total supply (bigint enforced by Fleet)
    name: "MyToken",
    decimals: 2,             // UI: 1_000_000 raw = 10,000.00 display units
    description: "A fungible EIP-4 token example"
  });
  // Fleet internally encodes name → R4, description → R5, decimals → R6
  // as Coll[Byte] (SigmaProp serialisation of UTF-8 byte arrays).

  // ── 2. Build the transaction ─────────────────────────────────────────────
  const unsignedTx = new TransactionBuilder(creationHeight)
    .from(inputs)                           // inputs[0].boxId → Token ID
    .to(mintingBox)
    .sendChangeTo(recipientErgoTree)        // ERG change
    .payFee(RECOMMENDED_MIN_FEE_VALUE)      // 0.001 ERG minimum transaction fee
    .build();

  return unsignedTx;
}
```

#### NFT Minting (Picture NFT — EIP-4 Type 0x01)

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
  SConstant,
  SColl,
  SByte,
  SInt
} from "@fleet-sdk/core";

/**
 * Asset type tags defined in EIP-4:
 *  0x01 0x01 → Picture NFT  (JPEG/PNG/etc.)
 *  0x01 0x02 → Audio NFT
 *  0x01 0x03 → Video NFT
 *  0x02 0x01 → Membership NFT (threshold signature)
 */
const PICTURE_NFT_TYPE = Uint8Array.from([0x01, 0x01]);

/**
 * Mint a picture NFT following EIP-4.
 *
 * @param contentHash - SHA-256 hash of the off-chain image as a hex string
 */
function mintPictureNFT(
  inputs: Array<{ boxId: string; value: bigint; ergoTree: string }>,
  recipientErgoTree: string,
  creationHeight: number,
  contentHash: string // 32-byte SHA-256 hex
) {
  const contentHashBytes = Uint8Array.from(
    Buffer.from(contentHash, "hex")
  );

  const mintingBox = new OutputBuilder(
    SAFE_MIN_BOX_VALUE,
    recipientErgoTree,
    creationHeight
  )