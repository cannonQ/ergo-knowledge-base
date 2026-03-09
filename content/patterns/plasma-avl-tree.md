---
title: Plasma / AVL tree state
description: Plasma / AVL tree state — off-chain authenticated data with on-chain proof verification, PlasmaMap pattern
tags: [plasma-avl-tree, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [paideiadao/paideia-contracts, ergoplatform/sigmastate-interpreter]
---
# Plasma / AVL Tree State: Off-Chain Authenticated Data with On-Chain Proof Verification

## Overview

### What Is This Pattern?

The **Plasma / AVL Tree** pattern (also called the **PlasmaMap pattern**) enables Ergo smart contracts to authenticate and verify large off-chain datasets using compact cryptographic proofs verified entirely on-chain. It is one of Ergo's most powerful scaling primitives, allowing a single on-chain **Box** to represent state that would be prohibitively expensive or impossible to store directly in the eUTXO model.

The core primitive is the **AVL tree** (Adelson-Velsky and Landis tree) — an authenticated, self-balancing binary search tree. In Ergo's context, the AVL tree's **digest** (a 33-byte Merkle-style root hash) is stored in a **Register** of an on-chain Box. The actual tree data lives off-chain. When a contract needs to read or mutate this data, the caller submits a **proof** alongside the transaction; the ErgoScript verifier checks the proof against the stored digest without needing the full dataset.

### Why Does It Exist?

Ergo's eUTXO model stores state in Boxes. Each Box has a minimum box value enforced by **Storage Rent** and is constrained by maximum serialized size. Storing thousands of user balances, staking positions, or membership records directly in Box **Registers** or as **Native Tokens** is impractical. The AVL tree pattern solves this by:

- Keeping the on-chain footprint **constant** (33-byte digest) regardless of dataset size
- Providing **cryptographic integrity** — any mutation to off-chain data invalidates the digest
- Enabling **trustless verification** — proofs are checked in ErgoScript with no trusted intermediary
- Supporting **batch operations** — multiple insertions, lookups, and deletions can be proven in a single proof

### When to Use It

| Use Case | Fits PlasmaMap? |
|---|---|
| Staking registries (thousands of stakers) | ✅ Ideal |
| DAO membership / voting weight | ✅ Ideal |
| Whitelist / allowlist verification | ✅ Ideal |
| Order books with many entries | ✅ Ideal |
| Token distribution (airdrops) | ✅ Ideal |
| Small state (< 10 entries) | ❌ Use Registers directly |
| Frequently contested single value | ❌ Use Singleton/State NFT alone |

---

## How It Works

### Conceptual Flow

```
Off-chain (Prover)                    On-chain (Verifier / ErgoScript)
─────────────────────────────────     ─────────────────────────────────
Full AVL tree data                    Digest stored in R4[AvlTree]
         │                                        │
         ▼                                        │
  Perform operation                               │
  (insert/update/delete/lookup)                   │
         │                                        │
         ▼                                        │
  Generate proof bytes                            │
         │                                        │
         ▼                                        ▼
  Attach proof to Transaction ──────► ErgoScript verifies proof
  via Context Extension                against stored digest
         │                                        │
         │                            If valid: accept new digest
         ▼                                        ▼
  Compute new digest                   New digest written to
  (post-operation)                     output Box R4[AvlTree]
```

### Step-by-Step Breakdown

#### Step 1: Initial State — Storing the Digest

A **Singleton Box** (identified by a **State NFT** / Token ID rule) holds the AVL tree digest in a Register, typically `R4[AvlTree]`. The `AvlTree` type in ErgoScript encodes:

- The 33-byte **digest** (root hash + tree height)
- **Flags** indicating which operations are enabled (`insertAllowed`, `updateAllowed`, `removeAllowed`)
- The **key length** (fixed-length keys only; variable-length keys require a workaround)
- An optional `maxKeySize` for value-size proofs

#### Step 2: Off-Chain — Build and Maintain the Tree

The contract operator maintains the full AVL tree off-chain using libraries such as `ergo-lib` (Rust/WASM), `sigma-rust`, or the JVM-based `sigmastate-interpreter`. The tree is a **persistent data structure** — each version is derived from the previous one.

#### Step 3: Off-Chain — Generate Proof

Before constructing the transaction, the off-chain actor:

1. Selects the operations to perform (e.g., `update(key, newValue)`)
2. Calls the prover to generate a **proof** — a serialized byte array encoding the Merkle path(s) needed to verify the operation
3. Computes the **new digest** that results after applying the operations

#### Step 4: On-Chain — Attach Proof via Context Extension

The proof bytes are attached to the spending transaction's input using a **Context Extension** (also called `ContextVar`). Context Extensions allow arbitrary bytes to be passed to an ErgoScript at evaluation time without being committed to the Box itself.

```
Input Box
  ├── contextVars[0] = proof bytes (for the operation)
  └── contextVars[1] = operation keys/values (optional, can be in data input)
```

#### Step 5: On-Chain — ErgoScript Verifies the Proof

ErgoScript calls AVL tree methods:

- `tree.contains(key, proof)` — lookup
- `tree.insert(kvPairs, proof)` — returns `Option[AvlTree]` with new digest
- `tree.update(kvPairs, proof)` — returns `Option[AvlTree]` with new digest
- `tree.remove(keys, proof)` — returns `Option[AvlTree]` with new digest

The script checks:
1. The proof is valid for the current digest
2. The resulting new digest matches the digest in the **output Box**
3. All other contract invariants hold (NFT preserved, correct output structure, etc.)

#### Step 6: New Digest Propagated

The output Box receives the new `AvlTree` digest. The State NFT is forwarded to this output Box, maintaining the singleton invariant.

---

## Implementation

### ErgoScript Contract: Plasma Staking (Adapted from Paideia)

This is the core staking contract. The AVL tree maps `staker_address_bytes → stake_amount_long`.

```scala
// plasmaStaking.es — Simplified Plasma Staking Contract
// The SELF box is the staking state box, identified by a Singleton/State NFT
{
  // ─── Read current state from Registers ───────────────────────────────────
  // R4: AVL tree digest representing the map of staker_key → stake_record
  val stakeState      = SELF.R4[AvlTree].get

  // R5: Operational parameters packed as a Coll[Long]
  val emissionAmount  = SELF.R5[Coll[Long]].get(0)  // tokens emitted per cycle
  val emissionDelay   = SELF.R5[Coll[Long]].get(1).toInt
  val cycleLength     = SELF.R5[Coll[Long]].get(2)  // blocks per emission cycle
  val nextSnapshot    = SELF.R5[Coll[Long]].get(3)  // HEIGHT for next snapshot
  val stakers         = SELF.R5[Coll[Long]].get(4)  // total number of stakers
  val totalStaked     = SELF.R5[Coll[Long]].get(5)  // total tokens staked

  // R6: Historical snapshots — Coll[(epoch_id, (emission_per_token, AvlTree))]
  // Each snapshot records the reward rate and the state tree at that epoch
  val snapshots = SELF.R6[Coll[(Long, (Long, AvlTree))]].get

  // ─── Identify the State NFT (Singleton) ─────────────────────────────────
  // The first token on SELF is the governance/state NFT — Token ID rule ensures
  // only one such box can exist in the protocol
  val stakeStateNFT = SELF.tokens(0)._1

  // ─── Output box must preserve the Singleton NFT ──────────────────────────
  val successor = OUTPUTS(0)
  val nftPreserved = successor.tokens(0)._1 == stakeStateNFT

  // ─── Context Extension: proof supplied by transaction builder ─────────────
  // ContextVar index 0: the AVL tree proof for the stake operation
  val proof = getVar[Coll[Byte]](0).get

  // ContextVar index 1: the keys being inserted/updated (staker public keys)
  val stakeKeys = getVar[Coll[Coll[Byte]]](1).get

  // ContextVar index 2: the new stake values (encoded as Coll[Byte])
  val stakeValues = getVar[Coll[Coll[Byte]]](2).get

  // ─── Build key-value pairs for AVL tree update ───────────────────────────
  val kvPairs: Coll[(Coll[Byte], Coll[Byte])] = stakeKeys.zip(stakeValues)

  // ─── Perform the authenticated update ────────────────────────────────────
  // stakeState.insert returns Some(newTree) if proof is valid, None otherwise
  val newStakeStateOpt: Option[AvlTree] = stakeState.insert(kvPairs, proof)

  // Proof validity — if proof is invalid, newStakeStateOpt is None and
  // isDefined returns false, causing the script to evaluate to false
  val proofValid = newStakeStateOpt.isDefined

  // ─── New digest must match what the output box declares ──────────────────
  val newStakeState = newStakeStateOpt.get
  val successorState = successor.R4[AvlTree