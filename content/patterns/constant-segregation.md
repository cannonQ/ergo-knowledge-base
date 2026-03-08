---
title: Constant segregation
description: Constant segregation — substConstants pattern for contract templates without recompilation
tags: [constant-segregation, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [ergoplatform/sigmastate-interpreter, fleet-sdk/fleet]
---
# Developer Guide: Constant Segregation — `substConstants` Pattern for Contract Templates Without Recompilation

---

## Overview

### What Is This Pattern?

**Constant segregation** is a feature of Ergo's **ErgoTree** serialization format that separates a script's constant values from its structural logic. When the constant segregation bit is set in the **ErgoTree header**, constants are stored in a dedicated section at the beginning of the serialized byte array rather than being inlined at the positions where they appear in the script's abstract syntax tree.

The `substConstants` function — available both in **ErgoScript** (via the `Global` singleton) and in off-chain SDKs — allows you to take a constant-segregated ErgoTree byte array and produce a new, valid ErgoTree byte array with one or more constants swapped out, **without recompiling the script from source**.

This is the **contract template** pattern: compile once, deploy many times with different parameters.

### Why Does It Exist?

ErgoScript compilation is:
- **Expensive** relative to byte manipulation
- **Requires a compiler** (sigmastate-interpreter or an SDK that bundles it)
- **Non-trivial** to reproduce deterministically across languages and environments

In contrast, `substConstants` is:
- **Pure byte manipulation** on the segregated constants section
- **Deterministic** and reproducible in any environment
- **Available natively inside ErgoScript itself**, enabling on-chain contract factories
- **Safe** because the structural ErgoTree (the logic) is never modified — only the constant pool

### When to Use It

| Scenario | Use `substConstants`? |
|---|---|
| Deploy the same AMM contract for many token pairs | ✅ Yes |
| Issue many NFT sale contracts with different prices/owners | ✅ Yes |
| Build an on-chain contract factory (one box creates parameterized boxes) | ✅ Yes |
| Script logic changes between deployments | ❌ No — recompile |
| You need to change register values, not guarding logic | ❌ No — use Registers |
| Working with P2SH scripts (no segregation) | ❌ No — segregation flag not set |

---

## How It Works

### Step 1: Understand ErgoTree Structure

An **ErgoTree** is the serialized, typed representation of an **ErgoScript** program. Its serialized byte array has the following layout when constant segregation is enabled:

```
[ header: 1 byte ][ version: 1 byte ][ (size: optional 4 bytes) ]
[ numConstants: VLQ int ][ constant_0 ][ constant_1 ]...[ constant_N ]
[ root expression bytes ]
```

- **Header byte**: A bitmask. Bit 4 (`0x10`) is the **constant segregation flag**. Bit 3 (`0x08`) is the **size flag**.
- **Constants section**: A sequentially indexed array of typed constant values. Each constant has a type descriptor followed by its encoded value.
- **Root expression**: The script body, where every constant reference is a `ConstantPlaceholder(index, type)` node pointing back into the constants array by index.

From `ErgoTree.scala`:
```scala
/** @return true, if constant segregation bit is set in the header. */
def isConstantSegregation(): Boolean = tree.isConstantSegregation
```

From `ErgoBoxCandidate.scala`:
```scala
/** Transforms this tree to a proposition, substituting the constants if the constant
  * segregation flag is set. */
def proposition: SigmaPropValue = ergoTree.toProposition(ergoTree.isConstantSegregation)
```

This shows that when a **Box** is validated, the node automatically reconstructs the full proposition by injecting constants back into their placeholder positions.

### Step 2: Compile with Constant Segregation Enabled

During compilation, you must request constant segregation. This produces an ErgoTree where the header byte has bit 4 set (e.g., `0x10` for version 0, or `0x14` for version 0 with size flag).

The resulting `ergoTree.bytes` is your **template**. Store it (as hex, base64, or raw bytes).

### Step 3: Identify Constant Positions

Constants in the segregated section are **zero-indexed** in the order the compiler placed them. You must know which index corresponds to which logical parameter. This is determined at compile time and is stable for a given script source — **the positions do not change as long as the script source does not change**.

Tools for discovering positions:
- Inspect the ErgoTree with `ErgoTreeSerializer` / sigmastate tooling
- Use Fleet SDK's `ErgoTree` utilities
- Count constants by reading the serialized bytes manually

### Step 4: Call `substConstants`

Replace constants at specific positions:

**Signature (ErgoScript / SigmaDsl):**
```scala
def substConstants[T](
    scriptBytes: Coll[Byte],  // The constant-segregated ErgoTree bytes
    positions: Coll[Int],     // Zero-based indices of constants to replace
    newValues: Coll[T]        // New values; must match the type of existing constants
): Coll[Byte]
```

From `SigmaDsl.scala`:
```scala
def substConstants[T](scriptBytes: Coll[Byte],
    positions: Coll[Int],
    newValues: Coll[T]): Coll[Byte] = this.builder.substConstants(scriptBytes, positions, newValues)
```

The function returns a new valid ErgoTree byte array with the specified constants replaced. The structure (root expression, header, version) is preserved exactly.

### Step 5: Use the Result

The returned bytes are a fully valid **ErgoTree**. Use them as the `propositionBytes` (guarding script) of an output **Box** in a **Transaction**.

---

## Implementation

### Example 1: ErgoScript — On-Chain Contract Factory

This pattern is most powerful when used **inside ErgoScript** to produce new contract addresses on-chain, enabling a **multi-stage contract** or **singleton/state NFT** factory.

```scala
// FACTORY CONTRACT (ErgoScript)
// This contract, when spent, creates a new parameterized child contract box.
// SELF contains:
//   R4: Coll[Byte]  — the template ErgoTree bytes (constant-segregated)
//   R5: Int         — the constant position to customize (e.g., the owner pubkey position)
//
// The spending transaction must provide:
//   OUTPUTS(0) — the new child contract box
//   Context extension variable 0: Coll[Byte] — the new owner's serialized SigmaProp bytes

{
  val templateBytes: Coll[Byte]   = SELF.R4[Coll[Byte]].get
  val ownerPkPosition: Int        = SELF.R5[Int].get

  // The new owner's pk is provided as a context extension variable (Coll[Byte])
  // It must be the serialized constant form of a SigmaProp
  val newOwnerPkBytes: Coll[Byte] = getVar[Coll[Byte]](0).get

  // Produce the new child script bytes by substituting constant at ownerPkPosition
  val childScriptBytes: Coll[Byte] = Global.substConstants(
    templateBytes,
    Coll(ownerPkPosition),
    Coll(newOwnerPkBytes)
  )

  // Verify the first output box uses the resulting script
  val outputUsesChildScript: Boolean =
    OUTPUTS(0).propositionBytes == childScriptBytes

  // Verify the factory singleton NFT is preserved (state NFT / singleton pattern)
  val factoryNftId: Coll[Byte] = SELF.tokens(0)._1
  val nftPreserved: Boolean    = OUTPUTS(1).tokens(0)._1 == factoryNftId

  sigmaProp(outputUsesChildScript && nftPreserved)
}
```

> **Key insight**: `OUTPUTS(0).propositionBytes` returns the raw ErgoTree bytes of the output box, making it directly comparable to the result of `substConstants`. This is the foundation of on-chain contract verification.

---

### Example 2: TypeScript — Off-Chain Template Instantiation (Fleet SDK)

```typescript
import {
  ErgoAddress,
  ErgoTree,
  SConstant,
  SGroupElement,
  SSigmaProp,
  SInt,
  SLong,
  SColl,
  SByte,
  substConstants,   // fleet-sdk utility
  hex,
  Network
} from "@fleet-sdk/core";
import { compile } from "@fleet-sdk/compiler"; // wraps sigma-rust / sigmastate

// ─── Step 1: Define the template script ───────────────────────────────────────
// Dummy constants act as placeholders; their VALUES don't matter at this stage,
// only their TYPES do. The positions are determined by compilation order.
const TEMPLATE_SCRIPT = `
{
  // Constant at position 0: ownerPk (SigmaProp / GroupElement)
  // Constant at position 1: price   (Long, nanoERG)
  // Constant at position 2: tokenId (Coll[Byte])
  val ownerPk    = PK("9f5ZKbECVTm25JTRQHDHGM5ehC8tUw5g1fCBQ4aaE792rWBFrjK")
  val price      = 1000000000L  // 1 ERG placeholder
  val tokenId    = fromBase64("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")

  val correctPayment = OUTPUTS(0).value >= price
  val correctToken   = SELF.tokens(0)._1 == tokenId
  val refundOrBuy    =
    ownerPk ||
    (correctPayment && correctToken && OUTPUTS(1).propositionBytes == ownerPk.propBytes)

  sigmaProp(refundOrBuy)
}
`;

// ─── Step 2: Compile WITH constant segregation ────────────────────────────────