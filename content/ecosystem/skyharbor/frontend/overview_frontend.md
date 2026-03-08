---
title: ergo-pad/nft-market — Overview
description: ErgoPad NFT marketplace frontend — MUI + Next.js template, EIP-22/24 patterns
tags: [ergo-pad, nft-market, analytics, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergo-pad/nft-market"
project: ergo-pad-nft-market
group: analytics
priority: medium
languages: [typescript]
contract_count: 0
pattern_match_count: 1
---
# ergo-pad/nft-market — Developer Overview

---

## Overview

**ergo-pad/nft-market** is the frontend application powering the ErgoPad NFT marketplace, built on top of a Next.js + MUI (Material UI) TypeScript template. The application provides a user-facing interface for browsing, listing, buying, and selling NFTs minted on the Ergo blockchain, where NFTs are represented as **Native tokens** following the **Token ID rule** — each token is uniquely identified by the Box ID of the minting transaction's first input. The frontend is purpose-built for the eUTXO model, where every NFT and its associated metadata live inside **Boxes** with data stored in **Registers** (R4–R9).

Within the broader Ergo ecosystem, this project serves as the presentation and interaction layer for NFT marketplace smart contracts. It bridges end-users and the on-chain eUTXO state by constructing, assembling, and submitting unsigned **Transactions** via an EIP-12-compatible wallet connector. The marketplace conforms to **EIP-22** (Auction Contract) and **EIP-24** (NFT Collection Standard) patterns, ensuring NFT metadata, royalty information, and collection membership are encoded in a standardized, interoperable way that other Ergo tooling can consume.

As part of ErgoPad's analytics group, this project also plays a role in surfacing on-chain data — collection floor prices, trading volume, individual token provenance — by querying indexed node data or explorer APIs and rendering it through a cohesive React component hierarchy. The architecture is explicitly headless-friendly: the UI layer is decoupled from transaction construction logic, making it straightforward to adapt the off-chain interaction patterns for bots or alternative frontends.

---

## Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────┐
│                   Next.js App (pages/)               │
│  ┌──────────┐  ┌────────────┐  ┌─────────────────┐  │
│  │ /market  │  │ /collection│  │ /token/[tokenId]│  │
│  └────┬─────┘  └─────┬──────┘  └────────┬────────┘  │
│       └──────────────┴──────────────────┘            │
│                       │                              │
│            ┌──────────▼──────────┐                   │
│            │   React Components  │                   │
│            │   (MUI + custom)    │                   │
│            └──────────┬──────────┘                   │
└───────────────────────┼─────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────────┐
│  EIP-12      │ │  Explorer /  │ │  API Routes    │
│  Connector   │ │  Node API    │ │  (pages/api/)  │
│  (ergoConnec-│ │  (off-chain  │ │  (BFF / proxy) │
│   tor global)│ │   queries)   │ │                │
└───────┬──────┘ └──────┬──────┘ └─────┬──────────┘
        │               │               │
        ▼               ▼               ▼
  Wallet / dApp    Ergo Explorer    Internal Cache /
  (Nautilus, etc.) Indexer REST     Analytics Store
```

### Key Layers

| Layer | Technology | Responsibility |
|---|---|---|
| **Pages** | Next.js `pages/` | Route definitions, SSR/SSG data fetching, page-level layout |
| **Components** | MUI + custom TSX | Rendering NFT cards, auction timers, wallet state, collection grids |
| **Theme** | `theme.ts` | Single-source MUI theme with dark/light palette; token colors map to UI states |
| **Wallet Integration** | EIP-12 / `ergoConnector` | Accessing wallet Boxes, signing transactions, reading connected address |
| **API Routes** | `pages/api/` | Backend-for-frontend: proxying explorer calls, aggregating collection analytics |
| **Path Aliases** | `tsconfig.json` path definitions | Eliminates relative import spaghetti; enforces module boundaries |
| **Animations** | Framer Motion | Full-page transitions and component-level enter/exit animations |

### Data Flow

1. **Page load**: Next.js performs SSR or SSG, fetching collection metadata and Box states from the Ergo Explorer REST API. EIP-24 collection data (stored in **R4–R7** of NFT Boxes) is decoded and passed as props.
2. **Wallet connection**: The `ergoConnector` global (injected by EIP-12-compatible wallets such as Nautilus) is detected on `window.ergoConnector`. On approval, the dApp receives read access to the user's UTxO set and change address.
3. **Transaction construction**: When a user lists or purchases an NFT, the frontend reads relevant **Boxes** (the NFT box, any auction contract box) and constructs an unsigned `Transaction` object conforming to the marketplace contract's spending conditions. This unsigned transaction is handed to the wallet for signing via EIP-12.
4. **Submission**: The signed transaction is broadcast through the wallet or directly to a node API endpoint.
5. **State refresh**: After broadcast, the UI polls the Explorer or listens for confirmation before updating the displayed Box state.

---

## Smart Contracts

> **Note**: The README and source tree for this repository describe a frontend template; on-chain ErgoScript contract source is not co-located in this repository. The contracts are referenced by address and interacted with through transaction construction in the off-chain layer. The following describes the expected contract responsibilities based on the EIP-22/EIP-24 patterns the project explicitly targets.

### EIP-22 — Auction Contract

EIP-22 defines a standard **multi-stage contract** for NFT auctions on Ergo. The auction Box holds:

- **Value**: Current highest bid (in nanoERG, respecting **Minimum box value** constraints).
- **R4**: Seller's public key (`SigmaProp`).
- **R5**: Bid step (minimum increment).
- **R6**: Auction end height (absolute block height).
- **R7**: Bidder's public key (`SigmaProp`) — updated on each bid.
- **Tokens[0]**: The auctioned NFT (Native token).

The **ErgoScript** spending condition enforces the auction **invariant**: a bid transaction must produce a new auction Box with an increased value, updated R7, and the same NFT token. The seller can collect funds only after the end height. The frontend constructs bid and finalize transactions that satisfy these **ErgoTree** spending paths.

### EIP-24 — NFT Collection Standard

EIP-24 governs how NFT collection membership and per-token metadata are encoded in **Registers**:

| Register | Content |
|---|---|
| R4 | NFT name (UTF-8 `Coll[Byte]`) |
| R5 | NFT description |
| R6 | Media SHA-256 hash |
| R7 | Royalty recipient and percentage |
| R8 | Collection issuer Box ID (links token to collection via **Singleton / State NFT** pattern) |
| R9 | Additional traits / properties |

The frontend decodes these registers client-side when rendering token detail pages, using the Ergo Explorer API to fetch the minting Box's register values. The **Token ID rule** is used to verify authenticity: the token ID must equal the Box ID of the first input in the minting transaction.

### Direct Sale Contract

In addition to auction mechanics, a fixed-price sale contract is expected in the marketplace. This contract holds the NFT in a Box guarded by an ErgoScript that releases the token to a buyer who provides the exact ERG price to the seller's address in the same transaction — a form of **Atomic swap** enforced at the contract level, requiring no trusted intermediary.