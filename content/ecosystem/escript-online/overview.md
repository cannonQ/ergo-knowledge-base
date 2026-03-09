---
title: SavonarolaLabs/escript-online — Overview
description: EScript Online — in-browser ErgoScript editor and compiler playground
tags: [savonarolalabs, escript-online, reference, typescript, svelte]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/SavonarolaLabs/escript-online"
project: savonarolalabs-escript-online
group: reference
priority: low
languages: [typescript, svelte]
contract_count: 0
pattern_match_count: 2
---
# EScript Online — Developer Overview

---

## Overview

EScript Online (`SavonarolaLabs/escript-online`) is an in-browser ErgoScript editor and compiler playground that allows developers to write, compile, and inspect ErgoScript contracts without leaving the browser. It serves as a zero-friction entry point for developers exploring the Ergo eUTXO smart contract model, removing the need for a local Scala/SBT toolchain to experiment with ErgoScript compilation. The tool lowers the barrier to entry for authoring contracts that compile to ErgoTree — the low-level bytecode representation executed by Ergo nodes.

Within the Ergo ecosystem, EScript Online functions as a reference and educational resource. Developers can immediately validate ErgoScript syntax, inspect the resulting ErgoTree serialization, and reason about Sigma protocol predicates — all from a browser tab. This makes it particularly valuable during the early design phases of Multi-stage contracts, Singleton/State NFT patterns, or any contract that requires iterative scripting and inspection before integration into an off-chain bot or Headless dApp.

The project is built with SvelteKit and TypeScript, keeping the UI layer reactive and the compiler logic modular. A secondary Blockly-based interface (`src/routes/blockly/ergoscript.ts`) suggests a visual, block-based authoring surface for ErgoScript, aimed at developers who are less familiar with the textual DSL but want to construct contracts compositionally.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Browser (SvelteKit)            │
│                                                 │
│  ┌──────────────┐      ┌───────────────────┐   │
│  │  Editor UI   │─────▶│  compiler.ts      │   │
│  │  (Svelte     │      │  (src/lib/)       │   │
│  │   component) │      │                   │   │
│  └──────────────┘      │  ErgoScript →     │   │
│                        │  ErgoTree / bytes │   │
│  ┌──────────────┐      └───────────────────┘   │
│  │  Blockly UI  │─────▶ ergoscript.ts           │
│  │  (visual     │       (block → script text)   │
│  │   blocks)    │                               │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

### Key Components

| Component | Path | Role |
|---|---|---|
| **Compiler module** | `src/lib/compiler.ts` | Core compilation logic: accepts ErgoScript source text and invokes the ErgoScript compiler (likely via a WASM or JS-compiled Sigma-Rust / Sigma.js binding) to produce ErgoTree bytes |
| **Editor route** | `src/routes/` | SvelteKit route providing the primary text-based editor UI, input binding, and output display |
| **Blockly ErgoScript** | `src/routes/blockly/ergoscript.ts` | Defines Blockly block definitions and code generators that emit ErgoScript source text from a visual block graph |
| **SvelteKit shell** | `svelte.config.js`, `vite.config.ts` | Build and adapter configuration; the app is statically deployable (no server-side state required) |

### Data Flow

```
[User types ErgoScript]
        │
        ▼
[compiler.ts: parse + compile]
        │
        ├──▶ [ErgoTree hex / Base58]
        ├──▶ [Serialized contract bytes]
        └──▶ [Compilation error / type errors]

[Blockly blocks]
        │
        ▼
[ergoscript.ts: block → ErgoScript source]
        │
        ▼
[compiler.ts] ──▶ [same output pipeline]
```

The compiler module is the single authoritative transformation point. Both authoring surfaces (text editor and Blockly) funnel into it, meaning ErgoTree output is consistent regardless of the input modality.

---

## Smart Contracts

EScript Online does not deploy or own any on-chain ErgoScript contracts of its own — it is entirely a client-side tooling application with no protocol-level presence. Its purpose is the **authoring and inspection** of ErgoScript contracts that developers will deploy elsewhere.

However, the tool directly supports the full ErgoScript contract surface:

- **Sigma protocol predicates** — `sigmaProp`, `proveDlog`, `proveDHTuple`, threshold signatures (`atLeast`), Ring signatures
- **Box and Register access** — `SELF`, `INPUTS`, `OUTPUTS`, `dataInputs`; typed register extraction via `R4`–`R9`
- **Context and ErgoScript context variables** — `HEIGHT`, `CONTEXT`, `LastBlockUtxoRootHash`, AVL tree membership proofs
- **Context extension** — custom key-value pairs injected by the prover into a transaction input
- **Native token logic** — Token ID rule enforcement, token amounts in Box assets
- **Constant segregation** — ErgoScript constants can be separated from ErgoTree structure, enabling template reuse

Developers commonly use the playground to prototype:
- **Multi-stage contract** scripts with state transitions guarded by predicate checks
- **Singleton / State NFT** locking scripts that enforce a unique Token ID rule through the transaction
- **Storage rent**-aware contracts that account for box longevity
- Atomic swap scripts and time-locked Sigma protocol predicates

---

## Integration Guide

EScript Online is a frontend-only tool; there is no REST API or SDK surface to call programmatically. Integration is developer-workflow-oriented rather than application-to-application.

### Using Compiler Output in Off-Chain Code

The primary integration pattern is **copy the ErgoTree output into your off-chain tooling**:

**Fleet SDK (TypeScript)**
```typescript
import { ErgoTree, ErgoAddress } from "@fleet-sdk/core";

// Paste the ErgoTree hex from EScript Online
const ergoTreeHex = "0008cd..."; // output from compiler.ts

const address = ErgoAddress.fromErgoTree(ergoTreeHex, Network.Mainnet);
console.log(address.toString()); // P2S address for the contract
```

**AppKit (JVM / Scala)**
```scala
val ergoTreeHex = "0008cd..." // paste from EScript Online
val ergoTree = ErgoTreeSerializer.DefaultSerializer
  .deserializeErgoTree(Base16.decode(ergoTreeHex).get)
val contract = new ErgoTreeContract(ergoTree, NetworkType.MAINNET)
```

### Running EScript Online Locally

```bash
git clone https://github.com/SavonarolaLabs/escript-online
cd escript-online
npm install
npm run dev
```

### Embedding the Compiler Module

If `src/lib/compiler.ts` exposes a compile function, it can be consumed directly in other TypeScript/SvelteKit projects:

```typescript
import { compile } from "$lib/compiler";

const result = await compile(`
  sigmaProp(HEIGHT > 1000000)
`);

if (result.success) {
  console.log(result.ergoTree);  // hex-encoded ErgoTree
} else {
  console.error(result.error);
}
```

The exact API shape depends on whether the underlying compiler is Sigma-Rust WASM, a bundled JS port, or a remote compilation endpoint — inspect `compiler.ts` to determine the binding.

---

## Key Patterns

### In-Browser ErgoScript Compilation
The most notable pattern: the full ErgoScript → ErgoTree compilation pipeline runs **client-side in the browser**. This is achieved via a WebAssembly or JavaScript compilation target (likely `sigma-rust` compiled to WASM, or `sigmastate-interpreter` via Scala.js). This enables offline use and zero backend infrastructure.

### Dual Authoring Surface (Text + Visual / Blockly)
The project demonstrates a **code generation pattern** where Blockly block graphs are translated to ErgoScript source text before compilation. This is a common pattern for educational tools and mirrors how Scratch-style environments generate code. The `ergoscript.ts` file defines the mapping