---
title: Transaction building
description: Transaction building — Fleet SDK + AppKit patterns, box selection, fee handling, token ops
tags: [transaction-building, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [fleet-sdk/fleet, fleet-sdk/fleet-by-example, arkadianet/citadel, ergoplatform/ergo-appkit]
---
# Developer Guide: Transaction Building with Fleet SDK and AppKit

## Overview

Ergo's **eUTXO model** treats every on-chain value container as a **Box** — an immutable, typed record holding ERG (in nanoERGs), **Native tokens**, **Registers** (R0–R9), and an **ErgoTree** (the compiled form of an **ErgoScript** spending condition). Unlike account-based chains, spending a box *destroys* it entirely; a transaction consumes one or more input boxes and creates one or more output boxes. This architecture enables **Multi-stage contracts**, **Atomic swaps**, **Singleton/State NFT** patterns, and sophisticated **Sigma protocols** natively, without requiring layer-2 machinery.

**Transaction building** is the craft of assembling those inputs and outputs correctly so that:

- Every nanoERG and token is accounted for (conservation law)
- Every output meets the **Minimum box value** (storage-rent economic floor)
- The network fee is explicit and valid
- Token minting, burning, and transfers satisfy the **Token ID rule**
- Register packing order is respected
- The resulting `UnsignedTransaction` can be signed and broadcast

Two primary SDKs cover this surface:

| SDK | Language | Ideal for |
|-----|----------|-----------|
| **Fleet SDK** (`fleet-sdk/fleet`) | TypeScript/JavaScript | Browser wallets, dApps, Node.js backends |
| **AppKit** (`ergoplatform/ergo-appkit`) | Scala/Java/Kotlin | JVM services, node plugins, Scala smart contracts |

Both SDKs expose the same conceptual pipeline; this guide teaches both with runnable examples and explains where they diverge.

---

## How It Works

### The eUTXO Transaction Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│                     TRANSACTION BUILDING FLOW                    │
│                                                                  │
│  1. COLLECT INPUTS                                               │
│     Query unspent boxes (UTXOs) from node/explorer               │
│     Select boxes covering ERG + token requirements               │
│                                                                  │
│  2. DEFINE OUTPUTS                                               │
│     Specify recipient ErgoTree / address                         │
│     Set value (≥ minimum box value)                              │
│     Attach tokens, register data                                 │
│                                                                  │
│  3. HANDLE CHANGE                                                │
│     ERG change → change box back to sender                       │
│     Token change → same change box or dedicated box              │
│                                                                  │
│  4. FEE BOX                                                      │
│     Special output with miner's ErgoTree                         │
│     Value ≥ RECOMMENDED_MIN_FEE_VALUE (1_100_000 nanoERG)        │
│                                                                  │
│  5. VALIDATE                                                      │
│     Conservation: ΣinputERG = ΣoutputERG + fee                   │
│     Token conservation / minting / burning rules                 │
│     Minimum box value per output                                  │
│     Register packing (no gaps R4→R5→R6…)                         │
│                                                                  │
│  6. SIGN & BROADCAST                                             │
│     Wallet signs with Schnorr / Sigma proofs                     │
│     Serialised transaction → node /transactions endpoint         │
└──────────────────────────────────────────────────────────────────┘
```

### Box Selection Algorithm

Fleet SDK's `BoxSelector` implements a **first-fit descending** heuristic:

1. Sort available boxes by ERG value descending.
2. Iterate until accumulated ERG + tokens cover the target.
3. Add additional boxes for any uncovered token IDs.
4. Return the minimal covering set.

The selector is pluggable — you can supply a custom comparator or filter (e.g., exclude boxes below a dust threshold, or prefer boxes carrying a specific token).

### The Token ID Rule

When a transaction mints a new token, the **Token ID** *must equal* the **Box ID of the first input box**. This rule is enforced at the consensus layer; no minting is possible without consuming the designated input. It guarantees global uniqueness of all Token IDs and makes **Singleton/State NFTs** (quantity = 1) trivially verifiable.

### Storage Rent

Boxes that remain unspent for ~4 years (≈1,051,200 blocks) accumulate a storage-rent obligation. Miners can reclaim nanoERGs from such boxes to cover rent. The `SAFE_MIN_BOX_VALUE` / `estimateMinBoxValue` helpers in Fleet SDK ensure your outputs carry enough ERG to survive economically, avoiding premature reclamation.

### Minimum Box Value Derivation

```
minValue = estimatedSizeInBytes × BOX_VALUE_PER_BYTE
         = estimatedSizeInBytes × 360 nanoERG/byte
```

Fleet exports both a constant (`SAFE_MIN_BOX_VALUE = 1_000_000n`) and a dynamic estimator (`estimateMinBoxValue`) that measures the serialised size of the `OutputBuilder`'s current state.

---

## Implementation

### Fleet SDK (TypeScript)

#### 1. Basic ERG Transfer

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

/**
 * Build a simple ERG transfer transaction.
 *
 * @param inputs     - Unspent boxes owned by the sender (fetched from node/explorer)
 * @param recipient  - Base58-encoded Ergo address of the recipient
 * @param amount     - Amount in nanoERG (BigInt)
 * @param changeAddr - Sender's address for ERG/token change
 * @param height     - Current blockchain height (creationHeight for outputs)
 */
function buildTransfer(
  inputs: Box<Amount>[],
  recipient: string,
  amount: bigint,
  changeAddr: string,
  height: number
) {
  const unsignedTx = new TransactionBuilder(height)
    // ① Supply the unspent boxes; Fleet will select the minimum covering set
    .from(inputs)
    // ② Define the recipient output
    .to(
      new OutputBuilder(amount, recipient)
      // No explicit creation height needed here; TransactionBuilder injects it
    )
    // ③ Automatically build a fee box with the recommended minimum fee
    //    (1_100_000 nanoERG as of EIP-0016)
    .payMinFee()
    // ④ Send leftover ERG (and any unspent tokens) back to sender
    .sendChangeTo(changeAddr)
    // ⑤ Produce the unsigned transaction object
    .build();

  return unsignedTx;
}
```

**What `build()` does internally:**

1. Runs `BoxSelector` over `inputs` to cover `amount + fee`.
2. Injects `creationHeight` from the builder's height parameter into every `OutputBuilder`.
3. Assembles fee and change outputs.
4. Validates ERG conservation and register packing.
5. Returns a plain-object `UnsignedTransaction` (JSON-serialisable).

---

#### 2. Token Transfer

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

const TOKEN_ID =
  "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04"; // arbitrary example

function buildTokenTransfer(
  inputs: Box<Amount>[],
  recipient: string,
  tokenAmount: bigint,
  changeAddr: string,
  height: number
) {
  return new TransactionBuilder(height)
    .from(inputs)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, recipient)
        // Attach token to the output; Fleet validates conservation automatically
        .addTokens({ tokenId: TOKEN_ID, amount: tokenAmount })
    )
    .payMinFee()
    .sendChangeTo(changeAddr)
    .build();
}
```

> **Key point:** The ERG value of a token-carrying output must still satisfy `minBoxValue`. Use `SAFE_MIN_BOX_VALUE` (1 000 000 nanoERG) as a safe lower bound, or `estimateMinBoxValue()` for a tighter estimate based on actual serialised size.

---

#### 3. Token Minting (EIP-0004 Standard)

EIP-0004 defines the register layout for fungible tokens and NFTs. Fleet SDK's `mintToken` helper enforces this layout automatically.

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

/**
 * Mint a new EIP-0004-compliant fungible token.
 *
 * The Token ID will equal the Box ID of the first selected input —
 * this is the Token ID Rule enforced by Ergo's consensus layer.
 */
function mintFungibleToken(
  inputs: Box<Amount>[],
  mintingAddress: string,
  changeAddr: string,
  height: number
) {
  return new TransactionBuilder(height)
    .from(inputs)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, mintingAddress)
        .mintToken({
          // amount: total supply (all decimals included — no floating point)
          amount: 1_000_000n,
          name: "MyToken",
          description: "A Fleet SDK minted token",
          // decimals stored in R7 per EIP-0004; display only, not enforced on-chain
          decimals: 2,
        