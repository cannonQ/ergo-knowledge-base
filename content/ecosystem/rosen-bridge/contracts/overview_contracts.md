---
title: rosen-bridge/contract — Overview
description: Rosen Bridge contracts — guard/watcher architecture, multi-sig consensus, RWT staking, fraud detection
tags: [rosen-bridge, contract, infrastructure, ergoscript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
project: rosen-bridge-contract
group: infrastructure
priority: high
languages: [ergoscript]
contract_count: 10
pattern_match_count: 0
---
# Rosen Bridge Contract — Developer Overview

## Overview

The **rosen-bridge/contract** project contains the complete ErgoScript on-chain logic for the Rosen Bridge, an Ergo-centric cross-chain bridge that connects the Ergo blockchain to external networks (Ethereum, Cardano, Bitcoin, and others). The bridge is "Ergo-centric" in the sense that all consensus, fraud detection, staking, and governance procedures execute as eUTXO contracts on Ergo, while interactions with foreign chains use simpler multi-signature wallets whose authorization ultimately references the Ergo-side state. Every major bridge lifecycle event — watcher registration, commitment submission, event triggering, fraud slashing, and guard-set rotation — is enforced by one of the contracts in this repository.

The architecture separates two roles with fundamentally different trust levels. **Guards** are a small, trusted quorum who hold shared cryptographic keys and execute final payment transactions; their consensus is represented on-chain by the **Guard NFT**, a Singleton / State NFT that acts as a linearizer in the eUTXO model. **Watchers** are permissionless volunteers who observe source chains, post cryptographic commitments, and stake **X-RWT** (chain-specific Rosen Watcher Tokens) as collateral. The contracts enforce that watchers can only act within their staked capacity and that erroneous or fraudulent behavior results in automatic collateral slashing, while correct behavior earns reward redistribution. No special off-chain permissions are needed to become a watcher beyond holding sufficient RSN tokens.

The contract repository is written entirely in ErgoScript, compiled and addressed via a Scala/SBT toolchain that produces a runnable JAR. The JAR exposes CLI commands to generate canonical contract addresses and token map files for each supported network type and version, making it the authoritative source of truth for all deployed contract addresses within the Rosen ecosystem.

---

## Architecture

### Component Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Ergo Blockchain                                │
│                                                                         │
│  ┌──────────────┐    data input    ┌──────────────────┐                │
│  │  GuardSign   │◄─────────────────│   Lock (Wallet)  │                │
│  │  (State NFT) │                  │  (m-of-n spend)  │                │
│  └──────┬───────┘                  └──────────────────┘                │
│         │ data input                                                    │
│         ▼                                                               │
│  ┌──────────────┐    data input    ┌──────────────────┐                │
│  │  RepoConfig  │◄─────────────────│    RwtRepo       │                │
│  │ (Config NFT) │                  │ (Repo State NFT) │                │
│  └──────────────┘                  └────────┬─────────┘                │
│                                             │ issues                   │
│                                    ┌────────▼─────────┐                │
│                                    │  WatcherPermit   │                │
│                                    │  (X-RWT tokens)  │                │
│                                    └────────┬─────────┘                │
│                                             │ consumes                 │
│                                    ┌────────▼─────────┐                │
│                                    │   Commitment     │                │
│                                    │  (per-watcher)   │                │
│                                    └────────┬─────────┘                │
│                                             │ merges into              │
│                                    ┌────────▼─────────┐                │
│                                    │  EventTrigger    │                │
│                                    │  (quorum proof)  │                │
│                                    └────┬──────┬──────┘                │
│                                         │      │                       │
│                              ┌──────────▼┐  ┌──▼──────────┐           │
│                              │  Permit   │  │    Fraud    │           │
│                              │ (reward)  │  │  (slash)    │           │
│                              └───────────┘  └─────────────┘           │
│                                                    │                   │
│                              ┌─────────────────────▼──┐                │
│                              │   Collateral (AWC NFT) │                │
│                              └────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary

1. A volunteer watcher locks RSN tokens into **RwtRepo**, receiving X-RWT tokens and a WID token (minted as a unique watcher identifier). A **WatcherCollateral** box is created, holding the AWC NFT and recording the staked RWT amount in R5.
2. When the watcher observes a cross-chain event, it spends a **WatcherPermit** box to create an **EventCommitment** box storing `blake2b256(eventData ++ WID)` — a commitment that binds the watcher's identity to a specific event without revealing its contents.
3. Once enough watcher commitments exist (quorum per **RepoConfig** parameters), one watcher merges all commitments into an **EventTrigger** box, revealing the event data and the list of participating WIDs. RWT tokens from all commitments are pooled into the trigger.
4. **Guards** observe the EventTrigger. If valid, they spend the **GuardSign** box (in a multi-sig transaction satisfying `atLeast(paymentSignCount, guards)`) to execute the cross-chain payment via the **Lock** contract.
5. If the event was fraudulent or unverifiable, the **Cleanup** service, after a confirmation delay, redirects the RWT pool to a **Fraud** box. The **Fraud** contract then atomically slashes the collateral in the watcher's **WatcherCollateral** box, reducing R5 accordingly.
6. The **Emission** contract manages the RSN token reserve, enforcing that each RSN removed from the reserve is balanced by a newly recorded EmittedRSN token quantity — a strict conservation invariant.

---

## Smart Contracts

All contracts are written in ErgoScript and live under `src/main/scala/rosen/bridge/scripts/`.

### `GuardSign.es` — Guard Consensus State Machine
Holds the **Guard NFT** (Singleton / State NFT), all guard public keys in R4 (`Coll[Coll[Byte]]`), and two signature thresholds in R5 (`[paymentRequiredSigns, updateRequiredSigns]`). Any state transition (guard set rotation, threshold change) requires `atLeast(updateRequiredSigns, proveDlog(decodePoint(pk)))` — an M-of-N Sigma protocol proof. The Guard NFT linearizes the eUTXO state, preventing concurrent forks of the guard state.

### `Lock.es` — Ergo-Side Bridge Wallet
Protects the pool of Ergo-wrapped tokens. It references **GuardSign** as a **Data input** (non-consuming) to read the current guard public keys and payment threshold, then enforces `atLeast(paymentSignCount, sigmas)`. This means the wallet address never changes when the guard set rotates — only the GuardSign state box is updated.

### `RwtRepo.es` — Watcher Permit Repository
A multi-path State Machine that manages four transitions: initial permit issuance, permit extension (restaking), partial permit return, and full watcher exit. It holds the Repo State NFT (token 0), X-RWT pool (token 1), RSN pool (token 2), and X-AWC NFT pool (token 3). R5 stores the total active watcher count. A **RepoReplication Invariant** is checked on every non-administrative path: script hash, token IDs, R4 chain ID, and minimum box value must all be preserved in the output.

### `RepoConfig.es` — Bridge Governance Parameters
A singleton configuration box (authenticated by a Config NFT