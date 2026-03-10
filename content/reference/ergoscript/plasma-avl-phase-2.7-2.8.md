---
title: "Plasma-AVL Phase 2.7-2.8 Staging and Fraud Proof Patterns"
category: reference
difficulty: advanced
tags: [avl-tree, plasma-toolkit, leaderboard, fraud-proof, ergoscript]
author: CannonQ
source: original
source_url: ""
license: AGPL-3.0
updated: 2026-03-09
---
# Phase 2.7/2.8 Patterns — Detailed Reference

Lessons from a 1304-byte staging/challenge contract with 2 spending paths (payout + fraud proof), on-chain scoring formula, leaderboard AVL insert+update, Season Box spending/recreation, and off-chain score parity. Tested on Ergo mainnet, Run 13 (heights 1733815–1733891, Mar 2026). 68/68 tests passed.

## Table of Contents

1. Staging Contract — 2-Path Architecture
2. Path A — Payout TX (Phase 2.7)
3. Path B — Fraud Proof TX (Phase 2.8)
4. On-Chain Scoring Formula
5. Off-Chain Score Computation (Bit-Identical Parity)
6. Leaderboard AVL Tree (Season Box R5)
7. LeaderboardManager — Second PlasmaMap
8. R7 Entry Layout (86 bytes)
9. R9 Packed Data (64 bytes)
10. Season Box Spending vs DataInput
11. P2PK ErgoTree Reconstruction
12. JitCost Measurement Pattern

---

## 1. Staging Contract — 2-Path Architecture

A single contract guards the staging box with two spending paths via `pathId` context variable:

```
Context vars (Staging Box input):
  Path A (pathId=1): 0=pathId, 1=insertProof, 2=seasonNftId, 3=insertCount,
                     4=updateProof, 5=lbKeys, 6=lbValues
  Path B (pathId=2): 0=pathId, 1=challengedIndex, 2=seasonNftId, 3=challengerAddress
```

Path selection:

```ergoscript
val pathId = getVar[Int](0).get
if (pathId == 1) {
  // PATH A: Payout — challenge window expired
  sigmaProp(windowExpired && payoutValid && leaderboardValid && bondReturned)
} else {
  // PATH B: Fraud Proof — within challenge window
  sigmaProp(withinWindow && scoreMismatch && refundsValid && bondToChallenger)
}
```

**Key difference from Phase 2.5 race contract:** The staging contract uses `if/else` (2 paths), not `if/else if/else` (3 paths). Path A and B are mutually exclusive by timing: `HEIGHT >= challengeDeadline` vs `HEIGHT < challengeDeadline`.

---

## 2. Path A — Payout TX (Phase 2.7)

### TX Structure

```
INPUTS:  [0] Staging Box (guarded by staging contract)
         [1] Season Box (spent and recreated — first time spent, not a dataInput)

OUTPUTS: [0] Recreated Season Box (R5 updated with leaderboard, everything else preserved)
         [1..N] Payout outputs (one per entrant with payoutAmount > 0)
         [N+1] Resolver bond return (to R8 address)
```

### Season Box Spending — Self-Replicating Pattern

Path A is the **first time the Season Box is spent** (all prior TXs used it as a read-only dataInput). The contract validates a full self-replication:

```ergoscript
val seasonBox = INPUTS(1)
val newSeasonBox = OUTPUTS(0)
val seasonSelfReplicating = newSeasonBox.propositionBytes == seasonBox.propositionBytes
val seasonValuePreserved = newSeasonBox.value >= seasonBox.value
val seasonNftPreserved = newSeasonBox.tokens.exists {
  (t: (Coll[Byte], Long)) => t._1 == seasonNftId
}
// R4, R6, R7, R8, R9 preserved (immutable config)
val seasonR4Preserved = newSeasonBox.R4[Coll[Long]].get == seasonBox.R4[Coll[Long]].get
// ... same for R6, R7, R8, R9
// R5 updated separately (leaderboard AVL)
```

### Scala Side — Season Box Recreation

```scala
val inputErgoTree = seasonBox.getErgoTree
val replicatedContract = new ErgoTreeContract(inputErgoTree, NetworkType.MAINNET)

val newSeasonBox = ctx.newTxBuilder().outBoxBuilder()
  .value(seasonBox.getValue)
  .contract(replicatedContract)
  .tokens(seasonNft)
  .registers(
    seasonR4,               // R4: config preserved
    lbUpdate.newDigest,     // R5: updated leaderboard AVL digest
    seasonR6, seasonR7, seasonR8, seasonR9  // R6–R9: preserved
  )
  .build()
```

### Bond Return Calculation

```ergoscript
val totalPayouts = payoutAmounts.fold(0L, { (acc: Long, v: Long) => acc + v })
val bondOutputIdx = 1 + payoutCount
val bondOutput = OUTPUTS(bondOutputIdx)
val bondReturned = bondOutput.propositionBytes == resolverAddr &&
  bondOutput.value >= SELF.value - totalPayouts - 2200000L  // fee tolerance
```

---

## 3. Path B — Fraud Proof TX (Phase 2.8)

### TX Structure

```
INPUTS:      [0] Staging Box
DATA INPUTS: [0] Season Box (read-only — NOT spent)

OUTPUTS: [0..N-1] Refund outputs (entry fee to each entrant)
         [N] Bond to challenger
```

### Key Difference: Season Box as DataInput

Path B uses the Season Box as a **dataInput** (read-only) — it only needs to read weights and focusStatIndex. Path A **spends** the Season Box because it updates the leaderboard.

```ergoscript
// Path A:
val seasonBox = INPUTS(1)  // spent and recreated

// Path B:
val seasonBox = CONTEXT.dataInputs(0)  // read-only
```

### Refund Logic

On successful fraud proof, all entrants get their entry fee back (race voided):

```ergoscript
val refundsValid = results.indices.forall { (i: Int) =>
  val payoutAddr = results(i).slice(50, 86)  // 36-byte P2PK ErgoTree
  OUTPUTS(i).propositionBytes == payoutAddr &&
  OUTPUTS(i).value >= entryFee
}

val challengerAddr = getVar[Coll[Byte]](3).get
val bondOutput = OUTPUTS(results.size)
val bondToChallenger = bondOutput.propositionBytes == challengerAddr &&
  bondOutput.value >= resolverBond
```

---

## 4. On-Chain Scoring Formula

The full scoring formula runs in ErgoScript for fraud proof verification. All Long arithmetic, no floating point, no bitwise operators.

### Step-by-Step

```ergoscript
// Step 1: Weighted base power (x1000 scale)
val basePower_s = stat0 * weights(0) + stat1 * weights(1) + ... + stat7 * weights(7)

// Step 2: Fatigue modifier [5000, 10000] = [0.50, 1.00]
val fatigueMod_s = 10000L - fatigue_s * 50L / 100L

// Step 3: Sharpness modifier [8000, 10500] = [0.80, 1.05]
val sharpnessMod_s = 8000L + sharpness_s * 25L / 100L

// Step 4: RNG pipeline — blake2b256 + sign-bit clear
val seed = raceBoxId ++ blockHash ++ tokenIdBytes
val hash = blake2b256(seed)
val rawLong = byteArrayToLong(hash.slice(0, 8))
val longMin = -9223372036854775807L - 1L    // Long.MIN_VALUE (can't write literal)
val absRaw = if (rawLong >= 0L) rawLong else rawLong - longMin
val rngCentered = absRaw % 20001L - 10000L  // [-10000, +10000]

// Step 5: Focus swing
val effectiveFocus_s = if (focusStatIndex == 0L) stat0 else if ... else stat7
val denom = 8000L + baseBudget * 100L
val focusSwing_s = 3000L * (denom - effectiveFocus_s) / denom

// Step 6: Luck
val luck_s = focusSwing_s * rngCentered / 10000L

// Step 7: Final score — SINGLE DIVISION (not interleaved)
val preLuck_s = basePower_s * fatigueMod_s * sharpnessMod_s / 100000000L
val finalScore_s = preLuck_s * (10000L + luck_s) / 10000L
```

### Critical Parity Points

1. **`absRaw` uses `rawLong - Long.MIN_VALUE`** for negatives — NOT conditional negation (`-rawLong`). This is the arithmetic equivalent of `rawLong & 0x7FFFFFFFFFFFFFFF` (bitwise AND unavailable in ErgoScript).

2. **`Long.MIN_VALUE` composed as `-9223372036854775807L - 1L`** — the ErgoScript parser cannot parse `9223372036854775808` (overflows Long). Two-step composition required.

3. **Single division** for `preLuck_s` — `basePower * fatigueMod * sharpnessMod / 100000000` in one step. NOT interleaved (`/ 10000 * sharpnessMod / 10000`). Single division matches the TypeScript reference oracle. Interleaved division loses precision at certain edge values (test 4j confirms: single=99, interleaved=98).

4. **Overflow analysis:** Max `basePower_s * fatigueMod_s * sharpnessMod_s` = 7,600,000 * 10,000 * 10,500 = 798,000,000,000,000. Long.MAX = 9.2 * 10^18. No overflow.

5. **`focusStatIndex` if/else chain** — ErgoScript cannot dynamically index a `Coll` of named vals. Use explicit if/else chain for all 8 stat indices.

### Snapshot Parsing (11 Shorts from 54 bytes)

Same byte-parsing pattern as training contract — arithmetic unsigned-byte conversion:

```ergoscript
val indices11 = Coll(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
val shorts = indices11.map { (i: Int) =>
  val off = 32 + i * 2
  val hi = snapshot(off).toLong
  val lo = snapshot(off + 1).toLong
  val ulo = if (lo < 0L) lo + 256L else lo
  hi * 256L + ulo
}
```

---

## 5. Off-Chain Score Computation (Bit-Identical Parity)

The Scala off-chain scoring must produce the **exact same Long value** as the ErgoScript on-chain formula for the same inputs. Any difference causes either false-positive or false-negative fraud proofs.

```scala
// Uses scorex.crypto.hash.Blake2b256 — same implementation as ErgoScript's blake2b256()
val hash = Blake2b256.hash(seed)
// Uses ByteBuffer.wrap(hash.take(8)).getLong — same as ErgoScript's byteArrayToLong()
val rawLong = ByteBuffer.wrap(hash.take(8)).getLong
// Same absRaw formula
val absRaw = if (rawLong >= 0L) rawLong else rawLong - Long.MinValue
```

**Verification pattern:** `FraudProofTxBuilder.verifyAllScores()` parses the staging box registers, recomputes all scores, and returns indices where `expectedScore != claimedScore`.

---

## 6. Leaderboard AVL Tree (Season Box R5)

### Schema

- **Key:** 32 bytes = `blake2b256(seasonNftId ++ tokenId)`
- **Value:** 14 bytes = `LeaderboardEntry`

```
Offset 0–1:   leaguePoints (Short)
Offset 2–3:   wins (Short)
Offset 4–5:   places (Short)
Offset 6–7:   shows (Short)
Offset 8–9:   racesEntered (Short)
Offset 10–13: lastRaceHeight (Int)
```

### Insert/Update Split in ErgoScript

The contract handles mixed inserts (new creatures) and updates (returning creatures) with separate proofs:

```ergoscript
val insertProof = getVar[Coll[Byte]](1).get
val insertCount = getVar[Int](3).get
val lbKeys = getVar[Coll[Coll[Byte]]](5).get
val lbValues = getVar[Coll[Coll[Byte]]](6).get

val insertPairs = lbKeys.slice(0, insertCount).zip(lbValues.slice(0, insertCount))
val updatePairs = lbKeys.slice(insertCount, lbKeys.size).zip(lbValues.slice(insertCount, lbValues.size))

val treeAfterInserts = if (insertCount > 0) {
  leaderboardTree.insert(insertPairs, insertProof).get
} else {
  leaderboardTree
}

val finalTree = if (updatePairs.size > 0) {
  val updateProof = getVar[Coll[Byte]](4).get
  treeAfterInserts.update(updatePairs, updateProof).get
} else {
  treeAfterInserts
}

val leaderboardValid = newLeaderboardTree.digest == finalTree.digest
```

**Key pattern:** Inserts first, then updates. The insert proof is generated against the original tree, the update proof against the tree-after-inserts. Two separate proofs in two separate context vars.

### Coll[Coll[Byte]] Context Vars for Keys/Values

Keys and values are passed as `Coll[Coll[Byte]]` context vars. Built via `RaceCreator.buildCollCollByte()` (same utility used for R5 snapshots in Phase 2.2). Confirmed working on mainnet with 2 entries.

---

## 7. LeaderboardManager — Second PlasmaMap

A second LevelDB-backed PlasmaMap, separate from the creature state tree. Simpler than PlasmaService:

- **No pessimistic queue** — leaderboard updates are serialized by staggered race deadlines
- **Commit/rollback** for mempool resilience (same pattern, simpler)

```scala
class LeaderboardManager(dbPath: String) {
  private var plasmaMap: PlasmaMap[Array[Byte], LeaderboardEntry] = newEmptyMap()

  def updateForRace(seasonNftId: Array[Byte], results: Seq[LeaderboardRaceResult], raceHeight: Int)
    : Either[String, LeaderboardUpdateResult]

  def commitPending(): Either[String, String]    // persist to LevelDB
  def rollbackPending(): Either[String, String]  // rebuild from LevelDB
}
```

**Key:** `blake2b256(seasonNftId ++ tokenId)` — not just the tokenId. This scopes entries to a season.

**ByteConversion for LeaderboardEntry:** 14-byte fixed-length serialization via `ByteBuffer.putShort/putInt`.

**Rebuild on rollback:** PlasmaMap inserts can't be undone, so rollback does a full rebuild from LevelDB. This is acceptable because leaderboard updates are infrequent.

---

## 8. R7 Entry Layout (86 bytes, updated from 50 in Phase 2.5)

```
Offset 0–31:  tokenId (32 bytes, blake2b256 of creature NFT ID)
Offset 32–39: claimedScore (Long, x1000 scaled)
Offset 40–47: payoutAmount (Long, nanoERG)
Offset 48–49: lpCredits (Short)
Offset 50–85: payoutAddress (36 bytes, P2PK ErgoTree)
```

**Why 36 bytes, not 38:** P2PK ErgoTree = `0x0008cd` prefix (3 bytes) + 33-byte compressed EC point = 36 bytes. This is the ErgoTree serialization, not the address encoding (which adds network byte + checksum = 38 bytes). The contract uses `propositionBytes` comparison, which operates on ErgoTree bytes.

**Phase 1 limitation:** All payout addresses assumed to be P2PK (36 bytes fixed). Script address support deferred to Phase 4.

---

## 9. R9 Packed Data (64 bytes, updated from 32 in Phase 2.5)

```
Bytes 0–31:  raceBoxId (32 bytes, original race box ID from Phase 2.5 resolution)
Bytes 32–63: blockHash (32 bytes, pinned block hash at deadline+1)
```

```ergoscript
val r9Data = SELF.R9[Coll[Byte]].get
val raceBoxId = r9Data.slice(0, 32)
val blockHash = r9Data.slice(32, 64)
```

**Why both are needed:** The RNG seed is `raceBoxId ++ blockHash ++ tokenId`. The resolution keeper (off-chain) uses the race box ID, but the fraud proof runs on the staging box — `SELF.id` would be the staging box ID, not the race box ID. R9 carries the original race box ID forward.

---

## 10. Season Box Spending vs DataInput

| Path | Season Box Role | Why |
|------|----------------|-----|
| Path A (Payout) | INPUTS[1] — spent and recreated | Leaderboard R5 is updated |
| Path B (Fraud Proof) | CONTEXT.dataInputs(0) — read-only | Only needs weights and focusStatIndex |
| Phase 2.5 (Resolution) | DataInput — read-only | Only needs validation, no state change |
| Phase 1.4 (Training) | DataInput — read-only | Only needs config |

Path A is the first time the Season Box is spent in the entire lifecycle. All prior phases used it as a dataInput.

---

## 11. P2PK ErgoTree Reconstruction

To build output boxes targeting addresses stored in R7 (36-byte ErgoTree bytes):

```scala
import sigmastate.Values.ErgoTree
import org.ergoplatform.appkit.impl.ErgoTreeContract

val payoutAddrBytes = resBytes.slice(50, 86)  // 36 bytes from R7
val payoutTree = ErgoTree.fromBytes(payoutAddrBytes)
val payoutContract = new ErgoTreeContract(payoutTree, NetworkType.MAINNET)

ctx.newTxBuilder().outBoxBuilder()
  .value(payoutAmount)
  .contract(payoutContract)
  .build()
```

**`ErgoTree.fromBytes`** parses raw ErgoTree bytes back into an `ErgoTree` object. Works for P2PK trees (36 bytes). Confirmed on mainnet.

For the challenger address (passed via context var), use `Address.toPropositionBytes`:

```scala
val challengerPropBytes = challengerAddress.toPropositionBytes
val stagingBoxWithCtx = stagingBox.withContextVars(
  ContextVar.of(3.toByte, ErgoValue.of(challengerPropBytes))
)
```

---

## 12. JitCost Measurement Pattern

Measure JIT cost before signing using `prover.reduce()`:

```scala
val cost = prover.reduce(tx, 0).getCost()
println(s"[JitCost] Path A (Payout): $cost")
val signedTx = prover.sign(tx)
```

**Measured results (mainnet, Run 13):**

| Path | JitCost | Budget | % Used |
|------|---------|--------|--------|
| Path A (Payout) | 168,695 | 500,000 | 33.7% |
| Path B (Fraud Proof) | 164,402 | 500,000 | 32.9% |
| Path B (Negative — correct score) | 164,337 | 500,000 | 32.9% |

Both paths are well within budget. Path B cost is dominated by `blake2b256` (~5,285 JitCost) and the scoring formula arithmetic.
