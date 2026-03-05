---
title: fleet-sdk/fleet-by-example — Overview
description: Fleet SDK worked examples — direct cookbook material for token minting, tx building
tags: [fleet-sdk, fleet-by-example, sdk, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/fleet-sdk/fleet-by-example"
project: fleet-sdk-fleet-by-example
group: sdk
priority: high
languages: [typescript]
contract_count: 0
pattern_match_count: 1
---
# fleet-sdk/fleet-by-example: Developer Overview

---

## Overview

`fleet-by-example` is the official cookbook repository for the Fleet SDK, providing TypeScript-based worked examples that demonstrate how to construct Ergo transactions and interact with the eUTXO model programmatically. It serves as a direct companion to the Fleet SDK core library, translating abstract SDK capabilities into concrete, runnable patterns that developers can adapt for production dApps. The repository is spiritually a port of the earlier `ergoscript-by-example` project, bringing its educational mission into the Fleet SDK ecosystem with a modern TypeScript toolchain.

Within the Ergo ecosystem, this project occupies the "learning and reference" layer between raw SDK documentation and full application codebases. Rather than shipping a deployable product, it ships *knowledge as executable code* — each example is a passing test that proves the pattern works against real Fleet SDK internals. This makes it an authoritative source of truth for transaction construction idioms, because examples cannot silently drift from SDK behaviour without breaking the test suite.

The project is particularly valuable for developers approaching Ergo's eUTXO model from a UTXO-naive or account-model background. Ergo's Box-centric design — where outputs carry value, Native tokens, Registers, an ErgoTree, and optionally a Context extension — requires a mental shift that worked examples communicate far more efficiently than prose documentation alone.

---

## Architecture

The repository is structured as a flat collection of test specifications, each encapsulating one self-contained scenario. There is no runtime application; the architecture is **test-as-documentation**.

```
fleet-by-example/
├── tests/
│   └── timedFundContract.spec.ts   # Example: time-locked funding box
├── package.json
└── tsconfig.json
```

**Key components and data flow:**

| Component | Role |
|---|---|
| `TransactionBuilder` | Assembles the full transaction — inputs, outputs, fee, change |
| `OutputBuilder` | Constructs individual output Boxes with value, tokens, Registers, and ErgoTree |
| Test runner (Jest/Vitest) | Executes each example as a passing assertion, enforcing correctness |
| Fleet SDK (`@fleet-sdk/core`) | Underlying library providing all builder primitives |

**Data flow within an example:**

```
ErgoScript contract (compiled ErgoTree)
        │
        ▼
OutputBuilder  ←── Registers (R4–R9), Native tokens, nanoERG value
        │
        ▼
TransactionBuilder ←── Input Boxes (eUTXOs), Data inputs, fee policy
        │
        ▼
Unsigned Transaction (serialised for signing / EIP-12 connector)
```

Each test constructs one or more `OutputBuilder` instances representing the desired post-transaction Box set, feeds them into a `TransactionBuilder` alongside the spending input Boxes, and asserts that the resulting unsigned transaction satisfies structural invariants (correct token balances, Minimum box value, Minimum transaction fee, change output correctness).

---

## Smart Contracts

The repository demonstrates interaction with ErgoScript contracts from the **off-chain perspective** — contracts are referenced as pre-compiled ErgoTree byte strings or as P2S (pay-to-script) addresses rather than being compiled inline. The on-chain contract logic is treated as a black box whose spending conditions must be satisfied by the transaction structure Fleet SDK assembles.

**Current contract example — Timed Fund Contract (`timedFundContract.spec.ts`):**

- **Purpose:** A time-locked funding Box that can only be spent after a specified block height, a common primitive for vesting, escrow, and crowdfunding patterns.
- **ErgoScript responsibility:** Guards the Box with a `HEIGHT` context check — the spending transaction is only valid when the blockchain height exceeds a threshold stored in a Register (typically `R4`).
- **Off-chain responsibility:** Correctly populating the Register with the unlock height at Box creation time, and later constructing a spending transaction that includes the correct `Context extension` or `Data input` if required.

No AVL tree, Ring signature, NiPoPoW, or Multi-stage contract patterns are present in the currently committed examples, but the architecture accommodates them — additional spec files would follow identical structural conventions.

---

## Integration Guide

### Installation

```bash
git clone https://github.com/fleet-sdk/fleet-by-example
cd fleet-by-example
npm install
npm run test
```

### Adapting an Example

Each test file is a self-contained integration pattern. To adapt `timedFundContract.spec.ts` for a real dApp:

**1. Build the locking transaction (deposit):**

```typescript
import { TransactionBuilder, OutputBuilder, RECOMMENDED_MIN_FEE_VALUE } from "@fleet-sdk/core";

const lockingTx = new TransactionBuilder(currentHeight)
  .from(inputBoxes)                        // eUTXO inputs from wallet
  .to(
    new OutputBuilder(lockAmountNanoErg, contractAddress)
      .setAdditionalRegisters({
        R4: SLong(unlockHeight)            // Encode unlock height into Register
      })
  )
  .sendChangeTo(changeAddress)
  .payMinFee()                             // Enforces Minimum transaction fee
  .build();
```

**2. Build the spending transaction (withdrawal after unlock):**

```typescript
const spendingTx = new TransactionBuilder(currentHeight)
  .from(lockedBox)                         // The time-locked Box as input
  .to(new OutputBuilder(lockAmountNanoErg, recipientAddress))
  .sendChangeTo(changeAddress)
  .payMinFee()
  .build();
// Submit only when currentHeight > unlockHeight (enforced by ErgoScript on-chain)
```

**3. EIP-12 Connector integration:**

The unsigned transaction produced by `.build()` is directly serialisable to the EIP-12 format expected by Nautilus Wallet and other dApp connectors. No additional transformation is required for standard wallet signing flows.

**Minimum box value:** Fleet SDK enforces the Minimum box value automatically when using `OutputBuilder`; examples demonstrate this invariant explicitly through assertions.

---

## Key Patterns

### 1. Headless dApp Construction
Examples demonstrate the **Headless dApp** pattern: all transaction logic lives off-chain in TypeScript, with no dependency on a running node's wallet. Input Boxes are sourced externally (from an indexer or Explorer API), transaction building is pure in-process computation, and the resulting unsigned transaction is handed off to any compatible signer. This makes the patterns suitable for server-side Off-chain bots as well as browser-based dApps.

### 2. OutputBuilder as Box Specification
Rather than manipulating raw byte arrays, each output Box is declared declaratively via `OutputBuilder`. This cleanly separates *what the Box should contain* (value, tokens, Registers, ErgoTree) from *how the transaction balances* (handled by `TransactionBuilder`). This mirrors the eUTXO model's own separation of concerns.

### 3. Register-Encoded Contract Parameters
Examples show the idiomatic pattern of encoding contract parameters — such as unlock heights, owner public keys, or token quantities — into Registers (`R4`–`R9`) at Box creation time. This is the standard Ergo approach to **Constant segregation**: the ErgoScript logic is generic, and instance-specific data lives in Registers rather than in the ErgoTree itself.

### 4. Test-as-Specification
Every pattern is expressed as a passing test, enforcing that the example represents a structurally valid unsigned transaction. This guards against documentation rot and doubles as a regression suite when Fleet SDK versions change.

### 5. Native Token Handling (Token ID Rule)
The timed fund pattern can be extended (and the architecture supports) demonstrating the **Token ID rule** — where a minted token's ID is derived from the ID of the first input Box in the minting transaction. Examples set up `OutputBuilder` with token emission to illustrate this first-input-box derivation pattern.

---

## Related Projects

| Project | Relationship |
|---|---|
| **`fleet-sdk/fleet`** (`@fleet-sdk/core`) | Direct runtime dependency; provides `TransactionBuilder`, `OutputBuilder`, serialisation, and all eUTXO primitives |
| **`ergoscript-by-example`** | Spiritual predecessor; original cookbook using AppKit/Scala. `fleet-by-example` ports its patterns to Type