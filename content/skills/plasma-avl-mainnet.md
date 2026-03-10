---
title: "Plasma-Toolkit AVL Tree Operations on Ergo Mainnet"
category: skill
difficulty: advanced
tags: [avl-tree, plasma-toolkit, appkit, scala, mainnet]
author: CannonQ
source: original
source_url: ""
license: AGPL-3.0
updated: 2026-03-09
---

# Plasma-Toolkit AVL Tree Operations on Ergo Mainnet

## Overview

This skill covers using the Plasma-Toolkit library (GetBlok-Plasma fork by K-Singh) to build AVL tree proof round-trip pipelines on Ergo mainnet with ergo-appkit 5.0.4 and Scala 2.12. Developed through real mainnet deployments (Feb–Mar 2026) including a 4-TX chain test, Phase 1.1 on-chain AVL proof verification, Phase 1.3/1.4 training contracts (2290-byte ErgoTree, 7 context vars, JIT cost ~1420), Phase 2.1/2.2 race entry contracts (640-byte ErgoTree, 6 context vars, 2 DataInputs, `Coll[Coll[Byte]]` registers, AVL read-only lookup, 7-TX chain), Phase 2.4/2.5/2.6 race resolution (1223-byte ErgoTree, 3 paths, CONTEXT.headers), and Phase 2.7/2.8 staging/fraud proof contracts (1304-byte ErgoTree, on-chain scoring formula, leaderboard AVL insert+update, JIT cost 168K/164K).

**Prerequisite:** Read the `ergoscript-appkit-mainnet` skill first — this skill builds on the TX chaining, mnemonic API, and ErgoTree patterns documented there.

---

## Dependency Setup

### Plasma-Toolkit Version Selection — CRITICAL

| Version | sigma namespace | Compatible with appkit 5.0.4? |
|---|---|---|
| v1.0.4 | `sigma.data.AvlTreeFlags` (sigma 6.x) | **NO** — compile fails |
| v1.0.3 | `sigmastate.AvlTreeFlags` (sigma 5.x) | **YES** |

**Always use v1.0.3 with appkit 5.0.4.** Version 1.0.4 targets a deleted SNAPSHOT of appkit (`1381ea75-SNAPSHOT`) and sigma 6.x package namespaces.

**plasma-toolkit 1.0.3 resolves normally from Maven.** No `lib/` directory or unmanaged jars needed. The only jars that ever required `lib/` were unreleased 1.0.4 builds, which are incompatible with appkit 5.0.4.

### build.sbt

```scala
name := "avl-roundtrip"
version := "0.1.0"
scalaVersion := "2.12.18"

libraryDependencies ++= Seq(
  // CRITICAL: use 1.0.3, NOT 1.0.4 — see version table above
  ("io.github.k-singh" %% "plasma-toolkit" % "1.0.3")
    .exclude("org.ethereum", "leveldbjni-all"),  // Not needed for in-memory PlasmaMap
  "org.ergoplatform"    %% "ergo-appkit"      % "5.0.4",
  "org.scalatest"       %% "scalatest"        % "3.2.17" % Test,
  "org.slf4j"            % "slf4j-jdk14"      % "1.7.36",
  "javax.xml.bind"       % "jaxb-api"         % "2.4.0-b180830.0359"
)

// CRITICAL: Plasma-Toolkit pulls deleted SNAPSHOTs — force released versions
dependencyOverrides ++= Seq(
  "org.ergoplatform"     %% "ergo-appkit"     % "5.0.4",
  "org.scorexfoundation" %% "scrypto"         % "2.3.0"
)

resolvers ++= Seq(
  "New Sonatype Releases" at "https://s01.oss.sonatype.org/content/repositories/releases/",
  "Sonatype Releases"     at "https://oss.sonatype.org/content/repositories/releases/",
  "Sonatype Snapshots"    at "https://oss.sonatype.org/content/repositories/snapshots/",
  "Bintray"               at "https://jcenter.bintray.com/"
)

fork := true
javaOptions ++= Seq("-Xmx2g")
```

### Why Each Override Exists

- **`leveldbjni-all` excluded — NEVER add this as a direct dependency:** The artifact `org.ethereum:leveldbjni-all:1.18.3` does not exist in any public Maven repo. The `.exclude()` removes the transitive reference. If you need LevelDB for persistence, use `"org.iq80.leveldb" % "leveldb" % "0.12"` (see `references/phase-1.1-patterns.md`).
- **`ergo-appkit` override:** Plasma-Toolkit 1.0.3 depends on `ergo-appkit:5.0.3-19-fb04c04c-SNAPSHOT` which has been deleted from Sonatype.
- **`scrypto` override:** AppKit 5.0.4 pulls `scrypto:2.3.0-4-a0bc6176-SNAPSHOT` which has also been deleted.

---

## Import Namespaces — sigma 5.x vs 6.x

With appkit 5.0.4 you **must** use sigma 5.x imports:

```scala
// CORRECT — sigma 5.x (appkit 5.0.4 + plasma-toolkit 1.0.3)
import sigmastate.AvlTreeFlags

// WRONG — sigma 6.x (would need appkit 6.x + plasma-toolkit 1.0.4)
import sigma.data.AvlTreeFlags
import special.sigma.AvlTree          // Does NOT exist in sigma 5.x
import special.collection.{Coll, RType}  // Does NOT exist in sigma 5.x
```

If you see `sigma.data.*`, `special.sigma.*`, or `special.collection.*` in examples, those are 6.x. There is no direct `AvlTree` type access in sigma 5.x — use `ergoValue.toHex` for digest comparison (see `references/phase-1.1-patterns.md`).

---

## PlasmaMap Key Length — CRITICAL

PlasmaMap creates an AVL tree with `keyLength: 32` by default. **All keys must be exactly 32 bytes.** PlasmaMap does NOT hash keys internally.

```scala
// WRONG — 17 bytes, causes: IllegalArgumentException: requirement failed
val key = "test-creature-001".getBytes("UTF-8")
plasmaMap.insert((key, state))  // FAILS silently — tryOp = Failure

// CORRECT — pre-hash to 32 bytes
import scorex.crypto.hash.Blake2b256
val key = Blake2b256.hash("test-creature-001".getBytes("UTF-8"))
plasmaMap.insert((key, state))  // tryOp = Success(None) ← success for insert
```

**Failure mode:** PlasmaMap does not throw on key length mismatch. The `insert()` returns a `ProvenResult` whose `response.tryOp` is `Failure(...)`. The proof bytes are still non-empty but **invalid**. Always check `tryOp` after every operation.

For production with NFT tokenIds (already 32 bytes), pass them directly. For arbitrary string keys, always blake2b256-hash them first.

---

## ByteConversion Instances

PlasmaMap requires implicit `ByteConversion[K]` and `ByteConversion[V]` instances:

```scala
import work.lithos.plasma.ByteConversion

implicit val bytesKeyConversion: ByteConversion[Array[Byte]] =
  new ByteConversion[Array[Byte]] {
    override def convertToBytes(t: Array[Byte]): Array[Byte] = t
    override def convertFromBytes(bytes: Array[Byte]): Array[Byte] = bytes
  }
```

**Key Conversion Must Be Identity.** Do NOT hash inside the key `ByteConversion`. PlasmaMap may call `convertToBytes` internally — hashing there causes double-hashing.

---

## PlasmaMap Operations

```scala
val plasmaMap = new PlasmaMap[Array[Byte], MyState](
  AvlTreeFlags.AllOperationsAllowed, PlasmaParameters.default
)

// Insert — returns ProvenResult
val result = plasmaMap.insert((key, state))
result.response.head.tryOp match {
  case Success(None) => // Insert succeeded
  case Success(Some(old)) => // Key already existed
  case Failure(e) => // Operation failed — proof is INVALID
}
val proof: Proof = result.proof

// Batch Insert
val result = plasmaMap.insert(entries: _*)  // proof covers ALL entries

// Update
val result = plasmaMap.update((key, newState))

// Lookup — read-only, no tree mutation
val result = plasmaMap.lookUp(key)
val value: Option[MyState] = result.response.head.tryOp.toOption.flatten
val proof: Proof = result.proof  // same Proof class — .ergoValue works for context vars
```

**Lookup proofs** work with ErgoScript's `AvlTree.get(key, proof)` on mainnet (Phase 2.2). The proof format is the same `Proof` class as insert/update — `.ergoValue` produces the correct `ErgoValue[Coll[Byte]]` for context vars. The state box is used as a DataInput (read-only), not consumed.

---

## Passing Entries to ErgoScript

### Context Extension Variables (Recommended)

Constructing `ErgoValue[Coll[(Coll[Byte], Coll[Byte])]]` is **impossible** with appkit 5.0.4 / sigma 5.x — the required types exist only in sigma 6.x and the code does not compile. Pass key/value pairs as simple byte arrays via context extension variables.

**Scala side:**

```scala
val ctxVars = new java.util.ArrayList[ContextVar]()
ctxVars.add(ContextVar.of(0.toByte, proof.ergoValue))       // proof
ctxVars.add(ContextVar.of(1.toByte, ErgoValue.of(opType)))  // 0=insert, 1=update
ctxVars.add(ContextVar.of(2.toByte, ErgoValue.of(key)))     // 32-byte key
ctxVars.add(ContextVar.of(3.toByte, ErgoValue.of(value)))   // N-byte value

val boxWithCtx = stateBox.withContextVars(ctxVars.asScala: _*)
```

**ErgoScript side (tested on-chain, Phase 1.1):**

The contract uses `AvlTree.insert(entries, proof).get` / `.update(entries, proof).get` to compute a new digest, then validates `computedDigest == newTree.digest`. Key points:
- `.get` unwraps the `Option` — fails the script if the proof is invalid
- `compileContract` must set the ErgoTree size bit: `(rawTree.header | 0x08).toByte`
- Plasma-toolkit 1.0.3 proofs are compatible with ErgoScript's `AvlTree` operations on mainnet
- Entries built as `Coll((key1, value1))` from context vars

See `references/phase-1.1-patterns.md` for the full contract and batch entry patterns (2–10 entries via `isDefined` checks).

### Read-Only Lookup (Phase 2.2)

Single-key `get` returns `Option[Coll[Byte]]` — no tree mutation:

```scala
{
  val stateTree = CONTEXT.dataInputs(1).R5[AvlTree].get
  val lookedUpState = stateTree.get(creatureTokenId, avlProof).get
  val stateMatchesProof = lookedUpState == creatureStateBytes
}
```

- `.get` on the `Option` fails the script if the key is not found
- The state box is a DataInput — read-only, not consumed
- Proof comes from `plasmaService.lookup(key).proof.ergoValue` (same `Proof` class as insert/update)

---

### Leaderboard AVL — Insert + Update Split (Phase 2.7)

When a single TX must insert new keys AND update existing keys, use **two separate proofs** in two context vars. Insert proof is generated against the original tree; update proof against the tree-after-inserts:

```ergoscript
val insertPairs = lbKeys.slice(0, insertCount).zip(lbValues.slice(0, insertCount))
val updatePairs = lbKeys.slice(insertCount, lbKeys.size).zip(lbValues.slice(insertCount, lbValues.size))
val treeAfterInserts = if (insertCount > 0) {
  leaderboardTree.insert(insertPairs, insertProof).get
} else { leaderboardTree }
val finalTree = if (updatePairs.size > 0) {
  treeAfterInserts.update(updatePairs, updateProof).get
} else { treeAfterInserts }
```

Keys/values passed as `Coll[Coll[Byte]]` context vars. A second LevelDB-backed PlasmaMap manages leaderboard state separately from creature state. See `references/phase-2.7-2.8-patterns.md` for full schema and `LeaderboardManager`.

---

## ErgoScript Collection Operations — What Works

Tested on mainnet (Phase 1.3/1.4 through Phase 2.8). Key facts: `map`/`forall`/`fold` with closure capture work; `Coll[Coll[Long]]` and `Coll[Coll[Byte]]` register access works; `tokens.exists` requires explicit `(t: (Coll[Byte], Long))` annotation; dynamic indexing works on register collections but NOT on named `val` collections; `byteArrayToLong` is big-endian, matches Java `ByteBuffer.wrap(hash.take(8)).getLong`.

See `references/phase-1.3-1.4-patterns.md` for Coll operation code examples and `references/phase-2.1-2.2-patterns.md` for `Coll[Coll[Byte]]`, append validation, and lookup patterns.

---

## HEIGHT Mismatch: Prover vs Node — CRITICAL

The prover evaluates `HEIGHT` as `ctx.getHeight()` (current best block). The node evaluates at `ctx.getHeight() + 1` (the block being mined). If your contract checks `newLastAction == HEIGHT.toLong` and off-chain code uses `ctx.getHeight()`, the prover accepts but the node rejects.

Additionally, Ergo's `CleanupWorker` re-validates all mempool TXs when a new block arrives using the **new** HEIGHT. Any HEIGHT-dependent logic will fail re-validation if the TX sits in the mempool for >1 block.

**Fix:** Use ±10 tolerance in any contract that validates HEIGHT-derived values:

```scala
val hL = HEIGHT.toLong
val lastActionOk = newLastAction >= hL - 10L && newLastAction <= hL
```

**Do NOT try `ctx.getHeight() + 1` off-chain** — the prover still evaluates at `ctx.getHeight()`.

**Security analysis:** 10 blocks (~20 min) vs 180-block cooldown — negligible attack surface. See `references/phase-2.4-2.6-patterns.md` for the Run 12 evidence that ±1 was insufficient.

---


## CONTEXT.headers — Use `exists`, Never Direct Index — CRITICAL

`CONTEXT.headers` is a sliding window of 10 recent headers. `CONTEXT.headers(n)` returns the header at `HEIGHT - 1 - n`. When HEIGHT changes (new block), the index for a target height shifts — **TX is evicted from mempool.**

```ergoscript
// WRONG — HEIGHT-dependent, breaks in mempool
val pinnedBlockHash = CONTEXT.headers((HEIGHT - targetHeight - 2L).toInt).id

// CORRECT — mempool-resilient, searches all 10 headers
val pinnedBlockHash = getVar[Coll[Byte]](3).get
val hashVerified = CONTEXT.headers.exists { (h: Header) =>
  h.id == pinnedBlockHash && h.height == targetHeight.toInt
}
```

**Pattern:** Pass target block hash as a context variable, verify via `exists`. Costs more than direct indexing but is the ONLY mempool-safe approach. See `references/phase-2.4-2.6-patterns.md` for Run 13 evidence.

---

## Contract Fee Tolerance — CRITICAL

When a contract checks `output.value >= SELF.value - N`, the tolerance N **must** match or exceed the actual miner fee in the TX builder:

```ergoscript
// WRONG — tolerance (1.2M) < actual fee (2M) → script fails
val refundOk = refundOutput.value >= SELF.value - 1200000L

// CORRECT — tolerance (2.2M) > actual fee (2M)
val refundOk = refundOutput.value >= SELF.value - 2200000L
```

**Rule:** Always set tolerance ≥ actual fee + margin. See `references/phase-2.4-2.6-patterns.md`.

---

## State Box Register Layout

```
R4: SigmaProp  — owner public key (for spending authorization)
R5: AvlTree    — current AVL tree digest (updated each TX)
```

### R4 Type Confusion — GroupElement vs SigmaProp

`ErgoValue.of(ownerAddress.getPublicKey)` stores a GroupElement but appkit wraps it as `SigmaProp(ProveDlog(...))`. The contract must read as `SELF.R4[SigmaProp].get`, **not** `R4[GroupElement].get`.

---

## EIP-3 Address vs Master Key — CRITICAL

`prover.getAddress` returns the **master key address**, which typically has no UTXOs:

```scala
// WRONG: returns master key address — 0 wallet boxes found
val addr = prover.getAddress

// CORRECT: returns the EIP-3 derived address where funds are
val addr = Address.create(prover.getEip3Addresses.get(0).toString)
```

You must also call `.withEip3Secret(0)` on the prover builder.

---

## NFT Minting Without EIP-4 Register Conflicts

`outBoxBuilder().mintToken()` overwrites R4–R6 with EIP-4 metadata. If you need custom registers, use `.tokens()` directly:

```scala
val firstInputBoxId = fundingBoxes.get(0).getId.toString
val seasonNft = new ErgoToken(firstInputBoxId, 1L)  // Token ID = first input box ID

ctx.newTxBuilder().outBoxBuilder()
  .value(boxValue)
  .contract(contract)
  .tokens(seasonNft)                    // mint via .tokens(), not .mintToken()
  .registers(r4, r5, r6, r7, r8, r9)   // custom registers preserved
  .build()
```

Import: `org.ergoplatform.sdk.ErgoToken`.

---

## DataInputs API

DataInput boxes are read-only — not consumed. Use `new java.util.ArrayList[InputBox]()` with `.add(box)`, pass to `.withDataInputs(list)`. Access in ErgoScript via `CONTEXT.dataInputs(0)`. Order matters — `dataInputs(0)` is the first box added.

---

## Transaction Chaining — Full Pattern

All operations must be chained in a single `ergoClient.execute` block.

### Self-Replicating Output Contract

**CRITICAL:** Always copy the input box's ErgoTree for the output, never recompile:

```scala
import org.ergoplatform.appkit.impl.ErgoTreeContract
val replicatedContract = new ErgoTreeContract(stateBox.getErgoTree, NetworkType.MAINNET)
```

### Change Box Selection

**CRITICAL:** `getOutputsToSpend.get(1)` is NOT reliably the change box. Always iterate and pick the largest non-target output:

```scala
def findChangeBox(tx: SignedTransaction, targetBox: InputBox): InputBox = {
  val outputs = tx.getOutputsToSpend
  val targetId = targetBox.getId.toString
  var best: InputBox = null
  var maxVal = 0L
  for (i <- 0 until outputs.size()) {
    val b = outputs.get(i)
    if (b.getId.toString != targetId && b.getValue > maxVal) {
      maxVal = b.getValue; best = b
    }
  }
  best
}
```

### Multi-TX Chain (Proven for 7 TXs)

All TXs in a single `ergoClient.execute` block. Use `signed.getOutputsToSpend.get(0)` for state box, `findChangeBox(signed, stateBox)` for fee input. Builder functions return `SignedTransaction` to enable chaining. Proven: 7-TX chain confirmed in same block.

---

## INSERT vs UPDATE Metadata Validation

Fields "immutable after creation" need conditional checks — they're only immutable after the first write:

```scala
// WRONG: fails on insert because oldValue is all zeros
val baseBudgetOk = newBaseBudget == oldBaseBudget

// CORRECT: insert allows any value, update requires preservation
val baseBudgetOk = if (opType == 0) true else newBaseBudget == oldBaseBudget
```

---

## Mnemonic API — AppKit 5.0.4

```scala
val mnemonic = Mnemonic.create(phrase.toCharArray, Array.emptyCharArray)
ctx.newProverBuilder()
  .withMnemonic(mnemonic, false)   // false = no EIP-3 derivation prefix
  .withEip3Secret(0)               // REQUIRED for EIP-3 address access
  .build()
```

---

## Common Error → Fix Reference

| Error | Cause | Fix |
|---|---|---|
| `requirement failed` on insert/lookup tryOp | Key not 32 bytes | Pre-hash with `Blake2b256.hash()` |
| `sigma.data.AvlTreeFlags` not found | Plasma-Toolkit 1.0.4 + appkit 5.0.4 | Downgrade to plasma-toolkit 1.0.3 |
| `ergo-appkit:1381ea75-SNAPSHOT` not found | Deleted SNAPSHOT dependency | Add `dependencyOverrides` for appkit 5.0.4 |
| `leveldbjni-all:1.18.3` not found | Artifact doesn't exist | Exclude `org.ethereum:leveldbjni-all` |
| `Script reduced to false` | Any contract boolean check fails | Generic prover rejection — diagnose which condition failed |
| `Cannot getReg[GroupElement](4)` | R4 stored as SigmaProp, read as GroupElement | Use `SELF.R4[SigmaProp].get` |
| `overloaded method withMnemonic` | Missing boolean parameter | Add `, false` as second arg |
| `total inputs less than total outputs` | State box can't cover fee | Add feeBox parameter with wallet input |
| `404 not-found` on `getBoxesById` | UTXO not indexed for unconfirmed TX | Chain outputs via `getOutputsToSpend` |
| `Incorrect insert... this proof is wrong` | Key format mismatch between proof and contract | Ensure contract receives same 32-byte key used in PlasmaMap |
| `object sigma is not a member of package special` | Using `special.sigma.*` — sigma 6.x | Use `ergoValue.toHex` for digest |
| `object collection is not a member of package special` | Using `special.collection.Coll` — sigma 6.x | Use individual context vars instead |
| `constructor ErgoValue cannot be accessed` | Trying `new ErgoValue(...)` directly | Use `ErgoValue.of()` factory methods only |
| `found version conflict: circe 0.14.x vs 0.13.0` | http4s wants 0.14.x, sigma-state wants 0.13.0 | Add `libraryDependencySchemes` with `VersionScheme.Always` |
| `Iq80DBFactory` compile error | Case mismatch on class name | Correct: `Iq80DBFactory` (capital I, lowercase q, number 80) |
| 0 wallet boxes found | Using `prover.getAddress` (master key) | Use `prover.getEip3Addresses.get(0)` |
| `Success((false,N))` in node logs | Contract passes prover but fails at HEIGHT+1 | Add ±1 tolerance for HEIGHT checks |
| `Array[Nothing]` type inference | Missing explicit type on nested `ErgoValue` arrays | Add `: Array[sigma.Coll[java.lang.Long]]` |
| `mintToken` overrides R4–R6 | EIP-4 metadata clobbers custom registers | Use `.tokens()` instead of `.mintToken()` |
| `Success((false,162))` CleanupWorker eviction | `CONTEXT.headers(index)` shifts with HEIGHT | Use `CONTEXT.headers.exists` with context var |
| Path B "Script reduced to false" at sign | Fee tolerance < actual miner fee | Widen `SELF.value - N` tolerance to match fee |
| `Double spending attempt` (node 400) | Wallet UTXO already in mempool from prior TX | Wait for block confirmation or use a different UTXO |
| `Array[Nothing]` for `Coll[Coll[Byte]]` | Missing type annotation (same as Long variant) | Add `: Array[sigma.Coll[java.lang.Byte]]` |

---

## Debugging Checklist

1. **Is `tryOp` succeeding?** If `Failure(requirement failed)`, key length is wrong.
2. **Is R5 match true?** Compare `plasmaService.ergoValue` to `stateBox.getRegisters.get(1)`.
3. **Are trees matching?** Compare compiled vs input ErgoTree bytes.
4. **Is the change box correct?** Print its value — should be >> 0.001 ERG.
5. **Are entry keys the same bytes used by PlasmaMap?** Don't re-hash what's already hashed.
6. **Is the proof for the right operation?** Insert proof for insert, update proof for update.
7. **HEIGHT tolerance?** If contract validates HEIGHT-derived values, add ±1.
8. **Using EIP-3 address?** `prover.getAddress` is the master key, not the funded address.
9. **Lookup proof for get?** Use `plasmaService.lookup(key).proof.ergoValue` — same Proof class as insert/update.
10. **DataInput order?** `CONTEXT.dataInputs(0)` must match the first box in `withDataInputs`.
11. **Mempool eviction?** Check node logs for `Success((false,N))` — logic failure, not cost.
12. **CONTEXT.headers indexed or exists?** Direct indexing breaks in mempool. Always use `exists`.
13. **Fee tolerance >= actual fee?** Contract deduction tolerance must match TX builder fee.

---

## Measured Results (Mainnet, Feb–Mar 2026)

| Metric | Phase 1.0 (Chain) | Phase 1.4 (Training) | Phase 2.2 (Race Entry) | Phase 2.5 (Resolution) | Phase 2.7/2.8 (Staging) |
|---|---|---|---|---|---|
| ErgoTree size | 921 bytes | 2290 bytes | 640 bytes | 1223 bytes | 1304 bytes |
| Context vars | 2 | 7 | 6 | 4 (Path A) | 7 (Path A), 4 (Path B) |
| AVL tree ops | 0 | insert/update | get (read-only) | 0 | insert + update (Path A) |
| DataInputs | 0 | 1 (Season) | 2 (Season + State) | 1 (Season) | 0 (Path A), 1 (Path B) |
| Register types | — | Coll[Long], AvlTree | Coll[Coll[Byte]] x2 | R4–R9 (6 registers) | R4–R9 (6 registers) |
| TX chain depth | 4 | 4 | 7 | 1 | 1 |
| JIT cost | ~10,000 (est.) | ~1420 | not measured | not measured | **168,695** (A), **164,402** (B) |

---

## What This Skill Does NOT Cover

- Multi-party AVL tree operations (shared state between users)
- ErgoScript v2 / sigma 6.x (requires plasma-toolkit 1.0.4+ and appkit 6.x)
- JitCost measurement for batch contracts or large `Coll[Coll[Byte]]` registers (20+ entries)
- Class-restricted race entry validation on-chain (tested only with `rarityClassId = 0`)
- Resolution Keeper bot (Phase 2.9)
- Settlement box for large-season payout batching (Phase 3.x)

## Reference Files

- `references/phase-2.4-2.6-patterns.md` — Resolution paths A/B/C, CONTEXT.headers.exists, CleanupWorker eviction, fee tolerance, staging box registers, reclaim utilities
- `references/phase-2.7-2.8-patterns.md` — Staging/fraud proof contract (2-path), on-chain scoring, leaderboard AVL insert+update, off-chain score parity, Season Box spending/recreation, JitCost measurement
- `references/phase-1.1-patterns.md` — Batch entries (N-entry context var pattern), LevelDB sidecar persistence, AVL digest access under sigma 5.x, circe version conflict fix
- `references/phase-1.3-1.4-patterns.md` — ErgoScript Coll operations (map/forall/fold with closures), nested Coll registers, ErgoValue construction for nested types, insert vs update validation, NFT authentication
- `references/phase-2.1-2.2-patterns.md` — `Coll[Coll[Byte]]` register construction/access, AVL read-only lookup (`AvlTree.get`), append-only validation, de-duplication, permissionless contracts, `byteArrayToLong`, multi-DataInput, 7-TX chaining
