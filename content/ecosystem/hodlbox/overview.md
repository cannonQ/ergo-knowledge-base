---
title: c8e4/hodlbox — Overview
description: HodlBox — time-locked box dApp demonstrating HEIGHT-based contract guards on Ergo
tags: [c8e4, hodlbox, defi, typescript, svelte]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/c8e4/hodlbox"
project: c8e4-hodlbox
group: defi
priority: low
languages: [typescript, svelte]
contract_count: 0
pattern_match_count: 0
---
# HodlBox — Developer Overview

---

## Overview

HodlBox is a time-locking decentralized application (dApp) built on the Ergo blockchain that demonstrates HEIGHT-based contract guards — one of the most fundamental and powerful primitives available in ErgoScript. The core concept is simple: a user deposits ERG (or Native tokens) into a Box that is guarded by an ErgoScript condition requiring the spending Transaction to be included in a block at or above a specified block height. Until that height is reached, the funds are cryptographically locked and provably unspendable by anyone, including the original depositor. This makes HodlBox a clean, minimal reference implementation of time-locked custody entirely enforced on-chain with no trusted intermediary.

Within the Ergo ecosystem, HodlBox serves as both a practical utility and an educational reference. The eUTXO model on Ergo means that spending conditions are expressed entirely within the ErgoTree of the Box itself, and context values such as `HEIGHT` are first-class citizens of the ErgoScript context — available to any contract without oracles or off-chain coordination. HodlBox exploits this directly, encoding the unlock height into the contract at creation time (constant segregation is possible here to make the ErgoTree reusable across many instances). This positions the project as a canonical demonstration of how Ergo's context-aware scripts replace the need for timestamp oracles or timelocked multisigs common on account-based chains.

From a DeFi perspective, HEIGHT-based locking is a foundational building block used in more complex Multi-stage contracts, Atomic swaps, vesting schedules, and governance escrow systems across the ecosystem. HodlBox distills this primitive into a standalone, user-facing dApp with a SvelteKit frontend and TypeScript off-chain logic, making it approachable for developers seeking to understand how on-chain guards, off-chain transaction construction, and wallet connector integrations fit together on Ergo.

---

## Architecture

HodlBox follows a **Headless dApp** layered architecture, separating pure ErgoScript contract logic from off-chain transaction building and the user-facing Svelte frontend.

```
┌─────────────────────────────────────────┐
│            SvelteKit Frontend           │
│  (UI state, wallet connection, UX flow) │
└────────────────────┬────────────────────┘
                     │ calls
┌────────────────────▼────────────────────┐
│         Off-chain Transaction Layer     │
│  (TypeScript: box selection, tx build,  │
│   register encoding, fee handling)      │
└────────────────────┬────────────────────┘
                     │ submits via
┌────────────────────▼────────────────────┐
│       EIP-12 Wallet Connector           │
│  (Nautilus or compatible injected API)  │
└────────────────────┬────────────────────┘
                     │ broadcasts to
┌────────────────────▼────────────────────┐
│         Ergo Node / Explorer API        │
│  (UTXO indexing, mempool, chain data)   │
└─────────────────────────────────────────┘
```

**Key Components:**

| Component | Role |
|---|---|
| **ErgoScript Contract** | Encodes the HEIGHT guard and owner's spending key; compiled to an ErgoTree and embedded in the lock Box |
| **Lock Transaction Builder** | Constructs the Transaction that moves ERG from the user's wallet into the HodlBox output Box, encoding the target height and owner `SigmaProp` into Registers |
| **Unlock Transaction Builder** | Validates that current HEIGHT ≥ unlock height off-chain before building and submitting the spending Transaction |
| **SvelteKit UI** | Manages wallet state, user input (unlock height, amount), and transaction status feedback |
| **EIP-12 Connector** | Bridges the TypeScript transaction builder to the user's browser wallet for signing and broadcasting |

**Data Flow:**

1. User specifies an amount and target unlock height in the UI.
2. The off-chain layer reads the user's `SigmaProp` (public key) from the connected wallet.
3. A lock Transaction is constructed: one output Box whose ErgoTree encodes `HEIGHT >= unlockHeight && proveDlog(ownerPK)`, with the target height optionally stored in a Register (e.g., `R4`) for indexing/display purposes.
4. The Transaction is passed to the EIP-12 wallet for signing and broadcast.
5. On unlock, the off-chain layer queries the current chain height, finds the HodlBox UTXO, and constructs a spending Transaction. The ErgoScript context automatically supplies `HEIGHT` for validation by nodes.

---

## Smart Contracts

### HodlBox Lock Contract

The core ErgoScript contract enforces two invariants simultaneously:

```scala
// Pseudocode representation of the ErgoScript guard
sigmaProp(
  HEIGHT >= unlockHeight &&    // Block-height-based time lock
  proveDlog(ownerPK)           // Owner's Sigma protocol key guard
)
```

**Responsibilities:**

- **HEIGHT Guard:** Uses the `HEIGHT` value injected by the ErgoScript context (the block height at which the spending Transaction is included). This is not an oracle — it is a native context variable guaranteed by every validating node. The unlock height is either hardcoded into the ErgoTree at compile time or read from a Register of the Box (e.g., `R4.get[Int]`).
- **Owner Authentication:** The `proveDlog(ownerPK)` clause enforces that only the holder of the private key corresponding to `ownerPK` can spend the Box after the height condition is met. This is a standard Sigma protocol proving discrete logarithm knowledge — no multisig or threshold is required for the basic case.
- **Logical Conjunction:** Both conditions must hold simultaneously. The `&&` inside `sigmaProp` means both the contextual height check and the cryptographic proof must be satisfied in the same Transaction. Neither alone is sufficient.

**Register Usage:**

| Register | Type | Contents |
|---|---|---|
| `R4` | `Int` | Target unlock block height (for off-chain indexing and UI display) |
| `R5` | `SigmaProp` | Owner's public key / `proveDlog` value |

**ErgoTree Considerations:**

- If the unlock height is a constant embedded at compile time, each distinct height produces a distinct ErgoTree and Box address — a natural consequence of constant segregation in ErgoScript compilation.
- Alternatively, storing the height in `R4` and referencing it via `SELF.R4[Int].get` in the script allows a single canonical ErgoTree (and thus a single contract address) to serve all HodlBox instances, making UTXO indexing by address straightforward.
- The Minimum box value constraint (currently ~0.001 ERG) applies to all outputs; the off-chain layer must account for this and the Minimum transaction fee when constructing Transactions.
- **Storage rent** (a fee levied after ~4 years on unspent Boxes) is relevant for very long lock periods; the locked Box must contain sufficient ERG to avoid reclamation by miners under the storage rent mechanism.

---

## Integration Guide

### Prerequisites

- Node.js 18+ with `npm` or `pnpm`
- A browser wallet supporting **EIP-12** (e.g., Nautilus Wallet)
- Access to an Ergo node or public Explorer/API endpoint

### Setup

```bash
git clone https://github.com/c8e4/hodlbox
cd hodlbox
npm install
npm run dev
```

### Off-chain Transaction Construction Pattern

HodlBox uses the **Fleet SDK** (TypeScript) pattern common in the Ergo ecosystem for off-chain transaction building:

```typescript
import { ErgoAddress, OutputBuilder, TransactionBuilder, SConstant, SInt, SSigmaProp } from "@fleet-sdk/core";

// 1. Compile or reference the pre-compiled ErgoTree for the HodlBox contract
const hodlBoxErgoTree = "..."; // compiled ErgoScript

// 2. Build the lock output Box
const lockOutput = new OutputBuilder(
  amountInNanoErg,
  hodlBoxErgoTree
)
  .setAdditionalRegisters({
    R4: SConst
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
