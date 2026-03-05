---
title: Constant segregation
description: Constant segregation — substConstants pattern for contract templates without recompilation
tags: [constant-segregation, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [ergoplatform/sigmastate-interpreter, fleet-sdk/fleet]
---
# Developer Guide: Constant Segregation — `substConstants` Pattern for Contract Templates Without Recompilation

---

## Overview

### What Is This Pattern?

**Constant segregation** is a feature of the ErgoTree serialization format that separates a script's embedded constants from its structural logic. When the constant segregation flag is set in the ErgoTree header, constants are stored in a dedicated indexed array rather than inline within the expression tree. The `substConstants` function — available both in ErgoScript (via `Global.substConstants`) and in off-chain SDKs — allows those constants to be replaced by new values at the **byte level**, producing a new valid ErgoTree without recompiling or re-parsing the underlying script.

The result is a **contract template** workflow: you write and compile an ErgoScript contract once, store the raw bytes, and then stamp new parameter values (public keys, token IDs, deadlines, prices) into copies of those bytes to produce per-instance contracts.

### Why Does It Exist?

ErgoScript compilation is an off-chain operation that produces an ErgoTree — a serialized, platform-canonical representation of the guarding condition of a Box. Recompiling from source on every parameterization:

- requires shipping a compiler at runtime (heavy dependency),
- risks divergence between source text and on-chain bytes if the compiler version changes,
- is slow for high-throughput dApp scenarios.

Constant segregation solves all three problems. The structure of the ErgoTree — its Sigma protocol expression graph, the positions of constants, and the script semantics — is fixed once. Only the constant array is mutated, and the ErgoTree header's `isConstantSegregation` bit tells the evaluator to reconstruct the full tree by merging the expression graph with the current constants before execution.

### When to Use It

| Use case | Use `substConstants`? |
|---|---|
| Parameterized DEX order contracts (per-user price, token ID) | ✅ Yes |
| NFT sale contracts with per-seller payout address | ✅ Yes |
| Time-locked vaults with per-instance deadline | ✅ Yes |
| Auction contracts needing per-auction reserve price | ✅ Yes |
| Contracts whose *logic* changes between instances | ❌ No — recompile |
| Contracts with no parameterization | ❌ No benefit |

**Key rule of thumb:** if two contract instances differ only in their embedded *values* (not their *structure*), `substConstants` is the correct tool.

---

## How It Works

### 1. ErgoTree Header and the Constant Segregation Bit

Every serialized ErgoTree begins with a header byte. Bit 4 (value `0x10`) is the **constant segregation flag**. When set, the serialized form is:

```
[header byte] [version byte?] [size (4 bytes, if hasSize)] [constants count (VLQ)] [constant_0] ... [constant_n] [expression tree bytes]
```

Constants within the expression tree are replaced by **placeholder nodes** (`ConstantPlaceholder(index, type)`) that reference the constant array by index. The evaluator re-injects constants before execution. This is what `isConstantSegregation` reports:

```scala
// ErgoTree.scala
def isConstantSegregation(): Boolean = tree.isConstantSegregation
```

And the `ErgoBoxCandidate` uses this flag when reconstructing the proposition:

```scala
// ErgoBoxCandidate.scala
def proposition: SigmaPropValue =
  ergoTree.toProposition(ergoTree.isConstantSegregation)
```

### 2. Compiling a Template with Constant Segregation Enabled

At development time, you compile your ErgoScript with constant segregation enabled. All compilers (AppKit, Fleet SDK, sigma-rust) expose a flag for this. The output is a hex-encoded ErgoTree whose header has bit 4 set. This hex string is your **template**.

### 3. Identifying Constant Positions

The constants in the segregated array are zero-indexed in declaration order as they appear during compilation. You must know which index corresponds to which parameter. There are two ways:

- **Inspect the compiled template** using SDK tooling to list constants and their types.
- **By convention during development** — write the contract so parameters appear in a known order and document those indices.

### 4. Calling `substConstants`

Given:
- `scriptBytes`: the template's serialized bytes (`Coll[Byte]`)
- `positions`: the indices of constants to replace (`Coll[Int]`)
- `newValues`: replacement values of matching types (`Coll[T]`)

The function returns a new `Coll[Byte]` representing the mutated ErgoTree. The structure is identical; only the targeted constant slots are overwritten.

In ErgoScript (on-chain use — e.g., a factory contract minting parameterized children):

```scala
val newScript = Global.substConstants(
  SELF.R4[Coll[Byte]].get,  // template stored in a register
  Coll(0, 1),                // positions of buyer key and deadline
  Coll(buyerPk, deadline)
)
```

Off-chain (TypeScript, Scala, Python), the same bytes-in / bytes-out transformation is performed before constructing the output Box.

### 5. Using the Result

The returned bytes are a valid ErgoTree. You pass them directly as the `ergoTree` of an output Box candidate in your transaction. No further compilation step is needed. The node evaluates the script normally, reading from its own constant array.

### Full Flow Diagram

```
ErgoScript source
       │
       ▼  (compile once, constant segregation ON)
  Template ErgoTree bytes  ──────────── stored off-chain or in a Box register
       │
       ▼  (off-chain or on-chain substConstants call)
  Instance ErgoTree bytes  ◄── inject: user pubkey, token ID, deadline, price, …
       │
       ▼
  Output Box in Transaction
       │
       ▼
  Node evaluates: merges constants array + expression tree → SigmaProp → Sigma protocol
```

---

## Implementation

### ErgoScript — On-Chain Factory Pattern

A **factory contract** (sometimes called a **multi-stage contract** orchestrator) holds the template in a register and stamps out child contracts. This is the canonical on-chain use of `substConstants`.

```scala
{
  // The template ErgoTree bytes are stored in R4 of the factory box (Singleton / State NFT pattern)
  val templateBytes: Coll[Byte] = SELF.R4[Coll[Byte]].get

  // Parameters for the new child contract instance
  val buyerPk: GroupElement  = INPUTS(1).R4[GroupElement].get   // buyer's public key
  val deadlineHeight: Int    = CONTEXT.preHeader.height + 1440  // ~2 days at 2 min/block
  val tokenId: Coll[Byte]    = INPUTS(1).R5[Coll[Byte]].get    // Native token Token ID

  // Positions: 0 = buyer pubkey placeholder, 1 = deadline, 2 = token ID
  val instanceBytes: Coll[Byte] = substConstants(
    templateBytes,
    Coll(0, 1, 2),
    Coll(buyerPk, deadlineHeight, tokenId)
  )

  // The output box at index 0 must carry the stamped script
  val outputBox: Box = OUTPUTS(0)

  // Verify the output box uses exactly the stamped ErgoTree
  outputBox.propositionBytes == instanceBytes &&
  outputBox.value >= 1000000L  // Minimum box value enforced
}
```

> **Note:** `substConstants` is accessible in ErgoScript via the implicit `Global` object, identical to `Global.substConstants(...)`. The `Global` prefix is optional inside a script.

---

### TypeScript — Fleet SDK

[Fleet SDK](https://github.com/fleet-sdk/fleet) is the primary TypeScript library for building Ergo transactions. It provides `ErgoAddress`, `Box`, and low-level ErgoTree utilities.

#### Step 1: Compile the Template Once

```typescript
import { compile } from "@fleet-sdk/compiler";
import { ErgoAddress, Network } from "@fleet-sdk/core";

// ErgoScript source — parameters are placeholder values that will be substituted
// Use real typed values; their types determine what substConstants accepts later
const templateSource = `
{
  val buyer       = PK("9f4QF8AD1nQ3nJahQVkMj8hFSVVzVom77b52JU7EW71Zexg6N8v")  // index 0
  val deadline    = 1000000                                                       // index 1
  val requiredId  = fromBase16("0000000000000000000000000000000000000000000000000000000000000000") // index 2

  val validToken  = INPUTS(1).tokens(0)._1 == requiredId
  val validTime   = HEIGHT < deadline
  val validSig    = buyer

  sigmaProp(validToken && validTime) && validSig
}
`;

// Compile WITH constant segregation enabled
const template = compile(templateSource, {
  segregateConstants: true,   // sets bit 4 in the ErgoTree header
  version: 1,
});

console.log("Template ErgoTree (hex):", template.toHex());
// Store this hex string — it is your reusable template
```

#### Step 2: Inspect Constants (Development Time)

```typescript
import { ErgoTree } from "@fleet-sdk/core";

const tree = ErgoTree.fromHex(template.toHex());

// List all segregated constants with their indices and types
tree.constants.forEach((constant, index) => {
  console.log(`[${index}] type: ${constant.type}, value: ${constant.value}`);
});

// Expected output:
// [0] type: SGroupElement,  value: <GroupElement of placeholder pubkey>
// [1] type: SInt,           value: 1000000
// [2] type: SColl[SByte],   value: <32 zero bytes>
```