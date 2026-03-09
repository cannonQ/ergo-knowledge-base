---
title: "ErgoScript Built-in Functions"
description: "Quick reference for all global/predefined functions available in ErgoScript."
tags: [ergoscript, built-in-functions, reference, global-functions, predefined-functions]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: original
---

# ErgoScript Built-in Functions

All functions below are available globally in any ErgoScript contract without import or declaration.

---

## Sigma Proposition Constructors

```scala
def sigmaProp(condition: Boolean): SigmaProp
```
Lifts a `Boolean` into a `SigmaProp`. Required to combine boolean logic with cryptographic proofs.

```scala
def proveDlog(value: GroupElement): SigmaProp
```
Creates a sigma proposition for proof of knowledge of discrete logarithm (Schnorr signature).

```scala
def proveDHTuple(g: GroupElement, h: GroupElement, u: GroupElement, v: GroupElement): SigmaProp
```
Creates a sigma proposition for proof of a Diffie-Hellman tuple relationship.

```scala
def atLeast(k: Int, properties: Coll[SigmaProp]): SigmaProp
```
Threshold proposition: proven when at least `k` of the given sigma propositions are proven.

---

## Logical Aggregation

```scala
def allOf(conditions: Coll[Boolean]): Boolean
```
Returns `true` if **all** elements are `true`. Equivalent to chained `&&`.

```scala
def anyOf(conditions: Coll[Boolean]): Boolean
```
Returns `true` if **any** element is `true`. Equivalent to chained `||`.

```scala
def xorOf(conditions: Coll[Boolean]): Boolean
```
Returns `true` if an **odd number** of elements are `true`.

---

## Hash Functions

```scala
def blake2b256(input: Coll[Byte]): Coll[Byte]
```
Blake2b-256 cryptographic hash. Ergo's primary hash function (32-byte output).

```scala
def sha256(input: Coll[Byte]): Coll[Byte]
```
SHA-256 cryptographic hash (32-byte output).

---

## Type Conversions

```scala
def byteArrayToBigInt(input: Coll[Byte]): BigInt
```
Converts big-endian byte array to `BigInt` (256-bit signed).

```scala
def byteArrayToLong(input: Coll[Byte]): Long
```
Converts big-endian byte array (up to 8 bytes) to `Long`.

```scala
def longToByteArray(input: Long): Coll[Byte]
```
Converts `Long` to big-endian 8-byte array.

```scala
def decodePoint(bytes: Coll[Byte]): GroupElement
```
Decodes compressed elliptic curve point bytes into a `GroupElement`.

---

## Context Variable Access

```scala
def getVar[T](tag: Int): Option[T]
```
Retrieves a typed context extension variable by index. Returns `None` if absent, fails if type mismatch.

```scala
def executeFromVar[T](tag: Int): T
```
Executes serialized ErgoTree script bytes stored in context variable `tag`. Used for MAST-like patterns.

---

## Compile-Time Functions

These resolve at **compile time** only — arguments must be string literals.

```scala
def PK(input: String): SigmaProp
```
Converts a Base58 address string to a `proveDlog` sigma proposition.

```scala
def fromBase16(input: String): Coll[Byte]
```
Decodes a hex (Base16) string literal to bytes.

```scala
def fromBase58(input: String): Coll[Byte]
```
Decodes a Base58 string literal to bytes.

```scala
def fromBase64(input: String): Coll[Byte]
```
Decodes a Base64 string literal to bytes.

```scala
def deserialize[T](string: String): T
```
Deserializes a Base58-encoded binary constant into a typed value at compile time.

---

## Script Template Manipulation

```scala
def substConstants[T](scriptBytes: Coll[Byte], positions: Coll[Int], newValues: Coll[T]): Coll[Byte]
```
Replaces constants at given positions in serialized ErgoTree bytes. Used to verify output boxes carry expected contract logic with specific parameters.

---

## Global Object Methods

Accessed via `Global.methodName(...)` or directly in scope:

```scala
def groupGenerator: GroupElement
```
Returns the generator point `g` of the secp256k1 elliptic curve group.

```scala
def xor(l: Coll[Byte], r: Coll[Byte]): Coll[Byte]
```
Byte-wise XOR of two byte collections.

```scala
def serialize[T](value: T): Coll[Byte]
```
Serializes a value to bytes using default Sigma serialization.

```scala
def deserializeTo[T](bytes: Coll[Byte]): T
```
Deserializes bytes back to a typed value (runtime, unlike compile-time `deserialize`).

```scala
def fromBigEndianBytes[T](bytes: Coll[Byte]): T
```
Decodes a numeric value from big-endian bytes.

```scala
def encodeNbits(bi: BigInt): Long
```
Encodes a `BigInt` into NBits compact difficulty representation.

```scala
def decodeNbits(l: Long): BigInt
```
Decodes an NBits-encoded difficulty into `BigInt`.

---

## See Also

- [ErgoScript Types](types.md)
- [Context Variables](context-variables.md)
- [Language Specification](language-spec.md)
