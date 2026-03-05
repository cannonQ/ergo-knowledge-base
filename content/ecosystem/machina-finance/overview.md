---
title: nautls/machina-finance — Overview
description: Machina Finance — off-chain bot platform, settings contract, order execution framework
tags: [nautls, machina-finance, defi, ergoscript, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/nautls/machina-finance"
project: nautls-machina-finance
group: defi
priority: medium
languages: [ergoscript, typescript]
contract_count: 1
pattern_match_count: 3
---
# nautls/machina-finance — Developer Overview

---

## Overview

Machina Finance is an off-chain bot platform and order execution framework built on the Ergo blockchain, designed to enable decentralized, non-custodial order matching within the eUTXO model. The project provides the foundational infrastructure for limit orders and swap routing — combining on-chain ErgoScript contracts that enforce protocol invariants with off-chain TypeScript bots that discover, match, and submit valid spending transactions. Rather than relying on an on-chain automated market maker loop, Machina Finance separates concerns cleanly: contracts define what is valid, and off-chain bots define what is profitable or timely to execute.

Within the Ergo ecosystem, Machina Finance occupies the role of a **headless dApp** execution layer — the contracts expose pure validation logic with no embedded UI or oracle dependency hardcoded into the ErgoTree itself. Protocol parameters (fees, thresholds, version identifiers) are instead stored in a dedicated Settings singleton box, which order contracts reference as a **data input** at execution time. This design allows the execution environment to be reconfigured through governance without redeploying order contracts, and it keeps individual order boxes lightweight and composable.

The project is grouped under DeFi and targets the growing need for permissionless, bot-driven order execution on Ergo — analogous in intent to off-chain relayers in other ecosystems, but architecturally native to eUTXO semantics. By leveraging Ergo's data input mechanism, storage rent economics, and the Singleton / State NFT pattern, Machina Finance demonstrates a production-grade approach to multi-stage contract composition and off-chain automation.

---

## Architecture

Machina Finance is structured as a monorepo with at least two primary packages: `packages/contracts` (ErgoScript source files, TypeScript box/transaction object models, and contract tests) and the off-chain bot layer (TypeScript). The data flow follows a clear pipeline:

```
[User / Frontend]
       │
       ▼
[Order Box created on-chain]
  (ErgoScript order contract, user-signed)
       │
       ▼
[Off-chain Bot]
  - Scans UTXO set for open order boxes
  - Fetches Settings box as data input
  - Constructs matching transaction (TransactionBuilder)
  - Submits to Ergo node / mempool
       │
       ▼
[Execution Transaction]
  Inputs:  Order Box(es)
  Data Inputs: Settings Box (read-only)
  Outputs: Filled order recipient boxes, fee box, change
```

**Key Components:**

| Component | Location | Responsibility |
|---|---|---|
| `Settings.es` | `packages/contracts/src/contracts/` | Immutable protocol configuration singleton (data input only) |
| Box Objects | `packages/contracts/src/box-objects.ts` | TypeScript representations of on-chain box schemas |
| Transaction Objects | `packages/contracts/src/transaction-objects.ts` | `TransactionBuilder` wrappers for constructing valid spending transactions |
| Contract Tests | `packages/contracts/tests/spendSettings.test.ts` | Validation of contract behavior against the Ergo execution model |
| Off-chain Bot | Top-level TypeScript | UTXO scanning, order matching logic, transaction submission |

The `box-objects.ts` module defines typed interfaces that mirror the register layout of each on-chain box type, ensuring the off-chain layer and on-chain contracts share a consistent schema. The `TransactionBuilder` in `transaction-objects.ts` assembles inputs, data inputs, outputs, and context extensions into well-formed transactions before signing and submission.

---

## Smart Contracts

### `Settings.es`

**Language:** ErgoScript  
**Pattern:** Read-only Singleton / State NFT

The Settings contract is the protocol's immutable configuration anchor. Its entire validation guard is:

```ergoscript
sigmaProp(false)
```

This **impossible spending condition** means the box can never be consumed as a regular transaction input — it is permanently locked on-chain and accessible only as a **data input**. This is a deliberate application of the read-only state machine pattern in eUTXO: the box carries authoritative protocol parameters in its Registers, and any contract that needs those parameters declares the Settings box as a data input in its spending transaction.

**Register Layout (inferred from integration context):**

| Register | Expected Type | Purpose |
|---|---|---|
| R4 | `Long` | Execution fee amount or fee basis points |
| R5 | `Long` | Minimum order size or timeout block height |
| R6–R9 | TBD | Reserved for governance parameters, oracle addresses, or protocol version |

**Singleton enforcement:** The Settings box is expected to carry a **State NFT** (a token with a unique Token ID derived from its creation transaction outbox index) in its `tokens` field. Order contracts reference this NFT's Token ID to guarantee they are reading from the canonical settings box and not a spoofed lookalike.

**Upgrade path:** When governance is introduced, a multi-stage contract will validate the atomic replacement of the current Settings box with a new one — spending the State NFT from the old box and reissuing it into the new one in a single transaction, preserving the invariant that exactly one authoritative settings box exists at all times.

**Order Contracts (referenced, not yet detailed):**

Order execution contracts (e.g., limit order contracts) are the primary consumers of the Settings box. They follow this data input access pattern:

```ergoscript
val settings    = CONTEXT.dataInputs(0)
val executionFee = settings.R4[Long].get
// ... enforce that outputs satisfy fee and order invariants
```

The order contract's ErgoTree encodes the user's swap intent (token pair, price, expiry) and delegates parameter lookup to the Settings singleton at execution time.

---

## Integration Guide

### Deploying the Settings Box

The Settings box must be initialized once by the protocol deployer:

1. Construct a box with `Settings.es` compiled to its ErgoTree.
2. Mint a State NFT (singleton token) and include it in the box's `tokens` field. The Token ID must be recorded and hardcoded or distributed to all downstream contracts and bots.
3. Populate R4–R9 with the initial protocol parameters (encoded as `Long`, `Coll[Byte]`, or appropriate types).
4. Submit as a standard transaction. After confirmation, this box is permanently immutable under the `sigmaProp(false)` guard.

### Off-chain Bot Integration Pattern

```typescript
import { TransactionBuilder } from './transaction-objects';
import { SettingsBox, OrderBox } from './box-objects';

// 1. Fetch the Settings box by its State NFT Token ID
const settingsBox: SettingsBox = await explorer.getBoxByTokenId(SETTINGS_NFT_ID);

// 2. Scan the UTXO set for open order boxes
const openOrders: OrderBox[] = await explorer.getBoxesByErgoTree(ORDER_ERGOTREE);

// 3. Select a matching pair (e.g., two complementary limit orders)
const [makerOrder, takerOrder] = matchOrders(openOrders);

// 4. Build the execution transaction
const tx = new TransactionBuilder()
  .addInput(makerOrder)
  .addInput(takerOrder)
  .addDataInput(settingsBox)       // Settings referenced read-only
  .addOutput(filledMakerOutput)
  .addOutput(filledTakerOutput)
  .addOutput(feeBox)
  .build();

// 5. Sign (bot's key covers execution fee box) and submit
const signedTx = await wallet.sign(tx);
await node.submitTransaction(signedTx);
```

**Key integration rules:**
- The Settings box **must** appear in `CONTEXT.dataInputs`, not `CONTEXT.inputs`. Passing it as a regular input will cause validation failure due to `sigmaProp(false)`.
- Always verify the Settings box contains the expected State NFT Token ID before trusting its register contents.
- Respect the **Minimum box value** for all output boxes (currently 0.001 ERG) and the **Minimum transaction fee** enforced by the Ergo network.
- Bot operators must account for **storage rent**: order boxes that remain unmatched for ~4 years may be reclaimed by miners. The off-chain bot should monitor box