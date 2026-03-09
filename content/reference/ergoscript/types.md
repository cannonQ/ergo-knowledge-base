---
title: "ErgoScript Types"
description: "Quick reference for all ErgoScript data types, their properties, and methods."
tags: [ergoscript, types, box, coll, sigmaprop, group-element, avl-tree, option, reference]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: original
---

# ErgoScript Types

All ErgoScript values are immutable. Types are checked statically at compile time.

---

## Primitive Types

| Type | Size | Description |
|------|------|-------------|
| `Boolean` | 1 bit | `true` or `false` |
| `Byte` | 8-bit signed | -128 to 127 |
| `Short` | 16-bit signed | -32768 to 32767 |
| `Int` | 32-bit signed | -2^31 to 2^31-1 |
| `Long` | 64-bit signed | -2^63 to 2^63-1 |
| `BigInt` | 256-bit signed | Arbitrary-precision modular arithmetic |
| `UnsignedBigInt` | 256-bit unsigned | Non-negative big integer (Sigma 6.0+) |
| `Unit` | — | Single value `()` |

Numeric operators: `+`, `-`, `*`, `/`, `%`. Bitwise: `|`, `&`, `^`, `<<`, `>>`, `>>>`.

---

## `SigmaProp`

Sigma proposition — the required return type of every ErgoScript contract.

| Member | Signature | Description |
|--------|-----------|-------------|
| `propBytes` | `Coll[Byte]` | Serialized ErgoTree bytes of this proposition |
| `isProven` | `Boolean` | Whether the proposition is proven (frontend only) |

Operators: `&&` (AND), `||` (OR) compose sigma propositions with zero-knowledge proofs.

---

## `GroupElement`

Elliptic curve point on secp256k1. Used for public keys and cryptographic operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `getEncoded` | `Coll[Byte]` | Compressed point encoding (33 bytes) |
| `exp(k)` | `(BigInt) => GroupElement` | Scalar exponentiation: `this^k` |
| `multiply(other)` | `(GroupElement) => GroupElement` | Group operation (point addition) |
| `negate` | `GroupElement` | Inverse element in the group |

---

## `Box`

A UTXO containing ERG, tokens, a guarding script, and register data.

| Member | Type | Description |
|--------|------|-------------|
| `value` | `Long` | ERG amount in nanoERGs |
| `propositionBytes` | `Coll[Byte]` | Guarding script (serialized ErgoTree) |
| `tokens` | `Coll[(Coll[Byte], Long)]` | Token pairs: (tokenId, amount) |
| `id` | `Coll[Byte]` | Unique box ID (blake2b256 of content) |
| `creationInfo` | `(Int, Coll[Byte])` | (creation height, txId ++ outputIndex) |
| `bytes` | `Coll[Byte]` | Full serialized box content |
| `bytesWithoutRef` | `Coll[Byte]` | Serialized content without txId/index |
| `R0[T]`..`R9[T]` | `Option[T]` | Typed register access (R0-R3 mandatory, R4-R9 optional) |
| `getReg[T](regId)` | `(Int) => Option[T]` | Register access by numeric ID |

**Register shortcuts:** `box.value` = R0, `box.propositionBytes` = R1, `box.tokens` = R2, `box.creationInfo` = R3.

---

## `Coll[T]`

Immutable indexed collection (array) of elements of type `T`.

| Method | Signature | Description |
|--------|-----------|-------------|
| `size` | `Int` | Number of elements |
| `(index)` | `(Int) => T` | Element at index (0-based) |
| `getOrElse(i, default)` | `(Int, T) => T` | Element at index or default |
| `map(f)` | `(T => R) => Coll[R]` | Transform each element |
| `filter(p)` | `(T => Boolean) => Coll[T]` | Keep elements matching predicate |
| `exists(p)` | `(T => Boolean) => Boolean` | True if any element matches |
| `forall(p)` | `(T => Boolean) => Boolean` | True if all elements match |
| `fold(zero, op)` | `(R, (R,T) => R) => R` | Left fold / reduce |
| `flatMap(f)` | `(T => Coll[R]) => Coll[R]` | Map then flatten |
| `zip(other)` | `(Coll[R]) => Coll[(T,R)]` | Pair elements by index |
| `indices` | `Coll[Int]` | Collection of valid indices |
| `slice(from, until)` | `(Int, Int) => Coll[T]` | Sub-collection [from, until) |
| `append(other)` | `(Coll[T]) => Coll[T]` | Concatenate (also `++` operator) |
| `indexOf(elem, from)` | `(T, Int) => Int` | First index of element, or -1 |
| `patch(from, patch, replaced)` | `(Int, Coll[T], Int) => Coll[T]` | Replace segment |
| `updated(index, elem)` | `(Int, T) => Coll[T]` | New collection with one element replaced |

---

## `Option[T]`

Container that is either `Some(value)` or `None`.

| Method | Signature | Description |
|--------|-----------|-------------|
| `isDefined` | `Boolean` | `true` if value is present |
| `get` | `T` | Unwrap value (fails if `None`) |
| `map(f)` | `(T => R) => Option[R]` | Transform inner value if present |
| `filter(p)` | `(T => Boolean) => Option[T]` | `None` if predicate fails |

---

## `AvlTree`

Authenticated dictionary (AVL+ tree) digest for off-chain data verification.

| Member | Type | Description |
|--------|------|-------------|
| `digest` | `Coll[Byte]` | Tree root digest (33 bytes) |
| `enabledOperations` | `Byte` | Bitmask: insert(0x01), update(0x02), remove(0x04) |
| `keyLength` | `Int` | Fixed key length in bytes |
| `valueLengthOpt` | `Option[Int]` | Fixed value length if defined |

| Method | Signature | Description |
|--------|-----------|-------------|
| `contains(key, proof)` | `(Coll[Byte], Coll[Byte]) => Boolean` | Verify key existence |
| `get(key, proof)` | `(Coll[Byte], Coll[Byte]) => Option[Coll[Byte]]` | Lookup value by key |
| `getMany(keys, proof)` | `(Coll[Coll[Byte]], Coll[Byte]) => Coll[Option[Coll[Byte]]]` | Batch lookup |
| `insert(entries, proof)` | `(Coll[(Coll[Byte], Coll[Byte])], Coll[Byte]) => Option[AvlTree]` | Insert key-value pairs |
| `update(entries, proof)` | `(Coll[(Coll[Byte], Coll[Byte])], Coll[Byte]) => Option[AvlTree]` | Update existing entries |
| `remove(keys, proof)` | `(Coll[Coll[Byte]], Coll[Byte]) => Option[AvlTree]` | Remove keys |
| `updateDigest(newDigest)` | `(Coll[Byte]) => AvlTree` | New tree with replaced digest |
| `updateOperations(newOps)` | `(Byte) => AvlTree` | New tree with replaced operations flag |

---

## `Header`

Block header (last 10 available via `CONTEXT.headers`).

| Member | Type | Description |
|--------|------|-------------|
| `id` | `Coll[Byte]` | Block ID |
| `version` | `Byte` | Protocol version |
| `parentId` | `Coll[Byte]` | Parent block ID |
| `ADProofsRoot` | `Coll[Byte]` | AD proofs root digest |
| `stateRoot` | `AvlTree` | UTXO set state root |
| `transactionsRoot` | `Coll[Byte]` | Transaction Merkle root |
| `timestamp` | `Long` | Block timestamp (ms) |
| `nBits` | `Long` | Encoded difficulty |
| `height` | `Int` | Block height |
| `extensionRoot` | `Coll[Byte]` | Extension section root |
| `minerPk` | `GroupElement` | Miner public key |
| `powOnetimePk` | `GroupElement` | PoW one-time public key |
| `powNonce` | `Coll[Byte]` | PoW nonce |
| `powDistance` | `BigInt` | PoW solution distance |
| `votes` | `Coll[Byte]` | 3-byte miner votes |

---

## `PreHeader`

Current block candidate (miner-dependent).

| Member | Type | Description |
|--------|------|-------------|
| `version` | `Byte` | Protocol version |
| `parentId` | `Coll[Byte]` | Parent block ID |
| `timestamp` | `Long` | Block timestamp (ms) |
| `nBits` | `Long` | Encoded difficulty |
| `height` | `Int` | Block height |
| `minerPk` | `GroupElement` | Miner public key |
| `votes` | `Coll[Byte]` | 3-byte miner votes |

---

## Tuple Types `(T1, T2)`

Access elements with `._1` and `._2`. Nest arbitrarily: `(Int, (Long, Boolean))`.

---

## See Also

- [Built-in Functions](built-in-functions.md)
- [Context Variables](context-variables.md)
- [Language Specification](language-spec.md)
