---
title: Transaction building
description: Transaction building — Fleet SDK + AppKit patterns, box selection, fee handling, token ops
tags: [transaction-building, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [fleet-sdk/fleet, fleet-sdk/fleet-by-example, arkadianet/citadel, ergoplatform/ergo-appkit]
---
# Developer Guide: Transaction Building with Fleet SDK & AppKit

## Overview

Ergo's extended UTXO (eUTXO) model treats every on-chain value store as a **Box** — a first-class object containing ERG value, **Native tokens**, typed **Registers** (R0–R9), a guarding **ErgoTree** (compiled **ErgoScript**), and a creation height. Unlike account-based chains, there is no mutable state: every transaction consumes input Boxes and creates new output Boxes, with the chain's validity rules enforced entirely by ErgoScript predicates evaluated inside a **Sigma protocols** framework.

This guide covers the two dominant transaction-building ecosystems:

| SDK | Language | Primary use-case |
|---|---|---|
| **Fleet SDK** | TypeScript / JavaScript | Browser, Node.js, dApp front-ends |
| **AppKit** | Scala / Java / Kotlin | JVM back-ends, bots, tooling |

You need this pattern whenever you must:

- Select input Boxes from a wallet or contract address (box selection)
- Assemble output Box candidates with correct ERG values, tokens, and Register contents
- Apply the **Minimum box value** and **Minimum transaction fee** rules
- Mint, transfer, or burn **Native tokens** following the **Token ID rule**
- Handle change outputs and **Storage rent** implications
- Integrate contract-level interactions such as **Multi-stage contracts** or **Singleton / State NFT** patterns

---

## How It Works

### 1. Gather context

Before building anything you need:

- Current blockchain **height** (used as `creationHeight` on every output Box)
- The full UTXO set of the spending address (raw Box objects with all fields populated)
- The ErgoTree or address of each recipient

### 2. Select input Boxes

Box selection must satisfy two constraints simultaneously:

1. **Value coverage** — total ERG in selected inputs ≥ sum of all output values + fee
2. **Token coverage** — every token that appears in outputs (and is not being minted) must exist in inputs

Fleet SDK ships a `BoxSelector` with configurable strategies (simple, target-value, etc.). AppKit's `BoxOperations` provides similar utilities.

### 3. Build output Box candidates

For each output you specify:

- ERG value (must be ≥ **Minimum box value** which is derived from box byte size at 360 nanoERG/byte)
- Optional token list
- Optional Register values (R4–R9; R0–R3 are protocol-reserved)
- An ErgoTree (recipient address compiles to one)
- Creation height

### 4. Attach the fee output

The miner fee output is a special Box whose ErgoTree matches the canonical fee ErgoTree (`1005040004000e36100204a00b08cd…`). The **Minimum transaction fee** (`RECOMMENDED_MIN_FEE_VALUE`) is 1 000 000 nanoERG (0.001 ERG), but complex transactions or those with many inputs/outputs warrant higher fees.

### 5. Add a change output

Any ERG and tokens left after outputs + fee are returned to the sender in a change Box. Fleet's `TransactionBuilder.sendChangeTo()` automates this. Forgetting this step causes `MalformedTransaction` errors or, worse, silently donates value to miners.

### 6. Sign and submit

The unsigned transaction is handed to the wallet (Nautilus, Eternl-Ergo, etc. via EIP-0012) or to an AppKit `Prover`. The signed transaction is broadcast via a node's `/transactions` endpoint.

---

## Implementation

### Fleet SDK (TypeScript)

#### Installation

```bash
npm install @fleet-sdk/core @fleet-sdk/common
# Optional plugins
npm install @fleet-sdk/babel-fees-plugin
```

#### Core types and constants

```typescript
// @fleet-sdk/core re-exports these; understanding them is essential
import {
  RECOMMENDED_MIN_FEE_VALUE, // 1_000_000n nanoERG
  type Box,
  type Amount,
  type TokenAmount,
} from "@fleet-sdk/common";

import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,   // 1_000_000n nanoERG — practical minimum for simple boxes
  BOX_VALUE_PER_BYTE,   // 360n nanoERG/byte — used for dynamic estimation
  estimateMinBoxValue,  // factory: returns a callback that measures the built box
  ErgoAddress,
  ErgoTree,
} from "@fleet-sdk/core";
```

#### Basic ERG transfer

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

/**
 * Build an unsigned ERG transfer transaction.
 *
 * @param inputs     - UTXOs owned by the sender (fetched from node/explorer)
 * @param recipient  - Base58-encoded Ergo address
 * @param amount     - Amount in nanoERG (bigint)
 * @param senderAddr - Base58-encoded sender address (receives change)
 * @param height     - Current blockchain height
 */
function buildTransfer(
  inputs: Box<Amount>[],
  recipient: string,
  amount: bigint,
  senderAddr: string,
  height: number
) {
  const unsignedTx = new TransactionBuilder(height)
    .from(inputs)                          // register input boxes
    .to(
      new OutputBuilder(amount, recipient) // output box candidate
    )
    .sendChangeTo(senderAddr)              // change output (ERG + unspent tokens)
    .payMinFee()                           // attaches fee box at RECOMMENDED_MIN_FEE_VALUE
    .build();                              // returns EIP-0012 UnsignedTransaction

  return unsignedTx;
}
```

#### Dynamic minimum box value estimation

The **Minimum box value** rule (360 nanoERG × serialized-byte-size) means boxes carrying tokens or large Register values cost more than bare ERG boxes.

```typescript
import { OutputBuilder, estimateMinBoxValue } from "@fleet-sdk/core";

// estimateMinBoxValue() returns a callback; OutputBuilder evaluates it lazily
// after all tokens and registers have been added.
const output = new OutputBuilder(
  estimateMinBoxValue(), // ← dynamic: measured after build
  recipientAddress,
  height
)
  .addTokens({ tokenId: "abc123...", amount: 1n })
  .setAdditionalRegisters({
    R4: "0e0568656c6c6f", // SBytes "hello" (serialised constant)
  });

// To inspect the estimated value before building:
// output.estimateSize() * BOX_VALUE_PER_BYTE
```

#### Native token transfer

Tokens in Ergo are identified solely by the **Token ID** — the Box ID of the transaction that minted them (**Token ID rule**). There is no separate contract; tokens live inside Boxes.

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";

function buildTokenTransfer(
  inputs: Box<Amount>[],
  recipient: string,
  tokenId: string,
  tokenAmount: bigint,
  senderAddr: string,
  height: number
) {
  return new TransactionBuilder(height)
    .from(inputs)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, recipient)
        .addTokens({ tokenId, amount: tokenAmount })
    )
    .sendChangeTo(senderAddr) // returns leftover tokens automatically
    .payMinFee()
    .build();
}
```

#### Token minting (EIP-0004 standard)

Token minting in Ergo requires the new token's ID to equal the Box ID of the **first input** (**Token ID rule**). Fleet's `OutputBuilder.mintToken()` enforces this context requirement.

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";

function buildMint(
  inputs: Box<Amount>[],
  senderAddr: string,
  height: number
) {
  return new TransactionBuilder(height)
    .from(inputs)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, senderAddr)
        .mintToken(
          {
            amount: 1_000_000n,        // total supply
          },
          {
            // EIP-0004 metadata stored in R4–R6
            name: "MyToken",
            description: "A test token",
            decimals: 2,
          }
        )
    )
    .sendChangeTo(senderAddr)
    .payMinFee()
    .build();
  // Note: calling mintToken() without a TransactionBuilder that can resolve
  // the first-input box ID throws UndefinedMintingContext
}
```

#### Token burning

By default Fleet **forbids** token burning to prevent accidental loss. Explicit opt-in is required:

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";

function buildBurn(
  inputs: Box<Amount>[],   // must contain the tokens to burn
  tokenId: string,
  burnAmount: bigint,
  senderAddr: string,
  height: number
) {
  return new TransactionBuilder(height)
    .from(inputs)
    .burnTokens({ tokenId, amount: burnAmount }) // explicit burn declaration
    .sendChangeTo(senderAddr)
    .payMinFee()
    .build();
}
```

#### Using registers for contract interaction

Registers R4–R9 store typed **ErgoScript** constants. Pass serialized hex-encoded `SType` values:

```typescript
import { OutputBuilder, SAFE_MIN_BOX_VALUE, SConstant, SColl, SByte }