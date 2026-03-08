---
title: StabilityNexus/Gluon-Ergo-SDK — Overview
description: Gluon Gold stablecoin SDK — headless TypeScript lib for fission/fusion/transmute operations
tags: [stabilitynexus, gluon-ergo-sdk, defi, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Gluon-Ergo-SDK"
project: stabilitynexus-gluon-ergo-sdk
group: defi
priority: medium
languages: [typescript]
contract_count: 0
pattern_match_count: 4
---
# StabilityNexus/Gluon-Ergo-SDK — Developer Overview

---

## Overview

The Gluon-Ergo-SDK is a headless TypeScript library that provides a complete programmatic interface for interacting with the **Gluon Gold** stablecoin protocol on the Ergo blockchain. Gluon Gold is a collateralized asset system built around two native tokens: **Neutrons (GAU)**, a gold-pegged stablecoin, and **Protons (GAUC)**, a leveraged reserve token analogous to the reserve coin in the SigmaUSD model. The SDK abstracts the complexity of constructing valid eUTXO transactions for four core protocol operations — **fission**, **fusion**, **transmute-to-gold**, and **transmute-from-gold** — without requiring a connected wallet or browser extension at the construction layer.

Within the Ergo DeFi ecosystem, Gluon occupies a role similar in spirit to SigmaUSD and Dexy: it uses ERG as its base reserve asset and exposes a two-token mechanic governed by an on-chain invariant. The protocol's Singleton/State NFT pattern means that the entire reserve state lives in a single **Gluon Box**, whose Registers carry all critical protocol variables (circulating supply of Neutrons and Protons, accumulated fees, etc.). The SDK surfaces this state cleanly, computing pricing, fee breakdowns, fusion ratios, TVL, and reserve ratios entirely off-chain from fetched Box data before any transaction is submitted.

The library is deliberately **headless** — it produces both `UnsignedTransaction` objects (suitable for server-side signing or off-chain bot usage) and **EIP-12**-formatted JSON objects (suitable for direct consumption by browser wallets such as Nautilus). This dual output strategy makes the SDK composable across the full range of Ergo dApp integration patterns without coupling it to any specific signing infrastructure.

---

## Architecture

### Core Components

```
┌──────────────────────────────────────────────────────────────┐
│                        Gluon (gluon.ts)                       │
│  Central orchestrator: transaction builders, pricing,         │
│  fee calculation, volume analytics, TVL, reserve ratio        │
└────────────┬──────────────────────┬──────────────────────────┘
             │                      │
             ▼                      ▼
┌────────────────────┐   ┌──────────────────────────┐
│  GluonBox          │   │  GoldOracleBox            │
│  (gluonBox.ts)     │   │  (goldOracleBox.ts)       │
│                    │   │                            │
│  - State NFT       │   │  - External gold price     │
│  - Neutron/Proton  │   │    (nanoERG per kg/gram)   │
│    circulating     │   │  - Read-only Data Input    │
│    supply in Regs  │   │    in most transactions    │
│  - Protocol        │   │                            │
│    invariant data  │   └──────────────────────────┘
└────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│                   fleet-sdk / sigma-rust-mini (WASM)          │
│  Box selection, transaction building, ErgoTree serialization  │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Fetch phase** — `Gluon` queries a configured node or explorer to retrieve the current **Gluon Box** (identified by its Singleton/State NFT Token ID) and the **Gold Oracle Box** (identified by its oracle NFT).
2. **Compute phase** — Off-chain arithmetic replicates the on-chain invariant to determine how many Neutrons/Protons are minted or burned and what fees (dev, UI, oracle) are due for a given ERG or token input amount.
3. **Build phase** — A transaction is assembled using `fleet-sdk`: input Boxes are selected from user UTXOs, the Gluon Box is consumed and re-created with updated Register values, fee Boxes are created for each recipient, and the Oracle Box is attached as a **Data Input** (read-only, not consumed).
4. **Output phase** — The built transaction is serialised either as a `fleet-sdk` `UnsignedTransaction` (for bot/server contexts) or as an EIP-12 JSON object (for browser wallet signing).

### Key Files

| File | Responsibility |
|---|---|
| `src/gluon.ts` | Main entry point; all four operation builders, pricing, analytics |
| `src/gluonBox.ts` | Wrapper around the live Gluon Box eUTXO; Register parsing, invariant helpers |
| `src/index.ts` | Public re-exports (`Gluon`, `GluonBox`, `GoldOracleBox`) |
| `src/test.ts` | Integration test harness demonstrating full transaction lifecycle |

---

## Smart Contracts

The SDK does not ship ErgoScript source directly, but it interacts with the following on-chain contract boundaries:

### Gluon Reactor Box (Multi-stage State Machine)

The central **Gluon Box** is a multi-stage contract controlled by a Singleton/State NFT. Its ErgoTree enforces the protocol invariant across all four operations:

- **Fission** — ERG is deposited; the contract verifies that the correct proportions of Neutrons and Protons (as native tokens) are emitted to the user Box, consistent with the current reserve ratio encoded in the Registers.
- **Fusion** — Neutrons and Protons are burned in the ratio the contract mandates; ERG is returned to the user. The contract checks that the re-created Gluon Box carries updated circulating-supply values in its Registers.
- **Transmute-to-Gold** — Protons are sent to the reactor in exchange for Neutrons. The contract validates the transmutation price derived from the Gold Oracle Box (supplied as a **Data Input**) and the current Proton/Neutron ratio.
- **Transmute-from-Gold** — The inverse: Neutrons are exchanged for Protons.

### Oracle Buyback Box

Used exclusively in transmute operations. The `OracleBuyBackBox` acts as an additional on-chain participant that receives a portion of the oracle fee, ensuring oracle incentives are correctly distributed at the ErgoScript level.

### Fee Model

The contract enforces a three-way fee split validated in the ErgoScript context:
- **Dev fee** — to a hardcoded developer address.
- **UI fee** — to a configurable UI provider address (passed at transaction build time).
- **Oracle fee** — to the Oracle Buyback Box.

All fee amounts are computed off-chain by the SDK and then validated by the contract's spending conditions — a canonical **Constant Segregation** pattern where values are computed off-chain and proven correct on-chain.

---

## Integration Guide

### Installation

```bash
npm install gluon-gold-sdk
```

### Instantiation

```typescript
import { Gluon } from 'gluon-gold-sdk';

const gluon = new Gluon(); // connects to default node/explorer endpoints
```

All numeric values (ERG amounts, token quantities, prices) are expressed in **base units without decimals** (nanoERG for ERG; raw integer amounts for tokens). This mirrors Ergo's on-chain representation inside Box values and Registers.

### Fetching Protocol State

```typescript
const gluonBox    = await gluon.getGluonBox();       // Singleton State NFT box
const oracleBox   = await gluon.getGoldOracleBox();  // Gold price oracle box
const buyBackBox  = await gluon.getOracleBuyBackBoxJs();
const height      = await nodeService.getHeight();   // Current network height
```

These calls should be refreshed before each transaction construction to ensure you are building against the latest eUTXO state, preventing double-spend conflicts.

### Building Transactions

#### Fission (ERG → Neutrons + Protons)

```typescript
const ergAmount