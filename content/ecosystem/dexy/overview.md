---
title: kushti/dexy-stable — Overview
description: Dexy stablecoin — oracle-pegged minting, LP, cross-tracker, anti-drain mechanisms
tags: [kushti, dexy-stable, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
project: kushti-dexy-stable
group: defi
priority: high
languages: [ergoscript, scala]
contract_count: 22
pattern_match_count: 0
---
# Dexy Stablecoin (kushti/dexy-stable) — Developer Overview

---

## Overview

Dexy is a dual-mechanism stablecoin protocol built natively on Ergo, combining an algorithmic bank with an AMM-style liquidity pool to maintain oracle-pegged token prices. Unlike SigmaUSD's purely collateral-driven model, Dexy introduces a two-sided stabilization architecture: the bank mints stablecoins (DexyGold or DexyUSD) when the LP price rises above the oracle reference, and automatically buys them back from the pool when the price falls below peg. This design turns the LP itself into a price-discovery and stabilization surface rather than treating it as an external dependency. All protocol logic is expressed entirely in ErgoScript, with no trusted contracts or external signers — correctness is enforced at the consensus layer via eUTXO spending conditions.

The protocol deploys three core stablecoin variants (DexyGold pegged to gold, DexyUSD pegged to USD) and introduces GORT (Gold Oracle Reward Token), a purpose-built incentive mechanism for oracle pool operators. GORT tokenomics create a closed feedback loop: minting fees flow into a Buyback contract that purchases GORT from an ERG/GORT LP, which is then redistributed to oracle operators via oracle pool 2.0 contracts. This makes Dexy one of the first Ergo protocols to implement trustless, on-chain oracle compensation as a first-class protocol invariant rather than a governance side-effect.

Within the broader Ergo DeFi ecosystem, Dexy serves as both a production stablecoin and a reference implementation of advanced eUTXO design patterns: multi-stage contracts with Singleton/State NFT routing, counter-reset state machines encoded in Registers, oracle data consumption via Data inputs, cross-contract tracking boxes that detect price deviation events, and on-chain governance via ballot NFTs and weighted vote aggregation. The codebase in `kushti/dexy-stable` covers ErgoScript contracts, Scala off-chain tooling, deployment specifications, and the GORT developer emission schedule.

---

## Architecture

### High-Level Component Map

```
Oracle Pool (data input) ──────────────────────────────────────────────────────┐
                                                                                │
┌──────────────┐    mint/redeem    ┌──────────────┐    swap/add/remove   ┌──────────────┐
│  Bank Box    │◄─────────────────►│ Dexy LP Box  │◄───────────────────►│  LP Actions  │
│ (bankNFT)    │                   │ (lpNFT)      │                      │ Swap/Mint/   │
└──────┬───────┘                   └──────┬───────┘                      │ Redeem/      │
       │                                  │                               │ Extract      │
       │ delegates to                     │ tracked by                   └──────────────┘
       ▼                                  ▼
┌──────────────────────────────────────────────────────────────┐
│                  Auxiliary Bank Contracts                      │
│  ArbitrageMint │ FreeMint │ Intervention │ Payout             │
└──────────────────────────────────────────────────────────────┘
       │
       │ fee ERG
       ▼
┌──────────────┐    swap GORT    ┌──────────────┐    reward    ┌──────────────┐
│ Buyback Box  │────────────────►│ GORT/ERG LP  │             │ Oracle Pool  │
│ (buybackNFT) │◄────────────────│              │◄────────────│ (GORT token) │
└──────────────┘    receive GORT └──────────────┘             └──────────────┘
                                        ▲
                                        │ GORT emission
                                  ┌──────────────┐
                                  │ GORT Dev     │
                                  │ Emission Box │
                                  └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Tracking Boxes (95%, 98%, 101%)            │
│   Monitor LP/oracle rate ratio; record trigger heights       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Governance (Update / Ballot)                    │
│   updateNFT + ballotTokenId + minVotes (3-of-5)             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Oracle rate** enters all minting and intervention contracts as a **Data input** — the oracle pool box is read-only; no ERG is consumed from it. Its R4 register carries the current nanoErgs-per-unit rate.
2. **LP state** is also consumed as a Data input for minting decisions, providing live `lpReservesX` (ERG) and `lpReservesY` (Dexy) figures. For intervention and LP-modifying transactions, the LP box is a full spending input.
3. **Tracking boxes** (95%, 98%, 101%) observe the LP/oracle ratio over time and record the block height at which a threshold was first breached in their R7 register. Downstream contracts (ArbitrageMint, Intervention) read this height to enforce time delays before action.
4. **Bank box** is always at input index 1 and output index 1 in all bank-related transactions, enforcing deterministic box ordering that ErgoScript conditions depend on.
5. **Fee ERG** flows from each mint transaction into both the Bank box (collateral backing) and the Buyback box (GORT acquisition reserve). The Buyback contract later executes a swap against the GORT/ERG LP, then returns acquired GORT to the oracle pool.

---

## Smart Contracts

All contracts are written in ErgoScript and reside under `contracts/`. Each stateful contract instance is authenticated by a **Singleton/State NFT** held in `tokens(0)`. State is persisted across transactions through R4–R7 registers. Constants (NFT token IDs, thresholds, fee numerators) are injected at compile time via **constant segregation** placeholders (e.g., `$bankNFT`, `$oracleNFT`).

### Bank Contracts (`contracts/bank/`)

#### `bank.es` — Bank Vault (State Machine Root)
The canonical Dexy token supply ledger. Holds the `bankNFT` singleton and all unminted Dexy tokens. Contains no minting logic itself — it validates only that exactly one recognized auxiliary contract (identified by NFT) is present at a designated input index, then enforces that its own successor at output index 1 preserves `bankNFT` and the Dexy token ID. The dexy token amount is the only mutable field. Routing logic:

| Input index 0 NFT | Path |
|---|---|
| `freeMintNFT` or `arbitrageMintNFT` | Mint path |
| `interventionNFT` (at index 2) | Intervention path |
| `payoutNFT` | Payout path |
| `updateNFT` | Governance update (bypasses all other checks) |

#### `freemint.es` — Free Mint (Rate-Limited, Permissionless)
Allows any user to mint up to 1% of LP Dexy reserves per epoch (~360 blocks). Uses a two-register counter state machine: R4 holds the next reset height; R5 holds remaining quota. Oracle rate validation enforces `lpRate * 100 > oracleRate * 98` — minting is blocked if the LP price is already at or below 98% of oracle. Fee split: 0.3% to Bank (collateral), 0.2% to Buyback (GORT acquisition).

#### `arbmint.es` — Arbitrage Mint (Threshold-Triggered)
Activates only when `lpRate > oracleRate * 101%`, indicating the pool price is