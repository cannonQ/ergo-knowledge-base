---
title: StabilityNexus/Gluon-Ergo-UI — Overview
description: Gluon Gold stablecoin frontend — Next.js dApp with EIP-12 wallet connector, swap UI
tags: [stabilitynexus, gluon-ergo-ui, defi, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Gluon-Ergo-UI"
project: stabilitynexus-gluon-ergo-ui
group: defi
priority: low
languages: [typescript]
contract_count: 0
pattern_match_count: 3
---
# StabilityNexus/Gluon-Ergo-UI — Developer Overview

---

## Overview

Gluon-Ergo-UI is the frontend interface for the **Gluon Gold** stablecoin protocol deployed on Ergo — an autonomous, crypto-backed stablecoin system that uses ERG as collateral to mint two synthetic tokens: **GAU** (a gold-pegged stablecoin) and **GAUC** (a leveraged counterpart token). The application is built with **Next.js**, **TypeScript**, **Tailwind CSS**, **Shadcn UI**, and **Zustand**, and serves as the primary user-facing entry point for interacting with the Gluon smart contract system. It bridges the human interface layer to the underlying eUTXO-based protocol, abstracting away the complexity of Box selection, Registers, and Transaction construction behind an accessible swap UI.

Within the Ergo DeFi ecosystem, this project occupies the same conceptual niche as the SigmaUSD front-end or the Dexy UI: it is the dApp shell that wraps an on-chain multi-stage contract protocol. Unlike purely off-chain bots, this UI is designed for end users performing manual swaps — **fission** (ERG → GAU + GAUC), **fusion** (GAU + GAUC → ERG), and **transmutation** (GAU ↔ GAUC conversion via the Reactor). The application fetches live protocol state from the Ergo blockchain, reads oracle Box data (gold price feed), and constructs unsigned Transactions that are signed by an EIP-12-compatible browser wallet.

The project is intentionally structured as a **headless dApp** frontend: business logic (swap calculations, invariant checks, token validation) is separated from rendering concerns, and all on-chain interactions are delegated to the **Gluon Gold SDK**. This separation means the core protocol functions (`reactor/` utilities, token math) can be tested independently of the UI, as demonstrated by the 168-test suite covering conversion, error classification, and swap logic.

---

## Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                      Next.js Pages Layer                     │
│  index.tsx (Home)          dashboard.tsx (Dashboard)         │
│  _app.tsx (Providers: ErgoProvider, ThemeProvider)          │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
┌──────────────▼──────────┐  ┌────────────▼──────────────────┐
│  Layout Components       │  │  Block Components              │
│  - TopNavbar.tsx         │  │  - Dashboard stats/metrics     │
│  - Sidebar               │  │  - Home sections               │
└──────────────────────────┘  └────────────────────────────────┘
               │                          │
┌──────────────▼──────────────────────────▼───────────────────┐
│              Blockchain Components                           │
│  ┌─────────────────────────┐  ┌──────────────────────────┐  │
│  │  WalletConnector.tsx    │  │  ReactorSwap.tsx          │  │
│  │  (EIP-12 connector)     │  │  (fission/fusion/transm.) │  │
│  └────────────┬────────────┘  └────────────┬─────────────┘  │
└───────────────┼──────────────────────────── ┼───────────────┘
                │                             │
┌───────────────▼─────────────────────────────▼───────────────┐
│              Providers & State (Zustand / Context)           │
│  ErgoProvider — wallet state, connected address, balances    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Business Logic Layer (src/lib/functions)        │
│  reactor/utils.ts — token validation, swap action builders  │
│  reactor/ — fission, fusion, transmutation calculations     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Utility Layer (src/lib/utils)                   │
│  erg-converter.ts      — nanoERG ↔ ERG, K/M/B formatting    │
│  node-service.ts       — Ergo Node / Explorer API calls      │
│  transaction-listener.ts — Transaction confirmation polling  │
│  error-handler.ts      — error classification & UX messages  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              External Dependencies                           │
│  Gluon Gold SDK        — GluonBox, OracleBox, TX builders   │
│  EIP-12 Wallet         — ergoConnector (Nautilus, etc.)     │
│  CoinGecko API         — ERG/USD price feed                 │
│  Ergo Node / Explorer  — Box queries, TX submission         │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **On mount**: `ErgoProvider` detects an injected `window.ergoConnector` (EIP-12), requests wallet access, and fetches the connected address and token balances (GAU, GAUC, ERG) from the node.
2. **Protocol state polling**: Every 5 minutes, `node-service.ts` queries the Ergo Node for the **Gluon singleton Box** (identified by its State NFT / Token ID) and the **Gold Oracle Box** (Data input). These Boxes are passed to the Gluon SDK to compute current reserve ratios, swap rates, and protocol fees.
3. **Swap construction**: When a user initiates a swap in `ReactorSwap.tsx`, the reactor business logic validates token amounts, applies the protocol invariant, and invokes the Gluon SDK to construct an unsigned Transaction referencing the Gluon Box (as an input Box) and the Oracle Box (as a Data input). The Transaction includes the user's input Boxes and output Boxes with correct Minimum box value and Minimum transaction fee.
4. **Signing & submission**: The unsigned Transaction is passed to `window.ergoConnector` via EIP-12's `ergo.sign_tx()`. The signed Transaction is submitted to the Ergo Node via `node-service.ts`.
5. **Confirmation monitoring**: `transaction-listener.ts` polls the node or Explorer for Transaction inclusion, updating UI state on confirmation.

### State Management

- **Zustand**: Lightweight stores for wallet state (address, balances), protocol metrics (reserve ratio, GAU/GAUC prices), and UI state (selected swap mode, loading flags).
- **React Context** (`ErgoProvider`, `ThemeProvider`): Provider-level state for wallet connectivity and theming, available application-wide.
- **No Redux**: Intentional — the protocol interaction surface is narrow enough that Zustand stores per domain are sufficient.

---

## Smart Contracts

The Gluon-Ergo-UI does not contain ErgoScript source code directly — contract logic is owned by the Gluon Gold protocol and exposed through the **Gluon Gold SDK**. However, the UI is architected around the following on-chain contract responsibilities:

### Gluon Box (Singleton / State NFT)

The central multi-stage contract Box identified by a **Singleton NFT** (State NFT) whose Token ID is stored in `src/lib/constants/`. This Box holds:
- The ERG collateral reserve.
- The outstanding supply of GAU (gold-pegged stablecoin, Native token) and GAUC (leveraged token, Native token) tracked via Registers (`R4`–`R7`).
- The ErgoScript invariant that enforces correct reserve ratios during fission, fusion