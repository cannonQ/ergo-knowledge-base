---
title: Transaction building
description: Transaction building — Fleet SDK + AppKit patterns, box selection, fee handling, token ops
tags: [transaction-building, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [fleet-sdk/fleet, fleet-sdk/fleet-by-example, arkadianet/citadel, ergoplatform/ergo-appkit]
---
# Developer Guide: Transaction Building with Fleet SDK & AppKit

## Overview

Ergo's **eUTXO** (extended Unspent Transaction Output) model treats every **Box** as a first-class citizen: each box carries a value in nanoERGs, zero or more **Native tokens**, up to ten **Registers** (R0–R9), and an **ErgoTree** (the compiled form of an **ErgoScript** guard script). A transaction consumes one or more input boxes and produces one or more output box candidates. Nothing is "sent" — boxes are destroyed and new ones are created.

This guide covers the two dominant transaction-building stacks in the Ergo ecosystem:

| Stack | Language | Best for |
|---|---|---|
| **Fleet SDK** (`@fleet-sdk/core`) | TypeScript / JavaScript | Front-ends, bots, off-chain dApps |
| **AppKit** (`ergo-appkit`) | JVM (Scala / Java / Kotlin) | Back-end services, node plug-ins |

You will need both patterns when you build a full dApp: Fleet in the browser/node process that assembles and signs, AppKit in any JVM service that submits or verifies.

**When to use this pattern:**

- Transferring ERG or tokens between addresses
- Minting or burning **Native tokens**
- Interacting with **Multi-stage contracts** (spending a **Singleton / State NFT** box)
- Building atomic-swap transactions
- Any situation where you need precise control over **box selection**, **fee handling**, **Storage rent** compliance, and register packing

---

## How It Works

### 1. Gather Input Boxes

The transaction builder must know which boxes it can consume. Boxes come from:

- A node `/utxo/byAddress` or `/utxo/withPool` query
- An indexer (Explorer API, Spectrum, Nautilus backend)
- Hard-coded test vectors

Box selection is **greedy by default** in Fleet: the selector accumulates boxes until the total nanoERG value covers outputs + fee + any token requirements.

### 2. Define Output Box Candidates

Each output specifies:

- **Value** – in nanoERGs, must be ≥ `SAFE_MIN_BOX_VALUE` (1 000 000 nanoERG = 0.001 ERG) or the dynamically estimated minimum (see `estimateMinBoxValue`).
- **ErgoTree / Address** – the locking script for the new box.
- **Tokens** – a `TokensCollection` mapping Token ID → amount.
- **Registers** – R4–R9 packed in strict ascending order (packing gaps are a consensus error).
- **Creation height** – must be ≤ the current block height and > 0.

### 3. Handle the Fee Box

The **Minimum transaction fee** (currently `RECOMMENDED_MIN_FEE_VALUE = 1 100 000` nanoERG) must be paid to the fee address (`ErgoFeeContract`). Fleet's `TransactionBuilder.payMinFee()` / `.payFee(n)` handles this automatically by emitting a dedicated fee output.

### 4. Change Box

After selecting inputs the builder computes:

```
change = Σ(inputs.value) − Σ(outputs.value) − fee
```

Leftover tokens not present in any output are either routed to the change box or — if you explicitly call `.burnTokens()` — subtracted from the consumed total. **Burning without permission throws `NotAllowedTokenBurning`.**

### 5. Build → Sign → Submit

```
UnsignedTransaction  ──sign──▶  SignedTransaction  ──submit──▶  mempool
```

Fleet produces a plain JS object (`EIP-12`-compatible); signing is delegated to a wallet connector (Nautilus, SAFEW) or a `Prover` (AppKit / `ergo-lib-wasm`).

### Storage Rent Compliance

Any box that remains unspent for **1 052 060 blocks** (~4 years) enters the **Storage rent** period and can be "swept" by miners who deduct 0.13 ERG per sweep cycle. Your fee/change logic must ensure boxes carry enough ERG so they are never swept prematurely.

---

## Implementation

### Fleet SDK — TypeScript

#### 1. Basic ERG Transfer

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,   // re-exported from @fleet-sdk/common
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

/** boxes fetched from /utxo/byAddress or an indexer */
const inputBoxes: Box<Amount>[] = await fetchBoxes(senderAddress);

const unsignedTx = new TransactionBuilder(currentHeight)
  .from(inputBoxes)                        // candidate input pool
  .to(
    new OutputBuilder(
      SAFE_MIN_BOX_VALUE,                  // value in nanoERG
      recipientAddress,                    // base58 P2PK or P2S
      currentHeight                        // creation height
    )
  )
  .sendChangeTo(senderAddress)             // change box address
  .payMinFee()                             // appends fee box automatically
  .build();

// unsignedTx is an EIP-12 UnsignedTransaction object
console.log(unsignedTx.inputs.length);     // selected input count
console.log(unsignedTx.outputs.length);    // outputs + change + fee
```

#### 2. Token Transfer

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";

const TOKEN_ID =
  "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04";

const unsignedTx = new TransactionBuilder(currentHeight)
  .from(inputBoxes)
  .to(
    new OutputBuilder(SAFE_MIN_BOX_VALUE, recipientAddress, currentHeight)
      .addTokens({
        tokenId: TOKEN_ID,
        amount: BigInt(100),               // token amount (no decimals, raw)
      })
  )
  .sendChangeTo(senderAddress)
  .payMinFee()
  .build();
```

> **Token ID rule**: a token's ID is always the box ID of the box in which it was *first minted*. You cannot choose an arbitrary ID.

#### 3. Token Minting (EIP-4 Standard)

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";

// The FIRST input box ID becomes the new Token ID
const mintingBoxId = inputBoxes[0].boxId;

const unsignedTx = new TransactionBuilder(currentHeight)
  .from(inputBoxes)
  .to(
    new OutputBuilder(SAFE_MIN_BOX_VALUE, senderAddress, currentHeight)
      .mintToken(
        {
          tokenId: mintingBoxId,           // must equal first input's box ID
          amount: BigInt(1_000_000),
        },
        {
          name: "MyToken",
          description: "A fungible token",
          decimals: 2,
          // stored in R4–R6 per EIP-4
        }
      )
  )
  .sendChangeTo(senderAddress)
  .payMinFee()
  .build();
```

#### 4. Token Burning

```typescript
const unsignedTx = new TransactionBuilder(currentHeight)
  .from(inputBoxes)
  .to(
    new OutputBuilder(SAFE_MIN_BOX_VALUE, recipientAddress, currentHeight)
  )
  .burnTokens({                            // explicit permission required
    tokenId: TOKEN_ID,
    amount: BigInt(50),
  })
  .sendChangeTo(senderAddress)
  .payMinFee()
  .build();
```

Without `.burnTokens()`, any unaccounted token in the inputs throws `NotAllowedTokenBurning`. This is a **safety net** — accidental burns are caught at build time, not on-chain.

#### 5. Registers and Contract Interaction

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";
import { SByte, SColl, SInt, SLong } from "@fleet-sdk/serializer";

// Interacting with a Multi-stage contract — spending a Singleton / State NFT box
const contractBox: Box<Amount> = await fetchContractBox(contractAddress);

const unsignedTx = new TransactionBuilder(currentHeight)
  .from([...userBoxes, contractBox])       // contract box is an input
  .to(
    // Re-create the contract box with updated state
    new OutputBuilder(contractBox.value, contractAddress, currentHeight)
      .addTokens(contractBox.assets)       // preserve Singleton NFT
      .setAdditionalRegisters({
        R4: SInt(42).toHex(),              // packed in strict R4→R9 order
        R5: SLong(BigInt(1_000_000)).toHex(),
        R6: SColl(SByte, [0x01, 0x02, 0x03]).toHex(),
      })
  )
  .to(
    new OutputBuilder(SAFE_MIN_BOX_VALUE, userAddress, currentHeight)
  )
  .sendChangeTo(userAddress)
  .payMinFee()
  .build();
```

> **Registers must be packed without gaps**: if you skip R5 and set R6, the transaction is invalid. Fleet throws `InvalidRegistersPacking` at build time.

#### 6. Custom Box Selection & Fee Estimation

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  estimateMinBoxValue,
  BOX_VALUE_PER_BYTE,
  SAFE_MIN_BOX_