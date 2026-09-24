---
title: fleet-sdk/docs — Overview
description: Fleet SDK VitePress documentation — migrate and cross-reference
tags: [fleet-sdk, docs, sdk, markdown]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/fleet-sdk/docs"
project: fleet-sdk-docs
group: sdk
priority: high
languages: [markdown]
contract_count: 0
pattern_match_count: 0
---
# Fleet SDK Docs — Developer Overview

---

## Overview

The **fleet-sdk/docs** project is the official VitePress-based documentation site for [Fleet SDK](https://github.com/fleet-sdk/fleet), a modular, TypeScript-native off-chain SDK for the [Ergo Platform](https://ergoplatform.org). Its primary role is to serve as the canonical developer reference for constructing, signing, and submitting Ergo transactions entirely in TypeScript — without requiring a custom backend. The documentation covers everything from initial installation and package imports through advanced topics such as Native token minting, token burning, Data inputs, and wallet interaction patterns.

Within the Ergo ecosystem, this documentation site occupies a critical education and onboarding function. It bridges the gap between Ergo's eUTXO data model — where every value-carrying unit is a **Box** carrying ERG (in nanoergs), **Native tokens**, and up to ten **Registers** — and the TypeScript developer audience that may be unfamiliar with Ergo's extended UTXO semantics. The docs explain how Ergo's **eUTXO** model differs from account-based chains, why atomic transaction semantics matter, and how **Data inputs** allow contracts (such as **SigmaUSD**'s oracle-fed price feed) to read external state without consuming it.

The project also acts as a living migration and cross-reference hub: as Fleet SDK packages evolve, the docs are updated to reflect breaking changes, new EIP compliance (e.g., **EIP-4** token standard), and new patterns such as headless dApp construction. All content is written in Markdown and rendered via VitePress, making it straightforward to contribute through GitHub pull requests or a local IDE.

---

## Architecture

The documentation project is a static VitePress site. Its architectural components are minimal but purposeful:

### Content Layer (Markdown)

All developer-facing content lives as `.md` files organized by topic:

| File | Responsibility |
|---|---|
| `index.md` | VitePress home page — hero section, feature highlights, navigation entry points |
| `getting-started.md` | Step-by-step installation, first import, and minimal transaction construction |
| `transaction-building.md` | Deep-dive into `TransactionBuilder` and `OutputBuilder` APIs, covering Boxes, eUTXO semantics, Data inputs, token minting, change calculation, and fee handling |
| `token-burning.md` | Explains the **Token ID rule** and safe/explicit token burning via `burnTokens()` |
| `wallet-interaction.md` | (referenced) Covers EIP-12 wallet connector patterns for fetching boxes and obtaining creation height |

### Build Layer (VitePress)

VitePress compiles the Markdown sources into a static site using Vue 3 under the hood. Code blocks leverage VitePress's `::: code-group` and `[!code focus]` directives to produce tabbed, annotated examples. No server-side runtime is required; the output is fully static and CDN-deployable.

### Data Flow

```
Developer reads docs
        │
        ▼
VitePress static site (Markdown → HTML)
        │
        ▼
Code examples reference @fleet-sdk/core APIs
        │
        ├── TransactionBuilder   ←→  Input Boxes (fetched from node / wallet)
        │         │
        │         ├── .from(inputs)            — eUTXO Box selection
        │         ├── .withDataFrom(dataInputs) — Data input references
        │         ├── .to(OutputBuilder)        — eUTXO output construction
        │         ├── .burnTokens(...)          — Token ID burn declaration
        │         ├── .sendChangeTo(addr)       — Change box routing
        │         └── .payMinFee()              — Minimum transaction fee
        │
        └── OutputBuilder
                  ├── addTokens(...)            — Native token attachment
                  └── mintToken(...)            — EIP-4 token minting
```

The documentation itself does not execute code; it describes the API surface of `@fleet-sdk/core` and cross-references related packages (serialization, crypto, wallet connectors) via sidebar links.

---

## Smart Contracts

The **fleet-sdk/docs** project contains **no ErgoScript contracts directly**. It is a documentation-only repository written entirely in Markdown.

However, the documentation extensively references smart contract concepts as context for the off-chain code it describes:

- **ErgoTree / ErgoScript**: The `Box` type exposed in the docs includes an `ergoTree` field — the serialized, compiled form of the contract guarding each box. Fleet SDK consumers must supply valid ErgoTree strings when constructing output boxes.
- **Registers**: The `additionalRegisters` field on the `Box` type (R4–R9) is referenced throughout. Contracts read register values at validation time; Fleet SDK populates them via `OutputBuilder` methods.
- **Data inputs**: Documented explicitly in `transaction-building.md` as a mechanism for contracts to read oracle box state (e.g., the ERG/USD price box used by **SigmaUSD**) without spending it. This is a core eUTXO pattern enabling **multi-stage contracts** and **state machine** designs.
- **EIP-4 Token Standard**: The `mintToken()` API encodes token metadata into **Registers** R4–R7 following EIP-4, which defines how token name, description, decimal count, and type are stored so that wallets and dApps can uniformly decode them.
- **Singleton / State NFT pattern**: Implicitly supported — developers can mint exactly one token (one token per transaction, Token ID equals first input's Box ID, enforced by the **Token ID rule**) to create an NFT usable as a **Singleton** or **State NFT** in multi-stage contract designs.

---

## Integration Guide

Fleet SDK docs describe integration from an entirely **off-chain perspective**. The canonical integration path for a developer reading this documentation is as follows:

### 1. Install the Core Package

```bash
npm i @fleet-sdk/core
```

Additional Fleet packages (serialization, crypto, wallet connectors) are installed separately, following Fleet's modular design.

### 2. Obtain Inputs and Creation Height

Before building a transaction, the developer must:
- Fetch unspent **Boxes** (eUTXO inputs) from the Ergo node REST API or a connected EIP-12 wallet.
- Retrieve the current block height (used as **creation height** for new output boxes).

The `wallet-interaction.md` page (referenced in `getting-started.md`) covers this via the EIP-12 dApp connector pattern.

### 3. Construct the Transaction

```ts
import { TransactionBuilder, OutputBuilder } from "@fleet-sdk/core";

const unsignedTx = new TransactionBuilder(creationHeight)
  .from(inputs)                          // eUTXO Box inputs
  .withDataFrom(dataInputs)              // optional Data inputs (e.g., oracle boxes)
  .to(
    new OutputBuilder(1_000_000n, recipientAddress)
      .addTokens({ tokenId, amount })    // Native token transfer
  )
  .sendChangeTo(changeAddress)           // change Box routing
  .payMinFee()                           // Minimum transaction fee (currently 0.001 ERG)
  .build();
```

### 4. Sign and Submit

The unsigned transaction object produced by `.build()` is passed to a signing layer — either an EIP-12 wallet connector (browser) or a node-side signing key. After signing, the signed transaction is submitted to the Ergo node via the `/transactions` REST endpoint.

### 5. Token Operations

| Operation | API | Notes |
|---|---|---|
| Transfer Native tokens | `OutputBuilder.addTokens()` | Sums duplicates by default |
| Mint new token (EIP-4) | `OutputBuilder.mintToken()` | One token per transaction; Token ID = first input Box ID |
| Burn tokens | `TransactionBuilder.burnTokens()` | Explicit declaration required; Fleet enforces input/output token balance by default |

### Key Type: Box

```ts
type Box = {
  boxId: string;
  value: string | bigint;          // nanoergs
  assets: { tokenId: string; amount: string | bigint }[];
  ergoTree:
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
