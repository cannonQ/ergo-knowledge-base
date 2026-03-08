---
title: ergoplatform/eips — Overview
description: All Ergo Improvement Proposals as structured reference docs
tags: [ergoplatform, eips, core-protocol, markdown]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergoplatform/eips"
project: ergoplatform-eips
group: core-protocol
priority: high
languages: [markdown]
contract_count: 0
pattern_match_count: 0
---
# ergoplatform/eips — Developer-Focused Overview

---

## Overview

The **Ergo Improvement Proposals (EIPs)** repository is the canonical, structured reference for all standards governing the Ergo Platform. It serves the same function as EIPs in Ethereum or BIPs in Bitcoin: a disciplined, peer-reviewed process for proposing, debating, and ratifying changes or conventions that affect the protocol, tooling, wallet integrations, and dApp development practices. Each EIP is a self-contained Markdown document with a defined format covering motivation, specification, and rationale, making the repository the authoritative source of truth for anyone building on or extending the Ergo ecosystem.

The scope of EIPs deliberately spans multiple layers of the stack. Some EIPs define **core protocol behavior** — such as consensus-level Soft-fork rules (EIP-0027, EIP-0039) touching the Emission schedule, Autolykos block rewards, and Box creation-height invariants. Others establish **client and wallet standards** (EIP-0001, EIP-0003, EIP-0020) that govern how off-chain software communicates with nodes and signs transactions. A third category covers **dApp and contract standards** (EIP-0004, EIP-0005, EIP-0022, EIP-0024, EIP-0034) that define how Native tokens, NFTs, and ErgoScript contracts should be structured so that wallets, explorers, and front-ends can interoperate without bespoke integration work.

For developers, the EIPs repository is a prerequisite reading list. Understanding which EIPs your project touches — whether you are implementing a Headless dApp, an Off-chain bot, an EIP-12-style connector, or a Multi-stage contract — determines the interfaces, data formats, Registers conventions, and transaction-building rules your code must respect. Non-compliance with a ratified EIP typically means incompatibility with the broader ecosystem tooling.

---

## Architecture

The repository itself has a deliberately flat, document-centric architecture. There are no build artifacts, compiled outputs, or runtime dependencies — the entire content is Markdown files plus a README index. The design reflects the nature of a standards body: the "components" are the EIPs themselves, organized by concern, and their relationships are cross-references between documents.

### Logical Groupings

| Layer | EIPs | What They Define |
|---|---|---|
| **Core Protocol** | EIP-0027, EIP-0039 | Soft-fork rules, Emission retargeting, Monotonic Box creation height rule, Difficulty adjustment side-effects |
| **Wallet & Key Management** | EIP-0001, EIP-0003, EIP-0019, EIP-0044 | Application-Friendly Wallet API, Deterministic Wallet Standard (HD paths), Cold Wallet Protocol, Arbitrary Data Signing Standard |
| **Transaction Protocols** | EIP-0020, EIP-0025, EIP-0031, EIP-0043 | ErgoPay Protocol, Payment Request URI, Babel Fees, Reduced Transaction format |
| **Token & Asset Standards** | EIP-0004, EIP-0021, EIP-0024, EIP-0034 | Assets standard (Token ID rule, Registers layout), Genuine token verification, Artwork Standard, NFT Collection Standard |
| **Contract Standards** | EIP-0005, EIP-0006, EIP-0017, EIP-0022 | Contract Template format, Informal Smart Contract Protocol Specification, Proxy Contracts, Auction Contract |
| **Process** | EIP-0001 (meta), EIP-0002 | EIP formatting expectations, Ergo grant program |

### Data Flow Through the Standards

```
Core Protocol EIPs
        │  define consensus rules, Box validity, emission
        ▼
Node / Ergo Reference Client
        │  exposes REST API shaped by
        ▼
EIP-0001 (Wallet API) ──► EIP-0020 (ErgoPay) ──► EIP-0025 (Payment URI)
        │
        ▼
SDK / dApp layer
        │  builds Transactions using Boxes with Registers
        │  laid out per EIP-0004 / EIP-0024 / EIP-0034
        ▼
Wallet (EIP-0003 HD paths, EIP-0019 cold signing, EIP-0044 data signing)
        │
        ▼
Signed Transaction → mempool → confirmed eUTXO state
```

Each EIP is effectively a **contract between implementers**: a node implementation, a wallet, and a dApp can all be written independently and still interoperate because they share the normative text of the relevant EIPs.

---

## Smart Contracts

Several EIPs directly specify ErgoScript contracts or define standards that govern how contracts must be written and registered.

### EIP-0005 — Contract Template
Defines a structured format for publishing ErgoScript contract templates, including parameter declarations, ErgoTree derivation rules, and Constant segregation. Allows tooling to instantiate a contract by substituting constants without recompiling the full ErgoScript source, which is essential for reproducible ErgoTree verification.

### EIP-0006 — Informal Smart Contract Protocol Specification Format
Provides a documentation schema for describing Multi-stage contracts and State machine protocols. Specifies how to document each stage's Box structure, Registers usage, guarding ErgoScript, and valid Transaction shapes (inputs, outputs, Data inputs). This is the authoring standard used by projects like SigmaUSD and Dexy when publishing their protocol specs.

### EIP-0017 — Proxy Contracts
Specifies a Proxy Contract pattern where a user funds an intermediate Box whose ErgoScript allows a designated off-chain bot to complete a transaction on the user's behalf. Critical for dApps where the user cannot construct the full Transaction in one step (e.g., AMM order execution). Defines the spending conditions, refund paths, and the Minimum box value guarantees the proxy must preserve.

### EIP-0022 — Auction Contract
Provides a reference ErgoScript implementation and behavioral specification for on-chain English auctions over Native tokens and NFTs. Defines Registers layout (R4: seller address, R5: minimum bid, R6: auction end height, R7: bid step), valid bid Transaction structure, and the winner-claim Transaction. Serves as both a deployable contract and a standard so multiple auction front-ends can read the same on-chain state.

### EIP-0031 — Babel Fees
Specifies the contract and protocol allowing transaction fees to be paid in Native tokens rather than ERG. The Babel Fee provider posts a Box with an ErgoScript that accepts a specific Token ID in exchange for ERG, enabling fee-abstraction for end users. The EIP defines the exchange-rate encoding in Registers and the atomic Transaction structure that simultaneously satisfies the Minimum transaction fee in ERG and reimburses the provider in tokens.

### EIP-0027 — Emission Retargeting Soft-Fork
Though primarily a protocol-level EIP, it specifies the modified emission contract (a redeployment of the emission Box guarding script) that redistributes a portion of miner rewards to re-emission. Documents the Soft-fork activation mechanism, the new ErgoTree for the emission Singleton box, and the Storage rent implications.

---

## Integration Guide

Because EIPs are standards documents rather than executable code, "integration" means **conforming your implementation to the normative specifications**. The following describes how each major EIP category translates into off-chain development work.

### Reading and Writing Tokens (EIP-0004, EIP-0021, EIP-0024, EIP-0034)

All Native token metadata follows the **Assets standard (EIP-0004)**, which defines that:
- The issuing Box (the one with the minting Transaction's first input Box ID as Token ID) places metadata in **R4** (name, UTF-8 bytes), **R5** (description), **R6** (number of decimals), **R7** (optional logo/type indicator).
- Downstream tooling (explorers, wallets) reads these Registers to display token information without a separate registry.

**EIP-0024** (Artwork) and **EIP-0034** (NFT Collections) extend EIP-0004 with additional Register conventions:
- R7 encodes artwork type or collection link Token ID.
- R8/R9 hold royalty information and trait data, respectively, encoded as `