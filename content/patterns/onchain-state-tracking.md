---
title: On-chain state tracking
description: On-chain state tracking — scanning frameworks, box tracking by token/address, state reconstruction
tags: [onchain-state-tracking, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repos: [rosen-bridge/scanner, paideiadao/paideia-state, ergo-pad/danaides]
---
# Developer Guide: On-Chain State Tracking in Ergo

## Overview

On-chain state tracking is the practice of continuously monitoring the Ergo blockchain to reconstruct, maintain, and query the current state of smart contract systems from historical transaction and box data. Rather than relying on a trusted centralized service, your application derives ground truth directly from the eUTXO ledger.

### Why It Exists

Ergo's eUTXO model stores application state in **Boxes** — each box contains a value (nanoERG), optional **Native tokens**, up to ten **Registers** (R0–R9), and an **ErgoTree** locking script. Unlike account-based chains, there is no persistent "contract storage"; every state transition consumes old boxes and creates new ones. A dApp therefore cannot query a single address for "current state" — it must trace the chain of box consumption and creation to locate the live box.

Key drivers:

| Driver | Detail |
|---|---|
| eUTXO immutability | Spent boxes vanish from the UTXO set; only active boxes are queryable via the node API without history |
| **Singleton / State NFT** pattern | A unique token (Token ID rule: first input's ID at minting time) travels through every state-changing transaction, identifying the canonical live box |
| **Storage rent** | Boxes older than ~4 years have their nanoERG drained; trackers must detect and respond to rent-triggered box recreation |
| Off-chain components | Watchers, bots, oracle feeders, and UI indexers all require a reliable, up-to-date view of on-chain state |
| **Multi-stage contracts** | Complex protocols (DEXes, bridges, DAOs) chain multiple contract stages; each stage must be tracked independently |

### When to Use This Pattern

- Building an indexer or explorer for a specific protocol (Rosen Bridge, PaideiaDAO, ErgoPad)
- Implementing a watcher/relayer that must act on state changes
- Reconstructing historical state for auditing or analytics
- Writing off-chain logic that feeds data into **Data input** boxes read by ErgoScript
- Any application where `node.utxo.byAddress()` alone is insufficient because historical transitions matter

---

## How It Works

### High-Level Flow

```
Blockchain
    │
    ▼
Network Connector  (node REST / WebSocket)
    │  raw Block + Transactions
    ▼
Scanner Core       (block sequencing, fork detection, DB persistence)
    │  Block + TransactionType
    ▼
Extractor(s)       (protocol-specific parsing of ErgoTrees, Registers, Tokens)
    │  domain entities
    ▼
Database / State Store
    │
    ▼
Application Logic  (bots, APIs, UI)
```

### Step-by-Step

#### 1. Block Ingestion

The scanner connects to an Ergo node (via REST polling or WebSocket) and fetches blocks sequentially. Each block is represented as a `BlockInfo` struct containing:

```
{ height: number, hash: string, parentHash: string, timestamp: number }
```

The scanner checks `parentHash` against its last stored block to detect **chain reorganizations** (forks). On fork detection it rolls back the database to the common ancestor before re-processing.

#### 2. Transaction Extraction

For each block, every `Transaction` is passed to all registered `AbstractExtractor` instances. A transaction in Ergo contains:

- **Inputs** — box IDs being spent (boxes are removed from the UTXO set)
- **Data inputs** — boxes read without being spent (used by ErgoScript context)
- **Outputs** — new boxes created (each has ErgoTree, value, tokens, registers)
- **Context extension** — arbitrary key-value pairs passed to ErgoScript context

#### 3. Box Identification

Extractors identify relevant boxes using one or more of:

| Strategy | Mechanism |
|---|---|
| **Token ID filter** | Check `box.assets` for a known Singleton / State NFT token ID |
| **ErgoTree filter** | Match `box.ergoTree` against a compiled contract template |
| **Address filter** | Convert ErgoTree → P2PK or P2S address; compare against a watch-list |
| **Register content** | Inspect R4–R9 for protocol-specific markers |

The **Token ID rule** makes the Singleton NFT approach the most robust: the NFT's ID is immutable (it equals the box ID of the UTXO consumed during minting), so it uniquely identifies the contract instance forever.

#### 4. State Reconstruction

The extractor:

1. Detects when a tracked box is **spent** (appears in a transaction's `inputs`)
2. Finds the **new output** box in that same transaction that carries the NFT forward
3. Writes the new box state (registers decoded, token amounts, etc.) to the database, replacing the previous state record
4. Links the old and new records via `txId` for full audit history

#### 5. Fork Handling & Rollback

Every stored entity is tagged with `blockHeight` and `blockHash`. On fork:

```
DELETE FROM state_entities WHERE blockHeight > forkHeight
```

The scanner then re-processes the canonical chain from the fork point.

#### 6. Application Consumption

Downstream consumers query the database (or an API layer over it) for the latest state entity. Because state is persisted, consumers are decoupled from the node and survive node downtime.

---

## Implementation

### Project Setup (TypeScript)

```bash
npm install @rosen-bridge/scanner @rosen-bridge/scanner-interfaces \
            @rosen-bridge/abstract-extractor typeorm reflect-metadata
```

### 1. Database Entities

Define TypeORM entities for your protocol state. Here we track a **DEX pool** identified by a Singleton NFT:

```typescript
// src/entities/poolStateEntity.ts
import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  Index,
  CreateDateColumn,
} from 'typeorm';

/**
 * Represents one observed state of a DEX liquidity pool box.
 * Each row corresponds to a single on-chain Box that carries the pool NFT.
 * The row is immutable once written; the "current" state is the row
 * with the highest blockHeight that has not been marked as spent.
 */
@Entity('pool_state')
export class PoolStateEntity {
  @PrimaryGeneratedColumn()
  id!: number;

  /** The box ID of this pool box on-chain */
  @Column({ unique: true })
  @Index()
  boxId!: string;

  /** Transaction that created this box */
  @Column()
  creationTxId!: string;

  /** Transaction that spent this box (null = currently unspent) */
  @Column({ nullable: true, type: 'varchar' })
  spentTxId!: string | null;

  /** Block height at which this box was created */
  @Column()
  @Index()
  creationHeight!: number;

  /** Block height at which this box was spent (null = unspent) */
  @Column({ nullable: true, type: 'integer' })
  spentHeight!: number | null;

  /**
   * Singleton NFT token ID — the canonical identifier for this pool.
   * Equals the box ID of the UTXO consumed when the NFT was first minted
   * (Token ID rule). Immutable across all state transitions.
   */
  @Column()
  @Index()
  poolNftId!: string;

  /** Amount of ERG locked in this box (nanoERG as string to avoid JS bigint loss) */
  @Column('varchar')
  ergValue!: string;

  /** Amount of token X in the pool (R4 register, decoded) */
  @Column('varchar')
  tokenXAmount!: string;

  /** Amount of token Y in the pool (R5 register, decoded) */
  @Column('varchar')
  tokenYAmount!: string;

  /** Raw R4 register value (hex) for full auditability */
  @Column({ nullable: true, type: 'varchar' })
  r4Raw!: string | null;

  /** Raw R5 register value (hex) */
  @Column({ nullable: true, type: 'varchar' })
  r5Raw!: string | null;

  /** Block hash — used for fork detection rollback */
  @Column()
  blockHash!: string;

  @CreateDateColumn()
  observedAt!: Date;
}
```

### 2. Abstract Extractor Implementation

```typescript
// src/extractors/poolExtractor.ts
import { AbstractExtractor } from '@rosen-bridge/abstract-extractor';
import { AbstractLogger, DummyLogger } from '@rosen-bridge/abstract-logger';
import { Block } from '@rosen-bridge/scanner-interfaces';
import { DataSource, Repository } from 'typeorm';
import { PoolStateEntity } from '../entities/poolStateEntity';

/**
 * Ergo transaction type as returned by the node REST API / scanner.
 * This matches the /blockchain/transaction/byId response schema.
 */
interface ErgoBox {
  boxId: string;
  transactionId: string;
  blockId: string;
  value: string;           // nanoERG as string (use BigInt internally)
  index: number;
  globalIndex: number;
  creationHeight: number;
  settlementHeight: number;
  ergoTree: string;        // hex-encoded ErgoTree
  address: string;         // base58-encoded P2S or P2PK address
  assets: Array<{
    tokenId: string;
    amount: string;
  }>;
  additionalRegisters: {
    R4?: string;           // hex-encoded SType value
    R5?: string;
    R6?: string;
    R7?: string;
    R8?: string;
    R9?: string;
  };
  spentTransactionId: string | null;
}

interface ErgoTransaction {
  id: string;
  inputs: Array<{ boxId: string }>;
  dataInputs: Array<{ boxId: string }>;
  outputs: ErgoBox[];
}

/**
 * PoolExtractor monitors a specific liquidity pool identified by its
 * Singleton NFT (pool
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
