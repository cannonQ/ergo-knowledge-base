---
title: Off-chain bots
description: Off-chain bots — chain scanning → state detection → tx assembly → submission
tags: [offchain-bots, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [spectrum-finance/ergo-dex-backend, duckpools/lend-protocol-contracts, duckpools/voting-bot]
---
# Off-Chain Bots: Chain Scanning → State Detection → TX Assembly → Submission

## Overview

### What This Pattern Is

The **off-chain bot pattern** is the backbone of decentralized application automation on Ergo. It describes a class of programs—commonly called *bots*, *executors*, or *watchers*—that continuously observe the Ergo blockchain, identify actionable on-chain state encoded in **eUTXO Boxes**, assemble valid **Transactions** that advance that state, and submit those transactions to the network.

Because Ergo's **eUTXO** model stores all application state in **Boxes** (each carrying a value in nanoERGs, optional **Native tokens**, up to ten **Registers** of typed data, and an **ErgoTree** spending condition), the blockchain itself becomes the canonical source of truth. The off-chain bot is the *executor* of intent that cannot be—or should not be—encoded purely in **ErgoScript**.

### Why It Exists

**ErgoScript** is a non-Turing-complete, purely functional language for spending conditions. It cannot:

- Initiate transactions autonomously
- Perform off-chain computation or I/O
- React to the passage of real time without an external trigger
- Efficiently search for counterpart boxes across the UTXO set

Off-chain bots fill this gap. They provide the *liveness* property that smart contracts on their own cannot supply. The cryptographic guarantees—enforced by **Sigma protocols** and the **ErgoTree** interpreter—remain entirely on-chain. The bot merely *finds* valid execution opportunities and *constructs* the witness.

### When to Use It

| Scenario | Examples |
|---|---|
| Automated order matching | AMM DEX (Spectrum Finance), order-book execution |
| Liquidation engines | Lending protocols (duckpools lend-protocol) |
| Governance tallying | Voting bots (duckpools voting-bot) |
| Oracle data posting | Oracle pools epoch transitions |
| Storage-rent reclamation | Dust consolidation bots |
| **Multi-stage contract** advancement | Any protocol where boxes must be redeemed and re-created in sequence |

---

## How It Works

The pattern decomposes into four well-defined, repeating phases executed in a continuous loop:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Bot Main Loop                            │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   SCAN       │───▶│   DETECT     │───▶│  ASSEMBLE    │      │
│  │ (chain +     │    │  (classify   │    │  (build tx   │      │
│  │  mempool)    │    │   & filter)  │    │   & sign)    │      │
│  └──────────────┘    └──────────────┘    └──────┬───────┘      │
│         ▲                                        │              │
│         │            ┌──────────────┐            │              │
│         └────────────│    SUBMIT    │◀───────────┘              │
│                      │  (+ retry   │                            │
│                      │   logic)    │                            │
│                      └──────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 1 — Chain Scanning

The bot polls Ergo node API endpoints (or an indexed data source like Explorer) to:

1. Retrieve confirmed blocks since the last processed height
2. Retrieve the **mempool** (unconfirmed transactions) to avoid double-spending inputs already consumed
3. Extract **Boxes** matching a known **ErgoTree** (contract address) or **Token ID**

**Key concept — Singleton / State NFT:** Many protocols use a single NFT (a token minted with supply = 1) to uniquely identify the canonical state box of a **multi-stage contract**. Scanning for this **Token ID** is more reliable than matching by address alone, because the address encodes the **ErgoTree** which may vary across versions.

### Phase 2 — State Detection

Raw boxes are deserialized and classified:

- **Register** values are decoded (R4–R9 hold typed `EvaluatedValue[SType]` data)
- Business logic determines whether an order/position/epoch is *actionable*
- **Storage rent** deadlines may be checked (boxes older than ~4 years lose value to miners unless re-created)
- Mempool state is diffed against confirmed state to avoid re-executing already-pending orders

### Phase 3 — Transaction Assembly

The bot constructs an `ErgoLikeTransaction` composed of:

| Component | Description |
|---|---|
| **Inputs** | Boxes being spent (must satisfy their `ErgoTree`) |
| **Data inputs** | Read-only boxes referenced for oracle prices, pool state, etc. without being spent |
| **Outputs** | New boxes created, each with `value`, `ergoTree`, tokens, and registers |
| **Context extension** | Key-value pairs injected into the **ErgoScript context** for scripts that read `getVar[T](id)` |

The **Minimum box value** (currently ~0.001 ERG, enforced by the node) must be respected for every output. The **Minimum transaction fee** (typically 0.001 ERG) is collected by miners via a dedicated fee box with a standard fee **ErgoTree**.

### Phase 4 — Submission and Error Handling

The assembled transaction is submitted via `POST /transactions`. The bot must handle:

- **`TxFailed`** — invalid inputs (race condition: another bot spent the box first)
- **Network partitions** — retry with exponential backoff
- **Height drift** — some scripts use `HEIGHT` context variable; re-assembling at the current height may be necessary

---

## Implementation

### Project Structure

A production-grade bot typically separates concerns into:

```
bot/
├── scanner/        # Block/mempool polling
├── detector/       # Box classification and filtering
├── interpreter/    # TX assembly (ErgoScript context setup)
├── executor/       # Submission and retry logic
└── network/        # Node API client
```

---

### 1. Node API Client (TypeScript)

This layer wraps the Ergo node REST API. It handles both confirmed UTXO scanning and mempool awareness.

```typescript
// network/ErgoNodeClient.ts

import axios, { AxiosInstance } from "axios";

/**
 * Minimal representation of an Ergo Box as returned by the node API.
 * Full boxes carry value (nanoERGs), ergoTree (hex-encoded ErgoTree),
 * assets (Native tokens with Token ID + amount), and additionalRegisters.
 */
export interface ErgoBox {
  boxId: string;
  value: number;           // nanoERGs — must be >= Minimum box value
  ergoTree: string;        // hex-encoded ErgoTree
  creationHeight: number;
  assets: Array<{
    tokenId: string;       // Token ID rule: first input's boxId on minting tx
    amount: number;
  }>;
  additionalRegisters: {   // R4–R9: hex-encoded typed Ergo values
    R4?: string;
    R5?: string;
    R6?: string;
    R7?: string;
    R8?: string;
    R9?: string;
  };
  transactionId: string;
  index: number;           // Output index within the transaction
}

export interface ErgoTransaction {
  id: string;
  inputs: Array<{ boxId: string; spendingProof: { proofBytes: string; extension: Record<string, string> } }>;
  dataInputs: Array<{ boxId: string }>;  // Data inputs: read-only, not spent
  outputs: ErgoBox[];
}

export interface NodeInfo {
  fullHeight: number;
  headersHeight: number;
  bestFullHeaderId: string;
}

export class ErgoNodeClient {
  private readonly http: AxiosInstance;

  constructor(nodeUrl: string, apiKey?: string) {
    this.http = axios.create({
      baseURL: nodeUrl,
      headers: apiKey ? { "api_key": apiKey } : {},
      timeout: 10_000,
    });
  }

  /** Current confirmed blockchain height — used to set transaction.creationHeight */
  async getNodeInfo(): Promise<NodeInfo> {
    const { data } = await this.http.get<NodeInfo>("/info");
    return data;
  }

  /**
   * Fetch all unspent boxes protected by a given contract address.
   * Internally, the node matches boxes whose ErgoTree hashes to this address.
   */
  async getUnspentBoxesByAddress(
    address: string,
    offset = 0,
    limit = 50
  ): Promise<ErgoBox[]> {
    const { data } = await this.http.get<ErgoBox[]>(
      `/blockchain/box/unspent/byAddress/${address}`,
      { params: { offset, limit } }
    );
    return data;
  }

  /**
   * Scan by Token ID — critical for Singleton / State NFT pattern.
   * Returns all unspent boxes containing this token regardless of ErgoTree.
   */
  async getUnspentBoxesByTokenId(
    tokenId: string,
    offset = 0,
    limit = 50
  ): Promise<ErgoBox[]> {
    const { data } = await this.http.get<ErgoBox[]>(
      `/blockchain/box/unspent/byTokenId/${tokenId}`,
      { params: { offset, limit } }
    );
    return data;
  }

  /**
   * Retrieve unconfirmed transactions from the mempool.
   * Essential for filtering out boxes already consumed by pending transactions —
   * attempting to spend such boxes causes immediate TxFailed errors.
   */
  async getUnconfirmedTransactions(
    offset = 0,
    limit = 100
  ): Promise<ErgoTransaction[]> {
    const { data } = await this.http.