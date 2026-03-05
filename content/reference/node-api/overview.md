---
title: ergoplatform/ergo — Overview
description: Ergo node — REST API endpoints (Swagger), config options, mining parameters
tags: [ergoplatform, ergo, core-protocol, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergoplatform/ergo"
project: ergoplatform-ergo
group: core-protocol
priority: high
languages: [scala]
contract_count: 0
pattern_match_count: 0
---
# Ergo Node — Developer Overview

---

## Overview

The **ergoplatform/ergo** repository is the reference implementation of the Ergo Protocol — a Proof-of-Work blockchain built on the extended UTXO (eUTXO) model. Written primarily in Scala and built on the **Scorex** framework, it serves as the canonical node client responsible for block validation, transaction processing, peer-to-peer networking, wallet management, and exposing the full REST API surface via a Swagger-documented interface. As the most complete implementation of the Ergo protocol, it defines the ground truth for consensus rules, **Autolykos2** mining, the **Emission schedule**, **Difficulty adjustment**, and the **Storage rent** (demurrage) fee model.

Beyond serving as an infrastructure node, the ergo reference client encodes the entire economic and scripting model of the platform: **ErgoScript** contract evaluation via the **sigmastate-interpreter**, **AVL tree**-backed authenticated state, **NiPoPoW**-based light client bootstrapping, and a modular sync architecture that supports full, digest (stateless), and UTXO-snapshot modes. Every on-chain construct — **Boxes**, **Registers**, **Native tokens**, **Data inputs**, **ErgoTree** serialization — is implemented and enforced here, making this project the definitive integration target for any off-chain tooling in the Ergo ecosystem.

The project follows a modular structure exposing three independently usable sub-modules: `avldb` (authenticated AVL+ tree persistence), `ergo-core` (SPV-level primitives including P2P messages, PoW, and NiPoPoW), and `ergo-wallet` (JVM transaction signing and verification). This design allows downstream developers to consume only the protocol components relevant to their use case without pulling in the full node runtime.

---

## Architecture

### Key Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Ergo Node Process                        │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │  P2P Network │   │  REST API    │   │   Wallet / Keys    │  │
│  │  (Scorex)    │   │  (Swagger)   │   │   (ergo-wallet)    │  │
│  └──────┬───────┘   └──────┬───────┘   └────────┬───────────┘  │
│         │                  │                    │               │
│  ┌──────▼──────────────────▼────────────────────▼───────────┐  │
│  │                    Node Core / Actors                     │  │
│  │   (NodeViewHolder, Mempool, History, ErgoState)           │  │
│  └──────┬─────────────────────────────────────┬─────────────┘  │
│         │                                     │                 │
│  ┌──────▼───────────┐              ┌──────────▼──────────────┐  │
│  │  ErgoHistory     │              │  ErgoState              │  │
│  │  (Block headers, │              │  (UTXOState / Digest    │  │
│  │  NiPoPoW proofs, │              │   StateType, AVL tree,  │  │
│  │  PoW validation) │              │   Storage rent checks)  │  │
│  └──────┬───────────┘              └──────────┬──────────────┘  │
│         │                                     │                 │
│  ┌──────▼───────────┐              ┌──────────▼──────────────┐  │
│  │  ergo-core       │              │  avldb                  │  │
│  │  (SPV, PoW,      │              │  (Authenticated AVL+    │  │
│  │  NiPoPoW,        │              │   tree, persistence,    │  │
│  │  P2P messages)   │              │   proofs)               │  │
│  └──────────────────┘              └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Role |
|---|---|
| **Scorex Framework** | Provides the actor-based P2P networking layer, node view synchronization, and modular blockchain abstractions that the Ergo node is built upon |
| **ErgoHistory** | Maintains the chain of block headers, validates **Autolykos2** Proof-of-Work, manages **Difficulty adjustment**, stores and verifies **NiPoPoW** proofs for light client bootstrapping |
| **ErgoState (UTXOState / DigestState)** | The full UTXO set or its authenticated digest; backed by `avldb` AVL+ tree; enforces **Storage rent** collection, validates **ErgoTree** scripts via sigmastate-interpreter, and applies/rolls back **Transactions** |
| **ErgoMempool** | Unconfirmed transaction pool; enforces **Minimum transaction fee** and **Minimum box value** constraints before admitting transactions |
| **ergo-wallet** | JVM-native signing and verification; manages keys, constructs unsigned transactions, handles **Token ID rule** compliance and **Box** selection |
| **REST API (Swagger)** | Full HTTP interface for node interaction; exposes endpoints for transaction submission, UTXO queries, block data, mining, wallet operations, and peer management |
| **avldb** | Standalone authenticated AVL+ tree implementation with LevelDB-backed persistence; generates inclusion/exclusion proofs used by stateless (digest) nodes |
| **ergo-core** | Minimal dependency module containing SPV client primitives, block section data structures, PoW verification, and **NiPoPoW** proof construction/verification |
| **Mining Module** | Exposes `/mining/candidateBlock` and solution submission endpoints; integrates with external **Autolykos2** miners via the REST API |

### Data Flow

```
External Miner / Off-chain Bot / SDK
         │  REST API (Swagger)
         ▼
  ErgoMempool ──► Transaction validation
         │        (ErgoScript / ErgoTree evaluation,
         │         Sigma protocols, Register checks,
         │         Minimum box value, Storage rent)
         ▼
  NodeViewHolder (actor)
         │
         ├──► ErgoHistory (header chain, NiPoPoW, Difficulty)
         │
         └──► ErgoState
               ├── UTXOState: AVL tree mutation + proof generation
               └── DigestState: proof verification only (stateless mode)
```

**Block application path:**
1. New block received via P2P (Scorex) or mined locally
2. `ErgoHistory` validates header: **Autolykos2** PoW, **Difficulty adjustment**, timestamp window (±20 min)
3. `ErgoState` validates block transactions: **ErgoTree** evaluation per **Box**, **Data input** resolution, **Context extension** handling, **Sigma protocols** / **Ring signatures** verification, **Native token** conservation, **Storage rent** deductions
4. AVL tree (`avldb`) is updated; new authenticated state root committed to block header
5. REST API reflects updated chain state; wallet UTXOs refreshed

---

## Smart Contracts

The Ergo node itself does not deploy application-level ErgoScript contracts — it *implements and enforces* the contract execution environment. However, several protocol-level contracts are embedded directly in the node codebase:

### Protocol-Embedded Contracts

| Contract | Description |
|---|---|
| **Emission Contract** | Governs the **Emission schedule** — the rate at which new ERG is released to miners and the Ergo Foundation treasury. Encoded as a **Singleton / State NFT**-style box whose **ErgoTree** enforces spending rules tied to block height |
| **Storage Rent Contract** | Enforces demurrage: any **Box** that has not been spent within 1,260 blocks (≈4 years