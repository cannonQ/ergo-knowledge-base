---
title: BetterMoneyLabs/chaincash — Overview
description: ChainCash — note-based monetary system, layer-2 redemption, reserve contracts, off-chain basis protocol
tags: [bettermoneylabs, chaincash, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
project: bettermoneylabs-chaincash
group: defi
priority: high
languages: [ergoscript, scala]
contract_count: 8
pattern_match_count: 0
---
# ChainCash Developer Overview

## Overview

ChainCash is a note-based monetary protocol built on the Ergo blockchain that enables elastic, peer-to-peer money creation through a combination of on-chain collateral and off-chain trust relationships. Each note represents a unit of account (denominated in milligrams of gold) and accumulates a collective backing as it circulates: every agent who spends a note attaches a cryptographic signature to its history, binding their reserve to potential redemption liability. This design allows notes to be issued without any initial collateral — accepted purely on trust — while still enabling any holder to redeem against any prior signer's reserve at any time, giving the system both elasticity and a transparent audit trail.

Within the Ergo ecosystem, ChainCash occupies the intersection of Layer 2 payment channels and DeFi reserve management. It exploits Ergo's eUTXO model and register system to encode rich multi-stage state machines directly in Boxes, while also supporting a fully off-chain transfer mode in which notes change hands without touching Layer 1 at all, with only redemption events requiring on-chain settlement. This architecture positions ChainCash as a scalable Layer 2 monetary layer sitting above the base Ergo chain, complementing existing stablecoin protocols like SigmaUSD by offering reserve-backed note issuance with user-defined collateral types including ERG, native tokens, or tokenized real-world assets.

The protocol is actively developed across two repositories: this reference implementation (contracts, whitepaper, Scala prototyping) and a production Rust server (`chaincash-rs`) that acts as a self-sovereign bank with client-side note validation. The Scala codebase serves as the canonical source for ErgoScript contracts, off-chain transaction builders, and Kiosk-based integration tests, while the Rust server exposes an HTTP API for real deployments.

---

## Architecture

ChainCash is organized around four interacting layers: the on-chain contract layer (Boxes and ErgoScript), the off-chain data layer (AVL tree state, signature chains), the Layer 2 transfer layer (off-chain note passing), and the server/bot layer (transaction construction and submission).

```
┌─────────────────────────────────────────────────────────────────┐
│                        Off-Chain Tier                           │
│  ChainCash Server (chaincash-rs)  ◄──► Off-chain Bot (Scala)   │
│   - HTTP API                            - Chain tracker         │
│   - Note validation                     - TX builders           │
│   - AVL tree management                 - Persistence           │
└────────────────────┬────────────────────────────────────────────┘
                     │ constructs / submits transactions
┌────────────────────▼────────────────────────────────────────────┐
│                     Layer 1 (Ergo Mainnet)                      │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  Note Box    │───►│ Reserve Box  │───►│  Receipt Box     │  │
│  │  (note.es)   │    │ (reserve.es) │    │  (receipt.es)    │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│          │                  │                                   │
│          │ data input       │ data input                        │
│  ┌───────▼──────┐  ┌────────▼───────┐                          │
│  │ Reserve Box  │  │  Oracle Box    │                          │
│  │ (holder ref) │  │ (gold price)   │                          │
│  └──────────────┘  └────────────────┘                          │
│                                                                 │
│  ┌──────────────────────┐   ┌────────────────────────────────┐ │
│  │  Redemption Box      │   │  Redproducer Box               │ │
│  │  (redemption.es)     │   │  (redproducer.es)              │ │
│  └──────────────────────┘   └────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────────┐                                       │
│  │  Basis Reserve Box   │                                       │
│  │  (basis.es)          │                                       │
│  └──────────────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow for a Layer 2 note transfer:**

1. Alice creates a note record `(zeroTreeHash, aliceReserveId, value, bobReserveId)` and signs it off-chain, sending the record and signature to Bob directly.
2. Bob validates Alice's Schnorr signature and the AVL+ tree root, then constructs his own signed transfer record with an updated tree root (containing Alice's leaf at key `0`).
3. Each successive holder appends their signature as a leaf in an AVL+ tree keyed by a synthetic counter, accumulating the chain of custody entirely off-chain.
4. When redemption is needed, the current holder submits the full signature tree to the on-chain redemption contract. The contract verifies inclusion proofs, identifies the earliest reserve with sufficient coverage, and deducts from that reserve Box, producing a Receipt Box as proof.

**Data flow for on-chain note spending (Layer 1 mode):**

1. Spender provides a Note Box as input, a Reserve Box as a Data input (non-consuming), and Context extension variables containing the Schnorr signature `(a, z)` and an AVL tree insertion proof.
2. The note contract verifies the signature, inserts the leaf `(position || reserveId) → (a || z)` into R4's AVL+ tree, and produces an output Note Box with incremented R6, updated R4 digest, and the new holder's public key in R5.
3. For redemption, the note contract verifies the reserve contract's ErgoTree hash against `$reserveContractHash`, produces a Receipt Box at the corresponding output index, and the reserve contract independently deducts ERG at the oracle price with a 2% fee.

---

## Smart Contracts

All contracts are written in ErgoScript and live under `contracts/`. There are two parallel contract families: `contracts/onchain/` for the primary Layer 1 implementation and `contracts/layer2-old/` for an earlier Layer 2 prototype. The `contracts/offchain/` directory contains the Basis reserve contract for off-chain credit systems.

### `contracts/onchain/note.es` — Note Contract

The core currency primitive. A Note Box holds:
- **R4** (`AvlTree`): AVL+ tree of spending history; keys are `positionBytes || reserveId`, values are Schnorr signature components `a_encoded || z_encoded`.
- **R5** (`GroupElement`): Current holder's public key.
- **R6** (`Long`): Sequential position counter; incremented on every spend to prevent signature replay.
- **Token #0**: Native token whose amount equals the note value in milligrams of gold; the Token ID Rule enforces accounting invariants across all note Boxes in a chain.

**Spending path** (`action >= 0`): Verifies a Schnorr proof-of-knowledge over `position || noteValue || tokenId`, reads the holder's public key from a Reserve Box supplied as a Data input (non-consuming), inserts the signature leaf into R4's AVL tree via a provided Context extension proof, and validates that output Note Boxes have incremented R6, preserved ErgoTree, and defined R5. A `proveDlog(holder)` guard prevents mempool-level manipulation.

**Redemption path** (`action < 0`): Verifies the consuming reserve Box's ErgoTree against the hardcoded `$reserveContractHash` (using Constant segregation to skip the version byte via `slice(1, size)`), checks that the output at the same index satisfies `$receiptContractHash`, and requires `proveDlog(holder)`.

### `contracts/onchain/reserve.es` — Reserve Contract