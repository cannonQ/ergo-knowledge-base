---
title: LiliumErgo/scala-api — Overview
description: Lilium — NFT collection minting suite, collection issuance, sale LP, singleton issuers, AVL tree state
tags: [liliumergo, scala-api, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
project: liliumergo-scala-api
group: defi
priority: medium
languages: [ergoscript, scala]
contract_count: 11
pattern_match_count: 8
---
# LiliumErgo/scala-api — Developer Overview

---

## Overview

The **Lilium Scala API** is the off-chain backbone of the Lilium NFT collection minting suite on Ergo. It accepts structured collection metadata from a frontend, compiles the full suite of ErgoScript contracts parameterized for that collection, builds and inserts AVL tree state, and persists the resulting data to a database — all in preparation for on-chain deployment. The API acts as the primary orchestration layer between user intent and the eUTXO state machine that governs NFT issuance, sale liquidity, and access control.

Within the Ergo ecosystem, Lilium occupies the role of a general-purpose NFT launchpad. It handles the full lifecycle of a collection: from minting the Collection Token (which uniquely identifies and authenticates the collection), to managing a Sale LP box that distributes proceeds to artists and the protocol, to issuing whitelist and premint tokens for tiered access. The system is designed around Ergo's eUTXO model — each phase of the collection lifecycle is encoded as a distinct Box type with explicit guards, and state transitions are atomic transactions that satisfy invariants enforced entirely on-chain.

A distinguishing feature of the Lilium architecture is its use of an AVL tree to store per-NFT metadata (traits, levels, stats, royalties, media hashes) off-chain in a database while committing the authenticated root digest on-chain inside the State Box. This allows the system to scale to arbitrarily large collections without bloating the UTXO set, while the ErgoScript contracts cryptographically verify any lookup against the committed root. The Scala API serves two primary HTTP endpoints: one that compiles contracts and builds AVL state for a new collection (`/submitCollection`), and one that encodes collection issuer metadata for on-chain registration (`/generateCollectionIssuerHex`).

---

## Architecture

### High-Level Component Map

```
Frontend / Client
       │
       ▼
┌─────────────────────┐
│   Scala API Server  │  (Play Framework, port 9000)
│  /submitCollection  │
│  /generateCollection│
│    IssuerHex        │
└──────────┬──────────┘
           │
    ┌──────┴──────────────────────────────────┐
    │                                          │
    ▼                                          ▼
┌──────────────────┐              ┌────────────────────────┐
│  ContractCompile │              │  AVL Tree Builder      │
│  (compile each   │              │  (metadata → AVL tree  │
│  ErgoScript with │              │   keyed by blake2b256  │
│  collection-     │              │   hashed index)        │
│  specific params)│              └────────────┬───────────┘
└──────────┬───────┘                           │
           │                                   ▼
           ▼                       ┌───────────────────────┐
┌──────────────────────┐           │  Database             │
│  LiliumContracts     │           │  (AVL tree nodes,     │
│  (ErgoTree registry: │           │   digests, proofs)    │
│   StateContract,     │           └───────────────────────┘
│   SaleLP,            │
│   IssuerContract,    │
│   CollectionIssuance,│
│   SingletonIssuer,   │
│   SingletonIssuance, │
│   WhitelistIssuer,   │
│   PreMintIssuer,     │
│   CollectionIssuer)  │
└──────────────────────┘
```

### Key Components and Data Flow

**`app/configs/conf.scala`** — Reads `serviceOwner.json` to hydrate compile-time constants used across all contracts: operator public key (`_txOperatorPK`), Lilium fee parameters (`_liliumFeeNum`, `_liliumFeeDenom`, `_liliumSigmaProp`), miner fee (`_minerFee`), minimum box value, and proxy contract bytes. These constants are injected into ErgoScript at compile time via **constant segregation**, meaning each collection deployment produces a distinct ErgoTree.

**`app/contracts/LiliumContracts.scala`** — Central registry that holds the compiled ErgoTree for every contract in the suite. It exposes typed handles (`CollectionIssuanceErgoTree`, `IssuerContractErgoTree`, `SaleLPErgoTree`, etc.) consumed by the output-building layer.

**`app/utils/ContractCompile.scala`** — Compiles raw `.es` ErgoScript source files into ErgoTree bytecode using the Ergo Appkit compiler, substituting collection-specific parameters (token IDs, price, supply cap, sale window, feature flags, royalty splits) as compile-time constants. Each contract compilation is deterministic: the same inputs always produce the same ErgoTree bytes, which is a hard requirement since downstream contracts embed upstream contract bytes as constants.

**`app/initialize/InitializeHelper.scala`** — Coordinates the full initialization sequence: compile contracts in dependency order, mint singleton and collection tokens conceptually, build AVL tree from metadata, persist to DB, and prepare the initial Box set for on-chain submission.

**`app/utils/OutBoxes.scala`** — Constructs `OutBox` instances for each box type in the state machine. Handles token attachment (`mintToken` pattern), register assignment (Registers R4–R9), and ERG value calculation respecting minimum box value and storage rent requirements.

**`app/utils/createCollection.scala`** — Top-level orchestrator called by `/submitCollection`. Invokes `ContractCompile`, `LiliumContracts`, `InitializeHelper`, and `OutBoxes` in sequence to produce a complete, ready-to-submit transaction set and associated AVL state.

**`app/configs/metadata.scala`** — Serializes NFT metadata (traits, levels, stats, royalty, explicit flag) into the byte format expected by the AVL tree and the `IssuerContract` on-chain verifier. Uses the length-prefixed concatenation scheme that `StateContract.es` expects for Blake2b256 hash reconstruction.

**`app/types/ContractErgoTree.scala`** — Typed wrapper around compiled ErgoTrees, used to pass `IssuerContract` ErgoTree bytes as context extension variables into transactions where downstream contracts must verify `propositionBytes` equality.

### Data Flow: `/submitCollection`

```
1. Client POST (collection JSON)
       │
       ▼
2. conf.scala        → load serviceOwner constants
3. metadata.scala    → serialize each NFT's metadata to bytes
4. AVL tree builder  → insert (blake2b256(index_bytes) → metadata_bytes)
                        for each NFT; capture root digest
5. ContractCompile   → compile all contracts with collection params
6. LiliumContracts   → register ErgoTrees
7. InitializeHelper  → build initial box set:
      - SingletonIssuer box  (mints Singleton NFT)
      - SingletonIssuance box (routes Singleton to State + SaleLP)
      - CollectionIssuer box  (mints Collection tokens)
      - CollectionIssuance box (routes Collection tokens to State)
      - State Box             (AVL root in R5, index=1 in R6, etc.)
      - SaleLP box            (if usePool=true)
      - WhitelistIssuer boxes (one per whitelisted address)
      - PreMintIssuer boxes   (one per premint address)
8. Database          → persist AVL tree nodes + root digest
9. Client response   → encoded contract hex + initialization tx hex
```

---

## Smart Contracts

All contracts reside in `conf/contracts/Lilium/BoxGuardScripts/`. They form a **multi-stage contract** system — a directed graph of Box types where spending one Box produces the next in the sequence.

### `SingletonIssuer.es`

**Role:** Gate contract for minting the Singleton / State NFT.  
**Mechanism:** Enforces that a new native token with ID = `SELF.id` (Token ID rule) is minted into the immediately downstream `SingletonIssuance` box. Token quantity is 1