---
title: StabilityNexus/BenefactionPlatform-Ergo — Overview
description: Benefaction Platform — decentralized fundraising/donation platform on Ergo
tags: [stabilitynexus, benefactionplatform-ergo, dao, ergoscript, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
project: stabilitynexus-benefactionplatform-ergo
group: dao
priority: medium
languages: [ergoscript, typescript]
contract_count: 5
pattern_match_count: 12
---
# Developer Overview: StabilityNexus/BenefactionPlatform-Ergo

---

## Overview

**Bene** is a fully decentralized, client-side fundraising platform built on the Ergo blockchain, implementing a **Proof-of-Funding** model using the eUTXO paradigm. Its core value proposition is trustless campaign resolution: project funds remain locked inside a guarded **Box** until either a predefined minimum goal is met (enabling withdrawal) or a deadline passes without success (enabling contributor refunds). Because all business logic resides exclusively in immutable ErgoScript contracts, there is no backend server, no administrator key, and no privileged actor who can redirect funds — the contract **is** the rule.

The platform employs a dual-token architecture (APT and PFT) to separate contribution receipts from final project participation rights. Contributors receive **Auxiliary Project Tokens (APT)** upon funding, which serve as redeemable escrow receipts. If the campaign succeeds, APTs are exchanged for **Proof-of-Funding Tokens (PFT)**; if it fails after the deadline, APTs are returned for a 100% refund of the base currency (ERG or any native token). This design cleanly separates the *accounting* layer (APTs) from the *value* layer (PFTs), enabling atomic, verifiable state transitions across the campaign lifecycle.

Within the broader Ergo ecosystem, Bene occupies the intersection of DAO tooling and decentralized finance infrastructure. It supports any Ergo-native token as the fundraising base currency (including stablecoins), integrates an on-chain comment/reputation protocol, and exposes a composable ownership model that allows other smart contracts — such as DAO treasuries or multi-sig schemes — to act as campaign owners. The entire frontend is a static site that communicates directly with a user-selected Ergo node or explorer, making it deployable on IPFS or any static host with no trusted intermediary.

---

## Architecture

### Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Client-Side)                   │
│                                                             │
│  ┌─────────────────────┐    ┌──────────────────────────┐   │
│  │   SvelteKit Frontend │    │  TypeScript Action Layer  │   │
│  │  (static site / SSG) │◄──►│  src/lib/ergo/actions/   │   │
│  └─────────────────────┘    └────────────┬─────────────┘   │
│                                           │                 │
│  ┌────────────────────────────────────────▼──────────────┐ │
│  │              Off-chain SDK / Headless dApp             │ │
│  │  platform.ts · project.ts · dev_contract.ts           │ │
│  │  submit.ts · buy_refund.ts · withdraw.ts              │ │
│  │  temp_exchange.ts · rebalance.ts · distribute_funds.ts│ │
│  └────────────────────────────────────────┬──────────────┘ │
└───────────────────────────────────────────┼─────────────────┘
                                            │  JSON/REST
                        ┌───────────────────▼──────────────┐
                        │   User-selected Ergo Node         │
                        │   or Public Explorer API          │
                        └───────────────────┬──────────────┘
                                            │  eUTXO
                ┌───────────────────────────▼────────────────┐
                │              Ergo Blockchain                │
                │                                            │
                │  ┌─────────────────────────────────────┐  │
                │  │       Bene Campaign Box (SELF)       │  │
                │  │  tokens: [APT (singleton+supply),    │  │
                │  │           PFT (project tokens),      │  │
                │  │           base_token? (non-ERG)]     │  │
                │  │  R4: deadline  R5: min goal          │  │
                │  │  R6: counters  R7: price             │  │
                │  │  R8: config    R9: metadata          │  │
                │  └────────────────┬────────────────────┘  │
                │                   │ fee output             │
                │  ┌────────────────▼────────────────────┐  │
                │  │       Dev Fee Contract Box           │  │
                │  │  Distributes to 4 recipients         │  │
                │  │  (Bruno 32%, Lgd 32%, Jm 32%,       │  │
                │  │   The Stable Order 4%)               │  │
                │  └─────────────────────────────────────┘  │
                └────────────────────────────────────────────┘
```

### Data Flow

1. **Campaign Creation (`submit.ts`):** The creator supplies PFT tokens and configuration parameters. An off-chain transaction builder constructs the initial campaign Box, encoding all immutable parameters into Registers R4–R9 and minting APTs at `PFT_supply + 1` (one unit reserved as Singleton/State NFT identifier).

2. **Contribution (`buy_refund.ts`):** A contributor's Box and the campaign Box are consumed as inputs. The action layer computes the APT amount from `R7` (price), constructs two outputs — the replicated campaign Box with updated `R6` counters and the contributor's Box holding new APTs — and submits the transaction.

3. **Chained Submission (`__submit_with_chain.ts`):** Handles mempool chaining, allowing sequential transactions referencing unconfirmed outputs. This is critical in a eUTXO model where the campaign Box is a single-input singleton.

4. **Withdrawal (`withdraw.ts`):** On success (R6[0] ≥ R5), the action layer constructs a transaction splitting ERG (or base tokens) to the owner address (95%) and the dev fee contract Box (5%).

5. **Fee Distribution (`distribute_funds.ts`, `dev_contract.ts`):** A separate transaction spends the dev fee Box, distributing accumulated fees to four hardcoded recipients in fixed proportions, validated entirely on-chain.

---

## Smart Contracts

### `contract_v2.es` — Main Campaign Contract (current)

This is the primary **multi-stage, state-machine** contract governing the full campaign lifecycle. It enforces a strict **Box replication invariant**: every spending transaction must produce `OUTPUTS(0)` as a valid successor Box with the same ErgoTree, same APT Singleton ID, and identical immutable Registers (R4, R5, R7, R8, R9). Only R6 (counters) and token amounts change across transitions.

**State Machine Transitions:**

| Action | Guard Condition | R6 Mutation | Token/Value Change |
|---|---|---|---|
| **Buy** | APT available; deadline not enforced on buy | R6[0] (sold) ↑ | ERG/base token in, APT out to user |
| **Refund** | Deadline passed (`R4`) AND sold < R5 | R6[1] (refunded) ↑ | APT in from user, ERG/base token out |
| **Exchange APT→PFT** | sold ≥ R5 (success) | R6[2] (exchanged) ↑ | APT in, PFT out |
| **Withdraw Funds** | sold ≥ R5 | — | ERG/base token split 95%/5% to owner + dev fee Box |
| **Withdraw Unsold PFT** | PFT_in_box ≥ APT_in_circulation | — | Surplus PFT out to owner |
| **Add Stock** | Owner authenticated | — | PFT added to Box |

**Security Invariant (enforced on every transition):**

```
PFT_in_box ≥ APT_in_circulation
```

where:

```ergoscript
available
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
