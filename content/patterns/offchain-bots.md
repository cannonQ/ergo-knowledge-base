---
title: Off-chain bots
description: Off-chain bots — chain scanning → state detection → tx assembly → submission
tags: [offchain-bots, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [spectrum-finance/ergo-dex-backend, duckpools/lend-protocol-contracts, duckpools/voting-bot]
---
# Off-Chain Bots: Chain Scanning → State Detection → TX Assembly → Submission

## Overview

### What This Pattern Is

An **off-chain bot** in the Ergo ecosystem is a persistent process that monitors the blockchain, identifies actionable eUTXO states, assembles valid transactions in response, and submits them to the network. The bot is an external actor — it holds no on-chain authority itself — but it drives the execution of on-chain logic by constructing transactions that satisfy **ErgoScript** guards protecting **Boxes**.

This pattern is the operational backbone of nearly every DeFi protocol on Ergo: DEX order matching, lending liquidations, DAO voting tallies, oracle pool refreshes, and yield farming compounders all rely on it.

### Why It Exists

Ergo's **eUTXO** model is purely reactive. A Box sitting on-chain cannot execute itself; it can only be spent by a transaction that satisfies its **ErgoTree**. The on-chain contract defines *what is valid*; the off-chain bot defines *what gets done and when*. This separation of concerns is intentional:

- **ErgoScript** is a non-Turing-complete language for validation, not computation.
- Heavy computation (order matching, price calculations, route finding) belongs off-chain.
- The bot internalises the economic incentive — it typically earns a protocol fee from the transaction it assembles.
- **Storage rent** (0.1 ERG per 4 years per box) creates a cost for abandoned boxes, incentivising bots to process them promptly.

### When to Use It

| Situation | Use this pattern |
|---|---|
| Orders / intents sit in boxes waiting to be matched or filled | ✅ |
| A **Singleton / State NFT** box must be updated on a schedule or trigger | ✅ |
| A **multi-stage contract** requires an external party to advance stage | ✅ |
| Liquidation conditions must be detected and acted on atomically | ✅ |
| A DAO vote period ends and a tally transaction is required | ✅ |
| Your contract can be fully self-executing within one user's wallet | ❌ |

---

## How It Works

The pattern decomposes into four sequential, repeating phases:

```
┌─────────────────────────────────────────────────────────────────────┐
│  BLOCK / MEMPOOL EVENTS                                             │
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│   │  1. SCAN     │───▶│  2. DETECT   │───▶│  3. ASSEMBLE │         │
│   │  Chain /     │    │  State       │    │  Transaction │         │
│   │  Mempool     │    │  Matching    │    │  (ErgoTx)    │         │
│   └──────────────┘    └──────────────┘    └──────┬───────┘         │
│                                                  │                  │
│                                           ┌──────▼───────┐         │
│                                           │  4. SUBMIT   │         │
│                                           │  + Confirm   │         │
│                                           └──────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
```

### Phase 1 — Chain Scanning

The bot polls the Ergo node REST API (or an indexer such as **Explorer** or **Spectrum's ergo-chain-grabber**) for:

- New blocks at the current tip (`/api/v1/blocks`)
- Unconfirmed mempool transactions (`/api/v1/mempool/transactions`)
- Specific **ErgoTree** addresses (`/api/v1/boxes/unspent/byErgoTree/{ergoTree}`)

The scan identifies **unspent Boxes** whose **ErgoTree** matches a known contract template. The bot maintains a local cursor (last processed height) so it can resume after restarts without re-scanning the entire chain.

**Key considerations:**
- Boxes in the mempool are *tentatively spent* — the bot must track them to avoid double-spend attempts.
- **NiPoPoW**-based light clients can reduce sync overhead in resource-constrained environments, but most production bots use a full node or trusted indexer.
- The node's `/blockchain/box/byId/{id}` endpoint returns a Box with all **Registers** (R4–R9) populated, essential for state extraction.

### Phase 2 — State Detection

Once candidate boxes are identified, the bot decodes their **Registers** and **Tokens** to reconstruct protocol state:

- **R4–R9** are typed registers holding `SLong`, `SInt`, `SColl[SByte]`, `SSigmaProp`, `SGroupElement`, `STuple`, etc.
- **Native tokens** on a box are inspected by **Token ID** — a 32-byte Blake2b256 hash of the creating transaction's first input box ID.
- A **Singleton / State NFT** (a token with a supply of exactly 1) uniquely identifies a live protocol instance (pool, vault, oracle).
- **AVL tree** digests stored in registers encode compact authenticated data structures for stateful contracts.

The bot applies matching logic: "Does this box represent an open limit order? Is the pool TVL sufficient? Has the voting period elapsed?"

### Phase 3 — Transaction Assembly

This is the most complex phase. The bot constructs an `ErgoLikeTransaction` containing:

| Element | Purpose |
|---|---|
| **Inputs** | Boxes being spent; must satisfy their ErgoTrees |
| **Data inputs** | Read-only boxes used for price feeds, oracle data, or auxiliary state — they are NOT spent |
| **Outputs** | New boxes produced by the transaction |
| **Context extension** | Key-value pairs injected into the **ErgoScript context** for inputs that require them |
| **Proofs** | Sigma-protocol proofs (Schnorr, DLOG, etc.) satisfying spending conditions |

Critical constraints the bot must enforce:

- **Minimum box value**: every output box must hold ≥ `minBoxValue` (currently ~0.001 ERG, calculated as `360 * maxBoxSize` nanoERG by the node).
- **Minimum transaction fee**: the fee box must hold ≥ `minFee` (1,000,000 nanoERG = 0.001 ERG minimum; DEX bots typically use 2,000,000–4,000,000 nanoERG).
- **Token conservation**: total tokens in = total tokens out for every Token ID (except minting/burning).
- **ERG conservation**: `sum(inputs.value) = sum(outputs.value) + fee`.
- The fee box must have `ErgoTree = feeErgoTree` (the standard miner fee tree: `1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304`).

The bot typically signs with its own **ErgoTree** (proving ownership of its ERG inputs needed for fees), while the contract inputs are satisfied by the ErgoScript logic itself (e.g., the script validates the output structure rather than requiring a signature).

### Phase 4 — Submission and Confirmation Tracking

The assembled transaction is submitted via `POST /api/v1/transactions`. The bot:

1. Optimistically marks involved boxes as "pending" in its local cache.
2. Polls for transaction confirmation (`GET /api/v1/transactions/{txId}`).
3. On confirmation failure (node rejection, double-spend, mempool eviction), rolls back the pending state and retries.
4. On `TxFailed` errors (as seen in Spectrum's `Execution.scala`), parses the error to identify missed inputs and refreshes state from the chain.

---

## Implementation

### Project Structure (Scala / TypeScript hybrid, reflecting real ecosystem patterns)

```
off-chain-bot/
├── scanner/          # Chain polling, box indexing
├── detector/         # State matching, order book, pool state
├── assembler/        # Transaction building
├── submitter/        # Network submission, retry logic
└── models/           # Box, Order, Pool domain types
```

---

### 1. Chain Scanning (TypeScript — ergo-lib-wasm)

```typescript
// scanner/ChainScanner.ts
import {
  ErgoNodeApi,
  OutputInfo,
  TransactionInfo,
} from "@ergo-graphql/types";
import axios from "axios";

const NODE_URL = "http://localhost:9053";
const EXPLORER_URL = "https://api.ergoplatform.com";

// The ErgoTree hex of the contract we are monitoring.
// In production this is generated from the compiled ErgoScript.
const POOL_ERGO_TREE =
  "19a3030f0400040204020404040404060406..."; // truncated

interface BoxCandidate {
  boxId: string;
  value: bigint; // nanoERG
  ergoTree: string;
  assets: Array<{ tokenId: string; amount: bigint }>;
  additionalRegisters: Record<string, string>; // R4-R9 as hex-encoded SType values
  creationHeight: number;
  transactionId: string;
  index: number;
}

interface ScanCursor {
  lastProcessedHeight: number;
}

export class ChainScanner {
  private cursor: ScanCursor = { lastProcessedHeight: 0 };

  /**
   * Fetch all unspent boxes matching a given ErgoTree.
   * Uses the Explorer v1 API which returns rich box data including registers.
   */
  async getUnspentBoxesByErgoTree(
    ergoTree: string,
    offset = 0,
    limit = 100
  ): Promise<BoxCandidate[]> {
    const response = await axios