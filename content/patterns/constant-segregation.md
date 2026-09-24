---
title: Constant segregation
description: Constant segregation — substConstants pattern for contract templates without recompilation
tags: [constant-segregation, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repos: [ergoplatform/sigmastate-interpreter, fleet-sdk/fleet]
---
# Developer Guide: Constant Segregation — `substConstants` Pattern for Contract Templates Without Recompilation

---

## Overview

### What This Pattern Is

**Constant segregation** is an ErgoTree serialization feature that physically separates the constant values embedded in a contract from its structural logic. When the constant segregation flag is set in the ErgoTree header byte, constants are stored in a dedicated array at the front of the serialized form, while the expression tree references them by positional index rather than by value.

The `substConstants` function — exposed on the `Global` object in ErgoScript and mirrored in the Fleet SDK, `sigma-rust`, and the JVM `SigmaDsl` — exploits this layout to **swap specific constants in a serialized ErgoTree without recompiling the script from source**. The result is a new, valid ErgoTree byte array representing a functionally identical contract parameterized with different values.

### Why It Exists

Compiling an ErgoScript program is an expensive operation that requires the full Sigma compiler toolchain. In production systems:

- Wallets and dApps often hold a single canonical **contract template** and need to stamp out thousands of per-user or per-session instances (e.g., one ErgoBox per liquidity position, one per vesting schedule, one per atomic swap offer).
- On-chain verification of script identity is easier when only the bytes change at well-known offsets — a verifier can reconstruct the expected script by calling `substConstants` on the canonical template rather than recompiling.
- Compilation in resource-constrained environments (browser WASM, mobile, embedded signers) is impractical; byte-level substitution is not.

The constant segregation header bit is the on-chain signal that tells the Ergo node's **ErgoTree** deserializer to apply the constants array before evaluating the proposition. When `isConstantSegregation()` returns `true`, `ErgoBoxCandidate.proposition` automatically merges the constants back into the tree at evaluation time.

### When to Use It

| Situation | Use `substConstants`? |
|---|---|
| Deploying parameterized contracts at scale (DEX orders, vesting, auctions) | ✅ Yes |
| Verifying on-chain that a Box holds the expected template | ✅ Yes |
| Building a contract factory that stamps out per-user scripts | ✅ Yes |
| One-off script with no parameters to vary | ❌ No — compile directly |
| Parameters are complex types not representable as ErgoTree constants | ❌ No — use Registers or Context extension |

---

## How It Works

### Step-by-Step Flow

#### 1. Compile the Template Once with Constant Segregation Enabled

The canonical template is compiled **once** from ErgoScript source with the `constantSegregation` flag set. This produces an ErgoTree whose header byte has bit 4 set (`0x10` combined with the version nibble).

```
Header byte layout (ErgoTree v0/v1):
  bit 7-4: reserved / version
  bit 3:   hasSize flag
  bit 4:   isConstantSegregation flag  ← must be 1 for this pattern
```

The serialized bytes look like:

```
[header][nConstants:VLQ][const_0_bytes]...[const_n_bytes][expression_tree_bytes]
```

Each constant reference in the expression tree is a `ConstantPlaceholder(index, type)` node instead of the literal value.

#### 2. Store or Distribute the Template Bytes

The template bytes are typically:
- Hard-coded as a hex string in a dApp's source code.
- Stored in a **Singleton / State NFT** Box register (e.g., `R4`) so contracts can read it as a data input.
- Published in documentation or an EIP so third parties can verify contract identity.

#### 3. Call `substConstants` to Parameterize

`substConstants(scriptBytes, positions, newValues)` takes:

| Parameter | Type | Description |
|---|---|---|
| `scriptBytes` | `Coll[Byte]` | The template's serialized ErgoTree bytes |
| `positions` | `Coll[Int]` | Zero-based indices into the constants array |
| `newValues` | `Coll[T]` | Replacement values, matched by position |

It returns a new `Coll[Byte]` with the specified constants replaced. The expression tree bytes are **not touched**.

#### 4. Use the Result as a Box's Guarding Script

The returned bytes are a complete, valid ErgoTree. They can be:
- Used as the `ergoTree` of an `ErgoBoxCandidate` in a transaction output.
- Verified on-chain by another contract that reconstructs the expected bytes and compares.

#### 5. On-Chain Evaluation

When the Ergo node evaluates the Box's proposition, it sees `isConstantSegregation == true` and merges the substituted constants back into the expression tree before running the Sigma protocol proof checker.

```
Deserialization path:
  bytes → header → isConstantSegregation? → merge constants array
        → ErgoTree expression with concrete values → ErgoScript context evaluation
        → SigmaProp → Sigma protocol verification
```

---

## Implementation

### ErgoScript: Verifying a Template On-Chain

The most powerful use of `substConstants` is **inside** an ErgoScript to verify that an output Box holds the expected parameterized contract. The `Global.substConstants` call is available in ErgoScript v1+.

```scala
// ErgoScript — contract that verifies an output holds a correctly parameterized child contract
// Scenario: a "factory" box that creates per-user vesting contracts.
// R4 of SELF holds the canonical template bytes (Coll[Byte]).
// The output at index 0 must carry the template instantiated with the buyer's PK.

{
  // Template bytes stored in R4 of the factory box
  val templateBytes = SELF.R4[Coll[Byte]].get

  // The buyer's public key is passed as the first input context extension variable
  // Context extension variable 0 holds the raw GroupElement bytes of the buyer's key
  val buyerPkBytes = getVar[Coll[Byte]](0).get

  // Position 0 in the constants array is the placeholder for the recipient public key
  val expectedScript = Global.substConstants(
    templateBytes,
    Coll(0),          // positions: replace constant at index 0
    Coll(buyerPkBytes) // newValues: the buyer's serialized GroupElement
  )

  // The output at index 0 must have exactly this script
  val outputScriptCorrect = OUTPUTS(0).propositionBytes == expectedScript

  // The output must carry the minimum box value
  val outputValueCorrect = OUTPUTS(0).value >= 1000000L

  sigmaProp(outputScriptCorrect && outputValueCorrect)
}
```

> **Key term note:** `OUTPUTS(0).propositionBytes` returns the raw serialized ErgoTree bytes of the output Box, identical to what `ErgoBoxCandidate.propositionBytes` exposes in the JVM SDK. This allows byte-exact comparison without deserialization.

---

### TypeScript: Fleet SDK

Fleet SDK provides `ErgoTree` and contract utilities. Use `sigma-rust-mini` (WASM) for `substConstants` in the browser, or the `@fleet-sdk/compiler` package with the ergoscript compiler server for the initial template compilation.

```typescript
import { ErgoTree, SConstant, SGroupElement, SInt } from "@fleet-sdk/core";
// sigma-rust WASM binding exposes substConstants
import init, { subst_constants } from "ergo-lib-wasm-browser";

await init(); // initialize WASM module

// ── Step 1: The canonical template (compiled once, stored as hex) ──────────
// This hex was produced by compiling the ErgoScript template with
// constant segregation enabled. Constants at positions:
//   [0] = recipient GroupElement (placeholder)
//   [1] = deadline height (placeholder)
const VESTING_TEMPLATE_HEX =
  "100204000e20" + // header + constants section prefix (illustrative)
  "...<full template hex>...";

const templateBytes = Buffer.from(VESTING_TEMPLATE_HEX, "hex");

// ── Step 2: Parameters for this specific vesting instance ─────────────────
// Recipient compressed public key (33 bytes, SEC-encoded GroupElement)
const recipientPkHex = "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798";

// Vesting deadline: block height 1,000,000
const deadlineHeight = 1_000_000;

// ── Step 3: Encode values as ErgoTree constants ────────────────────────────
// substConstants expects the new values encoded as ErgoTree constant bytes.
// SGroupElement wraps a 33-byte compressed point.
const recipientConstantBytes = SConstant(
  SGroupElement(Buffer.from(recipientPkHex, "hex"))
).toBytes(); // → Coll[Byte] in ErgoTree encoding

const deadlineConstantBytes = SConstant(
  SInt(deadlineHeight)
).toBytes();

// ── Step 4: Call substConstants via sigma-rust WASM ───────────────────────
// subst_constants(script_bytes, positions, new_values_bytes_concatenated)
// The WASM binding signature mirrors the ErgoScript Global.substConstants
const parameterizedBytes = subst_constants(
  templateBytes,
  new Int32Array([0, 1]),           // positions: indices 0 and 1
  [recipientConstantBytes, deadlineConstantBytes]
);

const parameterizedHex = Buffer.from(parameterizedBytes).toString("hex");

console.log("Parameterized ErgoTree:", parameterizedHex);

// ── Step 5: Build a transaction output using Fleet SDK ────────────────────
import { OutputBuilder, SAFE_MIN_BOX_VALUE, TransactionBuilder } from "@fleet-sdk/core";

const vestingOutput = new OutputBuilder(
  SAFE_MIN_BOX_VALUE,    // Minimum
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
