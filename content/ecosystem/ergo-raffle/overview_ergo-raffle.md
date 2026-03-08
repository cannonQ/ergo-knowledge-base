---
title: ErgoRaffle/raffle-backend — Overview
description: ErgoRaffle — crowdfunding/raffle platform, raffle contract lifecycle, donation mechanics
tags: [ergoraffle, raffle-backend, defi, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ErgoRaffle/raffle-backend"
project: ergoraffle-raffle-backend
group: defi
priority: medium
languages: [scala]
contract_count: 0
pattern_match_count: 4
---
# ErgoRaffle Backend — Developer Overview

---

## Overview

ErgoRaffle is a decentralized crowdfunding and raffle platform built on the Ergo blockchain, enabling anyone to create fundraising campaigns where backers donate ERG in exchange for raffle tickets. Each ticket represents a probabilistic claim on a reward pool, combining traditional crowdfunding incentives with provably fair, on-chain randomness. The platform supports diverse use cases ranging from charitable donations to business bootstrapping, with the key property that all campaign logic — ticket issuance, fund custody, and winner selection — is enforced by ErgoScript contracts on-chain.

Within the Ergo DeFi ecosystem, ErgoRaffle demonstrates a canonical **multi-stage contract** lifecycle: a raffle progresses through discrete states (created → active → funded/expired → settled) each represented by a distinct eUTXO box guarded by a corresponding ErgoScript. The backend service acts as the coordination layer — an **off-chain bot** that monitors blockchain state, constructs and submits transactions that advance the raffle state machine, and exposes a REST API consumed by the frontend. Because Ergo's eUTXO model requires explicit transaction construction rather than imperative state mutation, the backend is responsible for assembling well-formed transactions that satisfy each contract's spending conditions.

The project is significant as a reference implementation for crowdfunding mechanics on Ergo, illustrating how Native tokens (raffle tickets as tokens issued under the Token ID rule), Registers for metadata storage, and multi-stage contracts can be composed into a complete product without relying on a centralized escrow.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    raffle-backend (Play/Scala)           │
│                                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │  REST API   │   │  Raffle      │   │  Off-chain  │  │
│  │  Controllers│──▶│  Service     │──▶│  Bot / Poller│  │
│  └─────────────┘   └──────┬───────┘   └──────┬──────┘  │
│                           │                   │         │
│                    ┌──────▼───────┐   ┌───────▼──────┐  │
│                    │  RaffleContract│  │  Explorer /  │  │
│                    │  (ErgoScript  │  │  Node Client  │  │
│                    │   builder)   │  └───────────────┘  │
│                    └──────┬───────┘                     │
│                           │                             │
│                    ┌──────▼───────┐                     │
│                    │  Addresses   │                     │
│                    │  (ErgoTree   │                     │
│                    │   registry)  │                     │
│                    └─────────────┘                      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Local DB (SQLite / H2) — raffle request cache   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  raffle-frontend              Ergo Node / Explorer API
```

### Key Components

| Component | File(s) | Responsibility |
|---|---|---|
| **RaffleContract** | `app/raffle/RaffleContract.scala` | Compiles ErgoScript sources into ErgoTrees; provides address derivation per contract stage |
| **Addresses** | `app/raffle/Addresses.scala` | Central registry mapping each raffle lifecycle phase to its compiled ErgoTree / P2S address |
| **CreateReqUtils** | `app/raffle/CreateReqUtils.scala` | Constructs the creation transaction: builds output Boxes with correct Registers, token minting, and guard scripts |
| **Raffle Service** | `app/raffle/` (service layer) | Orchestrates state transitions; queries the chain for live raffle boxes; submits transactions |
| **Off-chain Bot / Poller** | Scheduler within service layer | Periodically scans the mempool and confirmed boxes; triggers deadline resolution, winner draws, and refund transactions |
| **REST Controllers** | `app/controllers/` | Exposes endpoints for creating raffles, retrieving active campaigns, submitting donations, and querying results |
| **Local DB** | `conf/application.conf` → DB config | Caches pending raffle creation requests and donation metadata before on-chain confirmation |

### Data Flow

1. **Create Raffle**: User submits campaign parameters via REST → `CreateReqUtils` assembles a *creation transaction* that mints a raffle ticket **Native token** and places the inaugural box (holding the Singleton / State NFT) at the `RaffleContract` address → submitted to the Ergo node.
2. **Donate**: Donor calls the donation endpoint → backend constructs a transaction spending the current raffle box and a donor input box, producing a new raffle box (updated `R4`–`R7` Registers: ticket count, accumulated ERG) and issuing ticket tokens back to the donor.
3. **Resolve**: The off-chain bot detects deadline passage → constructs either a *winner-selection transaction* (if funding goal met) using on-chain randomness from block headers, or a *refund transaction* dispersing ERG back to ticket holders.

---

## Smart Contracts

All contracts are written in **ErgoScript** and compiled to **ErgoTree** at runtime by `RaffleContract.scala`. The platform employs a **multi-stage contract** / **state machine** pattern with at least the following stages:

### 1. Raffle Creation Contract
- **Guard**: Ensures a valid raffle box is produced as output, correctly parameterized.
- **Registers used**:
  - `R4`: Fundraising goal (Long, in nanoERG)
  - `R5`: Deadline (block height as Long)
  - `R6`: Ticket price (nanoERG per ticket)
  - `R7`: Creator's payout address (SigmaProp / ErgoTree)
  - `R8`: Service fee numerator/denominator (project sustainability fee)
- **Token minting**: The creation transaction mints the raffle's ticket token under the **Token ID rule** (token ID = box ID of the first input); this token ID becomes the canonical identifier for the raffle.

### 2. Active Raffle Contract (Donation Stage)
- **Guard**: The core raffle box script. Enforces the **Invariant** that:
  - Each donation transaction produces exactly one continuing raffle box with updated ticket count.
  - The correct number of ticket tokens is sent to the donor.
  - The box value increases by exactly `ticketPrice × ticketsRequested`.
  - The deadline register is unchanged (immutable after creation).
- **Context extension / Data inputs**: Block height accessed via `ErgoScript context` (`HEIGHT`) for deadline enforcement.
- **Sigma protocols**: Spending the raffle box for winner payout requires satisfying the creator's stored `SigmaProp` or the contract's own resolution condition (deadline elapsed + quorum met).

### 3. Resolution / Winner Contract
- **Guard**: Activated after `HEIGHT > deadline`.
- **Winner selection**: Uses a hash of a recent block header (accessible as a **Data input** or via context) as a pseudo-random seed modulo the total ticket count — a common Ergo pattern for verifiable on-chain randomness without an oracle.
- **Paths**:
  - *Success*: Accumulated ERG ≥ goal → winner receives prize, service fee deducted, creator receives remainder.
  - *Failure*: ERG < goal → refund path; ticket holders can claim proportional ERG by presenting ticket tokens.

### 4. Refund Contract
- **Guard**: Validates that the spending transaction burns exactly the presented ticket tokens and returns the proportional ERG to the token holder's address.

> **Note**: Constant segregation is applied — script parameters (fee rates, service address) are embedded into the ErgoTree at compile time by