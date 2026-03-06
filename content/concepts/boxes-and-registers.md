---
title: "Boxes and Registers"
description: "Ergo's data model: box structure, mandatory registers R0-R3, optional registers R4-R9, type system, token mechanics, box identity, and common register conventions across the ecosystem."
tags: [boxes, registers, eutxo, tokens, eip-4, data-model, concepts]
category: concept
difficulty: beginner
sdk: [none]
updated: 2026-03-05
source: original
---

# Boxes and Registers

## What Is a Box?

A box is Ergo's fundamental data unit — the extended UTXO. Every piece of state on the Ergo blockchain lives inside a box. Boxes are **immutable**: once created, a box cannot be modified. To change state, you spend the old box and create a new one with updated data. Boxes are **unique**: each box has a cryptographic ID derived from its contents, and no two boxes on the blockchain can have the same ID.

A box contains:

```
Box
├── R0: Value           — ERG amount (nanoERGs)
├── R1: Script          — ErgoTree guarding script
├── R2: Tokens          — collection of (tokenId, amount) pairs
├── R3: Creation Info   — txId, output index, creation height
├── R4-R9: User Data    — six optional typed registers
```

## Mandatory Registers (R0-R3)

These four registers exist in every box and are set by the protocol.

### R0: Value

The amount of ERG in the box, denominated in **nanoERGs** (1 ERG = 1,000,000,000 nanoERGs). Every box must contain a minimum amount of ERG to cover its storage cost — roughly 0.001 ERG for a simple box, more for boxes with many tokens or large register data.

```ergoscript
// Access in ErgoScript
val myValue: Long = SELF.value
```

### R1: Guarding Script (ErgoTree)

The compiled ErgoScript program that protects this box. The script must evaluate to `true` (a valid `SigmaProp`) for the box to be spent. Stored as serialized proposition bytes.

```ergoscript
// Compare scripts between boxes
val sameScript: Boolean = OUTPUTS(0).propositionBytes == SELF.propositionBytes
```

This is how multi-stage contracts enforce continuity: the output box must have the same script as the input box, ensuring the protocol logic persists across state transitions.

### R2: Tokens

A collection of native assets stored in the box. Each token is a pair of `(tokenId: Coll[Byte], amount: Long)`. A box can hold up to **255 different tokens** alongside its ERG value, and the total box size cannot exceed 4 kilobytes.

```ergoscript
// Access tokens
val firstTokenId: Coll[Byte] = SELF.tokens(0)._1
val firstTokenAmount: Long = SELF.tokens(0)._2

// Check if a specific NFT is present
val hasNFT: Boolean = SELF.tokens(0)._1 == expectedNftId
```

**Token creation rule:** A new token can only be created when its token ID equals the ID of the first input box (`INPUTS(0).id`). This cryptographic binding ensures every token ID is globally unique — you cannot forge or duplicate a token ID. Only one new token type can be minted per transaction.

**Token preservation:** Transactions must preserve tokens — the total amount of each token across outputs must equal the total across inputs (except for newly minted tokens, and tokens being burned by omission from outputs).

### R3: Creation Info

Contains the transaction ID that created this box, the output index within that transaction, and the creation height (block height when the transaction was mined).

```ergoscript
// Access creation info
val (txId, outputIndex) = SELF.creationInfo
val creationHeight: Int = SELF.creationInfo._1  // used by storage rent
```

The creation height is what Ergo's storage rent mechanism uses to determine box age. Boxes older than 4 years (measured in block height) become eligible for miner collection.

**Why R3 guarantees uniqueness:** Since every transaction ID is unique and output indices are unique within a transaction, no two boxes can have the same `(txId, outputIndex)` pair. Combined with the blake2b256 hash of all register contents, this produces a globally unique box ID.

## Optional Registers (R4-R9)

Six general-purpose registers for storing application-specific data. These are what make Ergo's eUTXO model powerful — they turn boxes from simple value containers into stateful objects.

### Type System

Registers are **typed**. When you access a register in ErgoScript, you must declare the expected type:

```ergoscript
val name: Coll[Byte] = SELF.R4[Coll[Byte]].get
val count: Int = SELF.R5[Int].get
val owner: SigmaProp = SELF.R6[SigmaProp].get
```

Register access returns an `Option` type with three possible outcomes:

1. **Register is empty** — `SELF.R4[Int]` returns `None`. Calling `.get` on it will fail the script. Use `.isDefined` to check first.
2. **Register exists with the correct type** — `.get` returns the value.
3. **Register exists but with a different type** — the script **fails immediately**. This is not a `None` — it's a hard failure. This catches type mismatches at validation time.

```ergoscript
// Safe register access pattern
val hasR4 = SELF.R4[Int].isDefined
val value = if (hasR4) SELF.R4[Int].get else 0
```

### Supported Types

| Type | Description | Example Use |
|------|-------------|-------------|
| `Int` | 32-bit signed integer | Counters, enum values, small amounts |
| `Long` | 64-bit signed integer | Token amounts, timestamps, nanoERG values |
| `BigInt` | 256-bit signed integer | Cryptographic operations, large math |
| `Boolean` | True or false | Flags, state booleans |
| `Coll[Byte]` | Byte array | Hashes, addresses, encoded strings |
| `GroupElement` | Elliptic curve point (Secp256k1) | Public keys, DH tuples |
| `SigmaProp` | Sigma proposition | Owner public keys, spending conditions |
| `AvlTree` | Authenticated AVL+ tree digest | Plasma state, compact data structures |
| `Box` | Serialized box | Rare — box snapshots |
| `Coll[T]` | Collection of any supported type | Lists of public keys, arrays of values |
| `(A, B)` | Pair/tuple | Composite data |

### Packing Rules

Registers must be **densely packed** — you cannot leave a gap. If R6 is set, then R4 and R5 must also be set. You can leave R7-R9 empty if R4-R6 are filled.

Valid: R4, R5, R6 set; R7-R9 empty.
Invalid: R4 set, R5 empty, R6 set.

## Common Register Conventions

While registers are general-purpose, the ecosystem has converged on conventions:

### EIP-4 Token Metadata (minting transactions)

When minting a new token, the first output box carries token metadata in registers:

| Register | Type | Content |
|----------|------|---------|
| R4 | `Coll[Byte]` | Token name (UTF-8 encoded) |
| R5 | `Coll[Byte]` | Token description |
| R6 | `Coll[Byte]` | Number of decimal places (as string) |
| R7 | `Coll[Byte]` | Asset type (`0e020101` for NFT image, etc.) |
| R8 | `Coll[Byte]` | SHA-256 hash of the asset file |
| R9 | `Coll[Byte]` | Asset URL or IPFS link |

### Oracle Pool Data Boxes

| Register | Type | Content |
|----------|------|---------|
| R4 | `Long` | Data point value (e.g., ERG/USD price in nano-units) |
| R5 | `Int` | Epoch counter |
| R6 | `Coll[Byte]` | Additional oracle metadata |

### Singleton State Boxes (common pattern)

Many protocols use a pattern where R4-R9 hold protocol state, and a unique NFT in R2 identifies the box:

| Register | Type | Content |
|----------|------|---------|
| R4 | varies | Primary state value |
| R5 | varies | Secondary state value |
| R6 | `Coll[Byte]` | Script hash or config reference |

## Box Identity

Every box has a unique ID computed as:

```
boxId = blake2b256(R0 || R1 || R2 || R3 || R4 || ... || R9)
```

You can access a box's ID in ErgoScript via `SELF.id` or `INPUTS(i).id`. This ID is what the token creation rule references — new token IDs are set equal to `INPUTS(0).id`.

Two utility methods exist for comparing boxes:

- `box.bytes` — full serialized bytes including creation info
- `box.bytesWithoutRef` — serialized bytes excluding creation info, useful for comparing box "templates" (same script + registers, different creation context)

## Minimum Box Value

Every box must contain enough ERG to cover its byte-size cost. The formula is approximately:

```
minValue = boxSizeInBytes * valuePerByte
```

As of protocol v6, `valuePerByte` is 360 nanoERGs. A minimal box (no tokens, no extra registers) costs roughly 0.001 ERG. Boxes with many tokens or large register data cost more.

This prevents spam — you cannot create millions of tiny boxes for free.

## Practical Example

Here's a box serving as a "counter" that increments each time it's spent:

```ergoscript
{
  // This contract requires the output to:
  // 1. Have the same guarding script
  // 2. Carry the same NFT (identity token)
  // 3. Have R4 incremented by 1

  val currentCount = SELF.R4[Long].get
  val outputBox = OUTPUTS(0)

  val sameScript = outputBox.propositionBytes == SELF.propositionBytes
  val sameNft = outputBox.tokens(0)._1 == SELF.tokens(0)._1
  val incremented = outputBox.R4[Long].get == currentCount + 1L

  sigmaProp(sameScript && sameNft && incremented)
}
```

This pattern — checking that the output preserves the script and identity token while allowing specific register changes — is the foundation of every stateful Ergo protocol.

## Learn More

- [eUTXO Model](eutxo-model.md) — How boxes fit into the transaction model
- [Sigma Protocols](sigma-protocols.md) — The cryptographic proofs that guard boxes
- [Storage Rent](storage-rent.md) — How creation height (R3) affects box lifecycle
- [ErgoScript Fundamentals: Boxes, Registers & Context](../guides/ergoscript-fundamentals/01-boxes-registers-context.md) — Hands-on tutorial with register access patterns, adapted from [DeCo Education](https://github.com/DeCo-Education/ErgoScript-Developer-Course)
- [Guard Script Framework](../guides/ergoscript-fundamentals/02-guard-script-framework.md) — Design contracts systematically before coding
