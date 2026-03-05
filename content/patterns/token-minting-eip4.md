---
title: Token minting (EIP-4)
description: Token minting (EIP-4) — NFT and fungible token issuance, metadata registers, Token ID rule
tags: [token-minting-eip4, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [fleet-sdk/fleet, fleet-sdk/fleet-by-example, arkadianet/citadel, LiliumErgo/scala-api]
---
# Developer Guide: Token Minting (EIP-4) on Ergo

## Overview

EIP-4 defines the **standard for token issuance on Ergo** — covering both fungible tokens (FTs) and non-fungible tokens (NFTs). It specifies how metadata is stored in **Registers**, how the **Token ID rule** binds a token's identity to a specific UTXO, and how wallets and dApps interpret on-chain token data.

### Why It Exists

Ergo's **Native tokens** are first-class citizens of the eUTXO model — they live inside **Boxes** alongside ERG, not in separate contracts. However, the base protocol only tracks `(tokenId, amount)` pairs. EIP-4 layers a **metadata convention** on top, using a Box's Registers (R4–R9) to attach human-readable names, descriptions, decimal precision, and asset type information.

Without EIP-4, wallets and indexers have no agreed way to display "ERGODEX" vs a raw 64-character hex ID.

### When to Use It

| Use Case | Pattern |
|---|---|
| Launch a DAO governance token | Fungible token with decimals |
| Issue a unique artwork or collectible | NFT (amount = 1, no decimals) |
| Create a **Singleton / State NFT** for a multi-stage contract | NFT with amount = 1, used as a contract anchor |
| Issue game items with supply > 1 but no fractions | Semi-fungible / collection token |
| Bootstrap a DEX liquidity pool token | Fungible token with known supply |

---

## How It Works

### The Token ID Rule

The **Token ID rule** is the protocol-level guarantee that makes token issuance trustless:

> **A token's ID is always equal to the Box ID of the first input in the minting transaction.**

This is enforced by the Ergo node consensus, not by a contract. It means:
- Token IDs are globally unique (Box IDs are globally unique).
- No one can mint a second batch under the same Token ID after the first input UTXO is spent.
- To re-issue more supply, you must mint a *new* token with a *new* Token ID.

### The Minting Transaction Structure

```
┌─────────────────────────────────────┐
│  INPUTS                             │
│  [0] Funding Box (UTxO to spend)    │  ← Box ID becomes Token ID
│  [1..n] Additional inputs (optional)│
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  OUTPUTS                            │
│  [0] Minting Box                    │
│      • tokens: [(TokenId, amount)]  │
│      • R4: name (Coll[Byte])        │
│      • R5: description (Coll[Byte]) │
│      • R6: decimals (Coll[Byte])    │
│      • R7: asset type (optional)    │
│      • R8: artwork data (optional)  │
│      • R9: artwork hash (optional)  │
│  [1] Change Box (ERG remainder)     │
└─────────────────────────────────────┘
```

### Step-by-Step Flow

1. **Select a UTXO** from the wallet. Its Box ID will become the Token ID.
2. **Build the output Box** with:
   - A token entry `(inputBoxId, desiredAmount)`
   - EIP-4 metadata in Registers R4–R9
3. **Include the Minimum box value** of ERG (currently 0.001 ERG) to satisfy **Storage rent** dust rules.
4. **Sign** the transaction with the spending key for the input UTXO.
5. **Submit** to the Ergo network. Once confirmed, the Token ID is permanently established.

### EIP-4 Register Layout

| Register | Type | Purpose |
|---|---|---|
| R4 | `Coll[Byte]` | Token name (UTF-8) |
| R5 | `Coll[Byte]` | Token description (UTF-8) |
| R6 | `Coll[Byte]` | Number of decimals as UTF-8 string (e.g., `"2"`) |
| R7 | `Coll[Byte]` | Asset type (e.g., `"001"` = picture, `"002"` = audio) |
| R8 | `Coll[Byte]` | Content bytes or IPFS link |
| R9 | `Coll[Byte]` | SHA-256 hash of content |

> **Registers must be densely packed.** You cannot set R6 without also setting R4 and R5. The `areRegistersDenselyPacked` check in fleet-sdk enforces this.

---

## Implementation

### TypeScript — fleet-sdk

The [fleet-sdk](https://github.com/fleet-sdk/fleet) `OutputBuilder` provides a first-class `mintToken()` API that handles the Token ID rule automatically.

#### 1. Install dependencies

```bash
npm install @fleet-sdk/core @fleet-sdk/common
```

#### 2. Mint a Fungible Token

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
  ErgoAddress
} from "@fleet-sdk/core";

/**
 * Mints a fungible token following EIP-4.
 *
 * The Token ID is automatically derived from inputs[0].boxId by fleet-sdk.
 * Registers R4, R5, R6 are set from the NewToken metadata fields.
 */
async function mintFungibleToken(
  inputs: Box<bigint>[],     // Wallet UTXOs — inputs[0].boxId becomes Token ID
  changeAddress: string,
  height: number
) {
  const unsignedTx = new TransactionBuilder(height)
    .from(inputs)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, ErgoAddress.fromBase58(changeAddress))
        .mintToken({
          // tokenId is intentionally omitted — fleet derives it from inputs[0]
          amount: 1_000_000n,   // Total supply (raw, before decimals)
          name: "MyToken",
          decimals: 2,          // Stored as UTF-8 "2" in R6
          description: "A fungible token following EIP-4"
        })
    )
    .sendChangeTo(changeAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}
```

#### 3. Mint an NFT (amount = 1, decimals = 0)

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  ErgoAddress,
  SColl,
  SByte,
  stringify
} from "@fleet-sdk/core";

/**
 * Mints an EIP-4 NFT with artwork metadata.
 * R7 = "001" signals a picture NFT to wallets/marketplaces.
 */
async function mintNFT(
  inputs: Box<bigint>[],
  changeAddress: string,
  height: number,
  artworkIpfsUrl: string,
  artworkSha256Hex: string   // 32-byte SHA-256 of the artwork content
) {
  // Convert hex string to Uint8Array for register encoding
  const hashBytes = Uint8Array.from(
    Buffer.from(artworkSha256Hex, "hex")
  );

  const unsignedTx = new TransactionBuilder(height)
    .from(inputs)
    .to(
      new OutputBuilder(
        SAFE_MIN_BOX_VALUE,
        ErgoAddress.fromBase58(changeAddress)
      )
        .mintToken({
          amount: 1n,                  // NFT: exactly 1 token
          name: "My NFT Artwork",
          decimals: 0,
          description: "A unique digital artwork on Ergo"
        })
        // R7: asset type "001" = picture (per EIP-4 spec)
        .setAdditionalRegisters({
          R7: SColl(SByte, Buffer.from("001", "utf-8")).toHex(),
          R8: SColl(SByte, Buffer.from(artworkIpfsUrl, "utf-8")).toHex(),
          R9: SColl(SByte, hashBytes).toHex()
        })
    )
    .sendChangeTo(changeAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}
```

#### 4. Mint a Singleton / State NFT for a Multi-Stage Contract

A **Singleton NFT** is an NFT whose Token ID is used as the persistent identity of a contract's state box. The contract's ErgoScript checks that this token is present in the self box to authenticate the state.

```typescript
/**
 * Mints a Singleton NFT intended to live in a contract's state box forever.
 * The tokenId returned must be hardcoded into the contract's ErgoScript.
 */
async function mintSingletonNFT(
  inputs: Box<bigint>[],
  contractErgoTree: string,  // The multi-stage contract's ErgoTree
  changeAddress: string,
  height: number
) {
  // The Token ID will be inputs[0].boxId after signing
  const predictedTokenId = inputs[0].boxId;
  console.log("Predicted Singleton Token ID:", predictedTokenId);

  const unsignedTx = new TransactionBuilder(height)
    .from(inputs)
    .to(
      // Output goes directly to the contract address, not the wallet
      new OutputBuilder(SAFE_MIN_BOX_VALUE, contractErgoTree)
        .mintToken({
          amount: 1n,
          name: "ContractStateNFT",
          decimals: 0,
          description: