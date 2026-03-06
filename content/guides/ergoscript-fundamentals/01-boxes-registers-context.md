---
title: "ErgoScript Fundamentals: Boxes, Registers & Blockchain Context"
description: "Learn ErgoScript syntax, types, sigma propositions, box registers R0-R9, blockchain context objects (SELF, INPUTS, OUTPUTS, HEIGHT), and global functions — adapted from DeCo Education's ErgoScript Developer Course."
tags: [ergoscript, boxes, registers, eutxo, sigmaprop, tutorial, deco-education]
category: guide
difficulty: beginner
sdk: [none]
updated: 2026-03-06
source: adapted
original_source: "https://github.com/DeCo-Education/ErgoScript-Developer-Course"
original_author: "DeCo Education (lgd, kii)"
license: MIT
---

# ErgoScript Fundamentals: Boxes, Registers & Blockchain Context

> **Attribution:** This guide is adapted from [DeCo Education's ErgoScript Developer Course](https://github.com/DeCo-Education/ErgoScript-Developer-Course) (Week 1), originally created by lgd and kii under the MIT License. We build on their excellent teaching material with additional context and cross-references.

## Prerequisites

- Basic programming experience (variables, if/else, collections)
- Familiarity with what a blockchain transaction is
- Read [eUTXO Model](../../concepts/eutxo-model.md) and [Boxes and Registers](../../concepts/boxes-and-registers.md) for conceptual background

## ErgoScript Basics

ErgoScript is a statically typed language based on Scala. Every contract compiles to **ErgoTree** (the on-chain bytecode) and must return a **SigmaProp** — the cryptographic proposition that determines whether a box can be spent.

### Values and Types

All values are immutable. Use `val` to declare them:

```ergoscript
val flag: Boolean = true
val amount: Long = 1000000L        // nanoERGs (1 ERG = 1,000,000,000)
val name: Coll[Byte] = Coll(72, 101, 108, 108, 111)  // "Hello" as bytes
```

ErgoScript is **strongly typed**. The core types you'll encounter:

| Type | Description | Example |
|------|-------------|---------|
| `Boolean` | True or false | `val ok = true` |
| `Int` | 32-bit signed integer | `val count = 42` |
| `Long` | 64-bit signed integer | `val nanoErg = 1000000000L` |
| `BigInt` | 256-bit signed integer | Cryptographic math |
| `Coll[T]` | Collection (array) of type T | `Coll(1, 2, 3)` |
| `(A, B)` | Pair/tuple | `(42L, true)` |
| `SigmaProp` | Sigma proposition | Contract return type |
| `GroupElement` | Elliptic curve point | Public keys |

### Building Complex Types

You can layer pairs and collections to build rich data structures:

```ergoscript
val scores: Coll[Long] = Coll(0L, 1L, 2L)
val pair: (Long, Long) = (3L, 4L)
val nested: Coll[((Long, Long), Boolean)] = Coll(
  ((2L, 4L), true),
  ((7L, 2L), false)
)
```

### Functional Operations

ErgoScript supports standard functional programming patterns:

```ergoscript
val doubled: Coll[Long] = Coll(1L, 2L, 3L).map({ (x: Long) => x * 2L })
// Result: Coll(2L, 4L, 6L)

val total: Long = Coll(10L, 20L, 30L).fold(0L, { (acc: Long, x: Long) => acc + x })
// Result: 60L

val positives: Coll[Long] = Coll(-1L, 2L, -3L, 4L).filter({ (x: Long) => x > 0L })
// Result: Coll(2L, 4L)
```

### `def` vs `val` — When Code Executes

```ergoscript
// Evaluated ONCE when the script initializes
val computeAsVal = { (myInt: Int) => myInt + 1 }

// Evaluated EACH TIME it's called
def computeAsDef(myInt: Int): Int = { myInt + 1 }
```

Both produce the same result, but `val` evaluates at script initialization while `def` evaluates at each call site. In practice, you'll use `val` for most things. Use `def` when the computation is expensive and might not always be needed (short-circuit evaluation).

## Sigma Propositions

**Every ErgoScript contract must return a SigmaProp.** This is the spending condition — the cryptographic statement that must be proven true to spend the box.

> For the cryptographic theory behind sigma propositions, see [Sigma Protocols](../../concepts/sigma-protocols.md).

### From Booleans

Wrap any boolean expression with `sigmaProp()`:

```ergoscript
{
  val mathIsHard: Boolean = (1 + 1) != 2
  sigmaProp(mathIsHard) // Evaluates to false — this box can never be spent!
}
```

### From Public Keys

Public keys are SigmaProp values. The spender must prove knowledge of the private key:

```ergoscript
{
  val myPK: SigmaProp = PK("9etXmP7D3ZkWssDopWcWkCPpjn22RVuEyXoFSbVPWAvvzDbcDXE")
  myPK  // Only the private key holder can spend
}
```

### Combining Conditions (Spending Paths)

Use `||` (OR) and `&&` (AND) to create multiple spending paths:

```ergoscript
{
  val enoughERG = INPUTS(0).value > 1000000L
  val myPK = PK("9etXmP7D3ZkWssDopWcWkCPpjn22RVuEyXoFSbVPWAvvzDbcDXE")

  // Two spending paths:
  // 1. Anyone can spend if there's enough ERG in INPUTS(0)
  // 2. The key holder can always spend
  sigmaProp(enoughERG) || myPK
}
```

## The Blockchain Context

The blockchain context provides access to transaction data and chain state. These are the global objects available in every contract.

### HEIGHT

The current block height (an `Int`):

```ergoscript
val isAfterDeadline: Boolean = HEIGHT > 700000
```

### SELF

The box being spent — the one whose contract is currently executing:

```ergoscript
val myValue: Long = SELF.value          // ERG in this box
val myScript: Coll[Byte] = SELF.propositionBytes  // This box's script
val myId: Coll[Byte] = SELF.id          // Unique box identifier
```

### INPUTS and OUTPUTS

All input boxes being spent and all output boxes being created:

```ergoscript
val firstInput: Box = INPUTS(0)
val secondOutput: Box = OUTPUTS(1)
val inputCount: Int = INPUTS.size
```

**Key insight: SELF is always one of the INPUTS.** When your contract runs, SELF refers to itself within the INPUTS collection. But `SELF.id == INPUTS(0).id` is only true if your box happens to be the first input.

### Data Inputs

Read-only boxes — they provide data without being spent:

```ergoscript
val oraclePrice: Long = CONTEXT.dataInputs(0).R4[Long].get
```

Data inputs are powerful because the referenced box isn't consumed. An oracle box can be read by many transactions simultaneously. See [eUTXO Model — Data Inputs](../../concepts/eutxo-model.md) for more detail.

### Headers and PreHeaders

Access recent block information:

```ergoscript
// Last 10 block headers before current HEIGHT
val lastBlockMiner = CONTEXT.headers(0).minerPk

// Current block being mined (miner-dependent!)
val currentMiner = CONTEXT.preHeader.minerPk
```

**Warning:** PreHeader values depend on which miner finds the block. Your contract could execute differently depending on the miner. Use this deliberately, not accidentally.

## Boxes and Registers Deep Dive

Every box has 10 registers (R0–R9). The first four are mandatory:

| Register | Access | Contains |
|----------|--------|----------|
| R0 | `box.value` | ERG amount (nanoERGs) |
| R1 | `box.propositionBytes` | Guard script bytes |
| R2 | `box.tokens` | Token collection: `(tokenId, amount)` pairs |
| R3 | `box.creationInfo` | Transaction ID, output index, creation height |
| R4–R9 | `box.R4[Type].get` | User-defined typed data |

### Accessing Optional Registers

Registers R4–R9 are typed and optional. You **must** declare the expected type:

```ergoscript
val data: Long = SELF.R4[Long].get              // Fails if R4 is empty or wrong type
val maybeName = SELF.R5[Coll[Byte]].isDefined   // Safe check: true if R5 exists with this type
```

Three outcomes when accessing a register:
1. **Register exists with correct type** → `.get` returns the value
2. **Register is empty** → `.get` fails the script; use `.isDefined` to check first
3. **Register exists with wrong type** → script **fails immediately** (not `None`, a hard fail)

### Token Access

```ergoscript
val nftId: Coll[Byte] = SELF.tokens(0)._1     // First token's ID
val nftAmount: Long = SELF.tokens(0)._2        // First token's quantity
```

### Practical Example: Value Multiplier

```ergoscript
{
  val valueMultiplier = SELF.R4[Int].get
  val tokenMultiplier = INPUTS(1).R4[Int].get

  if (SELF.id == INPUTS(0).id) {
    // When this box is first input: multiply value and tokens
    val outputValue = OUTPUTS(0).value == SELF.value * valueMultiplier
    val outputTokens = OUTPUTS(0).tokens(0)._2 == SELF.value * tokenMultiplier
    sigmaProp(outputValue && outputTokens)
  } else {
    // When not first input: send to specific address
    val outputGoesToTarget = {
      PK("9etXmP7D3ZkWssDopWcWkCPpjn22RVuEyXoFSbVPWAvvzDbcDXE").propBytes
        == OUTPUTS(0).propositionBytes
    }
    sigmaProp(outputGoesToTarget)
  }
}
```

This example shows how SELF's position in INPUTS can create different spending paths within the same contract.

## Global Functions Reference

### Logical Functions

| Function | Description |
|----------|-------------|
| `allOf(Coll[Boolean])` | True if **all** elements are true (like chained `&&`) |
| `anyOf(Coll[Boolean])` | True if **any** element is true (like chained `\|\|`) |
| `xorOf(Coll[Boolean])` | True if **odd number** of elements are true |

### Cryptographic Functions

| Function | Description |
|----------|-------------|
| `blake2b256(Coll[Byte])` | Blake2b-256 hash (Ergo's primary hash) |
| `sha256(Coll[Byte])` | SHA-256 hash |
| `decodePoint(Coll[Byte])` | Bytes → GroupElement (curve point) |
| `proveDlog(GroupElement)` | Prove knowledge of discrete log (Schnorr signature) |
| `proveDHTuple(g, h, u, v)` | Prove Diffie-Hellman tuple relationship |

### Compile-Time Functions

These resolve at compile time, not at script execution:

| Function | Description |
|----------|-------------|
| `PK("address")` | Address string → SigmaProp public key |
| `fromBase64("string")` | Base64 string → `Coll[Byte]` |
| `fromBase58("string")` | Base58 string → `Coll[Byte]` |
| `deserialize[T]("base58")` | Base58 binary data → value of type T |

### Context Variables and SubstConstants

**Context Variables** — off-chain data attached to a box at transaction time:

```ergoscript
val myData: Coll[Byte] = getVar[Coll[Byte]](0).get  // Context var at index 0
```

**SubstConstants** — construct new contract bytes by replacing constants in a template:

```ergoscript
val newScript = substConstants(templateBytes, positions, newValues)
// Creates a new contract from a template with substituted constants
```

This is how contracts can verify that other boxes carry specific contract logic — a foundational pattern used in proxy contracts and multi-stage protocols.

## Exercise: The Pin-Lock

Consider this contract:

```ergoscript
{
  sigmaProp(SELF.R4[Coll[Byte]].get == blake2b256(OUTPUTS(0).R4[Coll[Byte]].get))
}
```

To spend this box, you must create an output whose R4 contains data that, when hashed with blake2b256, equals the hash stored in SELF's R4. You're proving you know the pre-image of the hash — like knowing a PIN.

**Think about:** If you replace `SELF` with `INPUTS(0)`, are the two contracts equivalent? When might they differ?

## What's Next

- [Guard Script Framework](02-guard-script-framework.md) — A systematic approach to designing ErgoScript contracts
- [Off-Chain with AppKit](03-offchain-appkit.md) — Building transactions in Scala using Ergo AppKit
- [Sigma Protocols](../../concepts/sigma-protocols.md) — The cryptographic theory behind SigmaProp
- [Boxes and Registers](../../concepts/boxes-and-registers.md) — Complete reference for box structure

---

*Adapted from [DeCo Education ErgoScript Developer Course](https://github.com/DeCo-Education/ErgoScript-Developer-Course) (MIT License) by lgd and kii. Original course materials provide additional exercises and Scala playground files.*
