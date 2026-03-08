---
title: ergoplatform/sigmastate-interpreter — Overview
description: ErgoScript compiler internals, ErgoTree spec, test cases as usage examples
tags: [ergoplatform, sigmastate-interpreter, core-protocol, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergoplatform/sigmastate-interpreter"
project: ergoplatform-sigmastate-interpreter
group: core-protocol
priority: high
languages: [scala]
contract_count: 0
pattern_match_count: 0
---
# Developer Overview: ergoplatform/sigmastate-interpreter

## Overview

The `sigmastate-interpreter` repository is the foundational cryptographic and compilation engine at the heart of Ergo's smart contract system. It implements the **ErgoScript compiler** and **ErgoTree interpreter** — collectively the "Sigma language" stack — which defines how spending conditions for eUTXO Boxes are expressed, compiled, reduced, and verified on the Ergo blockchain. Every Box stored in Ergo's UTXO set carries an ErgoTree (serialized bytecode) as its guarding proposition; this library is responsible for both producing that bytecode from human-readable ErgoScript source and evaluating it at transaction validation time.

ErgoTree is a typed, deterministic bytecode language whose propositions are logic formulas combining arbitrary predicate evaluation over a blockchain **ErgoScript context** (current height, spending transaction, input/output Boxes, Registers, Data inputs, Context extension variables) with cryptographic statements expressible as **Sigma protocols** — zero-knowledge proofs of knowledge connected via AND, OR, and k-of-n threshold connectives. This design allows Ring signatures, threshold multi-sig, and novel compound authentication schemes to be expressed without requiring a hard-fork to add new primitives. The Fiat-Shamir heuristic is applied to convert interactive Σ-protocol transcripts into non-interactive proofs (transaction signatures), making the entire system compatible with a standard UTXO-based blockchain.

Within the Ergo ecosystem this library is the lowest-level JVM (and JavaScript, via Scala.js) artifact for contract logic. It is consumed directly by the Ergo Node and ergo-wallet for transaction validation and signing. Application developers are generally encouraged to use **Appkit** or **Fleet** as higher-level SDKs that wrap this library, but direct use is appropriate when building tooling, alternative interpreters, or cross-platform (JS/Android) signing infrastructure.

---

## Architecture

### Sub-module Breakdown

| Module | Responsibility |
|---|---|
| `core` | Primitive types, `SType` hierarchy, `Value`/`SigmaBoolean` ADT, cost model constants |
| `data` | ErgoTree AST nodes, `ErgoTree` serialization/deserialization, address encoding, `Registers`, `Box` model, all serializers |
| `parsers` | ErgoScript text → untyped AST via FastParse; tokenizer and grammar rules |
| `sc` | Type-checker, binder, `SigmaCompiler` — produces typed ErgoTree from parsed AST; constant segregation |
| `interpreter` | `Interpreter` (verifier path) and `ProverInterpreter` (prover path); reduction engine, cost estimator, signature verifier |
| `sdk` | Higher-level `ReducingInterpreter`, `TransactionBuilder` helpers, transaction reduction and signing orchestration |
| `sigma-js` | Scala.js façade exposing core types and signing to the NPM `sigmastate-js` package |

### Data Flow

```
ErgoScript source text
        │
        ▼
  [parsers] FastParse → Untyped AST
        │
        ▼
  [sc] SigmaCompiler (type-check, bind, constant segregation)
        │
        ▼
  ErgoTree (typed AST + serialized bytes)  ──stored in Box.propositionBytes──►  Blockchain
        │                                                                              │
        │                                                           [data] deserialize │
        ▼                                                                              ▼
  [interpreter] Reduction phase                                            ErgoTree (in-memory)
    - Evaluates ErgoTree against ErgoScript context                                   │
    - Context: HEIGHT, SELF, INPUTS, OUTPUTS, Data inputs,                            │
      Context extension, AVL tree digests, Token IDs              ◄───────────────────┘
        │
        ▼
  SigmaBoolean (sigma proposition tree)
        │
        ├──[interpreter] Cost estimation → reject if > MAX_BLOCK_COST
        │
        ├──[Prover path] Fiat-Shamir transformation
        │       Secrets (dlog witnesses, Diffie-Hellman tuples) → Proof bytes
        │
        └──[Verifier path] Signature verification
                Proof bytes + SigmaBoolean + message hash → Boolean
```

### Key Abstractions

- **`ErgoTree`** (`data` module, `Values.scala`): The canonical in-memory and serialized representation of a guarding proposition. Carries a header byte (version, constant-segregation flag), an optional segregated constants array, and a root expression node.
- **`SigmaBoolean`** / **`SigmaProofTree`**: The output of the reduction phase. A tree of `ProveDlog`, `ProveDHTuple`, `CAND`, `COR`, `CTHRESHOLD` nodes representing the residual cryptographic obligation after all non-cryptographic predicates have been evaluated.
- **`ErgoScript context`** (`Context` / `ContextExtension`): The shared, deterministic environment available during reduction. Encapsulates `SELF` Box, `INPUTS`, `OUTPUTS`, `DATA_INPUTS`, `HEIGHT`, and a `ContextExtension` map for caller-supplied typed variables.
- **`SigmaCompiler`** (`sc` module): Entry point for source-to-ErgoTree compilation. Applies parsing → binding → type inference → IR lowering. Supports **constant segregation** (separating literal constants from the tree structure to enable template reuse).
- **`ProverInterpreter`** / **`Interpreter`**: The prover adds secrets and drives the two-phase prove/sign cycle. The verifier drives the two-phase reduce/verify cycle. Both share the same deterministic reduction engine.

---

## Smart Contracts

The repository does not deploy production application-level contracts (like SigmaUSD or Dexy vaults), but it contains an extensive suite of **ErgoScript contract examples used as specification test cases**. These cover the full surface of the ErgoScript language and serve as the canonical correctness reference:

| Contract Pattern | Description |
|---|---|
| **P2PK (Pay-to-Public-Key)** | `proveDlog(pk)` — simplest spending condition; baseline for all dlog-based authentication |
| **Freeze / time-lock** | `HEIGHT > deadline && pkOwner` — demonstrates context variable `HEIGHT` and boolean composition |
| **Multi-sig (k-of-n)** | `atLeast(k, Coll(pk1, pk2, pk3))` — k-out-of-n Σ-protocol threshold via `CTHRESHOLD` |
| **Ring signature** | `pkAlice || pkBob` — `COR` node enabling ring-sig without revealing which key signed |
| **Token-guarded boxes** | Checks `SELF.tokens`, enforcing **Token ID rule** and quantity invariants |
| **Register access** | Reads typed values from `R4`–`R9` Registers with `SELF.R4[T].get` |
| **Data input patterns** | Read-only oracle box access via `CONTEXT.dataInputs(0)` — the canonical oracle pattern |
| **AVL tree proofs** | `avlTree.contains(key, proof)` / `avlTree.insert(...)` — authenticated dictionary operations for State NFT patterns |
| **Context extension** | Caller-supplied variables injected via `getVar[T](id)` — enables parameterized scripts |
| **Atomic swap** | Two-party cross-chain swap using hash preimage + timeout, foundational for DEX designs |
| **Sigma-AND / Sigma-OR composition** | Compound propositions demonstrating all Σ-protocol connectives |
| **Storage rent (simulated)** | HEIGHT-based conditions modeling Storage rent collection eligibility |

These test contracts live primarily in `sc/src/test/` and `interpreter/src/test/` and double as the normative usage examples for the language specification.

---

## Integration Guide

### JVM (Scala/Java/Kotlin)

Add the Maven artifact:

```scala
// build.sbt
libraryDependencies += "org.scorexfoundation" %% "sigma-state" % "5.0.14"
```

**Compiling ErgoScript to