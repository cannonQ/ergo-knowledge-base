---
title: Plasma / AVL tree state
description: Plasma / AVL tree state — off-chain authenticated data with on-chain proof verification, PlasmaMap pattern
tags: [plasma-avl-tree, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [paideiadao/paideia-contracts, ergoplatform/sigmastate-interpreter]
---
# Plasma / AVL Tree State: Off-Chain Authenticated Data with On-Chain Proof Verification

## Overview

### What Is This Pattern?

The **Plasma / AVL tree pattern** (also called the **PlasmaMap pattern**) enables Ergo smart contracts to reason about arbitrarily large datasets without storing that data on-chain. Instead of placing every key-value pair inside a Box's Registers, only a **cryptographic commitment** — the root digest of an Authenticated AVL tree — lives on-chain. The full dataset is maintained off-chain by operators or users, who produce **cryptographic membership/modification proofs** and submit them alongside transactions. The ErgoScript contract verifies those proofs against the committed digest, then updates the digest to reflect whatever insertions, deletions, or lookups were performed.

This is Ergo's native answer to Ethereum's plasma/rollup scalability problem. Because Ergo's `AvlTree` type is a **first-class primitive in ErgoScript and the sigma-state interpreter**, proof verification happens inside the contract with no external oracle or trusted third party.

### Why Does It Exist?

Ergo's eUTXO model charges **Storage Rent** on every byte stored in a Box after ~4 years. Packing thousands of staker records, allowlist entries, or order-book positions directly into Registers is:

1. **Cost-prohibitive** — Storage Rent grows linearly with Register size.
2. **Computationally bounded** — ErgoScript execution has a cost limit per transaction.
3. **Inflexible** — a Box cannot be arbitrarily resized; its data is fixed at creation.

AVL trees solve all three: the on-chain footprint is a constant 33-byte digest regardless of how many entries the tree holds.

### When to Use This Pattern

| Situation | Use Plasma/AVL? |
|---|---|
| Allowlist / denylist with thousands of addresses | ✅ Yes |
| Staking registry tracking per-user balances | ✅ Yes (see Paideia) |
| Order book or AMM tick-map with many price levels | ✅ Yes |
| Simple 2-of-3 multisig treasury | ❌ No, overkill |
| Token vesting for a handful of recipients | ❌ No, use Registers |
| State that changes in every block across many users | ✅ Yes |

---

## How It Works

### Conceptual Flow

```
Off-chain world                          On-chain world
─────────────────────────────────────    ──────────────────────────────────
Full AVL tree data (keys + values)  →→   Box Register R4: AvlTree digest
                                          (33-byte commitment)
Operator performs lookup / update   →→   Transaction input includes:
and generates a Proof (byte array)        - Context extension with proof bytes
                                          - New digest in output Box R4
Contract verifies proof against           ErgoScript calls .update() /
current digest → accept / reject          .insert() / .contains()
```

### Step-by-Step Transaction Lifecycle

**Step 1 — Bootstrap: Create the State Box**

A **Singleton / State NFT** is minted in the same transaction that creates the state Box. The NFT's Token ID acts as a globally unique identifier for the contract instance. The Box's Register `R4` is set to the initial AVL tree digest (typically an empty tree or a pre-populated snapshot).

```
Genesis TX:
  Output 0: State Box
    Tokens:  [stateNFT: 1]
    R4:      AvlTree { digest: <initial_digest>, flags: INSERT|UPDATE|DELETE }
    R5–R8:   application-specific state
    ErgoTree: <plasmaContract>
```

**Step 2 — Off-Chain: Maintain the Full Tree**

A backend service (TypeScript, Python, or JVM) holds the complete key-value dataset in an `AuthenticatedTrieMap` (provided by the `scorex-crypto` library via `ergo-appkit` or `sigma-rust`). This is the **source of truth** for all off-chain data.

**Step 3 — Off-Chain: Generate Proofs**

Before constructing a transaction, the operator calls the tree's `.proveUpdate()`, `.proveInsert()`, `.proveLookup()`, or `.proveDelete()` method. This produces a serialized `Proof` byte array that cryptographically certifies the operation is consistent with the current root digest.

**Step 4 — Construct the Transaction**

The proof bytes are injected into the transaction via a **Context extension** (`ContextVar`). The Context extension is a per-input map of `Byte → ErgoValue[_]` that extends the ErgoScript context for that specific input — it does not consume box space.

```
Spend TX:
  Input 0: State Box (consumed)
    ContextVar(id=1): Coll[Byte] = <proof_bytes>
  Output 0: New State Box
    Tokens:  [stateNFT: 1]
    R4:      AvlTree { digest: <new_digest> }   ← updated by contract
    R5–R8:   updated application state
```

**Step 5 — On-Chain: Contract Verifies and Transitions**

The ErgoScript contract:
1. Reads the current `AvlTree` from `SELF.R4`.
2. Reads the proof from `getVar[Coll[Byte]](1).get`.
3. Calls the appropriate tree operation (`.update()`, `.insert()`, `.contains()`), passing the proof.
4. The operation returns `Some(newTree)` if valid, `None` if the proof is invalid.
5. Asserts that the **output Box's R4** matches the new tree's digest.
6. Enforces that the output Box still carries the State NFT.

---

## Implementation

### 1. ErgoScript Contract (`plasmaStaking.es`)

This is drawn directly from the Paideia staking contract. Annotations explain each AVL tree operation.

```scala
{
  // ── State stored in the current Box ──────────────────────────────────────
  // R4: the AVL tree commitment. `AvlTree` is a first-class ErgoScript type
  // whose `.digest` field is the 33-byte root hash + balance bit.
  val stakeState    = SELF.R4[AvlTree].get

  // R5: packed numeric parameters [emissionAmount, emissionDelay,
  //     cycleLength, nextSnapshot, stakerCount, totalStaked]
  val emissionAmount = SELF.R5[Coll[Long]].get(0)
  val emissionDelay  = SELF.R5[Coll[Long]].get(1).toInt
  val cycleLength    = SELF.R5[Coll[Long]].get(2)
  val nextSnapshot   = SELF.R5[Coll[Long]].get(3)
  val stakers        = SELF.R5[Coll[Long]].get(4)
  val totalStaked    = SELF.R5[Coll[Long]].get(5)

  // R6: snapshot history — Coll of (snapshotEpoch, (totalStaked, AvlTree))
  // Each snapshot stores a historical AVL tree digest for reward calculations.
  val snapshots = SELF.R6[Coll[(Long,(Long,AvlTree))]].get

  // ── Outputs ──────────────────────────────────────────────────────────────
  val successor     = OUTPUTS(0)                    // the new State Box
  val newStakeState = successor.R4[AvlTree].get     // must be updated digest

  // ── Proof injection via Context extension ────────────────────────────────
  // ContextVar 1 carries the serialized AVL proof bytes.
  // `getVar` is O(1) and does NOT read the full tree — only the proof path.
  val proof         = getVar[Coll[Byte]](1).get

  // ── STAKE action: insert a new staker entry ───────────────────────────────
  // The key is the staker's ErgoTree bytes (or a hash thereof).
  // The value is the staked amount serialised as 8 bytes (Long).
  val stakerKey     = INPUTS(1).propositionBytes     // staker's P2PK box
  val stakeAmount   = INPUTS(1).tokens(0)._2         // governance token amount

  // `insert` returns Option[AvlTree]. `get` throws if proof is invalid —
  // this is the primary security enforcement point.
  val insertResult  = stakeState.insert(
    Coll((stakerKey, longToByteArray(stakeAmount))),
    proof
  ).get  // ← contract FAILS (rejects TX) if proof doesn't match digest

  // ── Verify the output carries the correct new digest ─────────────────────
  // `digest` is the 33-byte serialised root. The new Box must commit to
  // exactly the tree that results from applying the proven operation.
  val correctDigest = insertResult.digest == newStakeState.digest

  // ── Singleton NFT continuity check ───────────────────────────────────────
  // Ensures this is the genuine state box, not a forgery.
  val nftPreserved  = successor.tokens(0)._1 == SELF.tokens(0)._1

  // ── Minimum box value and value continuity ───────────────────────────────
  val valuePreserved = successor.value >= SELF.value

  sigmaProp(correctDigest && nftPreserved && valuePreserved)
}
```

**Key ErgoScript AVL tree methods:**

| Method | Signature | Description |
|---|---|---|
| `.insert(entries, proof)` | `(Coll[(Coll[Byte], Coll[Byte])], Coll[Byte]) => Option[AvlTree]` | Insert key-value pairs; returns new tree or None |
| `.update(entries, proof)` | same shape | Update existing keys |
| `.delete(keys, proof)` | `(Coll