---
title: Off-chain bots
description: Off-chain bots — chain scanning → state detection → tx assembly → submission
tags: [offchain-bots, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [spectrum-finance/ergo-dex-backend, duckpools/lend-protocol-contracts, duckpools/voting-bot]
---
# Developer Guide: Off-Chain Bots — Chain Scanning → State Detection → Transaction Assembly → Submission

---

## Overview

### What This Pattern Is

The **off-chain bot pattern** is the primary mechanism by which Ergo dApps implement automated, reactive, and stateful behavior that cannot (or should not) live entirely on-chain. It describes a continuous loop running off-chain that:

1. **Scans** the blockchain (confirmed blocks and/or mempool) for relevant eUTXO Boxes
2. **Detects** application state encoded in those Boxes (via Registers, ErgoTree, or Token IDs)
3. **Assembles** a new Transaction that advances the protocol state
4. **Submits** that Transaction to the Ergo node for validation and eventual confirmation

### Why It Exists

Ergo's eUTXO model is fundamentally **reactive** at the chain level. ErgoScript defines spending conditions (what must be true for a Box to be consumed), but it has no notion of time-based triggers, loops, or side effects. The chain itself does not "push" — nothing happens unless someone constructs and submits a valid transaction.

Off-chain bots are the actors that:

- **Observe** the world state (current Boxes, block height, oracle data)
- **Decide** which protocol transitions are now valid or profitable
- **Execute** those transitions by building and submitting transactions

This mirrors how miners work in Proof-of-Work but for application-layer logic. The economic incentive for running a bot is typically embedded in the protocol itself — for example, a DEX bot collects an execution fee from each swap it processes, paid out of the user's deposited Box.

### When to Use This Pattern

| Situation | Use Off-Chain Bot? |
|---|---|
| AMM/DEX order matching (spectrum-finance) | ✅ Yes — orders sit as Boxes waiting to be matched |
| Lending protocol liquidations (duckpools) | ✅ Yes — undercollateralized positions must be detected |
| Governance/voting aggregation | ✅ Yes — vote Boxes must be tallied and committed on-chain |
| Oracle data posting | ✅ Yes — external data must be injected into Boxes periodically |
| Simple token transfer or NFT mint | ❌ No — user-initiated, single transaction |
| Pure on-chain logic with no triggers | ❌ No — ErgoScript handles it at spend time |

### Core Invariant

> **The off-chain bot is trusted by nobody.** The ErgoScript in each Box enforces all invariants. The bot merely finds opportunities the script already permits. A malicious or buggy bot can fail to execute, but cannot violate protocol rules — the node's validation ensures this.

This separation of concerns is what makes the pattern safe: correctness is guaranteed by the **ErgoTree** (compiled ErgoScript), not by the bot's logic.

---

## How It Works

### The Full Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    OFF-CHAIN BOT PROCESS                    │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   SCANNING   │───▶│    STATE     │───▶│  ASSEMBLY    │  │
│  │              │    │  DETECTION   │    │              │  │
│  │ Block/Mempool│    │ Box matching │    │  Build Tx    │  │
│  │ polling via  │    │ ErgoTree ID  │    │  inputs +    │  │
│  │ node API     │    │ Token ID     │    │  outputs +   │  │
│  │              │    │ Register val │    │  context ext │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                  │          │
│  ┌──────────────┐                               │          │
│  │  SUBMISSION  │◀──────────────────────────────┘          │
│  │              │                                           │
│  │ POST /tx     │                                           │
│  │ Handle err   │                                           │
│  │ Retry logic  │                                           │
│  └──────────────┘                                           │
│         │                                                   │
│         └──────────────────────────── loop ─────────────────┘
```

### Step 1: Chain Scanning

The bot polls the Ergo node's REST API at regular intervals. It queries:

- `/blockchain/box/byAddress/{address}` — unspent Boxes at a known contract address
- `/blockchain/transaction/byAddress/{address}` — recent transactions at that address
- `/transactions/unconfirmed` — mempool transactions (to avoid double-processing)
- `/blocks/lastHeaders/{n}` — recent block headers for current height

The bot maintains a **cursor** (last processed block height or box index) to avoid re-processing already-handled state. This cursor is typically persisted to a local database (Redis, PostgreSQL, or an embedded store).

**Key consideration:** Boxes in the **mempool** (unconfirmed) represent "pending" state. A robust bot must either:
- Skip mempool Boxes and wait for confirmation, or
- Track predicted next-state Boxes to avoid assembling conflicting transactions

Spectrum Finance's backend calls this the **resolver/predicted** mechanism — it stores the expected output Box of a pending transaction to avoid re-processing the same order.

### Step 2: State Detection

Once raw Boxes are retrieved, the bot **classifies** them. Classification uses:

- **ErgoTree matching** — compare the Box's `ergoTree` bytes against known compiled contract templates
- **Token ID matching** — check `tokens` array for a known **Singleton / State NFT** that uniquely identifies a contract instance
- **Register inspection** — decode `R4`–`R9` registers (which are `SType`-tagged byte arrays) to extract application state (pool reserves, loan terms, vote weights, etc.)
- **Value thresholds** — check that `value` (nanoERG) meets **Minimum box value** requirements

A Box that holds a **State NFT** (a token with exactly one unit in existence, sometimes called a Singleton) definitively identifies a unique contract instance. This is the standard Ergo pattern for distinguishing one pool/vault/position from another that uses the same ErgoScript template.

### Step 3: Transaction Assembly

This is the most complex step. The bot must construct a valid `ErgoLikeTransaction` that satisfies all ErgoScript spending conditions. This involves:

**Inputs:** The Boxes being consumed (e.g., a user's order Box, the pool's state Box)

**Data Inputs:** Read-only Boxes referenced by the transaction but not consumed (e.e., oracle price Boxes, governance parameter Boxes). Data inputs allow scripts to read external state without spending it.

**Outputs:** New Boxes that represent the next protocol state, with correct:
- `value` (nanoERG, must be ≥ **Minimum box value**, currently 0.001 ERG)
- `ergoTree` (the spending condition for the output)
- `tokens` (Native tokens, preserving **Token ID rule**: no token created without an input Box whose ID matches)
- Registers `R4`–`R9` (updated application state)
- `creationHeight` (set to current block height)

**Fees:** One output must pay the **Minimum transaction fee** (currently 0.001 ERG) to the fee address (`ErgoTree` = `1005040004000e36100204a00b08cd...`), or the fee can be paid from a dedicated fee Box.

**Context Extension:** Some contracts use `Context extension` variables (key-value pairs attached to inputs) to pass off-chain data into the ErgoScript execution context. This is how scripts can receive parameters that vary per execution without changing the ErgoTree.

**Sigma protocols:** The transaction must include valid proofs (signatures) for any `SigmaProp` spending conditions that require the bot's private key (e.g., an operator-gated contract).

### Step 4: Submission

The assembled transaction is serialized and POSTed to `/api/v1/transactions`. The node validates:

1. All input Boxes exist and are unspent
2. All ErgoScript conditions evaluate to `true`
3. Value conservation: `sum(inputs.value) = sum(outputs.value) + fee`
4. Token conservation: no tokens created without valid provenance
5. Context validity: height, self reference, etc.

If validation fails, the node returns an error. The bot must parse this error, determine if it is:
- **Recoverable** (e.g., input already spent by a competing bot → re-scan and try again)
- **Unrecoverable** (e.g., script logic error → alert and skip)

---

## Implementation

### Project Structure (Scala — Spectrum Finance style)

```
off-chain-bot/
├── scanning/
│   ├── BoxScanner.scala          # Polls node for Boxes
│   └── MempoolTracker.scala      # Tracks unconfirmed transactions
├── detection/
│   ├── OrderParser.scala         # Decodes order Boxes from raw API response
│   └── PoolParser.scala          # Decodes pool state Boxes
├── execution/
│   ├── TxAssembler.scala         # Builds ErgoLikeTransaction
│   └── Execution.scala           # Orchestrates the full loop
├── network/
│   ├── ErgoNetwork.scala         # Abstraction over node + explorer APIs
│   └── ErgoNode.scala            # Low-level node API client
└── Main.scala                    # Entry point, wires everything together
```

---

### Step 1 Implementation: Chain Scanning (Scala)

```scala
// ErgoNetwork.scala — Abstraction layer over Ergo node REST API
// Mirrors spectrum-finance/ergo-dex-backend architecture

import org.ergoplatform.ergo.domain.{Box, Transaction}
import tofu.higherKind.derived.representableK

/**
 * ErgoNetwork provides a typed, effect-polymorphic interface to the
 * Ergo node REST API. F[_] is typically IO or a tag