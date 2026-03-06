---
title: "The Extended UTXO Model"
description: "How Ergo extends Bitcoin's UTXO model with registers, guarding scripts, data inputs, and context variables — enabling expressive smart contracts without an accounts model."
tags: [eutxo, utxo, boxes, transactions, data-inputs, context, concepts]
category: concept
difficulty: beginner
sdk: [none]
updated: 2026-03-05
source: original
---

# The Extended UTXO Model

## What Is the UTXO Model?

Bitcoin introduced the UTXO (Unspent Transaction Output) model: instead of tracking account balances, the blockchain tracks individual "coins" — outputs of previous transactions that haven't been spent yet. A transaction consumes one or more existing UTXOs as **inputs** and creates new UTXOs as **outputs**. The old UTXOs are destroyed; the new ones exist until they too are spent.

Think of it like physical cash. You don't have a "balance" — you have specific bills in your wallet. To pay someone, you hand over bills (inputs) and receive change back (outputs). The bills you handed over no longer exist in your wallet.

Bitcoin's UTXOs are simple: they hold a value (satoshis) and a locking script (who can spend them). Ergo takes this model and extends it dramatically.

## How Ergo Extends It

Ergo's UTXOs are called **boxes**. A box is a container that holds:

- **Value** — an amount of ERG (in nanoERGs)
- **Tokens** — up to 255 additional native assets (NFTs, fungible tokens)
- **Registers** — six general-purpose typed data slots (R4 through R9) for storing arbitrary application state
- **Guarding script** — an ErgoScript program that defines the conditions under which this box can be spent
- **Creation info** — the transaction ID and output index that created this box, plus the block height

This is what makes it an **extended** UTXO model. A Bitcoin UTXO says "only this public key can spend me." An Ergo box says "here is a rich program with access to the full transaction context, my own stored data, and read-only access to other boxes on the chain — evaluate it, and only spend me if it returns true."

## The Transaction Model

An Ergo transaction has three collections:

```
Transaction
├── INPUTS        — boxes being spent (consumed and destroyed)
├── DATA INPUTS   — boxes being read (not consumed, not destroyed)
└── OUTPUTS       — new boxes being created
```

**Inputs** are boxes whose guarding scripts must all evaluate to `true` for the transaction to be valid. Once spent, these boxes cease to exist.

**Data inputs** are boxes that are referenced read-only. Their guarding scripts are NOT evaluated — they simply provide data to the transaction. This is one of Ergo's key innovations. An oracle can publish a price feed in a box, and any contract can read that price via data inputs without needing the oracle's permission or paying the oracle anything. The oracle box stays unspent.

**Outputs** are the new boxes created by the transaction. The total ERG value of outputs (plus the transaction fee) must equal the total ERG value of inputs. Tokens must also be preserved (except for minting new tokens, where the new token ID equals the first input's box ID).

## Context: What a Contract Can See

When an ErgoScript contract executes, it has access to the full transaction context through global variables:

| Variable | Type | Description |
|----------|------|-------------|
| `SELF` | `Box` | The input box that contains this contract |
| `INPUTS` | `Coll[Box]` | All input boxes being spent |
| `outputs` | `Coll[Box]` | All output boxes being created |
| `CONTEXT.dataInputs` | `Coll[Box]` | All data input boxes (read-only) |
| `HEIGHT` | `Int` | Current blockchain height |
| `CONTEXT.preHeader` | `PreHeader` | Block candidate info (miner PK, timestamp) |

This is fundamentally different from Bitcoin Script, which can only see the current input and the spending transaction's signatures. An Ergo contract can inspect every input, every output, every data input, and the current blockchain state. This enables complex multi-party protocols in a single transaction.

## Why Not Accounts?

Ethereum uses an accounts model: each address has a mutable balance and storage that gets modified in place. This is intuitive but has deep consequences:

| | eUTXO (Ergo) | Accounts (Ethereum) |
|---|---|---|
| **State** | Immutable boxes created and destroyed | Mutable account storage modified in place |
| **Parallelism** | Transactions on different boxes validate in parallel | Transactions on the same account must be serialized |
| **Determinism** | Transaction outcome is fully determined before submission | Transaction can fail after submission (out of gas, state changed) |
| **Failed transactions** | Cannot happen — you validate locally first | Common — you pay gas even when the transaction reverts |
| **Privacy** | Each box is a separate object; harder to trace | All activity tied to one address |
| **Composability** | Via data inputs and multi-box transactions | Via contract calls within a transaction |

The determinism point is crucial for developers: when you build a transaction in Ergo, you know exactly what inputs you're consuming and what outputs you're creating. If the transaction is valid when you construct it, it will be valid when a miner includes it (assuming the inputs haven't been spent by someone else first). There are no surprise gas costs or unexpected reverts.

## Multi-Stage Protocols

The eUTXO model enables **multi-stage protocols** — smart contracts that progress through states by consuming a box and recreating it with updated data. The pattern looks like:

```
Stage 1: Box A exists with state S1
    │
    ▼  Transaction spends Box A, creates Box B
Stage 2: Box B exists with state S2 (same script, updated registers)
    │
    ▼  Transaction spends Box B, creates Box C
Stage 3: Box C exists with state S3
```

Each box's guarding script enforces the valid state transitions. A singleton NFT token travels with the box to ensure identity — only one box with that token can exist, so the chain of state transitions is linear and verifiable.

This is how every major Ergo protocol works:

- **Dexy** tracks the stablecoin bank's reserve ratio across stages
- **Oracle pools** progress through data-posting and pool-update stages
- **Paideia DAO** moves proposals through creation → voting → execution stages
- **DuckPools** lending pools update interest rates and collateral ratios per stage

The research paper "Multi-Stage Contracts in the UTXO Model" formalizes this, showing that multi-stage eUTXO contracts achieve Turing-complete computation through transaction chains — even though ErgoScript itself is deliberately non-Turing-complete for safety.

## Ergo vs. Cardano's eUTXO

Both Ergo and Cardano implement extended UTXO models, but with differences:

| | Ergo | Cardano |
|---|---|---|
| **Contract language** | ErgoScript (Scala-like) | Plutus (Haskell-based) |
| **Data storage** | Typed registers R4-R9 in the box | Datum attached to the UTXO |
| **Read-only references** | Data inputs (from genesis) | Reference inputs (added in Vasil hardfork) |
| **Cryptographic proofs** | Native Sigma protocols (ZK proofs) | Planned for future development |
| **Token ID rule** | First input's box ID | Policy ID + asset name |
| **Max tokens per box** | 255 | Unlimited (within size limits) |

Ergo had data inputs from the beginning (2019), while Cardano added the equivalent "reference inputs" in the Vasil hardfork (2022). Both platforms collaborate through the eUTXO Alliance.

## The Mental Model

If you're coming from Ethereum development, the key mental shift is:

**Ethereum**: "I call a contract, it modifies its storage, done."

**Ergo**: "I build a transaction that consumes specific boxes and creates specific new boxes. Each box's script validates that the transition is legal. The entire transaction either succeeds atomically or doesn't happen at all."

You don't "call" an Ergo contract — you **spend** a box by constructing a transaction that satisfies its guarding script. The contract doesn't modify state; it validates that the proposed state change (old boxes → new boxes) is acceptable.

This is why the off-chain/on-chain split matters so much in Ergo development. The off-chain code (in TypeScript, Scala, Rust, or Python) is responsible for finding the right boxes, constructing the transaction, and submitting it. The on-chain code (ErgoScript) only validates — it never initiates or constructs anything.

## Learn More

- [Boxes and Registers](boxes-and-registers.md) — Detailed reference for box structure and register types
- [Sigma Protocols](sigma-protocols.md) — The cryptographic proof system behind SigmaProp
- [ErgoScript Fundamentals: Boxes, Registers & Context](../guides/ergoscript-fundamentals/01-boxes-registers-context.md) — Hands-on tutorial adapted from [DeCo Education](https://github.com/DeCo-Education/ErgoScript-Developer-Course)
- [Guard Script Framework](../guides/ergoscript-fundamentals/02-guard-script-framework.md) — Systematic contract design methodology from DeCo Education
- [Off-Chain with AppKit](../guides/ergoscript-fundamentals/03-offchain-appkit.md) — Building transactions with Ergo AppKit
