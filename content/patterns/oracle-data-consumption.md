---
title: Oracle data consumption
description: Oracle data consumption — reading price feeds and external state via Data inputs without spending
tags: [oracle-data-consumption, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [ergoplatform/oracle-core, kushti/dexy-stable, DjedAlliance/Djed-Ergo]
---
# Developer Guide: Oracle Data Consumption via Data Inputs in Ergo

## Overview

### What This Pattern Is

Oracle data consumption via **Data inputs** is an Ergo eUTXO design pattern that allows smart contracts to **read the current state of an oracle box — including price feeds and external data — without spending (consuming) that box**. This is a foundational primitive in Ergo's DeFi ecosystem, enabling trustless price discovery without requiring oracle operators to re-post data on every consumer transaction.

In traditional UTXO models, reading a box's contents requires spending it, which destroys it and forces recreation. Ergo's Data input mechanism, introduced formally in **EIP-0022**, solves this by allowing a transaction to reference boxes as **read-only witnesses**. The referenced box remains unspent in the UTXO set; it is simply inspected by the ErgoScript context of the spending transaction.

### Why It Exists

The oracle data consumption pattern exists because of fundamental properties of the eUTXO model:

- **Boxes are immutable once created.** Their Registers, tokens, and ErgoTree cannot be modified in place.
- **Spending a box destroys it.** Any contract that reads oracle data by spending the oracle box would either need to recreate it (adding complexity, coordination overhead, and transaction fees) or invalidate it for every concurrent consumer.
- **Concurrency at scale.** A single ERG/USD pool box might be referenced by hundreds of simultaneous transactions (DEX swaps, loan liquidations, stablecoin minting). If each consumer had to spend and recreate the oracle box, only one such transaction could succeed per block.

Data inputs solve the **concurrent read problem** elegantly: many transactions can reference the same oracle box as a Data input in the same block, and none of them consume it.

### When to Use This Pattern

Use oracle data consumption via Data inputs when:

| Situation | Use Data Input |
|-----------|---------------|
| Your contract needs a price feed (ERG/USD, ADA/ERG, etc.) | ✅ Yes |
| You need to verify external state held in a Singleton/State NFT box | ✅ Yes |
| You want to prove a fact about an unspent box without destroying it | ✅ Yes |
| You are updating the oracle box itself (pool refresh, epoch transition) | ❌ No — spend it |
| You need to alter any Register in the referenced box | ❌ No — spend it |

Concrete use cases in the Ergo ecosystem:

- **SigmaUSD / Djed**: reading the ERG/USD oracle pool box to compute collateral ratios before minting/redeeming SigmaRSV or SigmaUSD.
- **Dexy Stablecoin**: reading LP and oracle price to enforce the peg intervention logic.
- **DEX contracts**: reading external prices to prevent sandwich attacks or enforce slippage bounds.
- **Lending protocols**: reading collateral price to determine liquidation eligibility.

---

## How It Works

### Conceptual Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ERGO TRANSACTION                            │
│                                                                     │
│  INPUTS (spent, destroyed)          OUTPUTS (created)               │
│  ┌────────────────────┐             ┌────────────────────┐          │
│  │  User's ERG Box    │────────────▶│  New User Box      │          │
│  │  (collateral, etc.)│             │  (change, receipt) │          │
│  └────────────────────┘             └────────────────────┘          │
│                                                                     │
│  DATA INPUTS (read-only, NOT spent)                                 │
│  ┌────────────────────────────────────────────────────┐             │
│  │  Oracle Pool Box (Singleton NFT)                   │             │
│  │  R4: Long  = 165000000  (ERG/USD rate × 10^9)      │  ──────────▶│ ErgoScript can read
│  │  R5: Int   = 42         (epoch counter)            │             │ CONTEXT.dataInputs(0)
│  │  TOKENS(0) = pool_nft_id                           │             │
│  └────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Flow

#### Step 1: Oracle Posts Data to the Pool Box

The oracle-core software (running on each oracle operator's node) aggregates individual oracle boxes and publishes a canonical **pool box** — a box protected by the pool ErgoTree, holding a **Singleton NFT** (also called a State NFT or pool NFT) that uniquely identifies it. The current aggregate rate is stored in **R4** as a `Long`.

```
Pool Box:
  value:    minBoxValue (e.g., 10 ERG or minimum)
  tokens:   [ (pool_nft_id, 1), (reward_token_id, N) ]
  R4:       Long  — the current data point (e.g., nanoERG per USD cent)
  R5:       Int   — epoch counter
  ErgoTree: pool_contract (enforces update rules)
```

#### Step 2: Consumer Contract Declares Dependency on the Oracle

The consumer's ErgoScript specifies that a valid transaction **must** include the oracle pool box as `CONTEXT.dataInputs(0)`, and validates the box by checking its **Token ID** against a hardcoded pool NFT ID. This is the **Token ID rule**: the Singleton NFT guarantees there is exactly one authentic pool box in existence.

#### Step 3: Transaction Builder Adds the Data Input

The off-chain code (TypeScript/Rust/Python) building the consumer transaction fetches the current pool box from the node and adds it to the transaction's `dataInputs` array. The transaction structure is:

```
Transaction {
  inputs:      [userBox, collateralBox, ...],
  dataInputs:  [oraclePoolBox],          // read-only
  outputs:     [newUserBox, changeBox],
  fee:         minimumTransactionFee
}
```

#### Step 4: ErgoScript Evaluates the Context

During transaction validation, the Ergo node evaluates the ErgoScript of each spending input. The script accesses `CONTEXT.dataInputs` — a collection of `Box` objects — and reads their Registers. No signature from the oracle operator is required; the data is authenticated by the Token ID rule (only the box holding the genuine NFT is accepted).

#### Step 5: Rate Extraction and Business Logic

The script extracts the rate from R4, applies any necessary scaling (oracle data is typically stored as integers scaled by a power of 10 to preserve precision), and uses it in the contract's predicate logic (e.g., "only allow minting if collateral ratio > 400%").

---

## Implementation

### ErgoScript: Consumer Contract

The following ErgoScript demonstrates a minimal contract that reads an ERG/USD price feed from the oracle pool box and enforces a collateral ratio. This pattern is directly derived from the SigmaUSD and Dexy contract designs.

```scala
// Consumer contract: reads oracle pool box as Data input
// Assumes:
//   CONTEXT.dataInputs(0) = oracle pool box
//   oracle pool box R4 = Long: nanoERG per USD cent (rate)
//   oracle pool box TOKENS(0) = pool NFT
//
// Script guards a collateral box: allows withdrawal only if
// the collateral value is above a required USD threshold.

{
  // ── 1. Authenticate the oracle pool box by its Singleton NFT ──────────
  val poolNFT = fromBase16("your_pool_nft_token_id_here") // hardcoded at compile time

  val poolBox = CONTEXT.dataInputs(0)

  // Verify the box holds the authentic pool NFT in TOKENS(0)
  val validPoolBox = poolBox.tokens(0)._1 == poolNFT

  // ── 2. Extract the rate from R4 ───────────────────────────────────────
  // Rate is stored as: nanoERG per USD cent
  // i.e., rate = (nanoERG/ERG) / (USD price of 1 ERG in cents)
  // Example: if 1 ERG = $1.65, rate = 1_000_000_000 / 165 ≈ 6,060,606
  val rate = poolBox.R4[Long].get  // nanoERG per USD cent

  // ── 3. Business logic: require collateral ratio > 400% ────────────────
  // SELF.value is in nanoERG
  // required: collateral in nanoERG >= 4 * (debtInUSDCents * rate)
  val debtInUSDCents = SELF.R4[Long].get   // debt encoded in R4 of collateral box
  val minCollateral  = debtInUSDCents * rate * 4L

  val sufficientCollateral = SELF.value >= minCollateral

  // ── 4. Standard owner authorization ──────────────────────────────────
  val ownerPK = SELF.R5[GroupElement].get
  val ownerSig = proveDlog(ownerPK)

  // ── 5. Final predicate ────────────────────────────────────────────────
  sigmaProp(validPoolBox && sufficientCollateral) && ownerSig
}
```

**Key ErgoScript terms used:**
- `CONTEXT.dataInputs` — the read-only box collection in the ErgoScript context
- `poolBox.tokens(0)._1` — Token ID of the first token in the pool box
- `poolBox.R4[Long].get` — typed register extraction (will throw if absent or wrong type)
- `proveDlog(ownerPK)` — Sigma protocol: discrete log proof (standard P2PK ownership)
- `sigmaProp(...)` — lifts a Boolean predicate into a Sigma proposition

---

### TypeScript: Building a Transaction with a Data Input

Using the `@fleet-sdk/core` library (the standard Fleet SDK for