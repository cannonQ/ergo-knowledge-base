---
title: StabilityNexus/BenefactionPlatform-Ergo — Overview
description: Benefaction Platform — decentralized fundraising/donation platform on Ergo
tags: [stabilitynexus, benefactionplatform-ergo, dao, ergoscript, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
project: stabilitynexus-benefactionplatform-ergo
group: dao
priority: medium
languages: [ergoscript, typescript]
contract_count: 5
pattern_match_count: 12
---
# StabilityNexus/BenefactionPlatform-Ergo — Developer Overview

---

## Overview

**Bene** is a decentralized, trust-minimized fundraising platform built on the Ergo blockchain, implementing a **Proof-of-Funding** model entirely through ErgoScript smart contracts. Its core value proposition is eliminating counterparty risk in crowdfunding: project funds remain locked in a multi-stage contract Box until a predefined minimum goal (`R5`) is met, after which only the project owner can withdraw. If the campaign fails to reach its threshold by the configured deadline (`R4`), contributors are guaranteed an on-chain refund path without any intermediary. The platform is fully client-side, requiring no backend servers — the browser connects directly to a user-selected Ergo node or explorer, making the interface censorship-resistant by design.

The platform introduces a dual-token accounting system — the **APT (Auxiliary Project Token)** and the **PFT (Proof-of-Funding Token)** — to enforce a strict security invariant across all state transitions. APTs serve as on-chain deposit receipts distributed at contribution time, while PFTs represent the real participation or governance token released only upon campaign success. The contract enforces the invariant `PFT_in_box ≥ APT_in_circulation` at all times, preventing the project owner from draining locked PFTs while outstanding contributor claims remain. Campaign metadata, project discussions, and contribution records are all persisted directly on the Ergo blockchain, including a fully on-chain comment forum based on an open reputation protocol.

Within the Ergo ecosystem, Bene occupies the **DAO/fundraising** vertical and demonstrates several advanced eUTXO design patterns: singleton state NFTs for campaign identity, multi-stage contract replication for state evolution, multi-token payment flexibility (ERG or any native token as the base currency), and a headless dApp architecture where all transaction construction happens off-chain in TypeScript. The platform is deployed as a static GitHub Pages application and serves as a reference implementation for DAO tooling on Ergo.

---

## Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────────┐
│                  Browser (Client-Side)                  │
│                                                         │
│  ┌────────────────┐    ┌──────────────────────────────┐ │
│  │  SvelteKit UI  │───▶│  src/lib/ergo/actions/       │ │
│  │  (static site) │    │  buy_refund.ts               │ │
│  │                │    │  submit.ts                   │ │
│  │                │    │  withdraw.ts                 │ │
│  │                │    │  temp_exchange.ts             │ │
│  │                │    │  rebalance.ts                │ │
│  └────────────────┘    └──────────────┬───────────────┘ │
│                                       │                 │
│  ┌────────────────────────────────────▼───────────────┐ │
│  │  src/lib/common/                                   │ │
│  │  platform.ts   — campaign registry & lookup        │ │
│  │  project.ts    — project Box parsing & modeling    │ │
│  └────────────────────────────────────┬───────────────┘ │
│                                       │                 │
│  ┌────────────────────────────────────▼───────────────┐ │
│  │  src/lib/ergo/dev/                                 │ │
│  │  dev_contract.ts  — dev fee Box construction       │ │
│  │  distribute_funds.ts — fee split tx building       │ │
│  └────────────────────────────────────────────────────┘ │
└───────────────────────────────┬─────────────────────────┘
                                │  JSON-RPC / REST
                         ┌──────▼──────┐
                         │  Ergo Node  │
                         │  / Explorer │
                         └──────┬──────┘
                                │  eUTXO
               ┌────────────────▼────────────────┐
               │        Ergo Blockchain           │
               │                                  │
               │  ┌──────────────────────────┐    │
               │  │  Bene Campaign Box       │    │
               │  │  (contract_v2.es)        │    │
               │  │  tokens: [APT, PFT, base]│    │
               │  │  R4–R9: campaign state   │    │
               │  └──────────────────────────┘    │
               │                                  │
               │  ┌──────────────────────────┐    │
               │  │  Dev Fee Box             │    │
               │  │  (dev_fee.es)            │    │
               │  └──────────────────────────┘    │
               │                                  │
               │  ┌──────────────────────────┐    │
               │  │  Mint/IDT Transit Box    │    │
               │  │  (mint_idt.es)           │    │
               │  └──────────────────────────┘    │
               └──────────────────────────────────┘
```

### Data Flow: Contribution Lifecycle

```
Creator deploys campaign
    → mint_idt.es gates PFT routing to contract_v2.es
    → Bene Campaign Box created with:
         tokens(0) = APT (singleton NFT unit + emission supply)
         tokens(1) = PFT (full project token reserve)
         R4 = (useTimestamp: Boolean, deadline: Long)
         R5 = minimum PFT threshold
         R6 = [0L, 0L, 0L]  ← sold / refunded / exchanged counters
         R7 = price (base token per PFT)
         R8 = [ownerErgoTree, devFeeHash, feePercent, PFT_ID, baseToken_ID]
         R9 = project metadata JSON bytes

Contributor sends base token (ERG or native token)
    → buy_refund.ts constructs Buy Transaction
    → Input: Campaign Box (SELF) + User Box
    → Output[0]: Replicated Campaign Box (R6[0] incremented)
    → Output[1]: User Box receives APT

Campaign succeeds (sold ≥ R5)
    → withdraw.ts constructs Withdraw Transaction
    → Output[0]: Owner Box receives 95% of raised funds
    → Output[1]: Dev Fee Box receives 5%
    → (Campaign Box consumed or partially replicated)

Campaign fails (deadline passed, sold < R5)
    → buy_refund.ts constructs Refund Transaction
    → Input: Campaign Box + User Box (holds APT)
    → Output[0]: Replicated Campaign Box (R6[1] incremented)
    → Output[1]: User Box receives base tokens back

APT → PFT exchange (post-success)
    → temp_exchange.ts constructs Exchange Transaction
    → R6[2] incremented to adjust available PFT calculation

Dev fee distribution
    → distribute_funds.ts splits accumulated dev fee Box
    → 4 output Boxes: Bruno (32%), Lgd (32%), Josemi (32%), Order (4%)
```

### Key Relationships

| Module | Role | Depends On |
|---|---|---|
| `contract_v2.es` | Primary campaign state machine | APT/PFT native tokens, Registers |
| `dev_fee.es` | Fee custody and proportional distribution | `contract_v2.es` (receives fee on withdrawal) |
| `mint_idt.es` | IDT transit gate, routes PFTs to campaign contract | `contract_v2.es` (destination hash) |
| `actions/submit.ts` | Campaign deployment transaction builder | `common/project.ts`, node API |
| `actions/buy_refund.ts` | Buy and refund transaction builders | `common/project.ts`, node API |