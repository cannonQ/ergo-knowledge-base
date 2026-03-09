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
# Developer Guide: Transaction Building with Fleet SDK and AppKit

## Overview

Ergo's **eUTXO** (extended Unspent Transaction Output) model means every on-chain interaction is expressed as a *transaction* that consumes one or more **Boxes** as inputs and produces one or more Boxes as outputs. Unlike account-based chains, there is no mutable state: every output is a self-contained value container carrying ERG, **Native tokens**, and up to ten **Registers** (R0–R9), protected by an **ErgoTree** (the compiled form of **ErgoScript**).

This pattern covers the full lifecycle of constructing, balancing, and signing Ergo transactions using two complementary SDKs:

| SDK | Language | Primary Use |
|---|---|---|
| **Fleet SDK** (`fleet-sdk/fleet`) | TypeScript / JavaScript | Browser, Node.js, dApp frontends |
| **AppKit** (`ergoplatform/ergo-appkit`) | Scala / Java (JVM) | Backend services, bots, full-node integrations |

### Why This Pattern Exists

Ergo transactions have strict ledger rules that go beyond "send value":

- Every output Box must hold at least the **Minimum box value** (storage rent parameterised as `BOX_VALUE_PER_BYTE × estimated_size`)
- A fixed **Minimum transaction fee** (conventionally `1,000,000 nanoERG = 0.001 ERG`) must be paid to miners
- **Storage rent** (4 ERG per four years per box) is enforced at the consensus layer — outputs that do not carry enough ERG will eventually be claimed
- **Native tokens** follow the **Token ID rule**: a token can only be created in a transaction where at least one input box ID matches the token's ID (first-mint rule); subsequent transfers simply move the token
- **Box selection** (coin selection) must cover both the ERG value of all outputs *and* the fee, without accidentally burning tokens

### When to Use It

- Building simple transfers (ERG, tokens)
- Minting new **Native tokens** or **Singleton / State NFTs**
- Interacting with **Multi-stage contracts** (chaining transactions)
- Implementing **Atomic swaps**
- Constructing transactions that consume **Data inputs** (read-only boxes used by **ErgoScript** for oracle prices, parameters, etc.)
- Any scenario requiring custom **Registers**, **Context extension** variables, or **Sigma protocols**

---

## How It Works

### High-Level Flow

```
┌─────────────────────────────────────────────────────┐
│  1. Gather UTXOs (box selection)                    │
│     - fetch unspent boxes for the sender address    │
│     - select enough boxes to cover outputs + fee    │
├─────────────────────────────────────────────────────┤
│  2. Build outputs (OutputBuilder / UnsignedTx)      │
│     - set ERG value (≥ minimum box value)           │
│     - attach tokens                                  │
│     - populate Registers R4–R9                      │
│     - set ErgoTree / recipient address               │
├─────────────────────────────────────────────────────┤
│  3. Add fee output                                  │
│     - standard fee box to miner fee address         │
├─────────────────────────────────────────────────────┤
│  4. Compute change output                           │
│     - ERG change back to sender                     │
│     - unspent tokens back to sender                 │
├─────────────────────────────────────────────────────┤
│  5. Sign (wallet / prover)                          │
│     - Sigma protocol proofs attached                │
├─────────────────────────────────────────────────────┤
│  6. Submit to node / explorer API                   │
└─────────────────────────────────────────────────────┘
```

### Step-by-Step

**Step 1 — Box Selection**  
The SDK queries the node or explorer for unspent boxes owned by the sender. Fleet's `BoxSelector` applies a strategy (e.g. accumulate boxes until the total ERG and all required token quantities are covered). AppKit wraps this in `BoxOperations`.

**Step 2 — Output Construction**  
Each `OutputBuilder` (Fleet) or `OutBox` (AppKit) receives:
- `value` in nanoERG (must satisfy `estimateMinBoxValue`)
- optional token list (id + amount pairs)
- optional register values encoded as `SType` constants
- the protecting `ErgoTree` (or a P2PK address that Fleet/AppKit compiles to an ErgoTree automatically)

**Step 3 — Fee**  
A special output box is directed to the canonical miner fee address (`ErgoTree` = `1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304`, a well-known script encoding the fee treasury).

Fleet exposes `RECOMMENDED_MIN_FEE_VALUE` from `@fleet-sdk/common`. AppKit exposes `Parameters.MinFee`.

**Step 4 — Change**  
`TransactionBuilder.build()` (Fleet) or `UnsignedTransactionBuilder` (AppKit) automatically computes the ERG remainder and any unspent token quantities, routing them to the change address. If change would fall below `SAFE_MIN_BOX_VALUE`, the builder throws or adjusts selection.

**Step 5 — Signing**  
Fleet produces an `EIP-12`-compliant unsigned transaction object that a wallet connector (Nautilus, SAFEW) signs. AppKit uses a `Prover` that holds a secret key or delegates to an external wallet.

**Step 6 — Submission**  
The signed transaction is posted to `/api/v1/mempool/transactions/submit` (Ergo node REST API) or the Explorer submission endpoint.

---

## Implementation

### Fleet SDK (TypeScript)

#### Installation

```bash
npm install @fleet-sdk/core @fleet-sdk/common
# optional: peer packages for wallet connectivity
npm install @fleet-sdk/wallet
```

#### 1. Simple ERG Transfer

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
  ErgoAddress,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

// Boxes fetched from node/explorer for the sender address
const inputBoxes: Box<Amount>[] = await fetchUnspentBoxes(senderAddress);

// Current blockchain height — required for box creation height
const height: number = await fetchCurrentHeight();

const unsignedTx = new TransactionBuilder(height)
  // Register UTXOs that can be consumed
  .from(inputBoxes)
  // Describe the recipient output
  .to(
    new OutputBuilder(
      SAFE_MIN_BOX_VALUE,          // 1_000_000n nanoERG minimum
      recipientAddress,            // P2PK address string or ErgoTree hex
    )
  )
  // Change ERG and unspent tokens go here
  .sendChangeTo(senderAddress)
  // Standard miner fee
  .payMinFee()
  // Produce the unsigned transaction object
  .build()
  // Serialise to EIP-12 format for wallet connector
  .toEIP12Object();

console.log(JSON.stringify(unsignedTx, null, 2));
```

> **Note:** `payMinFee()` is shorthand for `.payFeeBy(RECOMMENDED_MIN_FEE_VALUE)`. For congested mempool conditions you may pass a larger value.

---

#### 2. Token Transfer

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";

const TOKEN_ID =
  "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04";
const TOKEN_AMOUNT = 500n; // base units (check token decimals separately)

const unsignedTx = new TransactionBuilder(height)
  .from(inputBoxes)
  .to(
    new OutputBuilder(SAFE_MIN_BOX_VALUE, recipientAddress)
      // Attach tokens; Fleet validates that inputs cover these amounts
      .addTokens({ tokenId: TOKEN_ID, amount: TOKEN_AMOUNT })
  )
  .sendChangeTo(senderAddress)
  .payMinFee()
  .build()
  .toEIP12Object();
```

Fleet's `TokensCollection` (used internally by `OutputBuilder`) automatically deduplicates and merges token entries. If the total token amount across outputs exceeds what the inputs supply, `TransactionBuilder.build()` throws `NotAllowedTokenBurning` unless you explicitly opt-in to burning.

---

#### 3. Token Minting (First-Mint / Token ID Rule)

The **Token ID rule** states that the ID of a newly minted token *must* equal the `boxId` of the first input box. Fleet enforces this through the minting API:

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  TokensCollection,
} from "@fleet-sdk/core";

// The first input box's ID becomes the new token's ID
const mintingBox = inputBoxes[0];

const unsignedTx = new TransactionBuilder(height)
  .from(inputBoxes)
  .to(
    new OutputBuilder(SAFE_MIN_BOX_VALUE, senderAddress)
      // mintTokens() signals Fleet to use first-input box ID as token ID
      .mintToken({
        amount: 1_000_000n,   // total supply in base units
        name: "MyToken