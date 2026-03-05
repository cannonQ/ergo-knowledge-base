---
title: Oracle data consumption
description: Oracle data consumption — reading price feeds and external state via Data inputs without spending
tags: [oracle-data-consumption, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [ergoplatform/oracle-core, kushti/dexy-stable, DjedAlliance/Djed-Ergo]
---
# Developer Guide: Oracle Data Consumption via Data Inputs in Ergo

## Overview

### What This Pattern Is

Oracle data consumption via **Data inputs** is a fundamental eUTXO design pattern in Ergo that allows smart contracts to **read external state — such as price feeds, exchange rates, or any off-chain data — without spending or modifying the source Box**. This is architecturally distinct from how most UTXO-based blockchains handle external data, and it is one of Ergo's most powerful primitives.

In the eUTXO model, every transaction consumes input Boxes and produces output Boxes. A **Data input** is a third category: a Box that is referenced by a transaction and made available to the ErgoScript context of all spending scripts in that transaction, but is **never consumed**. The Box remains in the UTXO set after the transaction completes, available for the next consumer.

The canonical use case is the **Oracle Pool** (EIP-0023): a pool of independent data providers who periodically aggregate their individual data points into a single **Pool Box** — a Singleton Box holding the canonical price feed in its registers. Any contract on-chain can then read this price by referencing the Pool Box as a Data input.

### Why It Exists

The naive alternative — consuming an oracle Box and re-creating it — creates critical problems:

| Problem | Consequence |
|---|---|
| Contention: only one transaction can spend a UTXO per block | Under high demand, oracle consumers would race and fail |
| Miner extractable value: oracle owner could front-run consumers | Systemic risk for DeFi protocols |
| Increased transaction complexity | Oracle Box must be reconstructed every time it is read |
| Storage rent accumulation on hot paths | Frequent recreation resets the rent clock but adds overhead |

Data inputs solve all of these simultaneously. Because the Pool Box is **never spent** during a read, an arbitrary number of transactions in the same block can reference it as a Data input simultaneously.

### When to Use This Pattern

Use oracle Data input consumption when:

- Your ErgoScript needs a **current price** (ERG/USD, ERG/RSV, ADA/ERG, etc.)
- You need to verify **external state** (e.g., a governance decision, a reserve ratio) without modifying it
- You are building **DeFi primitives**: stablecoins (Djed, DexyGold), lending protocols, options, AMMs with oracle-assisted pricing
- You want **non-interactive reads**: the data source does not need to co-sign or participate in your transaction
- You need **composability**: multiple protocols reading the same oracle in the same block

Do **not** use this pattern when you need to atomically update the oracle value as part of your transaction — that requires spending the oracle Box directly (the oracle pool's own internal transactions do this).

---

## How It Works

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Oracle Pool (EIP-0023)                                             │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │
│  │Oracle    │  │Oracle    │  │Oracle    │  (Individual oracle      │
│  │Box 1     │  │Box 2     │  │Box 3     │   boxes, R6 = data      │
│  │R4: PubKey│  │R4: PubKey│  │R4: PubKey│   point)                │
│  │R5: Epoch │  │R5: Epoch │  │R5: Epoch │                         │
│  │R6: Price │  │R6: Price │  │R6: Price │                         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                         │
│       │             │             │                                 │
│       └─────────────┼─────────────┘                                │
│                     │  Aggregation transaction                      │
│                     ▼  (spends oracle boxes, reads pool box)        │
│  ┌──────────────────────────────┐                                  │
│  │  Pool Box (Singleton / NFT)  │  ← Identified by Pool NFT Token  │
│  │  R4: Aggregated price (Long) │                                  │
│  │  R5: Epoch counter           │                                  │
│  │  TOKENS[0]: Pool NFT         │                                  │
│  │  TOKENS[1]: Reward token     │                                  │
│  └──────────────────────────────┘                                  │
└──────────────────────────────────────────────────────────────────────┘
                          │
                          │  Referenced as DATA INPUT (not spent)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Consumer Transaction                                               │
│                                                                     │
│  INPUTS:           DATA INPUTS:         OUTPUTS:                   │
│  ┌──────────┐      ┌──────────────┐    ┌──────────────┐           │
│  │ User Box │      │  Pool Box    │    │ Protocol Box │           │
│  │ (ERG)    │      │  R4: price   │    │ (updated     │           │
│  └──────────┘      │  ← read-only │    │  state)      │           │
│  ┌──────────┐      └──────────────┘    └──────────────┘           │
│  │Protocol  │                          ┌──────────────┐           │
│  │State Box │                          │ Change Box   │           │
│  └──────────┘                          └──────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Flow

#### Step 1: Oracle Pool Maintains the Pool Box

The Oracle Pool (a Multi-stage contract system) runs an off-chain agent (the oracle-core daemon) that:

1. Each oracle collects the current price from a trusted external source (e.g., CoinGecko, exchange APIs)
2. Each oracle posts its data point into its individual **Oracle Box** (Registers R4–R6), spending and recreating it
3. The pool's aggregation transaction **spends** all oracle Boxes for the current epoch, computes the median/average, and writes the result into the **Pool Box** R4 register
4. The Pool Box is identified by a **Singleton NFT** (Token ID rule: only one token of this ID can ever exist, minted at genesis). This NFT is the canonical identifier of the oracle feed

#### Step 2: Consumer Contract Declares Data Input Dependency

In ErgoScript, the consuming contract accesses Data inputs via `CONTEXT.dataInputs`, a zero-indexed collection of Boxes available read-only:

```scala
// ErgoScript: accessing the oracle pool box as a data input
val poolBox = CONTEXT.dataInputs(0)
val poolNFT = fromBase64("AAAA...") // Pool NFT Token ID (32 bytes, base64)

// Verify this is actually the legitimate oracle pool box
// by checking it holds the well-known Pool NFT
val validOracle = poolBox.tokens(0)._1 == poolNFT

// Read the price from R4 (stored as Long, e.g., nanoERG per USD cent)
val oraclePrice = poolBox.R4[Long].get

// Use the price in your business logic
val isSufficientCollateral = collateralNanoErg * 1000000L / oraclePrice >= minCollateralRatio
```

#### Step 3: Transaction Builder Adds Data Input

The off-chain transaction builder fetches the current Pool Box from the node/explorer and adds it to the transaction's `dataInputs` field. The transaction is then submitted. The Pool Box remains unspent.

#### Step 4: ErgoScript Context Validation

When a miner validates the transaction, the ErgoScript interpreter populates `CONTEXT.dataInputs` with the referenced Boxes. The contract reads registers, verifies the NFT, and applies its logic. If validation passes, the transaction is included in the block. The Pool Box UTXO is untouched.

### Data Input Box Identity and Security

The **Token ID rule** is the security cornerstone: since a token's ID is derived from the `(boxId, index)` of the minting transaction, and box IDs are globally unique, a Pool NFT is provably unique. An attacker cannot forge a fake pool box carrying the same NFT. Your contract must **always** validate the NFT:

```scala
// SECURE: verify pool NFT is present
val validPoolBox = CONTEXT.dataInputs(0).tokens(0)._1 == poolNFTId

// INSECURE: trusting only the ErgoTree (address) without NFT check
// An attacker could deploy a contract with the same ErgoTree but different data
```

---

## Implementation

### 1. ErgoScript: Consumer Contract (Djed-Style Stablecoin Reserve Check)

This contract guards a reserve Box and allows minting of stablecoins only when the oracle-reported ERG price indicates sufficient collateralization. It demonstrates the canonical pattern for reading the EIP-0023 Oracle Pool.

```scala
{
  // ============================================================
  // Oracle Data Consumption Contract
  // Reads ERG/USD price from Oracle Pool Box via Data input
  // ============================================================

  // --- Constants (compiled into ErgoTree at contract creation) ---
  // Pool NFT Token ID: identifies the legitimate EIP-0023 Oracle Pool Box
  // This is a 32-byte collection (Coll[Byte]) hardcoded at compile time
  val poolNFTId: Coll[Byte] = fromBase64("YOUR_POOL_NFT_BASE64_HERE")

  // Minimum collateral ratio: 400 = 400% (4x overcollateralized)
  val minCollateralRatio: Long = 400L

  // --- Data Input Validation ---
  // CONTEXT.dataInputs is a Coll[Box] of read-only referenced boxes
  // Index 0 is