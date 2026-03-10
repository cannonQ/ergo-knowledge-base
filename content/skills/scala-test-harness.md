---
title: "Scala Test Harness for ErgoScript Contracts"
description: "Production patterns for building Scala/AppKit test harnesses that validate ErgoScript contracts on mainnet. Covers GroupElement vs SigmaProp, HEIGHT off-by-one, ErgoTree size bit, register copying, context variables, JitCost measurement, and a complete error→fix reference."
tags: [appkit, scala, testing, mainnet, ergoscript, harness, registers, height, jitcost]
category: skill
difficulty: advanced
sdk: [appkit]
updated: 2026-03-10
source: original
author: CannonQ
license: AGPL-3.0
---
# Writing a Scala Test Harness for ErgoScript Contracts

## Context

NftRentalV3 is an audited ErgoScript NFT rental contract (audit score 9/10) with
three spending paths: Path A (Rent, permissionless), Path B (Owner Reclaim,
signature-required), and Path C (Bot Return, permissionless after grace period).

The contract needed mainnet validation — all three paths exercised with real
transactions — without modifying the audited contract file. The solution was a
self-contained sbt project ("test harness") that inlines the same ErgoScript and
builds transactions against a local Ergo node.

## Project Structure

```
nft-rental-test/
  build.sbt                              # ergo-appkit 5.0.4, Scala 2.12.18
  project/build.properties               # sbt 1.9.8
  run.sh                                 # Sources ~/.secrets, maps env vars
  src/main/scala/NftRentalV3Test.scala   # Self-contained test harness
```

## What Worked Well

### 1. Phased CLI Design

Splitting the test into `phase0` through `phase5` (each invoked via
`./run.sh phaseN [args]`) was extremely practical:

- Each phase prints the exact next command with box IDs to copy-paste
- Phases can be re-run independently after failures
- Long waits (grace period) don't block debugging other issues
- Phase 0 (compile-only) catches script/config issues before spending ERG

### 2. Self-Contained Harness (No Imports from Contract)

The original NftRentalV3.scala has `System.exit(1)` in its env var loading —
importing any field triggers it. The harness inlines `RENTAL_SCRIPT` and all
helpers, using its own flexible `envOrDie()` fallback chain. This was the right
call — it avoided classpath coupling entirely.

### 3. `sendSafe` Pattern

Wrapping `ctx.sendTransaction()` to catch "already in mempool" errors made the
harness re-run tolerant. When a phase crashes after TX submission but before
verification, re-running doesn't fail on duplicate submission.

### 4. Explorer URL Required

`RestApiErgoClient.create()` needs the explorer URL as the 4th parameter:
```scala
RestApiErgoClient.create(NODE_URL, NETWORK, API_KEY, "https://api.ergoplatform.com")
```
Without it, `getBoxesById` fails silently or returns stale data.

### 5. Direct Register Copying

For successor boxes (rent, bot return), copying registers directly from the
input box (`regs.get(0)` for R4, `regs.get(3)` for R7, etc.) preserves exact
types and values. This bypasses all AppKit type conversion issues.

## Issues Encountered and Solutions

### Issue 1: GroupElement vs SigmaProp (CRITICAL)

**Problem:** `Address.getPublicKey()` in ergo-appkit 5.0.4 returns
`sigmastate.crypto.DLogProtocol.ProveDlog` (a SigmaProp), NOT
`sigma.GroupElement`. When passed to `ErgoValue.of()`, it matches the SigmaProp
overload, creating an `SSigmaProp` register instead of `SGroupElement`. The
contract's `SELF.R4[GroupElement].get` then throws:
```
sigmastate.eval.InvalidType: Cannot getReg[GroupElement](4):
invalid type of value TestValue(SigmaProp(ProveDlog(ECPoint(...))))
```

**Root Cause:** AppKit's ISO type conversion layer wraps GroupElement as SigmaProp
during `ErgoValue.of()` construction.

**Solution — For new boxes (listing):** Reflection-based `fixOutBoxR4` helper:
1. Build box with `OutBoxBuilder` (handles tokens correctly)
2. Access the internal `ErgoBoxCandidate` via reflection
3. Create `GroupElementConstant(ownerAddr.getPublicKey.value)` — `.value`
   extracts the raw `EcPointType` from `ProveDlog`
4. Replace R4 in the register map
5. Wrap in new `OutBoxImpl(fixedCandidate)`

**Solution — For successor boxes (rent, reclaim):** Copy `regs.get(0)` directly
from the input box. The on-chain serialization preserves the correct type, and
AppKit passes it through without re-conversion.

**On-chain evidence:** R4 prefix `07` = SGroupElement (correct), `08cd` =
SSigmaProp (wrong). A box created with the wrong type has R4 that ALL script
paths try to read, making the box permanently unspendable.

### Issue 2: Non-Singleton Token Selection

**Problem:** `findNftBox` correctly checked `tok.getValue == 1L`, but
`listForRent` used `nftBox.getTokens.get(0)` which grabs the first token in
the box. In a multi-token box, the NFT might not be at index 0. This sent
1,750,000 RSN tokens (not a singleton) into the rental contract.

**Solution:** Pass the specific `nftTokenId` to `listForRent`, use
`findTokenInBox(box, tokenId)` to locate the exact token, and add a
`require(token.getValue == 1L)` guard.

**Recovery:** The RSN box had correctly-typed R4, so Path B worked — but the
contract checks `b.tokens(0)._2 == 1L` in the output. Created a
`recoverFromContract` function that splits the token: output with exactly 1
token (satisfies contract) + second output with the remaining 1,749,999. All
1,750,000 RSN recovered.

### Issue 3: HEIGHT vs ctx.getHeight Off-by-One

**Problem:** The contract checks `b.R6[Int].get >= HEIGHT + rentalDuration`.
`ctx.getHeight` returns the last confirmed block, but `HEIGHT` in the script is
the block being mined (typically `ctx.getHeight + 1` or more). Setting
`expiryHeight = ctx.getHeight + duration` fails the lower bound check.

The `expiryTolerance` (10 blocks) only covers the UPPER bound — it allows the
expiry to be up to 10 blocks too high, not too low.

**Symptom:** Node rejects with `Scripts of all transaction inputs should pass
verification ... Success((false,333))` — script evaluates to false, not a type
error.

**Solution:** `expiryHeight = currentHeight + duration + 2` — a 2-block buffer
accounts for mining lag while staying well within the 10-block tolerance.

### Issue 4: ErgoTree Size Bit for Mainnet

**Problem:** Compiled ErgoScript doesn't include the size bit by default,
causing mainnet rejection.

**Solution:**
```scala
val sizedTree = new ErgoTree(
  (rawTree.header | 0x08).toByte,
  rawTree.constants,
  rawTree.root
)
```

### Issue 5: Scala 2.12 / AppKit 5.0.4 Quirks

- **No `ErgoToken` class** — it's `org.ergoplatform.sdk.ErgoToken` (found via
  jar inspection, not in `org.ergoplatform.appkit._`)
- **No numeric separators** — `1_000_000` is invalid in Scala 2.12, use
  `1000000`
- **`Mnemonic.create`** takes `(phrase.toCharArray, Array.emptyCharArray)` — no
  `SecretString` in 5.0.4
- **sigma `Coll[Byte]`** — register values return `sigma.Coll[Byte]`, not
  `Array[Byte]`. Need a `regBytes()` helper that handles both
- **Register indexing** — `getRegisters.get(0)` = R4, `.get(1)` = R5, etc. (R0-R3
  are mandatory registers)
- **EIP-3 derived addresses** — must use `.withEip3Secret(0)` and
  `prover.getEip3Addresses.get(0)` for the funded wallet address
- **scrypto SNAPSHOT deleted** — ergo-appkit 5.0.4 pulls a deleted SNAPSHOT
  dependency; fix with `dependencyOverrides += "org.scorexfoundation" %%
  "scrypto" % "2.3.0"`

### Issue 6: Verification Timeouts

**Problem:** `verifyNftInWallet` polled 30 times at 15s intervals (7.5 min
total), but transactions sometimes took 10-15 min to confirm, especially when
submitted near block boundaries.

**Solution:** Increased to 60 retries (15 min total). For the grace period wait
(Phase 4c), the `waitForHeight` function polls every 30s which is appropriate
for the ~70 min wait.

## Key Patterns for Future Harnesses

1. **Always copy registers from input boxes** when building successor outputs.
   Never reconstruct register values through AppKit's `ErgoValue.of()` unless
   you've verified the type mapping.

2. **Add +2 to any HEIGHT-dependent calculation** to account for the gap between
   `ctx.getHeight` (last confirmed) and `HEIGHT` (block being mined).

3. **Guard token operations** with amount/ID checks before sending transactions.
   A singleton assertion (`require(token.getValue == 1L)`) would have prevented
   the RSN incident.

4. **Include a `recover` command** in the harness from the start. Contract boxes
   with unexpected state need a dedicated recovery path.

5. **Use `require()` not `System.exit()`** in test code. Stack traces from
   `require` are far more debuggable than silent exits.

6. **P2PK proposition bytes are 36 bytes** (`0x0008cd` + 33-byte compressed EC
   point). Don't confuse with Ergo address encoding.

7. **Chain related TXs in a single `ergoClient.execute` block.** Boxes from a
   previous execute block cannot be fetched by ID in a new one — the node's UTXO
   endpoint may not find them. Use output references from signed transactions:
   ```scala
   val signedTx1 = prover.sign(tx1)
   val outputBox = signedTx1.getOutputsToSpend.get(0)
   // build tx2 using outputBox as input — all in the same execute block
   ```

8. **Measure JitCost before signing** with `prover.reduce()`:
   ```scala
   val reducedTx = prover.reduce(tx, 0)  // 0 = input index
   val cost: Int = reducedTx.getCost()   // same units as node's 500K budget
   val signedTx = prover.sign(tx)        // then sign normally
   ```
   This gives exact JitCost without submitting. Confirmed on mainnet (Phase 2.7/2.8
   of plasma-service: Path A = 168,695, Path B = 164,402).

9. **Reconstruct contracts from stored ErgoTree bytes** using `ErgoTree.fromBytes`:
   ```scala
   import sigmastate.Values.ErgoTree
   import org.ergoplatform.appkit.impl.ErgoTreeContract
   val payoutTree = ErgoTree.fromBytes(rawBytes)  // 36 bytes for P2PK
   val contract = new ErgoTreeContract(payoutTree, NetworkType.MAINNET)
   ```
   Use when payout addresses are stored as raw ErgoTree bytes in registers.
   `Address.toPropositionBytes` is the cleanest way to get those bytes from an
   `Address` object.

10. **Include all tokens in outputs when batching token-carrying boxes.** Without
    `.tokens(allTokens: _*)`, the builder throws `NotEnoughCoinsForChangeBoxesError`
    trying to create change boxes for unassigned tokens.

---

## ErgoScript Language Constraints (sigmastate 5.x)

These constraints apply to the contract source and affect how harness code must
construct matching values.

### No Bitwise Operators

ErgoScript v1 has no `<<`, `>>`, `|`, `&`, `^`. The compiler throws
`GraphBuildingException: Don't know how to buildNode(BitOp(...))`. Use arithmetic:

| Bitwise Op | Arithmetic Equivalent |
|---|---|
| `x << 8` | `x * 256L` |
| `x \| y` | `x + y` (non-overlapping bits only) |
| `x & 0xFF` | `if (x < 0L) x + 256L else x` |

### No Dynamic Collection Construction

`Coll(item0, item1, ...)` doesn't work for building a collection to index
dynamically. Use an if/else chain instead. Each branch must construct a fixed-size
`Coll(...)` literal.

### Long.MIN_VALUE Literal Workaround

`-9223372036854775808L` overflows the ErgoScript parser. Compose it as:
```scala
val longMin = -9223372036854775807L - 1L
```

### sigmaProp Required

The top-level expression must return `SigmaProp`, not `Boolean`:
```scala
// WRONG: bare boolean → "Expected SigmaBoolean but was: true"
finalCheck == expected

// CORRECT
sigmaProp(finalCheck == expected)
```

### Available Built-in Functions (Verified on Mainnet)

- `blake2b256(input: Coll[Byte]): Coll[Byte]`
- `byteArrayToLong(input: Coll[Byte]): Long` (first 8 bytes, big-endian, signed)
- `CONTEXT.headers(0).id` — block header hash as `Coll[Byte]`
- `CONTEXT.dataInputs(0)` — first data input box
- `SELF.id` — spending box ID as `Coll[Byte]`
- `getVar[T](idx).get` / `.isDefined` — context extension variables
- `.slice(start, end)`, `.toLong`, `.toInt`, `.zip(other)`

---

## CONTEXT.headers — Sliding Window Semantics

`CONTEXT.headers` provides the 10 most recent block headers as `Coll[Header]`.

- `CONTEXT.headers(0)` is at `HEIGHT - 1`, `CONTEXT.headers(1)` at `HEIGHT - 2`, etc.
- Only 10 headers available — `CONTEXT.headers(10)` throws index-out-of-bounds.
- When HEIGHT changes, the entire window shifts.

**Safe pattern — search by height, not position:**
```ergoscript
val hashVerified = CONTEXT.headers.exists { (h: Header) =>
  h.id == targetHash && h.height == targetHeight
}
```

**Header race problem:** When a contract uses `CONTEXT.headers(0).id` for RNG,
the header can change between your off-chain computation and the prover's
evaluation. Solutions:
1. Pass the block hash as a context variable (`getVar[Coll[Byte]](1)`) — both
   sides use the same value.
2. Chain all TXs in a single execute block using output references.

---

## Multi-Path Contract Design

Use a context variable to select which validation path to execute:

```ergoscript
val pathId = getVar[Int](1).get

val valid = if (pathId == 2) {
  // PATH B: alternative conditions
  conditionB1 && conditionB2
} else if (pathId == 3) {
  // PATH C: timeout/fallback conditions
  conditionC1 && conditionC2
} else {
  // PATH A: default/happy path
  conditionA1 && conditionA2
}

sigmaProp(valid)
```

Only the executed branch contributes to JIT cost. Each path is a complete boolean
expression. The harness must pass the correct `pathId` via context variable for each
spending scenario.

---

## Context Variables (getVar)

Pass data to the contract via context extension on input boxes:

```scala
val boxWithVars = box.withContextVars(
  ContextVar.of(0.toByte, ErgoValue.of(score)),         // Long
  ContextVar.of(1.toByte, ErgoValue.of(blockHash))      // Coll[Byte]
)
```

`Coll[Coll[Byte]]` works in context variables too (not just registers):
```scala
val keysErgo = buildCollCollByte(keys)  // Seq[Array[Byte]] → ErgoValue
ctxVars.add(ContextVar.of(5.toByte, keysErgo))
```

For batch entries (1–10), use `isDefined` checks and nested if/else since there's
no dynamic collection append:
```ergoscript
val has2 = getVar[Coll[Byte]](4).isDefined
val entries = if (has2) {
  Coll((key1, value1), (getVar[Coll[Byte]](4).get, getVar[Coll[Byte]](5).get))
} else {
  Coll((key1, value1))
}
```

---

## Reclaiming Boxes from Old Contract Versions

When contract source changes, the compiled ErgoTree changes, so the P2S address
changes. Boxes at the old address become "orphaned" — address scans won't find them.

**Solution:** `ctx.getBoxesById(boxId)` fetches by ID regardless of contract version.
The node evaluates the ErgoTree embedded in the UTXO, not what you compile now:

```scala
val oldBox = ctx.getBoxesById("a9459b15...")(0)
// Old box with old contract logic — spending conditions still evaluated against
// the box's OWN ErgoTree
```

---

## Node Log Configuration

### Finding JitCost in Logs

At INFO level, the node logs script results for **failed** transactions only:
```
Success((false,333))  — script returned false, cost was 333
```

For successful transactions, set DEBUG logging:
```
scorex.logging.level = "DEBUG"
```

### Finding Logs

- `~/.ergo/ergo.log` (default)
- `~/ergo/ergo.log` (custom data dir)
- Docker: `docker logs ergo-node`
- Systemd: `journalctl -u ergo`

---

## build.sbt Reference

```scala
scalaVersion := "2.12.18"

libraryDependencies ++= Seq(
  "org.ergoplatform" %% "ergo-appkit" % "5.0.4"
)

// CRITICAL: ergo-appkit 5.0.4 pulls a deleted SNAPSHOT dependency
dependencyOverrides += "org.scorexfoundation" %% "scrypto" % "2.3.0"

// If using http4s alongside AppKit (circe version conflict):
libraryDependencySchemes ++= Seq(
  "io.circe" %% "circe-core"    % VersionScheme.Always,
  "io.circe" %% "circe-generic" % VersionScheme.Always,
  "io.circe" %% "circe-parser"  % VersionScheme.Always
)

resolvers ++= Seq(
  "Sonatype Releases" at "https://oss.sonatype.org/content/repositories/releases/",
  "Sonatype S01 Releases" at "https://s01.oss.sonatype.org/content/repositories/releases/",
  "Sonatype Snapshots" at "https://oss.sonatype.org/content/repositories/snapshots/"
)
```

---

## Common Error → Fix Reference

| Error | Cause | Fix |
|---|---|---|
| `Cannot getReg[GroupElement](4): invalid type` | `ErgoValue.of(pk)` stores SigmaProp, not GroupElement | Use `fixOutBoxR4` reflection helper or copy regs from input box |
| `Don't know how to buildNode(BitOp(...))` | Bitwise ops in ErgoScript | Replace with arithmetic equivalents |
| `Expected SigmaBoolean but was: true` | Missing `sigmaProp()` wrapper | Wrap final expression in `sigmaProp()` |
| `ErgoTree serialized without size bit` | Header byte missing bit 3 | Set `(header \| 0x08).toByte` |
| `Cannot create ErgoAddress from proposition` | Complex P2S tree (900+ bytes) | Wrap in try-catch, non-blocking |
| `For node-only use, use NodeDataSourceImpl` | Empty explorer URL | Provide `"https://api.ergoplatform.com"` |
| `scrypto 2.3.0-4-SNAPSHOT not found` | Deleted SNAPSHOT dependency | Add `dependencyOverrides` for scrypto 2.3.0 |
| `total inputs less than total outputs` | Wrong change box selected | Pick largest non-setup output |
| `already in the mempool` | Re-running after partial success | Catch and continue (`sendSafe` pattern) |
| `Script reduced to false` (cost > 0) | Logic error, e.g. HEIGHT off-by-one | Check expiry calculations (+2 buffer), verify context vars |
| `NotEnoughCoinsForChangeBoxesError` | Token-carrying boxes without tokens in output | Include all tokens via `.tokens(allTokens: _*)` |
| `type ErgoToken is not a member of appkit` | Wrong package | Use `org.ergoplatform.sdk.ErgoToken` |
| Old boxes unreachable by address scan | Contract source changed → different ErgoTree | Use `ctx.getBoxesById(boxId)` to fetch by ID directly |
| circe eviction errors with http4s | sigma-state uses circe 0.13, http4s wants 0.14 | Add `libraryDependencySchemes` for circe modules |
