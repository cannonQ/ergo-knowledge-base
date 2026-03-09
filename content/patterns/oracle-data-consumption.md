---
title: Oracle data consumption
description: Oracle data consumption — reading price feeds and external state via Data inputs without spending
tags: [oracle-data-consumption, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [ergoplatform/oracle-core, kushti/dexy-stable, DjedAlliance/Djed-Ergo]
---
# Developer Guide: Oracle Data Consumption via Data Inputs in Ergo

## Overview

### What This Pattern Is

The **Oracle data consumption pattern** enables smart contracts on Ergo to read external real-world data — price feeds, exchange rates, asset valuations, or any externally verified state — without spending the box that holds that data. This is accomplished through **Data inputs**, a first-class feature of the Ergo eUTXO model that allows a transaction to reference existing boxes in the UTXO set as read-only witnesses.

A **Data input** is a box included in a transaction solely for the purpose of making its contents — ERG value, tokens, and Registers R0–R9 — available to the ErgoScript context of spending contracts. Crucially, a Data input box is **not consumed**: it remains in the UTXO set after the transaction confirms, unchanged.

### Why It Exists

In account-based blockchains, contracts can call external state directly. The eUTXO model has no such mechanism — every state change requires spending and recreating a box. Data inputs solve the **oracle trilemma** specific to UTXO-based systems:

1. **Without Data inputs**, every contract needing a price feed would have to spend the oracle box, forcing sequential execution and making shared data feeds impossible at scale.
2. **With Data inputs**, an oracle's **Pool Box** (holding the aggregated, validated price) can be referenced simultaneously by thousands of transactions in the same block, all reading the same price without contention.
3. The oracle box is protected by its own **ErgoTree** guard script; it can only be updated by the oracle protocol itself, not by consumers.

This design is specified in [EIP-0022](https://github.com/ergoplatform/eips/blob/master/eip-0022.md) and is fundamental to how oracle-core, Dexy, and Djed operate.

### When to Use This Pattern

| Use Case | Use Data Input? |
|---|---|
| Reading a price feed (ERG/USD, etc.) | ✅ Yes |
| Checking whether a Singleton NFT exists | ✅ Yes |
| Enforcing a collateral ratio in a stablecoin | ✅ Yes |
| Reading on-chain governance state | ✅ Yes |
| Updating the oracle's aggregated price | ❌ No — spend the Pool Box |
| Minting tokens gated on current price | ✅ Yes (Data input for price, spending your own box) |

---

## How It Works

### The Oracle Architecture: Key Box Types

The Ergo Oracle Core protocol defines three principal box types that interact. Understanding them is prerequisite to consuming oracle data correctly.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Oracle Pool Lifecycle                        │
│                                                                 │
│  Individual Oracle Boxes          Pool Box (Aggregated)         │
│  ┌──────────────────────┐         ┌──────────────────────────┐  │
│  │ Oracle Box #1        │ ──────▶ │ Pool Box                 │  │
│  │ R4: oracle pubkey    │         │ R4: aggregated rate      │  │
│  │ R5: epoch counter    │ collect │ R5: epoch counter        │  │
│  │ R6: data point       │ tx      │ Tokens: Pool NFT +       │  │
│  │ Tokens: Oracle Token │         │         Reward tokens    │  │
│  └──────────────────────┘         └──────────────────────────┘  │
│  ┌──────────────────────┐                    │                  │
│  │ Oracle Box #2        │ ──────▶            │ Data input       │
│  │ ...                  │                    ▼                  │
│  └──────────────────────┘         ┌──────────────────────────┐  │
│                                   │ Consumer Transaction      │  │
│                                   │ (e.g., Dexy mint/redeem) │  │
│                                   └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Flow

#### Step 1: Oracle Operators Post Data Points

Each oracle operator monitors an off-chain data source and posts a signed data point into their individual **Oracle Box**. The Oracle Box holds:

- `TOKENS(0)`: the Oracle Token (unique per oracle, minted at pool bootstrap)
- `TOKENS(1)`: accumulated reward tokens
- `R4`: the oracle operator's public key (a `GroupElement` / EC point)
- `R5`: the epoch counter (`Int`)
- `R6`: the raw data point — e.g., nanoERG per USD cent (`Long`)

#### Step 2: The Collect Transaction Aggregates Data

A designated **Refresh** or **Collect** transaction spends the current Pool Box and up to N Oracle Boxes, computing a new aggregated rate (typically median), and produces a new Pool Box. This is the only transaction that *spends* the Pool Box.

#### Step 3: The Pool Box Holds Finalized Data

After collection, the Pool Box contains:

- `TOKENS(0)`: the **Pool NFT** — a Singleton NFT whose Token ID uniquely identifies this oracle pool. The **Token ID rule** makes it impossible to forge: the Pool NFT's ID equals the outbox index of the transaction that minted it, making it globally unique.
- `R4`: the aggregated, validated rate (`Long`)
- `R5`: the current epoch counter (`Int`)

#### Step 4: Consumer Contracts Reference the Pool Box as a Data Input

Any transaction may include the Pool Box as a **Data input**. In ErgoScript, Data inputs are accessed via the `CONTEXT.dataInputs` array (zero-indexed). The consumer contract:

1. Verifies that `CONTEXT.dataInputs(0).tokens(0)._1 == POOL_NFT_ID` — this authenticates the data source.
2. Reads `CONTEXT.dataInputs(0).R4[Long].get` — the aggregated price.
3. Uses the price to enforce contract logic (collateral ratio, swap price, etc.).

The Pool Box is **not consumed** — it remains in the UTXO set and is available to all other transactions in the block and in future blocks until the next Collect transaction updates it.

#### Step 5: Storage Rent Protects Long-Lived Boxes

Because the Pool Box is long-lived and referenced indefinitely, **Storage rent** (4 years / ~1,051,200 blocks at current parameters) applies. The oracle pool protocol is designed to keep the Pool Box adequately funded. Consumer contracts should not assume a stale Pool Box will remain perpetually; in practice, oracle operators continuously refresh it.

---

## Implementation

### 1. ErgoScript: Consumer Contract Authenticating a Data Input

This is the canonical pattern for any contract that reads an oracle price feed. The Pool NFT Token ID is baked into the contract at compile time as a constant.

```scala
// ErgoScript: Price-gated contract
// Allows spending only if the ERG/USD price from the oracle
// is above a specified threshold.
//
// Compile-time constant:
//   poolNFT: Coll[Byte]  — the Pool NFT Token ID
//   priceThreshold: Long — minimum acceptable rate (nanoERG per USD cent)

{
  // --- Data Input Authentication ---
  // We require exactly one data input: the oracle Pool Box.
  val poolBox = CONTEXT.dataInputs(0)

  // Authenticate by Token ID rule: the Pool NFT is a Singleton NFT
  // whose ID was set at pool bootstrap. Forgery is impossible because
  // Token IDs are derived from the spending transaction's input box ID.
  val validPoolBox = poolBox.tokens(0)._1 == poolNFT

  // --- Read the Aggregated Rate ---
  // R4 holds the rate as a Long: nanoERG per USD cent (oracle-core convention)
  val rate = poolBox.R4[Long].get

  // --- Enforce Business Logic ---
  val priceConditionMet = rate >= priceThreshold

  // --- Spending Condition ---
  sigmaProp(validPoolBox && priceConditionMet && SELF.R4[SigmaProp].get)
}
```

**Key points:**
- `CONTEXT.dataInputs(0)` — accesses the first Data input box.
- `.tokens(0)._1` — the `_1` field of the token tuple is the Token ID (`Coll[Byte]`), `_2` is the amount.
- `.R4[Long].get` — typed register extraction; throws if R4 is absent or wrong type. Use `.getOrElse(0L)` defensively if needed.
- `poolNFT` must be a compile-time constant (`Coll[Byte]`). Never make it a runtime parameter — that opens a substitution attack.

---

### 2. TypeScript: Building a Transaction with a Data Input (fleet-sdk)

```typescript
import {
  OutputBuilder,
  TransactionBuilder,
  ErgoAddress,
  Box,
  RECOMMENDED_MIN_FEE_VALUE,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";
import { NodeService } from "./node-service"; // your node API wrapper

// ──────────────────────────────────────────────
// Types matching oracle-core Pool Box structure
// ──────────────────────────────────────────────

interface OraclePoolBox {
  boxId: string;
  ergoTree: string;
  assets: Array<{ tokenId: string; amount: string }>;
  additionalRegisters: {
    R4: string; // encoded Long: aggregated rate (nanoERG per USD cent)
    R5: string; // encoded Int: epoch counter
  };
  creationHeight: number;
  value: string;
  transactionId: string;
  index: number;
}

// ──────────────────────────────────────────────
// Step 1: Fetch the oracle Pool Box from the node
// The Pool Box is identified by the Pool NFT Token ID.
// ──────────────────