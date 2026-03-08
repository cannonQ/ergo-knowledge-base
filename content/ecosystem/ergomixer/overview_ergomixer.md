---
title: ergoMixer/ergoMixBack — Overview
description: ErgoMixer — non-interactive mixing (ZeroJoin), stealth addresses, covert address generation
tags: [ergomixer, ergomixback, infrastructure, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ergoMixer/ergoMixBack"
project: ergomixer-ergomixback
group: infrastructure
priority: high
languages: [scala]
contract_count: 0
pattern_match_count: 6
---
# ErgoMixer / ergoMixBack — Developer Overview

---

## Overview

ErgoMixer is a non-interactive, serverless mixing application built on the Ergo platform, implementing the **ZeroJoin** protocol — a cryptographic construction that combines Zerocoin-style proofs with CoinJoin to achieve non-custodial, non-interactive privacy for ERG and Native tokens. Unlike traditional CoinJoin mixers that require coordination between participants, ZeroJoin relies on **Sigma protocols** — specifically composable zero-knowledge proofs available natively in ErgoScript — so each mixing step can be executed independently by a single participant without any peer-to-peer communication round. This makes the system fully asynchronous and censorship-resistant within Ergo's eUTXO model.

Within the Ergo ecosystem, ErgoMixer occupies a foundational privacy infrastructure role. It operates as an **off-chain bot** paired with on-chain ErgoScript contracts: the backend (this repository, Scala/Play Framework) monitors the blockchain, constructs and submits Transactions, manages local state in a SQLite database, and drives the multi-stage mixing state machine. The frontend (`ergoMixFront`, a React submodule) exposes a local web UI. The application requires no API key and connects to any standard Ergo full node plus an explorer endpoint, making it deployable by any user without node operator trust.

Beyond base mixing, ErgoMixer implements two additional privacy primitives: **stealth addresses** — one-time recipient addresses derived from a published public key using an ECDH-like construction over the Ergo group, ensuring on-chain unlinkability between sender and recipient — and **covert address** generation, which allows a user to repeatedly receive funds into addresses that, when mixed, cannot be correlated. The system also integrates with **SigmaUSD** (the Ergo algorithmic stablecoin), enabling users to convert mixed ERG directly into SigmaUSD or SigmaRSV without breaking the privacy chain.

---

## Architecture

ErgoMixer is structured as a Scala Play Framework application with a layered architecture separating concerns across persistence, domain logic, off-chain transaction construction, and HTTP API.

### Core Layers

```
┌──────────────────────────────────────────────┐
│              Play HTTP Controllers            │
│  (MixController, StealthController, etc.)    │
├──────────────────────────────────────────────┤
│             Application Services             │
│  (MixingService, CovertMixing, Withdrawal)   │
├──────────────────────────────────────────────┤
│         Off-chain Bot / State Machine        │
│  (MixingRunner, ErgoMixerJobs, Schedulers)   │
├──────────────────────────────────────────────┤
│           Transaction Constructors           │
│  (ErgoMix, SpendFullMix, HalfMix builders)   │
├──────────────────────────────────────────────┤
│              DAO / Persistence               │
│  (AllMixDAO, MixTransactionsDAO,             │
│   CovertAddressesDAO, CovertsDAO, Prune)     │
├──────────────────────────────────────────────┤
│           Node / Explorer Clients            │
│  (ErgoNodeClient, ErgoExplorerClient)        │
└──────────────────────────────────────────────┘
```

### Key Components

**State Machine / Off-chain Bot (`MixingRunner`, `ErgoMixerJobs`)**  
The heart of the backend is a scheduler-driven off-chain bot that continuously scans on-chain state and advances each mix through a defined progression. Each mix occupies one of several discrete states:

- `Requested` → `HalfMix` → `FullMix` → `WithdrawRequested` → `Withdrawn`

Each state transition corresponds to submitting a new Transaction to the network. The bot polls confirmed Boxes via the node/explorer, matches them against locally tracked mix sessions, and constructs the next-step Transaction accordingly. This is a textbook **multi-stage contract** interaction pattern: the ErgoScript contracts enforce valid transitions on-chain, while the off-chain bot is responsible for liveness (actually submitting the next step).

**DAO Layer (`dao/mixing/`)**  
Persistence is handled through a collection of DAO objects backed by a local SQLite database:
- `AllMixDAO` — aggregate view across all active mix records, used by the scheduler to find actionable items.
- `MixTransactionsDAO` — stores Transaction IDs and Box IDs for every on-chain mix step, enabling resumability after restart.
- `CovertAddressesDAO` / `CovertsDAO` — manage covert address sets: a covert address is a reusable deposit address whose outputs are funnelled into the mix pipeline automatically.
- `Prune` — handles cleanup of spent/expired mix state to bound database growth.

**Transaction Constructors**  
The Scala code constructs unsigned Transactions by:
1. Fetching current unspent Boxes (input selection) via the node's UTXO API.
2. Populating output Box candidates with the correct ErgoTree (contract), value (respecting Minimum box value), Registers, and Native tokens.
3. Signing via the embedded wallet (secrets stored in local DB) using the Ergo AppKit / Sigma-Rust bindings.
4. Submitting the signed Transaction to the connected node.

**Stealth Controller (`controllers/StealthController.scala`)**  
Handles the stealth address workflow: deriving one-time payment addresses from a published stealth public key, and scanning the blockchain for Boxes sent to derived addresses. The `StealthContract` ErgoTree encodes the spending condition for stealth outputs.

**Node / Explorer Clients**  
The application talks to:
- An Ergo full node (REST API, no `api_key` required for read operations) — for UTxO queries, Transaction submission, and current blockchain height.
- An Ergo Explorer instance — for historical Box lookups and confirmation checks.

### Data Flow: One Mixing Round

```
User deposit → CovertAddress / DirectDeposit Box
        ↓ (off-chain bot detects confirmed Box)
HalfMixTransaction: consumes deposit Box, creates HalfMix Box
        ↓ (bot finds matching HalfMix Box on-chain)
FullMixTransaction: consumes two HalfMix Boxes, creates two FullMix Boxes
        ↓ (withdrawal request set)
WithdrawTransaction: consumes FullMix Box, sends to destination address
```

Each Transaction is atomic from the eUTXO perspective — it either confirms entirely or fails, with no partial state.

---

## Smart Contracts

ErgoMixer's on-chain logic is implemented as ErgoScript contracts governing the spending conditions for each mixing Box type. These contracts leverage Sigma protocols — specifically **Ring signatures** (provable as `anyOf`/`OR`-compositions of discrete-log proofs) — to guarantee that a FullMix output can only be spent by one of the two participants who created it, without revealing which one.

### HalfMix Contract

Guards a Box representing an "open" mix offer. The spending condition allows either:
- The original depositor to cancel (reclaim) the Box, proving knowledge of the deposit secret.
- A second participant to join the mix, consuming this Box and a deposit of their own, producing a valid FullMix pair.

The contract encodes the depositor's public key (as a group element in a Register) and verifies a sigma-protocol proof. No interactive round-trip is required; the joiner constructs a valid Transaction locally.

### FullMix Contract

Guards a completed mix output. The spending condition is a **Ring signature** over the two participants' public keys:

```ergoscript
// Pseudocode - actual contract uses Sigma protocol composition
(proveDlog(pk_alice) || proveDlog(pk_bob))
```

This is an `OR`-composition of two `proveDlog` statements — a canonical Sigma protocol Ring signature. An observer cannot determine which participant is spending the output. The ErgoScript context provides group element commitments stored in Box Registers, enabling the verifier to check the proof without learning the spender's identity.

### Stealth Contract (`StealthContract`)

Encodes the spending condition for a stealth address output. The recipient derives a one