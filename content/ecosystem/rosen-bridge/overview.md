---
title: rosen-bridge/scanner — Overview
description: Rosen abstract scanner — address/token extractors, observation extraction pattern
tags: [rosen-bridge, scanner, infrastructure, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/rosen-bridge/scanner"
project: rosen-bridge-scanner
group: infrastructure
priority: high
languages: [typescript]
contract_count: 0
pattern_match_count: 2
---
# Rosen Bridge Scanner — Developer Overview

---

## Overview

The **rosen-bridge/scanner** project is a TypeScript monorepo that provides the off-chain scanning and data-extraction infrastructure for the Rosen Bridge cross-chain protocol. Its primary responsibility is to continuously monitor blockchain state — most critically the Ergo eUTXO ledger — and extract structured, application-level meaning from raw Box data. Rather than requiring every downstream consumer to re-implement chain-traversal logic, the scanner exposes a composable toolkit of abstract base classes and concrete extractors that can be composed, extended, or replaced independently.

Within the Ergo ecosystem, the scanner sits at the boundary between raw node data and the higher-level business logic of the Rosen Bridge watcher network. Watchers are off-chain bots that must observe user payment events on source chains and attest to them on Ergo. The scanner feeds these bots a clean, database-backed stream of relevant observations and protocol-specific Box states, insulating them from node RPC details, block reorganisations, and the low-level structure of ErgoScript ErgoTree outputs, Registers, and Native token payloads.

Because Ergo's eUTXO model encodes application state directly inside Boxes — using Registers (R4–R9), Native tokens identified by Token ID rule, and Singleton/State NFT patterns — reliable extraction requires understanding ErgoTree structure and contextual Box semantics. The scanner packages encode this understanding once, centrally, so that wallet connectors, watcher bots, and data-indexing services can consume typed, validated events rather than raw serialised byte arrays.

---

## Architecture

### Monorepo Package Map

```
rosen-bridge/scanner
├── packages/
│   ├── scanner/                  # abstract-scanner — core scanning loop
│   ├── abstract-extractor/       # AbstractExtractor base class
│   ├── address-extractor/        # UTXO Box extractor by address or Token ID
│   ├── observation-extractor/    # Cross-chain payment observation extraction
│   └── watcher-data-extractor/   # Rosen-protocol Box extraction on Ergo
```

### Core Components

#### `abstract-scanner` (scanner package)

The scanning loop abstraction. Responsible for:

- Advancing a block-height cursor against a blockchain node (Ergo node API or equivalent).
- Detecting and rolling back on chain forks/reorganisations (critical in eUTXO where a Box spent in an orphaned block reappears as unspent).
- Dispatching each confirmed Block — as an ordered list of Transactions, each containing input Box IDs and output Boxes — to a registered set of `AbstractExtractor` instances.
- Persisting scan progress so restarts resume cleanly without full re-scan.

#### `AbstractExtractor` (abstract-extractor package)

The base class all concrete extractors implement. Pattern-matched files:

- `packages/abstract-extractor/lib/abstractExtractor.ts`
- `packages/abstract-extractor/lib/ergo/extractors/abstractErgoExtractor.ts`

The Ergo-specific subclass (`abstractErgoExtractor`) adds awareness of:

- **Box structure**: BoxId, ErgoTree, value in nanoERG, creation height, Registers (typed `Coll[Byte]`, `Long`, `GroupElement`, `SigmaProp`, etc.), and attached Native tokens.
- **Singleton / State NFT** tracking to follow a State machine across Transactions.
- **Storage rent** lifecycle — Boxes approaching the four-year rent deadline may be re-created; extractors must handle re-registration of state.

Concrete extractors override `processBlock(block)` / `rollbackBlock(block)` hooks and write derived records to a TypeORM-managed database.

#### `address-extractor`

A general-purpose eUTXO Box extractor parameterised by:

- An **Ergo address** (resolved to an ErgoTree for exact matching).
- Or a **Token ID** (Native token identifier under the Token ID rule), capturing any Box that holds at least one unit of the specified token regardless of its ErgoTree guard script.

Suitable for indexing any contract address — including multi-stage contracts and proxy contracts — without bespoke parsing logic.

#### `observation-extractor`

Extracts cross-chain **payment observations**: structured records that a Rosen watcher will later use to construct an Ergo Transaction attesting that a user deposited funds on a source chain (Ergo, Cardano, Bitcoin, etc.). Each observation captures source/destination chain identifiers, asset Token ID mapping, amount, target address, and the originating Box or transaction reference. This is the primary data source for the off-chain bot logic responsible for bridge event attestation.

#### `watcher-data-extractor`

Ergo-specific extractor for Rosen protocol Boxes:

- **Commitment Boxes** — watcher commitments locked under a contract parameterised by a Singleton/State NFT identifying the watcher's permit.
- **Event Trigger Boxes** — aggregated multi-watcher commitment outputs.
- **Permit Boxes** — watcher RSN (Rosen token) permit state, tracked as a State machine across permit creation, use, and refund Transactions.
- **Revenue / reward Boxes** — GORT and bridge-fee distribution outputs.

### Data Flow

```
Ergo Node (REST API)
        │
        ▼
abstract-scanner
  ├─ iterates Blocks (height cursor)
  ├─ handles fork rollback
  └─ dispatches Block to each registered extractor
              │
    ┌─────────┼──────────────────────┐
    ▼         ▼                      ▼
address-   observation-        watcher-data-
extractor  extractor           extractor
    │         │                      │
    └─────────┴──────────────────────┘
                      │
               TypeORM / SQLite
               (or PostgreSQL)
                      │
              Watcher / Consumer
              Off-chain Bot Logic
```

---

## Smart Contracts

The scanner itself contains **no ErgoScript contracts**. It is a pure off-chain observer. However, its extractors are tightly coupled to the on-chain contract interfaces of the Rosen Bridge:

| Contract | Scanner Relevance |
|---|---|
| **Watcher Permit contract** | `watcher-data-extractor` tracks Permit Boxes by Singleton/State NFT Token ID; Registers R4–R6 encode permit quota and watcher identity |
| **Commitment contract** | Extractor identifies Commitment Boxes by ErgoTree guard and extracts observation hash from Registers |
| **Event Trigger contract** | Tracks aggregated commitment Boxes; NFT-keyed State machine transition detection |
| **Bridge fee/reward contracts** | Revenue Box extraction for GORT distribution accounting |

Register parsing follows Ergo's typed `ConstantNode` serialisation — the extractors decode `Coll[Byte]` Register values into typed domain objects, abstracting the ErgoScript constant segregation model from consumers.

---

## Integration Guide

### Installation

```bash
# Install individual packages from the monorepo (published to npm)
npm install @rosen-bridge/scanner
npm install @rosen-bridge/address-extractor
npm install @rosen-bridge/observation-extractor
npm install @rosen-bridge/watcher-data-extractor
```

### Registering Extractors with the Scanner

```typescript
import { ErgoScanner } from '@rosen-bridge/scanner';
import { AddressExtractor } from '@rosen-bridge/address-extractor';
import { ObservationExtractor } from '@rosen-bridge/observation-extractor';

// 1. Configure the scanner (node URL, initial height, dataSource)
const scanner = new ErgoScanner(
  { nodeUrl: 'http://localhost:9053', initialHeight: 950000 },
  dataSource   // TypeORM DataSource
);

// 2. Instantiate extractors with their TypeORM repositories
const addrExtractor = new AddressExtractor(
  '9f...<ergo-address>',   // or Token ID
  dataSource,
  networkType
);

const obsExtractor = new ObservationExtractor(
  bridgeConfig,
  dataSource
);

// 3. Register extractors — the scanner calls processBlock / rollbackBlock
scanner.registerExt