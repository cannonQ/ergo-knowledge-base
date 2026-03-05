---
title: capt-nemo429/sigmafi-ui — Overview
description: SigmaFi UI — P2P bonds/lending frontend, Fleet SDK plugins for bond transactions
tags: [capt-nemo429, sigmafi-ui, defi, typescript, vue]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/capt-nemo429/sigmafi-ui"
project: capt-nemo429-sigmafi-ui
group: defi
priority: medium
languages: [typescript, vue]
contract_count: 0
pattern_match_count: 3
---
# SigmaFi UI — Developer Overview

---

## Overview

SigmaFi UI is the frontend application for the SigmaFinance protocol, a peer-to-peer bond and lending platform built on the Ergo blockchain. The protocol enables trustless, collateralized lending by encoding loan terms — maturity dates, interest rates, repayment obligations, and collateral ratios — directly into eUTXO boxes governed by ErgoScript contracts. Borrowers lock collateral into contract-controlled boxes while lenders fund bonds by satisfying spending conditions, creating a fully non-custodial credit market without relying on any central intermediary or liquidity pool.

Within the Ergo DeFi ecosystem, SigmaFi occupies a distinct niche as a fixed-term, fixed-rate bond instrument rather than a dynamic AMM or order-book exchange. This design leverages Ergo's eUTXO model naturally: each bond is a self-contained box carrying all necessary state in its Registers, and the lifecycle of a bond (creation → funding → repayment or liquidation) maps cleanly onto a sequence of transactions that progress the box through a multi-stage contract state machine. The immutable, inspectable nature of eUTXO boxes makes the protocol's state fully auditable without requiring a trusted oracle of internal mutable state.

The UI layer is implemented as a Vue/TypeScript single-page application that communicates with the Ergo blockchain through Fleet SDK plugins and EIP-12 compliant wallet connectors. It abstracts the complexity of box selection, transaction construction, and context extension assembly behind user-facing bond management workflows, while keeping all signing operations client-side in the user's connected wallet.

---

## Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                        Vue SPA (UI Layer)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Bond Views  │  │ Wallet Store │  │  Story / Dev Env  │  │
│  │ (Create,    │  │ (EIP-12      │  │  (walletStore.ts  │  │
│  │  Fund,      │  │  Connector)  │  │   mock harness)   │  │
│  │  Repay,     │  └──────┬───────┘  └───────────────────┘  │
│  │  Liquidate) │         │                                  │
│  └──────┬──────┘         │                                  │
│         │                │                                  │
│  ┌──────▼────────────────▼──────────────────────────────┐  │
│  │              Off-Chain Layer                          │  │
│  │  ┌─────────────────┐    ┌───────────────────────┐    │  │
│  │  │  plugins.ts      │    │  utils/index.ts        │    │  │
│  │  │  (Fleet Plugins) │    │  (bondUtils helpers)   │    │  │
│  │  └────────┬─────────┘    └───────────────────────┘    │  │
│  └───────────┼───────────────────────────────────────────┘  │
└─────────────-┼───────────────────────────────────────────── ┘
               │
┌──────────────▼───────────────────────────────────────────── ┐
│                    Fleet SDK                                 │
│  Transaction Builder │ Box Selector │ ErgoTree encoding      │
└──────────────────────┬───────────────────────────────────── ┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Ergo Node / Explorer API                    │
│         (Box fetching, TX submission, mempool)               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| File/Module | Responsibility |
|---|---|
| `src/offchain/plugins.ts` | Fleet SDK `FleetPlugin` implementations that encapsulate bond transaction construction logic |
| `src/stories/walletStore.ts` | EIP-12 wallet connector abstraction; manages connection lifecycle and exposes signing context |
| `src/utils/index.ts` | `bondUtils` — pure helper functions for computing bond parameters (interest, maturity epochs, minimum box value constraints) |
| Vue Views/Components | Reactive UI bound to wallet and bond state; drives transaction submission flows |

### Data Flow

1. **User action** (e.g., "Create Bond") triggers a Vue component method.
2. **walletStore** resolves the connected EIP-12 wallet context (address, UTXOs, signing capability).
3. A **Fleet Plugin** (`plugins.ts`) is instantiated with bond parameters; it performs box selection, constructs the unsigned `Transaction` with correct output boxes, Registers, and ErgoTree, and applies context extensions where needed.
4. The unsigned transaction is passed to the wallet via the EIP-12 `ergoConnector` interface for user approval and signing.
5. The signed transaction is submitted to an Ergo node or public API endpoint; the UI reflects the new bond state optimistically.

---

## Smart Contracts

SigmaFi UI is a frontend client for the **SigmaFinance** ErgoScript contracts. While the contract source lives in a separate repository, the UI encodes knowledge of contract behavior through its off-chain plugins.

### Contract Roles (inferred from off-chain layer)

**Bond Contract (Multi-Stage)**

The core SigmaFi contract is a multi-stage contract governing the full bond lifecycle:

```
[Open / Unfunded Box]
    Registers:
      R4: Borrower PK (SigmaProp)
      R5: Repayment amount (Long, in nanoERG or token units)
      R6: Maturity height (Int, absolute block height)
      R7: Interest rate / collateral token ID
      R8: Loan principal amount

    ErgoTree enforces:
      - Only lender satisfying funding conditions can transition to Funded
      - Collateral box value ≥ Minimum box value + collateral threshold

[Funded / Active Box]
    - Borrower can repay before maturity height → releases collateral
    - After maturity height, lender can liquidate → claims collateral box

[Repaid / Liquidated]
    - Terminal states; boxes are consumed with value routed to correct party
```

**Invariants upheld by ErgoScript:**
- The State NFT (Singleton token) or bond ID token enforces uniqueness of each bond box, preventing double-spend replay across the multi-stage state machine.
- Storage rent pressure is mitigated by ensuring all output boxes carry sufficient nanoERG (Minimum box value enforced in off-chain plugin logic via `bondUtils`).
- Sigma protocols (standard `proveDlog`) secure borrower and lender authorization without requiring custom cryptographic primitives.

> **Note:** Developers integrating at the contract level should inspect the upstream SigmaFinance contract repository for the full ErgoScript source, ErgoTree encoding, and context variable assignments.

---

## Integration Guide

### Prerequisites

- Node.js ≥ 18, Vue 3, TypeScript
- Fleet SDK (`@fleet-sdk/core`, `@fleet-sdk/common`)
- An EIP-12 compatible wallet (Nautilus, SAFEW, etc.) injecting `window.ergoConnector`

### Connecting a Wallet

```typescript
// src/stories/walletStore.ts pattern
import { ref } from 'vue';

const connected = ref(false);
const walletApi = ref<EIP12WalletAPI | null>(null);

async function connect() {
  if (typeof ergoConnector === 'undefined') throw new Error('No EIP-12 wallet found');
  const granted = await ergoConnector.nautilus.connect();
  if (granted) {
    walletApi.value = await ergoConnector.nautilus.getContext();
    connected.value = true;
  }
}
```

### Using Fleet Plugins for Bond Transactions

The `FleetPlugin