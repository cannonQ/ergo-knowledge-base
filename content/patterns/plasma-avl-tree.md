---
title: Plasma / AVL tree state
description: Plasma / AVL tree state — off-chain authenticated data with on-chain proof verification, PlasmaMap pattern
tags: [plasma-avl-tree, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [paideiadao/paideia-contracts, ergoplatform/sigmastate-interpreter]
---
# Plasma / AVL Tree State: Off-Chain Authenticated Data with On-Chain Proof Verification

## Overview

### What This Pattern Is

The **Plasma / AVL tree pattern** (also called the **PlasmaMap pattern**) is an architectural technique for Ergo smart contracts that enables a single on-chain Box to commit to an arbitrarily large authenticated dataset — potentially millions of key-value entries — while keeping the raw data off-chain. On-chain, only the **AVL tree digest** (a 33-byte Merkle-like root hash) is stored in a Register. Any off-chain actor wishing to prove membership, insertion, deletion, or update in that dataset constructs a **cryptographic proof** and submits it as part of a Transaction. The ErgoScript contract verifies the proof against the stored digest without ever seeing the full dataset.

This pattern is a direct analog to "Plasma" side-chain constructions in other ecosystems, but implemented natively within Ergo's eUTXO model using **authenticated dynamic dictionaries** (the AVL+ tree structure from the Scorex framework).

### Why It Exists

Ergo Boxes carry a fixed on-chain footprint governed by **minimum box value** and **storage rent** rules. Storing a mapping of 100,000 staker addresses and balances directly in Registers is economically and technically impossible: Registers R4–R9 are finite, and every byte stored on-chain permanently increases the storage rent burden. The AVL tree pattern solves this by:

- **Compressing state**: An entire database is represented by a single 33-byte digest stored in a Register (typically `R4` or `R5`).
- **Enabling trustless proofs**: The AVL tree is an authenticated data structure — any lookup, insert, or delete operation produces a proof that ErgoScript can verify in O(log n) time without the full tree.
- **Scaling indefinitely**: The on-chain cost of a contract is independent of the number of entries in the dataset.
- **Preserving the eUTXO security model**: Proofs are submitted within Transactions as **Context extensions** or output Register values, keeping verification atomic and deterministic.

### When to Use It

Use the PlasmaMap pattern when your contract needs to:

| Scenario | Example |
|---|---|
| Track unbounded membership sets | Staking registries (Paideia DAO) |
| Store per-user balances or state | Token distribution, airdrops |
| Implement off-chain order books with on-chain settlement | DEX matching engines |
| Maintain governance voter records | DAO voting weights |
| Build layer-2 payment channels with on-chain exit proofs | Micro-payment networks |

**Do not** use this pattern when the dataset is small enough to fit in Registers directly, or when your contract logic requires iterating over all entries on-chain (the AVL tree only supports point operations and range operations with proofs; it cannot enumerate).

---

## How It Works

### The Authenticated AVL+ Tree

The underlying data structure is an **AVL+ tree** (a height-balanced binary search tree with authenticated nodes). Each node stores:
- A **key** (arbitrary byte array)
- A **value** (arbitrary byte array)
- A **hash** derived from its children and own data

The **digest** is the hash of the root node plus the tree height, packed into 33 bytes. Crucially:

- **Any modification** to any node changes the digest.
- **Any proof** of a lookup/insert/delete is a path from the root to the relevant leaf, plus sibling hashes sufficient to recompute the root.
- **ErgoScript's built-in `AvlTree` type** can verify these proofs natively using `avlTree.contains`, `avlTree.get`, `avlTree.insert`, `avlTree.delete`, and `avlTree.update` methods.

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        OFF-CHAIN                                 │
│                                                                  │
│  1. Operator maintains full AVL tree in memory / database        │
│     PlasmaMap<K, V> (getblok_plasma library)                     │
│                                                                  │
│  2. For each operation (insert/update/delete/lookup):            │
│     a. Apply operation to local tree                             │
│     b. Extract proof bytes from tree                             │
│     c. Record new digest (33 bytes)                              │
│                                                                  │
│  3. Build Transaction:                                           │
│     - INPUTS: current state Box (holds old digest in Register)   │
│     - OUTPUTS: new state Box (holds new digest in Register)      │
│     - Context extension: proof bytes attached to input           │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │  Transaction submitted to Ergo node
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ON-CHAIN (ErgoScript)                     │
│                                                                  │
│  4. Contract reads old digest from SELF Register                 │
│  5. Contract reads proof from Context extension                  │
│  6. Contract calls avlTree.insert(proof) or similar              │
│  7. Returned Option[AvlTree] contains new digest if valid        │
│  8. Contract asserts new digest == digest in OUTPUT Register     │
│  9. Additional business logic checks (amounts, NFTs, etc.)       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Singleton / State NFT Anchoring

The state Box holding the digest **must** be uniquely identified. This is achieved with the **Singleton / State NFT** pattern: a native token with a Token ID derived from the Box ID of the genesis transaction is placed in the state Box. ErgoScript checks `SELF.tokens(0)._1 == expectedNFTId` to guarantee that only one canonical state Box exists and cannot be forged.

### AvlTree Flags

The `AvlTreeFlags` byte embedded in the digest controls which operations the tree permits:

| Flag | Meaning |
|---|---|
| `insertAllowed` | New keys can be inserted |
| `updateAllowed` | Existing values can be updated |
| `removeAllowed` | Keys can be deleted |

ErgoScript enforces these flags at proof verification time. Your contract should set only the flags it needs.

---

## Implementation

### Project Structure Overview

The reference implementation is [paideiadao/paideia-contracts](https://github.com/paideiadao/paideia-contracts), which uses:
- **getblok_plasma** — Scala/JVM library for off-chain AVL tree manipulation
- **ergo_python_appkit** — Python bindings wrapping AppKit and getblok_plasma
- **ErgoScript** — On-chain proof verification

### Part 1: ErgoScript Contract (On-Chain)

The following is drawn from `plasmaStaking.es` in paideia-contracts, annotated for clarity:

```scala
{
  // -------------------------------------------------------------------------
  // STATE BOX REGISTERS
  // R4: AvlTree  — the authenticated digest of the staker registry
  //               Key: staker PK bytes, Value: (stakeAmount, lockHeight) encoded
  // R5: Coll[Long] — operational parameters
  //   index 0: emissionAmount  — tokens emitted per cycle
  //   index 1: emissionDelay   — blocks between snapshot and emission
  //   index 2: cycleLength     — blocks per staking cycle
  //   index 3: nextSnapshot    — block height of next snapshot
  //   index 4: stakers         — current count of registered stakers
  //   index 5: totalStaked     — sum of all staked token amounts
  // R6: Coll[(Long,(Long,AvlTree))] — historical snapshots for delayed emission
  // -------------------------------------------------------------------------

  val stakeState   = SELF.R4[AvlTree].get
  val emissionAmount = SELF.R5[Coll[Long]].get(0)
  val emissionDelay  = SELF.R5[Coll[Long]].get(1).toInt
  val cycleLength    = SELF.R5[Coll[Long]].get(2)
  val nextSnapshot   = SELF.R5[Coll[Long]].get(3)
  val stakers        = SELF.R5[Coll[Long]].get(4)
  val totalStaked    = SELF.R5[Coll[Long]].get(5)
  val snapshots      = SELF.R6[Coll[(Long,(Long,AvlTree))]].get

  // The Singleton / State NFT identifying this exact state Box lineage
  val stakeStateNFT = SELF.tokens(0)._1

  // -------------------------------------------------------------------------
  // CONTEXT EXTENSIONS (supplied by the transaction builder off-chain)
  // Index 0: proof bytes for the AVL tree operation being performed
  // Index 1: operation-specific auxiliary data (e.g., stake amount)
  // -------------------------------------------------------------------------
  val proof      = getVar[Coll[Byte]](0).get
  val stakeInput = getVar[Long](1).get

  // -------------------------------------------------------------------------
  // OUTPUT STATE BOX — must carry the same Singleton NFT forward
  // -------------------------------------------------------------------------
  val successor = OUTPUTS(0)
  
  // Guard: the successor must carry the Singleton NFT to prevent state forking
  val validSuccessor = successor.tokens(0)._1 == stakeStateNFT

  // -------------------------------------------------------------------------
  // STAKE OPERATION: insert a new staker entry into the AVL tree
  //
  // The transaction builder off-chain:
  //   1. Looks up staker PK in local PlasmaMap
  //   2. Generates insert proof
  //   3. Places new digest in successor R4
  //   4. Attaches proof bytes to Context extension index 0
  // -------------------------------------------------------------------------
  val stakerPK    = INPUTS(1).propositionBytes   // user's P2PK box
  val stakeEntry  