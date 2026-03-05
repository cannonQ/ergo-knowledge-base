---
title: On-chain state tracking
description: On-chain state tracking — scanning frameworks, box tracking by token/address, state reconstruction
tags: [onchain-state-tracking, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [rosen-bridge/scanner, paideiadao/paideia-state, ergo-pad/danaides]
---
# Developer Guide: On-Chain State Tracking in Ergo

## Overview

On-chain state tracking is the discipline of continuously monitoring the Ergo blockchain, identifying specific eUTXO **Boxes** of interest, and reconstructing application-level state from their contents — **Registers**, **Native tokens**, **ErgoTree** scripts, and spending history.

### Why It Exists

Ergo's eUTXO model differs fundamentally from account-based chains. There is no single "account state" to query. Instead, state lives inside Boxes that are created and destroyed (spent) by Transactions. A dApp's logical state — for example, a DEX pool's reserves, a DAO's governance token circulation, or a bridge's pending transfers — is encoded across one or more Boxes at any given block height.

To answer questions like *"What is the current price in the ERG/SigUSD pool?"* or *"Which withdrawal requests are pending?"*, you must:

1. Scan every block for relevant Boxes.
2. Persist their contents to a queryable off-chain store.
3. Reconstruct the logical state from that store.

### When to Use It

| Situation | Use On-Chain State Tracking |
|---|---|
| Your contract uses a **Singleton / State NFT** to identify the canonical state box | ✅ Yes |
| You need to list all UTXO boxes held by an address or script | ✅ Yes |
| You operate a **Multi-stage contract** pipeline (e.g., order → fill → settlement) | ✅ Yes |
| Your dApp must survive node restarts without replaying the entire chain | ✅ Yes |
| You only need the current best-block tip | ❌ Use node API directly |

### Ecosystem Implementations

| Project | Purpose |
|---|---|
| [`rosen-bridge/scanner`](https://github.com/rosen-bridge/scanner) | General-purpose block-by-block scanner with extractor plugins |
| [`paideiadao/paideia-state`](https://github.com/paideiadao/paideia-state) | DAO governance state reconstruction |
| [`ergo-pad/danaides`](https://github.com/ergo-pad/danaides) | Address/token indexing pipeline for ErgoFi ecosystem |

---

## How It Works

The following describes the canonical scanning loop shared by all three reference implementations.

### Step 1 — Establish a Chain Cursor

The scanner maintains a pointer to the last processed block (height + header hash). On startup it reads this from its persistent store. If none exists, it begins from a configured `initialHeight` (typically the block at which the contract was first deployed, not genesis).

```
stored_height = db.getLastProcessedBlock() ?? config.initialHeight
```

### Step 2 — Fetch the Next Block

The scanner polls (HTTP) or receives (WebSocket) the next block from an Ergo node. Each block contains:

- **Header**: height, `id` (header hash), `parentId`
- **Block transactions**: ordered list of `Transaction` objects, each containing `inputs` (spent Box IDs), `dataInputs` (read-only **Data inputs**), and `outputs` (new Boxes)

### Step 3 — Fork Detection

Before processing, the scanner checks that `block.parentId == stored_header`. If not, it rolls back stored blocks until it finds a common ancestor — this handles chain reorganisations.

```
if block.parentId != db.getHeaderAt(block.height - 1):
    rollbackTo(findCommonAncestor(block))
```

### Step 4 — Run Extractors

Each registered **Extractor** is a plugin that receives the raw block and emits structured records. An extractor typically does one of the following:

- **Filter by ErgoTree / address**: collect every output Box whose `ErgoTree` matches a known script template.
- **Filter by Token ID rule**: collect every output Box whose `tokens` array contains a specific **Native token** Token ID — especially useful for **Singleton / State NFT** tracking.
- **Filter by Register content**: inspect `R4`–`R9` for application-specific markers.

### Step 5 — Persist Box Records

Extractor output is written atomically with the block record. A single database transaction covers: marking the block as processed + inserting/updating all Box records for that height.

### Step 6 — State Reconstruction

Consumers query the off-chain store. For each logical entity (e.g., one liquidity pool) the latest unspent Box is the current state. Spent Boxes form a historical audit trail.

### Step 7 — Handle Storage Rent

After **Storage rent** epochs (~4 years per cycle), unmaintained Boxes are reclaimed by miners. A robust tracker must detect when a Box disappears without an explicit spend in a transaction (it was rent-collected) and handle this case without treating it as a fork.

---

## Implementation

### 1. TypeScript — Rosen Scanner Framework

The `rosen-bridge/scanner` library provides the scaffolding. You write an `AbstractExtractor` subclass; the framework handles block fetching, fork detection, and DB persistence.

#### 1.1 Define Your Extractor

```typescript
// src/extractors/poolExtractor.ts
import { AbstractExtractor } from '@rosen-bridge/abstract-extractor';
import { Block } from '@rosen-bridge/scanner-interfaces';
import { DataSource } from 'typeorm';

/**
 * Tracks all eUTXO Boxes whose ErgoTree matches the
 * ErgoDEX CFMMPool script template.
 *
 * The Singleton / State NFT approach: each pool box carries
 * a unique Native token (the "pool NFT") in its tokens[0]
 * slot. We index by Token ID to reconstruct individual pool
 * state without ambiguity.
 */
export class PoolStateExtractor extends AbstractExtractor<
  ErgoTransaction,  // the TransactionType for ErgoScanner
  PoolBoxRecord     // the entity type written to the DB
> {
  readonly POOL_NFT_POLICY_ID: string;

  constructor(
    dataSource: DataSource,
    poolNftPolicyId: string
  ) {
    super(dataSource);
    this.POOL_NFT_POLICY_ID = poolNftPolicyId;
  }

  /**
   * Unique name used for ExtractorStatusEntity tracking.
   * Changing this name resets the scan-from-height cursor.
   */
  getId = (): string => 'ergo-pool-state-extractor-v1';

  /**
   * Called once per block by GeneralScanner.
   * Must return DB entities to upsert atomically with block commit.
   */
  async processTransactions(
    transactions: ErgoTransaction[],
    block: BlockInfo
  ): Promise<boolean> {
    const poolBoxes: PoolBoxRecord[] = [];

    for (const tx of transactions) {
      // Mark inputs as spent — eUTXO boxes are destroyed on spend
      for (const input of tx.inputs) {
        await this.dataSource
          .getRepository(PoolBoxRecord)
          .update({ boxId: input.boxId }, { spentTxId: tx.id });
      }

      // Scan outputs for pool boxes identified by Token ID rule:
      // token[0] must be the Singleton / State NFT for this pool family
      for (const output of tx.outputs) {
        const nft = output.assets?.find(
          (a) => a.tokenId === this.POOL_NFT_POLICY_ID
        );
        if (!nft) continue;

        poolBoxes.push(
          this.buildPoolRecord(output, tx.id, block.height)
        );
      }
    }

    // Batch insert; framework wraps in the block's DB transaction
    if (poolBoxes.length > 0) {
      await this.dataSource
        .getRepository(PoolBoxRecord)
        .upsert(poolBoxes, ['boxId']);
    }

    return true; // signal success; false triggers retry
  }

  /**
   * Called by scanner during fork rollback.
   * Remove all records created at or above `height`.
   */
  async revertBlock(
    transactions: ErgoTransaction[],
    block: BlockInfo
  ): Promise<void> {
    await this.dataSource
      .getRepository(PoolBoxRecord)
      .delete({ createdHeight: block.height });

    // Restore the spent flag for inputs that were spent in reverted txs
    for (const tx of transactions) {
      for (const input of tx.inputs) {
        await this.dataSource
          .getRepository(PoolBoxRecord)
          .update({ boxId: input.boxId }, { spentTxId: null });
      }
    }
  }

  private buildPoolRecord(
    box: ErgoBox,
    txId: string,
    height: number
  ): PoolBoxRecord {
    return {
      boxId:         box.boxId,
      txId,
      createdHeight: height,
      spentTxId:     null,

      // Decode pool state from ErgoScript Registers:
      // R4 = fee numerator (Int)
      // R5 = emission LP amount (Long)
      // Registers are encoded as ErgoValue (sigma-serialised)
      feeNum:   decodeRegisterInt(box.additionalRegisters?.R4),
      lpAmount: decodeRegisterLong(box.additionalRegisters?.R5),

      // Native token amounts — pool's reserve balances
      tokenXId:     box.assets[1]?.tokenId ?? null,
      tokenXAmount: box.assets[1]?.amount  ?? 0n,
      tokenYId:     box.assets[2]?.tokenId ?? null,
      tokenYAmount: box.assets[2]?.amount  ?? 0n,

      // Minimum box value enforcement: store nanoERG value
      ergValue:  BigInt(box.value),

      serializedErgoTree: box.ergoTree,
    };
  }
}
```

#### 1.2 Wire the Scanner

```typescript
// src/scanner/poolScanner.ts
import { DataSource } from 'typeorm';
import { NodeNetworkConnector } from '@