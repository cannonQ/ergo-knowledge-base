---
title: AcoSmrkas/mew-prediction — Overview
description: MEW Prediction — prediction market campaigns, LP mechanics, cross-chain (Ergo + Cardano)
tags: [acosmrkas, mew-prediction, defi, typescript, svelte]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/AcoSmrkas/mew-prediction"
project: acosmrkas-mew-prediction
group: defi
priority: medium
languages: [typescript, svelte]
contract_count: 0
pattern_match_count: 1
---
# AcoSmrkas/mew-prediction — Developer Overview

---

## Overview

**MEW Prediction** is a decentralized prediction market platform built on Ergo, designed around campaign-based wagering where users stake ERG or Native tokens on discrete outcomes. Each prediction campaign is a self-contained on-chain construct: participants lock funds into eUTXO Boxes guarded by ErgoScript contracts, and outcomes are resolved through on-chain logic without requiring a trusted oracle operator beyond what the campaign creator defines. The platform's architecture embraces Ergo's eUTXO model natively, treating each campaign lifecycle phase (creation, participation, resolution, payout) as a distinct state transition across a set of guarded Boxes.

Within the Ergo DeFi ecosystem, MEW Prediction occupies the role of a structured outcome market, complementing liquidity and stablecoin primitives like SigmaUSD and Dexy by offering a venue for price-directional or event-driven speculation with deterministic payout mechanics. The inclusion of LP mechanics suggests that liquidity provisioning is a first-class concern — likely allowing liquidity providers to act as counterparties to prediction positions, earning fees in exchange for bearing directional risk, analogous to an AMM invariant applied to outcome probabilities.

The project is additionally scoped for **cross-chain operation spanning Ergo and Cardano**, indicating that campaign participation or asset bridging is intended to function across both eUTXO chains. This positions MEW Prediction as a multi-chain DeFi primitive, leveraging the structural similarities between Ergo's eUTXO and Cardano's eUTXO models while requiring careful handling of cross-chain message passing, asset representation (Native tokens on both sides), and state synchronization.

---

## Architecture

The project is structured as a **SvelteKit library and showcase application**, with the core reusable logic residing under `src/lib` and a SvelteKit route layer providing a preview/demo interface. The primary technical concern is the construction of well-formed Ergo Transactions off-chain before submission to the node or wallet connector.

### Key Components

```
src/
├── lib/
│   ├── contract/
│   │   └── createCampaignTx.ts     ← Transaction builder for campaign creation
│   └── (expected: participateTx, resolveTx, claimTx, lpTx)
└── routes/
    └── (SvelteKit UI showcase pages)
```

**`createCampaignTx.ts`** is the foundational transaction builder. It constructs the Box output(s) that instantiate a new prediction campaign on-chain. This module is responsible for:

- Assembling the correct **ErgoTree** (compiled from the campaign ErgoScript contract) as the output Box's guarding script.
- Populating **Registers** (R4–R9) with campaign metadata: outcome count, resolution deadline (block height), creator address, token identifiers for staking assets, and LP configuration parameters.
- Enforcing the **Minimum box value** constraint on all created Boxes.
- Injecting a **Singleton / State NFT** (minted in the same transaction via the Token ID rule — a token whose ID equals the Box ID of one of the transaction's inputs) to uniquely identify the campaign Box across its entire lifecycle.

### Data Flow

```
User Intent
    │
    ▼
Transaction Builder (TypeScript)
    │  assembles Inputs (user UTXOs) + Outputs (campaign Box with State NFT)
    ▼
EIP-12 Wallet Connector (e.g. Nautilus)
    │  signs via Sigma protocols
    ▼
Ergo Node / Explorer API
    │  confirms transaction
    ▼
Campaign Box (on-chain eUTXO)
    │  consumed by subsequent participate / resolve / claim transactions
    ▼
LP Boxes / Payout Boxes
```

The LP mechanics introduce additional Boxes that pool counterparty liquidity. These Boxes maintain an **invariant** over total liquidity and outstanding positions, updated atomically in each participation Transaction.

---

## Smart Contracts

> **Note:** No ErgoScript source files are directly visible in the provided repository snapshot. The following is inferred from the transaction builder pattern, project description, and standard prediction market eUTXO design on Ergo.

### Expected Contract Set

#### 1. Campaign Contract (State Machine Box)

The central **multi-stage contract** governing campaign lifecycle. Uses a **Singleton / State NFT** (minted at campaign creation) to enforce that only one authoritative campaign Box exists at each stage.

**Registers:**
| Register | Content |
|----------|---------|
| R4 | Campaign creator `SigmaProp` (for admin actions) |
| R5 | Resolution deadline as block height (`Int`) |
| R6 | Outcome count (`Int`) |
| R7 | Staking token `Token ID` (`Coll[Byte]`) |
| R8 | Current stage indicator: OPEN / RESOLVED / CLOSED (`Int`) |
| R9 | LP configuration or outcome odds encoding (`Coll[Long]`) |

**Spending paths:**
- **Participate:** Any user may spend the campaign Box, producing a new campaign Box (same NFT, updated totals) plus a position receipt Box.
- **Resolve:** Creator (or designated oracle input) transitions stage to RESOLVED, recording the winning outcome in R8/R9.
- **Claim:** Winners provide their position receipt Box as an input; contract verifies outcome match and releases proportional funds.

#### 2. LP Box Contract

Holds pooled liquidity from LP providers. Enforces an **invariant** on total liquidity relative to outstanding exposure. Likely uses **Constant segregation** to track individual LP shares via proportional token minting (LP share tokens).

#### 3. Position Receipt Contract

A lightweight Box issued to each participant, encoding their chosen outcome and stake amount in Registers. Acts as a **Data input** during the claim phase to prove entitlement without re-spending.

#### 4. Cross-Chain Bridge Interface

For Cardano interoperability, a Boxes-as-messages pattern is expected, where cross-chain intents are recorded in Ergo Boxes with Cardano destination addresses in Registers, consumed by an off-chain relayer bot.

---

## Integration Guide

### Prerequisites

```bash
npm install   # or pnpm install
npm run dev   # SvelteKit dev server
```

### Creating a Campaign (Off-Chain)

The primary integration point is `createCampaignTx.ts`. Expected usage pattern:

```typescript
import { createCampaignTx } from '$lib/contract/createCampaignTx';

// Construct the unsigned transaction
const unsignedTx = await createCampaignTx({
  creatorAddress: '9f...',          // Ergo P2PK address
  outcomeCount: 2,                  // Binary market: YES / NO
  resolutionHeight: 1_200_000,      // Deadline as absolute block height
  stakingTokenId: '...',            // Token ID of accepted stake token (or ERG)
  initialLiquidity: 1_000_000_000n, // nanoERG
  stateNFTInput: selectedUTXO,      // The UTXO whose Box ID becomes the NFT Token ID
  // ... additional LP params
});

// Submit via EIP-12 connector (Nautilus / SAFEW)
const signedTx = await ergo.sign_tx(unsignedTx);
await ergo.submit_tx(signedTx);
```

### EIP-12 Wallet Connection

The frontend integrates with **EIP-12** compatible wallets via the globally injected `ergo` object:

```typescript
// Check for EIP-12 wallet
if (typeof ergo !== 'undefined') {
  const connected = await ergo.request_read_access();
  const utxos = await ergo.get_utxos();
  const changeAddress = await ergo.get_change_address();
}
```

### Querying Campaign State

Campaign Boxes are identified by their **State NFT Token ID** (fixed at creation). Query via the Ergo Explorer API or an indexer:

```typescript
// Find current campaign Box by NFT
const response = await fetch(
  `https://api.ergoplatform.com/api/v1/boxes/unspent/byTokenId/${campaignN