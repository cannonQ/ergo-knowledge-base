---
title: "ErgoScript Context Variables"
description: "Quick reference for blockchain context objects available in every ErgoScript contract."
tags: [ergoscript, context, self, inputs, outputs, height, getvar, data-inputs, reference]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: original
---

# ErgoScript Context Variables

Every ErgoScript contract executes within a transaction context. These global objects provide access to the transaction data and blockchain state.

---

## Transaction Context

### `SELF` — Current Box

Type: `Box`

The input box whose contract is currently being evaluated. Always one of the `INPUTS`.

```scala
SELF.value              // Long — nanoERGs in this box
SELF.propositionBytes   // Coll[Byte] — this box's guard script
SELF.id                 // Coll[Byte] — unique box identifier
SELF.tokens             // Coll[(Coll[Byte], Long)] — tokens in this box
SELF.R4[Long].get       // typed register access
```

### `INPUTS` — All Input Boxes

Type: `Coll[Box]`

All boxes being spent in the current transaction. `SELF` is always a member of this collection.

```scala
INPUTS(0)               // Box — first input
INPUTS.size             // Int — number of inputs
INPUTS.exists { (b: Box) => b.value > 1000000000L }
```

### `OUTPUTS` — All Output Boxes

Type: `Coll[Box]`

All boxes being created by the current transaction.

```scala
OUTPUTS(0)              // Box — first output
OUTPUTS(0).value        // Long — ERG in first output
OUTPUTS.forall { (b: Box) => b.value > 0L }
```

### `CONTEXT.dataInputs` — Data Inputs

Type: `Coll[Box]`

Read-only reference boxes. They provide data without being spent, so many transactions can reference the same box concurrently (e.g., oracle price feeds).

```scala
val oracleBox = CONTEXT.dataInputs(0)
val price = oracleBox.R4[Long].get
```

---

## Blockchain State

### `HEIGHT` — Current Block Height

Type: `Int`

The height of the block in which this transaction is being validated.

```scala
sigmaProp(HEIGHT > 700000)           // spendable after block 700,000
sigmaProp(HEIGHT < SELF.creationInfo._1 + 100)  // time-locked for 100 blocks
```

### `CONTEXT.headers` — Recent Block Headers

Type: `Coll[Header]`

The last 10 block headers preceding `HEIGHT`. Index 0 is the most recent.

```scala
val lastMiner: GroupElement = CONTEXT.headers(0).minerPk
val lastTimestamp: Long = CONTEXT.headers(0).timestamp
val lastDifficulty: Long = CONTEXT.headers(0).nBits
```

Each `Header` contains: `id`, `version`, `parentId`, `ADProofsRoot`, `stateRoot`, `transactionsRoot`, `timestamp`, `nBits`, `height`, `extensionRoot`, `minerPk`, `powOnetimePk`, `powNonce`, `powDistance`, `votes`.

### `CONTEXT.preHeader` — Current Block Candidate

Type: `PreHeader`

Information about the block being mined. Values depend on which miner finds the block.

```scala
val currentMiner: GroupElement = CONTEXT.preHeader.minerPk
val blockTime: Long = CONTEXT.preHeader.timestamp
val blockVersion: Byte = CONTEXT.preHeader.version
```

Fields: `version`, `parentId`, `timestamp`, `nBits`, `height`, `minerPk`, `votes`.

**Warning:** `preHeader` values are miner-dependent. A contract using `preHeader.minerPk` will behave differently depending on who mines the block.

---

## Context Extension Variables (`getVar`)

Type: `getVar[T](tag: Int): Option[T]`

Off-chain data attached to an input at transaction construction time. Accessed by integer index (0-based) and expected type.

```scala
val key = getVar[GroupElement](0).get      // context var 0 as GroupElement
val data = getVar[Coll[Byte]](1).get       // context var 1 as byte array
val flag = getVar[Boolean](2).isDefined     // check if var 2 exists
```

Three outcomes when calling `getVar[T](id)`:

| Scenario | Result |
|----------|--------|
| Variable absent | Returns `None` |
| Variable present, correct type `T` | Returns `Some(value)` |
| Variable present, wrong type | **Script fails** |

### `executeFromVar`

Type: `executeFromVar[T](tag: Int): T`

Executes serialized ErgoTree bytes stored in a context variable. Enables MAST (Merkelized Abstract Syntax Trees) patterns where script fragments are provided at spend time.

```scala
val result: SigmaProp = executeFromVar[SigmaProp](0)
```

---

## Quick Reference Table

| Variable | Type | Description |
|----------|------|-------------|
| `SELF` | `Box` | The box being spent (whose script is executing) |
| `INPUTS` | `Coll[Box]` | All input boxes being consumed |
| `OUTPUTS` | `Coll[Box]` | All output boxes being created |
| `CONTEXT.dataInputs` | `Coll[Box]` | Read-only data input boxes |
| `HEIGHT` | `Int` | Current block height |
| `CONTEXT.headers` | `Coll[Header]` | Last 10 block headers |
| `CONTEXT.preHeader` | `PreHeader` | Current block candidate info |
| `getVar[T](tag)` | `Option[T]` | Context extension variable by index |
| `executeFromVar[T](tag)` | `T` | Execute script from context variable |

---

## Common Patterns

**Self-replicating contract** — ensure output preserves the same script:
```scala
OUTPUTS(0).propositionBytes == SELF.propositionBytes
```

**Oracle price feed** — read from data input without consuming it:
```scala
val oracle = CONTEXT.dataInputs(0)
val price = oracle.R4[Long].get
sigmaProp(OUTPUTS(0).value >= price)
```

**Time lock** — restrict spending until a future block:
```scala
sigmaProp(HEIGHT >= SELF.R4[Int].get)
```

**Multi-input validation** — verify all inputs share the same script:
```scala
INPUTS.forall { (b: Box) => b.propositionBytes == SELF.propositionBytes }
```

---

## See Also

- [Built-in Functions](built-in-functions.md)
- [ErgoScript Types](types.md)
- [Language Specification](language-spec.md)
