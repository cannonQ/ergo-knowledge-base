---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — Overview
description: Bountiful — decentralized bounty platform on Ergo with on-chain reward distribution
tags: [stabilitynexus, bountiful-bountyplatform-ergo, dao, ergoscript, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
project: stabilitynexus-bountiful-bountyplatform-ergo
group: dao
priority: medium
languages: [ergoscript, typescript]
contract_count: 12
pattern_match_count: 17
---
# Bountiful Bounty Platform — Developer Overview

## Overview

Bountiful is a decentralized bounty platform built on Ergo that enables trustless, on-chain reward distribution for development tasks, security audits, and other open-ended problem-solving challenges. Creators post bounties by locking ERG (and optionally native tokens) inside a multi-stage ErgoScript contract guarded by a **Singleton / State NFT** (the BBT token). The platform enforces the complete bounty lifecycle—creation, contribution, solution submission, judgment, reward withdrawal, and refund—entirely through on-chain contract logic, eliminating the need for any trusted intermediary. Because the eUTXO model makes all state explicit inside **Boxes** and their **Registers**, every lifecycle transition is atomic and auditable by any network participant.

The platform supports two complementary validation modes. In the automated path, solution validity is proven cryptographically (via a Celaut service that generates a Sigma protocol proof), allowing funds to be released without human involvement. In the arbitrated path, a configurable n-of-m multisig panel of judges (optionally backed by an on-chain **Sigma Reputation Panel**) reviews and countersigns submissions before the reward is unlocked. A hybrid approach—automated tests as a first filter, human judges for final approval—is also supported. A development fee is collected on every successful claim and routed through a dedicated `dev_fee.es` treasury contract that enforces proportional splits to four designated recipients.

Within the broader Ergo ecosystem, Bountiful represents a practical demonstration of **multi-stage contracts** and **State NFT**-driven state machines operating entirely within the eUTXO model. It sits in the StabilityNexus DAO group alongside SigmaUSD-adjacent infrastructure projects and integrates with external reputation oracles (GitHub, POAP, Gitcoin Passport) via **data inputs**, making it a reference implementation for DAO tooling on Ergo.

---

## Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                     Off-Chain (TypeScript)                  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  UI / Client │  │  Headless    │  │  Off-Chain Bot   │  │
│  │  (EIP-12     │  │  dApp Lib    │  │  (fee sweeper,   │  │
│  │   connector) │  │  src/lib/    │  │   submission     │  │
│  └──────┬───────┘  └──────┬───────┘  │   watcher)       │  │
│         │                 │          └────────┬─────────┘  │
│         └─────────────────┴────────────────────┘           │
│                           │                                 │
│              Transaction Builder (AppKit/Fleet)             │
└───────────────────────────┬─────────────────────────────────┘
                            │  signed Tx
┌───────────────────────────▼─────────────────────────────────┐
│                        Ergo Node / Explorer                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   On-Chain ErgoScript Contracts              │
│                                                             │
│  mint.es ──────────────────────────────────────────────┐    │
│      │ (initialises IDT, verifies contract hash)        │    │
│      ▼                                                  │    │
│  bounty_contract.es / bounty-v1.es  ◄──────────────────┘    │
│      │  (State NFT = BBT, R4–R9, multi-stage SM)            │
│      ├── proposal_v1_0.es  (Pending→Approved/Disputed)       │
│      ├── bounty_v1_0.es    (APT/PFT contribution model)      │
│      └── dev_fee.es        (4-way fee split treasury)        │
│                                                             │
│  digital_public_good.es  (immutable DPG metadata oracle)    │
│  reputation_system/                                         │
│      digital_public_good.es  (Type NFT, schema registry)    │
│      reputation-v0.es        (RBT, judge reputation events) │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow — Bounty Lifecycle

```
Creator
  │
  ▼
mint.es
  │  Verifies IDT token transfer + blake2b256(propositionBytes) == expected hash
  │  Creates bounty Box with BBT State NFT in tokens(0)
  ▼
bounty_contract.es  [R4=deadline, R5=minSubmissions, R6=[total,accepted,rejected],
                     R7=reward, R8=creatorPubKey, R9=submissionsRoot|judgmentsRoot|metadata]
  │
  ├── ADD_FUNDS tx     → value+R7 increase; all other Registers frozen
  ├── EXTEND_DEADLINE  → R4 updated; HEIGHT < old deadline enforced
  ├── UPDATE_METADATA  → R9 updated; version incremented; HEIGHT < deadline
  │
  ├── SUBMIT tx        → R6[0]++; R9 submissions Merkle root updated
  │       └── (submitter constructs proof via Celaut service)
  │
  ├── JUDGE tx  [data input: judgment decision box]
  │       └── → R6[1]++ (accepted) XOR R6[2]++ (rejected); R9 judgments root updated
  │           └── requires creatorProp = proveDlog(R8.toGroupElement)
  │
  ├── WITHDRAW_REWARD tx  [data input: winner_address, judgment_height]
  │       └── R6[1]>=1 AND R6[0]>=R5 AND HEIGHT >= judgment_height+dispute_period
  │           → winner Box (reward - dev_fee) + dev_fee Box → dev_fee.es
  │
  └── REFUND tx
          └── HEIGHT > R4 AND (R6[0]<R5 OR R6[1]==0)
              → creator refund Box

dev_fee.es  [accumulates fee UTXOs]
  └── FEE_DISTRIBUTION tx
          → Bruno(32%) + Lgd(32%) + Jossemii(32%) + TheStableOrder(4%) + MinerFee
              (validMinerFee checked via blake2b256 of miner-fee ErgoTree)
```

---

## Smart Contracts

### `mint.es`
**Role:** Minting initialiser / deployment guard.  
Validates that the Bounty ID Token (IDT) moves from the minting Box into `OUTPUTS(0)`, and that `blake2b256(OUTPUTS(0).propositionBytes)` matches the compile-time constant `${contract_bytes_hash}`. This prevents contract-template substitution attacks and ensures only one canonical bounty ErgoTree can be instantiated per IDT. No Registers are read; all logic depends on the ErgoScript context (`SELF`, `OUTPUTS`).

---

### `bounty_contract.es` / `contracts/ergo-bounty-contracts/bounty-v1.es`
**Role:** Core multi-stage state machine. This is the primary contract that every live bounty Box is locked under.

| Register | Type | Purpose | Mutable? |
|---|---|---|---|
| R4 | `Int` | Deadline (block height) | Extend-only |
| R5 | `Long` | Minimum submission count | Immutable |
| R6 | `Coll[Long]` | `[totalSubmissions, accepted, rejected]` | Incremented per action |
| R7 | `Long` | Reward