---
title: anon-real/ErgoAuctionHouse — Overview
description: Ergo Auction House — decentralized NFT auctions, bid assembly, EIP-22/24 patterns
tags: [anon-real, ergoauctionhouse, defi, javascript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/anon-real/ErgoAuctionHouse"
project: anon-real-ergoauctionhouse
group: defi
priority: medium
languages: [javascript]
contract_count: 0
pattern_match_count: 8
---
# Ergo Auction House — Developer Overview

---

## Overview

The **Ergo Auction House** (`anon-real/ErgoAuctionHouse`) is a fully decentralized NFT auction platform built on the Ergo blockchain, leveraging the eUTXO model to implement trustless, on-chain auctions without requiring a central order-book or custodian. Each auction is represented as a **Box** locked under an ErgoScript contract that encodes the auction rules — minimum bid, deadline, seller address, and current highest bidder — directly in **Registers** (R4–R7). The contract enforces bid progression and refund logic entirely at the protocol level, meaning no off-chain party can intercept or manipulate funds.

Within the Ergo DeFi ecosystem, the Auction House serves as the primary venue for trading **Native tokens** (primarily NFTs, which follow the **Token ID rule** — minted in a box whose token ID equals the box's creation transaction ID). It demonstrates how the eUTXO model enables stateful auction logic through **multi-stage contracts**: the auction box transitions through states (open → outbid → settled) with each spend, carrying state forward in registers and enforcing invariants purely through **ErgoScript context** evaluation. The project also implements **EIP-22** (Auction Contract standard) and **EIP-24** (NFT metadata standard), making it interoperable with other ecosystem tooling.

The frontend is a React single-page application that communicates with Ergo nodes and the **Assembler service** for transaction assembly. It supports both direct wallet signing (via **EIP-12** connector wallets such as Nautilus) and an assembler-based flow for users without a signing wallet, embodying the **headless dApp** philosophy where all contract logic is off-chain-constructible and wallet-agnostic.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (SPA)                    │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ ActiveAuction│  │  OwnedArtwork│  │  NewAuction       │ │
│  │  /Active     │  │  s           │  │  Assembler        │ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘ │
│         │                 │                   │             │
│  ┌──────▼─────────────────▼───────────────────▼──────────┐ │
│  │              Transaction Builder Layer                 │ │
│  │  placeBid.js │ newAuctionAssembler.js │ activeAuction  │ │
│  └──────┬──────────────────────────────────────┬─────────┘ │
└─────────┼──────────────────────────────────────┼───────────┘
          │                                      │
          ▼                                      ▼
  ┌───────────────┐                   ┌──────────────────────┐
  │  EIP-12       │                   │  Assembler Service   │
  │  Wallet       │                   │  (Transaction        │
  │  Connector    │                   │   Relay/Assembly)    │
  │  (Nautilus)   │                   └──────────┬───────────┘
  └───────┬───────┘                              │
          │                                      │
          └──────────────────┬───────────────────┘
                             ▼
                   ┌─────────────────┐
                   │   Ergo Node /   │
                   │  Explorer API   │
                   └─────────────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │  Ergo Blockchain│
                   │  (eUTXO Boxes)  │
                   │  Auction Boxes  │
                   │  R4–R7 State    │
                   └─────────────────┘
```

### Key Components

| Component | File(s) | Responsibility |
|---|---|---|
| **Active Auction UI** | `activeAuction.js`, `activeOther.js`, `showActives.js` | Fetches and renders live auction boxes from the chain; polls node/explorer for box state |
| **Bid Assembler** | `placeBid.js` | Constructs the bid transaction: spends the current auction box, creates a new auction box with updated highest-bid register, refunds prior bidder |
| **New Auction Assembler** | `newAuctionAssembler.js` | Constructs the auction-start transaction: locks the NFT + starting ERG into a new box under the auction ErgoTree |
| **Specific Auction View** | `specificAuction.js` | Deep-links to a single auction box by box ID; uses the box as a **Data input** candidate for inspection |
| **Owned Artworks** | `ownedArtworks.js` | Reads the user's wallet UTXOs, filters for EIP-24-compliant NFT boxes, presents them for listing |
| **Assembler Integration** | All `assembler`-patterned files | Submits partially-built transactions to the Assembler service when EIP-12 wallet is unavailable |

### Data Flow — Place Bid

```
User submits bid
      │
      ▼
placeBid.js queries Explorer API
  → fetches current auction Box (id, value, registers R4–R7)
      │
      ▼
Constructs unsigned Transaction:
  Input[0]: current auction box (ErgoTree = auction contract)
  Input[1]: bidder's ERG box(es)
  Output[0]: new auction box
    - value: new bid amount
    - R4: seller ErgoTree (preserved)
    - R5: min bid increment (preserved)
    - R6: auction deadline (preserved)
    - R7: new bidder address
  Output[1]: refund box → previous highest bidder
  Output[2]: change box → current bidder
      │
      ▼
Sign via EIP-12 wallet connector
  OR submit to Assembler service
      │
      ▼
Broadcast to Ergo node mempool
```

---

## Smart Contracts

The auction contracts follow **EIP-22** (Ergo Auction Contract specification) and are written in **ErgoScript**. The contract logic is embedded as an **ErgoTree** in the auction box's `propositionBytes`; the frontend holds the compiled ErgoTree bytes and uses them both to identify auction boxes on-chain and to construct valid spending transactions.

### Auction Box Contract (EIP-22)

**Registers used:**

| Register | Type | Content |
|---|---|---|
| `R4` | `SigmaProp` / `Coll[Byte]` | Seller's address (ErgoTree) — refund destination on auction end |
| `R5` | `Long` | Minimum bid / minimum bid increment in nanoERG |
| `R6` | `Int` | Auction end block height (deadline) |
| `R7` | `Coll[Byte]` | Current highest bidder's ErgoTree (updated on each bid) |

**Contract invariants enforced by ErgoScript:**

1. **Bid progression:** A spending transaction is valid only if `OUTPUTS(0).value >= SELF.value + R5` (new bid must exceed current by at least the minimum increment). This is a hard **invariant** enforced at the **ErgoScript context** level.

2. **Bidder refund:** The previous highest bidder (stored in `R7`) must receive a refund output of at least `SELF.value` in the same transaction. This eliminates the need for a separate claim step and prevents griefing.

3. **Register continuity (multi-stage contract):** On a bid-update spend, `R4`, `R5`, `R6` must be faithfully copied to `OUTPUTS(0)`, ensuring the seller, minimum bid, and