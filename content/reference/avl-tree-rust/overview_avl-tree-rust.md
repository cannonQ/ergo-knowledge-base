---
title: ergoplatform/ergo_avltree_rust — Overview
description: "Rust implementation of Ergo's AVL+ tree \u2014 authenticated data structures for on-chain verification"
tags: [ergoplatform, ergo-avltree-rust, core-protocol, rust]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repo: "https://github.com/ergoplatform/ergo_avltree_rust"
project: ergoplatform-ergo-avltree-rust
group: core-protocol
priority: high
languages: [rust]
contract_count: 0
pattern_match_count: 9
---
# ergoplatform/ergo_avltree_rust — Developer Overview

---

## Overview

`ergo_avltree_rust` is a Rust port of the authenticated AVL+ tree originally implemented in Scrypto (extracted from the [Scorex](https://github.com/ScorexFoundation/Scorex) modular blockchain framework). It provides **two-party authenticated data structures** for (key, value) pairs, with batching compression support and guaranteed verifier efficiency, as described in the cryptographic research at [eprint.iacr.org/2016/994](http://eprint.iacr.org/2016/994). The core guarantee is that a **Prover** holding a full data structure can produce compact cryptographic proofs for a batch of operations, and a **Verifier** holding only a short digest can replay those operations and confirm correctness without accessing the full tree.

Within the Ergo ecosystem, AVL+ trees are a first-class primitive. The ErgoScript interpreter natively understands AVL tree digests and proof verification, making this library the foundation for on-chain state that can be mutated off-chain and verified cheaply within ErgoScript contract execution. This underpins critical protocol-level features: the **UTXO set itself** is stored as an authenticated AVL+ tree, and application-layer constructs such as SigmaUSD, DEX order books, token registries, and other stateful contracts rely on AVL tree-backed state that can be read or mutated by off-chain bots and proven to on-chain verifiers. The **digest** of an AVL tree is typically stored in a Box Register (commonly `R4`–`R7`) attached to a **Singleton / State NFT** box that acts as the authoritative on-chain anchor.

The library is intentionally minimal and protocol-focused. It does not attempt to handle networking, serialization of full ErgoScript transactions, or wallet connectivity. Instead, it provides the cryptographic core — prover, verifier, tree node structures, and operation definitions — that higher-level Rust SDKs (such as `sigma-rust`) and off-chain bots compose to build full dApp workflows. Correctness of the Rust port is validated against the same test vectors used by the JVM reference implementation, ensuring interoperability across Ergo's multi-platform toolchain.

---

## Architecture

The library is organized around a clean separation between the **mutable prover side** (holds the full tree) and the **stateless verifier side** (holds only a digest and a proof). Data flows in one direction: the prover mutates state and emits a proof; the verifier consumes the digest, proof, and operation sequence to confirm the resulting digest.

### Core Modules

| Module | Responsibility |
|---|---|
| `src/batch_node.rs` | Defines the `AVLTree` struct and the internal node types (`Leaf`, `InternalNode`). Nodes carry balance factors, keys, values, and child hashes. This is the in-memory tree representation. |
| `src/operation.rs` | Defines the `Operation` enum: `Insert(KeyValue)`, `Update(KeyValue)`, `UpdateLongBy(KeyDelta)`, `Remove(key)`, `Lookup(key)`. Operations are pure data — they describe intent without carrying tree references. |
| `src/authenticated_tree_ops.rs` | Core trait defining `perform_one_operation`, `digest`, and tree traversal logic shared by both prover and verifier. Acts as the behavioral contract for authenticated tree manipulation. |
| `src/batch_avl_prover.rs` | Implements `BatchAVLProver`. Holds the full tree in memory. Tracks a running proof buffer across operations. Exposes `perform_one_operation`, `generate_proof` (consuming the current buffer), `digest`, and `unauthenticated_lookup` (side-effect-free reads). |
| `src/persistent_batch_avl_prover.rs` | A persistence-aware wrapper over `BatchAVLProver` that supports serializing and restoring tree state across process boundaries — essential for long-running off-chain bots. |
| `src/batch_avl_verifier.rs` | Implements `BatchAVLVerifier`. Constructed from a prior `digest` and a `proof` byte array. Replays the same operation sequence as the prover (excluding failed operations) and produces the updated digest. Accepts optional operation-count and deletion-count bounds to cap worst-case running time (DoS mitigation). |

### Data Flow

```
Off-chain Bot / SDK
        │
        ▼
  [BatchAVLProver]
  ┌──────────────────────────────┐
  │  Full AVL+ Tree (in memory)  │
  │  perform_one_operation(op)   │──► returns prior value or error
  │  unauthenticated_lookup(key) │──► side-effect-free read
  │  generate_proof()            │──► proof: Vec<u8>
  │  digest()                    │──► digest: [u8; 33]
  └──────────────────────────────┘
        │                  │
        │ digest            │ proof
        ▼                  ▼
  ┌─────────────────────────────────────────┐
  │  ErgoTransaction                        │
  │  ├─ Input Box (State NFT)               │
  │  │    R4: old_digest                    │
  │  ├─ Output Box (State NFT)              │
  │  │    R4: new_digest                    │
  │  └─ Context Extension: proof bytes      │
  └─────────────────────────────────────────┘
        │
        ▼
  [ErgoScript Verifier / BatchAVLVerifier]
  ┌───────────────────────────────────────────┐
  │  Constructed from: old_digest + proof      │
  │  perform_one_operation(op) × N             │
  │  digest() == new_digest  →  VALID          │
  └───────────────────────────────────────────┘
```

### Key Relationships

- **`AVLTree` ↔ `BatchAVLProver`**: The prover owns an `AVLTree` instance. Tree node resolution (loading nodes by hash) is handled through a resolver callback (`dummy_resolver` in tests; a real implementation resolves from a key-value store or in-memory map).
- **`BatchAVLProver` → `BatchAVLVerifier`**: The prover's `generate_proof()` output and `digest()` output are the only inputs the verifier needs — making the verifier entirely stateless with respect to tree storage.
- **`persistent_batch_avl_prover`**: Wraps `BatchAVLProver` with serialization, enabling the off-chain bot to crash-recover without reprocessing the entire chain history.
- **`Operation`**: Shared by both prover and verifier. Operations are defined once and passed to both sides — the verifier replays only the *successful* operations the prover acknowledged.

---

## Smart Contracts

`ergo_avltree_rust` is a pure cryptographic library with **no ErgoScript contracts defined within the repository itself**. However, it is the direct cryptographic backend for ErgoScript's built-in AVL tree verification capabilities.

### ErgoScript Integration Points

ErgoScript exposes AVL tree operations natively through its context and type system:

- **`AvlTree` type**: A first-class ErgoScript type representing an authenticated AVL+ tree. An `AvlTree` value encodes the digest, key length, optional value length, and enabled-operations flags.
- **`avlTree.contains(key, proof)`**: Verifies a membership proof against the tree's current digest.
- **`avlTree.get(key, proof)`**: Returns `Option[Coll[Byte]]` — the value associated with a key, verified against the digest.
- **`avlTree.insert(operations, proof)`**: Returns `Option[AvlTree]` — applies insert operations and returns the updated tree if proof is valid.
- **`avlTree.update(operations, proof)`**: Returns `Option[AvlTree]` — applies update operations.
- **`avlTree.remove(operations, proof)`**: Returns `Option[AvlTree]` — applies removals.

###