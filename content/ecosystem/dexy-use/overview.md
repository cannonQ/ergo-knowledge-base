---
title: kushti/dexy-stable — Overview
description: Dexy $USE stablecoin — USD-pegged fork of dexy-stable, ~$400K TVL, oracle-pegged minting
tags: [kushti, dexy-stable, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
project: dexy-use
group: defi
priority: high
languages: [ergoscript, scala]
contract_count: 22
pattern_match_count: 0
---
# Developer Overview: kushti/dexy-stable (USE / DexyUSD Stablecoin)

---

## Overview

**dexy-stable** is the reference implementation of the Dexy stablecoin protocol on Ergo, providing a USD-pegged stablecoin (**USE**, also referred to as DexyUSD) with approximately $400K TVL at time of writing. It is an oracle-pegged algorithmic stablecoin that mints and redeems against ERG collateral, using a combination of oracle rates and LP market rates to maintain its peg. The protocol is a fork/evolution of earlier Dexy designs and operates entirely on Ergo's eUTXO model, with all state managed through Singleton NFT-bearing boxes (State NFTs) and multi-stage contracts enforced in ErgoScript.

The protocol's architecture separates concerns into four functional subsystems: a central **Bank** (holding the USE token supply and ERG reserves), a **Liquidity Pool** (providing market price discovery), a **DORT/GORT Buyback** mechanism (recycling protocol fees into oracle incentives), and a **Governance** layer (enabling on-chain upgrade votes). Each subsystem is itself a network of cooperating eUTXO boxes, authenticated by singleton NFTs and coordinated through carefully validated multi-input transactions. The Bank does not encode minting logic directly—instead, it acts as a permissioned state machine that only accepts state transitions authorized by recognized satellite contract NFTs.

Within the broader Ergo ecosystem, dexy-stable represents one of the most sophisticated multi-stage contract deployments on mainnet. It connects to the **Ergo Oracle Pool** (for ERG/USD pricing), uses **DORT** (the USD-variant equivalent of GORT) as a governance/reward token, and complements existing primitives like **SigmaUSD** by providing an alternative collateralization model. The protocol also includes a companion **HodlERG** contract and a GORT developer emission schedule, making the repository a near-complete DeFi primitive stack built on native Ergo infrastructure.

---

## Architecture

### Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Inputs (Read-Only)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Oracle Pool │  │  LP Box      │  │  Tracking Boxes   │  │
│  │  (ERG/USD)   │  │  (USE/ERG)   │  │  (95/98/101%)     │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                       Bank Subsystem                        │
│                                                             │
│  ┌────────────┐   ┌─────────────┐   ┌──────────────────┐   │
│  │  FreeMint  │   │ ArbitrageMint│   │   Intervention   │   │
│  │  (freemint │   │ (arbmint.es)│   │  (intervention   │   │
│  │   .es)     │   │             │   │       .es)        │   │
│  └─────┬──────┘   └──────┬──────┘   └────────┬─────────┘   │
│        │                 │                   │              │
│        └────────┬─────────┘                  │              │
│                 ▼                            ▼              │
│          ┌────────────┐              ┌───────────────┐      │
│          │    Bank    │◄─────────────│   Payout      │      │
│          │  (bank.es) │              │  (payout.es)  │      │
│          └─────┬──────┘              └───────────────┘      │
│                │                                            │
│                ▼                                            │
│          ┌────────────┐                                     │
│          │  Buyback   │                                     │
│          │(buyback.es)│                                     │
│          └─────┬──────┘                                     │
└────────────────┼────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      LP Subsystem                           │
│  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ LP Swap  │ │LP Mint  │ │LP Redeem │ │ Extract-to-    │  │
│  │          │ │         │ │          │ │ Future (extract │  │
│  └──────────┘ └─────────┘ └──────────┘ │      .es)      │  │
│                                        └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   Governance Subsystem                      │
│  ┌──────────────┐     ┌──────────────┐                      │
│  │  Ballot Box  │────►│  Update Box  │                      │
│  │  (ballot.es) │     │  (update.es) │                      │
│  └──────────────┘     └──────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Price Discovery**: The Oracle Pool box carries the current ERG/USD rate in `R4` as a `Long` (nanoErgs per USD, adjusted for USE's 3 decimal places via division by 1000). This box is consumed as a **Data Input** (read-only) by FreeMint, ArbitrageMint, Intervention, and Payout — it is never spent.

2. **Tracking Boxes**: Three tracking boxes (95%, 98%, 101%) monitor the ratio of LP price to oracle price. They carry state in `R7` (the height at which the tracked condition was first satisfied). ArbitrageMint reads the 101% tracker; Intervention reads the 98% tracker. These enforce minimum observation windows before protocol actions can fire.

3. **Minting Flow**: A user or bot constructs a transaction with `[FreeMintBox | ArbitrageMintBox, BankBox, BuybackBox]` as inputs and `[OracleBox, LPBox, TrackingBox?]` as Data Inputs. The satellite mint box validates the rate, quota, and fee split. The Bank box validates only that the satellite's NFT is present in input position 0.

4. **Intervention Flow**: When LP price drops ≤98% of oracle, an off-chain bot constructs a transaction spending `[LPBox, BankBox, InterventionBox]`. ERG flows Bank→LP; USE flows LP→Bank. The AMM invariant is checked on-chain.

5. **Buyback Flow**: Accumulated ERG in the Buyback box is used to purchase DORT/GORT from the DORT/GORT LP. Purchased tokens are periodically returned to the Oracle Pool as data provider rewards via the give-back action.

6. **Governance Flow**: Ballot holders sign transactions setting `R5 = updateBoxId`, `R6 = blake2b256(newErgoTree)` in their ballot boxes. Once ≥3 of 5 ballots are collected, the Update box transaction atomically replaces the target contract's ErgoTree while preserving its Singleton NFT.

---

## Smart Contracts

All contracts are written in **ErgoScript** and compiled to **ErgoTree