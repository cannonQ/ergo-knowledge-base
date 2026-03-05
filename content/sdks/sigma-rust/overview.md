---
title: ergoplatform/sigma-rust — Overview
description: Rust sigma-state implementation — WASM bindings, wallet features, ErgoTree interpreter
tags: [ergoplatform, sigma-rust, core-protocol, rust]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergoplatform/sigma-rust"
project: ergoplatform-sigma-rust
group: core-protocol
priority: high
languages: [rust]
contract_count: 0
pattern_match_count: 0
---
# sigma-rust Developer Overview

---

## Overview

**sigma-rust** is the Rust implementation of the ErgoScript scripting language and ErgoTree interpreter — the core smart contract execution layer of the Ergo blockchain. It faithfully reimplements the reference [`sigmastate-interpreter`](https://github.com/ScorexFoundation/sigmastate-interpreter) (Scala) in Rust, providing the same cryptographic guarantees underpinning Sigma protocols, ring signatures, and the broader eUTXO model. The project is the foundational library for any Rust-based Ergo tooling: it understands the full ErgoTree IR, can evaluate ErgoScript contracts against an ErgoScript context, and handles the complete lifecycle of a transaction — from Box selection through signing and serialization.

Beyond pure contract evaluation, sigma-rust ships a comprehensive wallet-feature layer via its `ergo-lib` umbrella crate. This covers chain primitives (Boxes, Registers, Tokens, Native tokens, Transaction construction, Data inputs), JSON serialization compatible with the Ergo node REST API, coin selection heuristics, and multi-secret transaction signing. The library explicitly targets Minimum box value and Minimum transaction fee rules, respects Storage rent mechanics, and correctly enforces the Token ID rule during token creation and transfer.

The project is also the primary portability layer for the Ergo ecosystem. Through WASM bindings (`ergo-lib-wasm`) the full Rust core is exposed to browser and Node.js environments, enabling Headless dApp patterns in TypeScript/JavaScript. Additional language bindings (Swift, Java/JNI, C, Python, Go, Ruby) mean sigma-rust acts as the canonical cross-platform implementation of Ergo's cryptographic and contract-execution primitives for every non-JVM runtime.

---

## Architecture

### Crate Dependency Graph

```
ergoscript-compiler
    └─ ergotree-ir          (MIR, type system, serialization)
         └─ sigma-ser       (binary serialization primitives)

ergotree-interpreter
    └─ ergotree-ir

ergo-lib                    (public API surface)
    ├─ ergotree-interpreter
    ├─ ergotree-ir
    └─ sigma-ser

bindings/ergo-lib-wasm      ──► ergo-lib
bindings/ergo-lib-jni       ──► ergo-lib
bindings/ergo-lib-c         ──► ergo-lib
bindings/ergo-lib-python    ──► ergo-lib
```

### Core Crates

| Crate | Responsibility |
|---|---|
| `sigma-ser` | Low-level Ergo binary serialization primitives (`SigmaSerializable`, VLQ, ZigZag integers). All on-wire byte formats for Ergo types are built here. |
| `ergotree-ir` | The ErgoTree intermediate representation. Defines the complete MIR (Middle IR) node hierarchy, the type system, type-checking pass, and `SigmaSerializable` implementations for every MIR node. This is the canonical in-memory representation of an ErgoTree. |
| `ergoscript-compiler` | Multi-phase compiler: Lexer → Parser/AST → HIR → Binder → Type Inference → MIR lowering → Type Checking. Entry point: `compiler::compile()`. Produces `ergotree-ir` MIR trees from human-readable ErgoScript source. |
| `ergotree-interpreter` | Tree-walking evaluator. Each MIR node implements `Evaluable::eval()`. Receives a populated ErgoScript context (spending transaction, self Box, Boxes to spend, Data inputs, Context extension, headers) and reduces the tree to a `SigmaBoolean`, which feeds into Sigma protocol proof generation/verification. |
| `ergo-lib` | Umbrella crate. Composes all the above plus: Address types, HD wallet key derivation, Box selection algorithms, TransactionBuilder, signing (single- and multi-secret), JSON serialization, and node API client types. The only crate most downstream consumers import directly. |

### Data Flow: Transaction Building

```
ErgoScript source
      │  ergoscript-compiler
      ▼
  ErgoTree (MIR)  ──serialized──►  Box.ergoTree (P2S)
                                         │
               ergo-lib::TransactionBuilder
                 • selects input Boxes (coin selection)
                 • enforces Minimum box value
                 • enforces Minimum transaction fee
                 • attaches Context extension if required
                 • produces UnsignedTransaction
                         │
               ergotree-interpreter::eval()
                 • constructs ErgoScript context
                 • evaluates ErgoTree per input Box
                 • produces SigmaBoolean / proof hints
                         │
               ergo-lib::Wallet::sign_transaction()
                 • generates Sigma protocol proofs
                 • produces SignedTransaction (ready to submit)
```

### Data Flow: ErgoScript Compilation Pipeline

```
Source text
  │  Lexer (Logos)
  ▼
Token stream
  │  Parser (Rowan CST → AST)
  ▼
AST
  │  Lowering
  ▼
HIR  (Expr { kind, span, Option<Type> })
  │  Binder  (resolves HEIGHT, min/max, ScriptEnv variables)
  ▼
Bound HIR
  │  Type Inference
  ▼
Typed HIR
  │  Lowering
  ▼
MIR  (ergotree-ir)
  │  Type Checking
  ▼
Validated ErgoTree
```

### Key Types in `ergotree-ir` / `ergo-lib`

- **`ErgoTree`** — serialized + deserialized contract. Supports Constant segregation (constants stored separately from the tree body, enabling template reuse without recompilation).
- **`ErgoBox`** / **`ErgoBoxCandidate`** — eUTXO box with value (nanoERGs), `ergoTree`, Registers (R0–R9), Tokens (Native tokens list), creation height.
- **`Registers`** — typed `(R4–R9)` constant storage; mandatory registers (R0–R3) are first-class fields.
- **`Token` / `TokenId`** — enforces the Token ID rule (first input's box ID on minting).
- **`Transaction` / `UnsignedTransaction`** — inputs (with spend proofs), Data inputs, outputs (`ErgoBoxCandidate` list).
- **`ContextExtension`** — key-value map injected into the ErgoScript context by the prover, enabling parameterized contracts without recompilation.
- **`SigmaBoolean` / `SigmaProofTree`** — result of interpreter evaluation; root of Sigma protocol proof tree (supports AND/OR/threshold composition, enabling Ring signatures and threshold Sigma protocols).
- **`AVL tree`** — authenticated dictionary type exposed in ErgoScript context and MIR for stateful proofs.

---

## Smart Contracts

sigma-rust does not itself ship production ErgoScript contract source files — it is the *engine* that compiles and evaluates them. However, several important contract patterns are directly tested and exercised within the codebase:

### Contracts Exercised in Tests and Examples

| Pattern | Description |
|---|---|
| **P2PK (Pay-to-Public-Key)** | Standard `proveDlog(pk)` ErgoTree. The most common spending condition; default output of Address-to-ErgoTree conversion. |
| **P2S (Pay-to-Script)** | Arbitrary ErgoScript compiled to ErgoTree bytes and stored in a Box. |
| **Atomic swaps** | Cross-chain and intra-chain swaps exercising `HEIGHT`-bounded time locks and hash-locked spending conditions. |
| **Multi-stage contracts / State machine** | Transaction chains where output Boxes carry state in Registers and ErgoTree enforces valid state transitions. Used by Oracle Core and AgeUSD (SigmaUSD predecessor). |
| **Singleton / State NFT** | Box guarded by a script that enforces only one token with a specific Token ID exists, implementing a global mutable state cell. |
| **