---
title: On-chain state tracking
description: On-chain state tracking — scanning frameworks, box tracking by token/address, state reconstruction
tags: [onchain-state-tracking, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [rosen-bridge/scanner, paideiadao/paideia-state, ergo-pad/danaides]
---
# On-Chain State Tracking in Ergo: A Comprehensive Developer Guide

## Overview

### What Is On-Chain State Tracking?

On-chain state tracking is the practice of continuously monitoring the Ergo blockchain to reconstruct the current (and historical) state of a decentralized application from raw block and transaction data. Rather than trusting a centralized server to maintain application state, your off-chain code re-derives state from the eUTXO ledger itself — the canonical source of truth.

In Ergo's eUTXO model, application state is stored inside **Boxes** (UTXOs extended with **Registers**, **Native tokens**, and **ErgoTree** spending conditions). State transitions happen when transactions consume old boxes and produce new ones. Because boxes are immutable once created and destroyed once spent, "current state" means finding the **unspent box** that carries the latest version of your application's data.

### Why Does This Pattern Exist?

The eUTXO model eliminates shared mutable state (unlike the account model), which makes smart contracts more predictable and parallelizable. However, it shifts the burden of state reconstruction to the application layer:

- There is **no global mutable variable** you can read; you must find the right live box.
- A **Singleton / State NFT** (a token minted with a fixed supply of 1 using the **Token ID rule** — where the Token ID equals the Box ID of the minting input) is the idiomatic way to uniquely identify the box that holds current state.
- **Storage rent** means boxes that are not spent for roughly four years may be reclaimed by miners, so long-running applications must account for box lifecycle.
- **Multi-stage contracts** spread state across several chained boxes; tracking them requires following a graph of transactions, not just a single address.

### When to Use It

| Scenario | Use On-Chain State Tracking |
|---|---|
| DEX / AMM pool — track current reserves | ✅ |
| DAO governance — reconstruct proposal & vote state | ✅ |
| Bridge — detect deposit/withdrawal events | ✅ |
| NFT marketplace — track ownership and listings | ✅ |
| Simple wallet balance check | ❌ (use node API directly) |
| One-off transaction submission | ❌ (use fleet-sdk / appkit) |

---

## How It Works

### Conceptual Flow

```
Blockchain
    │
    ▼
[Scanner] ──polls/subscribes──► [Block stream]
    │
    ▼
[Extractors] ──filter boxes──► [Relevant box events (created / spent)]
    │
    ▼
[Database] ──persist──► [Box table + State table]
    │
    ▼
[State Reconstructor] ──query──► [Current application state]
    │
    ▼
[Application / UI / Off-chain agents]
```

### Step-by-Step Explanation

#### Step 1 — Anchor the Scan

Choose your scan anchor. You need at least one of:

- **Token ID** of a Singleton / State NFT — uniquely identifies the current state box no matter how many times the contract has been called.
- **ErgoTree** hash / **P2S address** — identifies all boxes locked by a particular contract.
- **P2PK address** — identifies boxes belonging to a particular public key (less common for contracts).

The Singleton / State NFT approach is strongly preferred for protocols that update state because the NFT must always live in exactly one unspent box.

#### Step 2 — Initialize the Scanner

The scanner connects to an Ergo node (or multiple nodes via a **FailoverStrategy** or **RoundRobinStrategy**) and begins streaming blocks from an `initialHeight`. For each block it:

1. Fetches full block data (headers + transactions).
2. Iterates every **Transaction** in the block.
3. For each transaction, iterates **inputs** (boxes being spent) and **outputs** (boxes being created).
4. Passes these to registered **Extractors**.

#### Step 3 — Extract Relevant Boxes

An **Extractor** is a filter + transformer. It receives a block's transactions and emits structured records about boxes it cares about. Typical extractor logic:

```
for each transaction T in block B:
    for each output box O in T:
        if O contains target Token ID OR O.ergoTree == targetErgoTree:
            emit BoxCreated(O, T.id, B.height)
    for each input I in T:
        if I.boxId is tracked in our DB:
            emit BoxSpent(I.boxId, T.id, B.height)
```

#### Step 4 — Handle Rollbacks

Ergo nodes can reorganize (fork) the chain. The scanner must detect when its stored `lastScannedHeader` no longer matches the node's chain and roll back to the last common ancestor. The `PROCEED` flag on `BlockEntity` signals whether a block is confirmed or pending rollback.

#### Step 5 — Persist Box State

Boxes are stored in a local database (typically TypeORM + PostgreSQL or SQLite) with:

- `boxId` (primary key)
- `ergoTree`
- `registers` (R4–R9, serialized)
- `tokens` (array of `{tokenId, amount}`)
- `value` (nanoERG — relevant for **Minimum box value** and **Storage rent** calculations)
- `creationHeight`, `creationTxId`
- `spentHeight`, `spentTxId` (null if unspent)

#### Step 6 — Reconstruct State

Query the database for the unspent box carrying the State NFT. Deserialize its **Registers** using the appropriate **ErgoScript** type encoders (SLong, SGroupElement, SColl, etc.) to recover the application-level state variables.

#### Step 7 — Serve State to Consumers

Expose state via a REST API, WebSocket feed, or internal service bus. Off-chain agents (bots, UI backends, other contracts' executors) consume this state to build and submit new transactions.

---

## Implementation

### Project Structure

```
ergo-state-tracker/
├── src/
│   ├── scanner/
│   │   ├── ergoScanner.ts        # Ergo-specific GeneralScanner subclass
│   │   └── extractors/
│   │       ├── stateNftExtractor.ts
│   │       └── poolExtractor.ts
│   ├── entities/
│   │   ├── trackedBox.entity.ts
│   │   └── appState.entity.ts
│   ├── state/
│   │   └── stateReconstructor.ts
│   └── index.ts
├── migrations/
└── ormconfig.ts
```

---

### 1. Database Entities (TypeORM)

```typescript
// src/entities/trackedBox.entity.ts
import {
  Entity,
  PrimaryColumn,
  Column,
  Index,
  CreateDateColumn,
} from 'typeorm';

/**
 * Represents a Box observed on-chain.
 * A box is "live" (unspent) when spentTxId IS NULL.
 *
 * Ergo terminology:
 *  - boxId:        32-byte Blake2b256 hash of the box serialization
 *  - ergoTree:     serialized ErgoScript spending condition (hex)
 *  - registers:    R4–R9 as hex-encoded ErgoValue serializations
 *  - value:        nanoERG (must be >= Minimum box value = 360 nanoERG/byte)
 *  - tokens:       Native tokens held in the box (Token ID + amount)
 */
@Entity('tracked_box')
export class TrackedBoxEntity {
  @PrimaryColumn({ type: 'varchar', length: 64 })
  boxId: string;

  @Index()
  @Column({ type: 'varchar', length: 64 })
  ergoTreeHash: string;

  @Column({ type: 'text' })
  ergoTree: string;

  // Serialized as JSON: { tokenId: string; amount: string }[]
  // amount is string to safely handle uint64 via BigInt
  @Column({ type: 'jsonb' })
  tokens: Array<{ tokenId: string; amount: string }>;

  // nanoERG value — stored as string to avoid JS number precision loss
  @Column({ type: 'varchar', length: 30 })
  value: string;

  // Registers R4–R9 serialized as hex ErgoValue
  @Column({ type: 'jsonb', default: '{}' })
  registers: Record<string, string>;

  @Index()
  @Column({ type: 'integer' })
  creationHeight: number;

  @Column({ type: 'varchar', length: 64 })
  creationTxId: string;

  @Index()
  @Column({ type: 'integer', nullable: true })
  spentHeight: number | null;

  @Column({ type: 'varchar', length: 64, nullable: true })
  spentTxId: string | null;

  @CreateDateColumn()
  createdAt: Date;
}
```

```typescript
// src/entities/appState.entity.ts
import { Entity, PrimaryColumn, Column, UpdateDateColumn } from 'typeorm';

/**
 * Materialized application state derived from the current live box
 * carrying the Singleton / State NFT.
 *
 * Updated atomically whenever the scanner observes the NFT moving
 * to a new box (i.e., a state transition transaction).
 */
@Entity('app_state')
export class AppStateEntity {
  // The State NFT token ID — fixed for the lifetime of the protocol
  @PrimaryColumn({ type: 'varchar', length: 64 })
  stateNftId: string;

  // boxId of the current (unspent) box carrying the NFT
  @Column({ type: 'varchar', length: 64 })
  currentBoxId: string;

  // Decoded R4 — example: a pool's LP token reserve (SLong)
  @Column({ type: 'varchar', length: 30, nullable: true })
  reserveX: string | null;