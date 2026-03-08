---
title: spectrum-finance/ergo-dex-backend — Overview
description: Spectrum off-chain execution bots — order matching, state tracking
tags: [spectrum-finance, ergo-dex-backend, defi, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/spectrum-finance/ergo-dex-backend"
project: spectrum-finance-ergo-dex-backend
group: defi
priority: high
languages: [scala]
contract_count: 0
pattern_match_count: 1
---
# spectrum-finance/ergo-dex-backend — Developer Overview

---

## Overview

**ergo-dex-backend** is the collection of off-chain execution bots and services that power Spectrum Finance (formerly ErgoDEX) on the Ergo blockchain. The project implements the off-chain half of Spectrum's AMM (Automated Market Maker) and Order Book DEX protocols: it monitors the Ergo UTXO set for relevant Boxes, matches or resolves pending orders, constructs valid spending Transactions against on-chain ErgoScript contracts, and submits those transactions back to the network. Without these bots the on-chain contracts would never be executed — the eUTXO model requires an explicit off-chain actor to assemble each transaction.

The system is architected as a set of loosely coupled microservices that communicate through Apache Kafka and share ephemeral state via Redis. Each service has a single, clearly bounded responsibility (tracking, matching, executing, or serving market data), making the codebase a reference implementation for production-grade **off-chain bot** design on Ergo. The bots are economically self-sustaining: an operator provides a funded mnemonic wallet, the bot pays miner fees from that wallet, and recovers costs through the execution fees embedded in each order Box.

The project is written entirely in Scala and makes heavy use of the Cats Effect / fs2 ecosystem for purely functional, streaming data pipelines. Configuration is environment-driven and the full service stack (node connectivity, Kafka, Redis, the bots themselves) is shipped as a Docker Compose bundle, lowering the operational barrier for independent bot operators who wish to participate in Spectrum's decentralised execution network.

---

## Architecture

### AMM Services

```
Ergo Node (REST)
      │
      ▼
┌─────────────┐      Kafka topics       ┌──────────────────┐
│ UTXO Tracker │ ──── orders feed ──────▶│  AMM Executor    │
│             │ ──── pool updates ──────▶│  (Execution.scala│
└─────────────┘                          │   submitTx)      │
      │                                  └──────────────────┘
      │  pool updates                           │
      ▼                                         ▼
┌──────────────┐                        Ergo Node (submit)
│ Pool Resolver│  (tracks singleton /
└──────────────┘   State-NFT pool Boxes)
```

### Order Book Services

```
Ergo Node (REST)
      │
      ▼
┌─────────────┐   Kafka    ┌─────────┐   matched pairs   ┌──────────────────┐
│ UTXO Tracker │──orders──▶│ Matcher │──────────────────▶│ Orders Executor  │
└─────────────┘            └─────────┘                   └──────────────────┘
                                │                                │
                           Redis (order                  Ergo Node (submit)
                            book state)
                                │
                           ┌────────────┐
                           │ Markets API│ ◀── external clients / frontend
                           └────────────┘
```

### Data Flow

1. **UTXO Tracker** polls the Ergo node's UTXO/mempool stream, decodes Box registers to identify AMM orders (swap, deposit, redeem) or Order Book limit orders, and publishes structured events to Kafka topics.
2. **AMM Executor / Orders Executor** consumes those topics, retrieves the relevant pool Box (identified by its **Singleton / State NFT**), constructs an unsigned Transaction that spends the order Box and pool Box simultaneously, signs it with the operator wallet, and submits it via `submitTransaction`.
3. **Pool Resolver** maintains a local view of each AMM pool's current state by replaying pool Box transitions from the same Kafka feed, providing the executor with a consistent, up-to-date pool Box without an extra node round-trip per execution.
4. **Matcher** (Order Book path) maintains an in-memory order book backed by Redis; when a bid and ask cross it emits a matched pair to the executor topic.
5. **Markets API** aggregates fill events and pool states into OHLCV and liquidity data served over HTTP.

---

## Smart Contracts

The backend does **not** define ErgoScript contracts itself — it is the off-chain counterpart to contracts maintained in companion repositories (see **Related Projects**). However, the codebase encodes deep knowledge of those contracts:

| Contract Role | Ergo Concepts Used | Off-chain Handling |
|---|---|---|
| **AMM Pool Box** | Singleton / State NFT in token slot 0 identifies the pool; pool reserves held as Native tokens; pool state (LP supply, fee numerator) encoded in **Registers** R4–R6 | Pool Resolver decodes R4–R6 on every Box update; Executor selects the pool Box as a Data input or spending input depending on operation |
| **Swap Order Box** | ErgoTree encodes the minimum output amount (slippage guard) and refund PK as an **Invariant**; fee amount locked as Native token or ERG | Executor reads the minimum-output register, constructs the output Box satisfying the constraint, pays miner fee from operator wallet |
| **Deposit / Redeem Order Boxes** | LP tokens minted or burned according to constant-product formula; Multi-stage contract chains deposit → pool update atomically | Executor batches deposit into a single Transaction spending both the order Box and the pool Box |
| **Order Book Limit Order Box** | Price and quantity encoded in Registers; partial-fill tracked via Context extension | Matcher compares decoded price/quantity; Executor constructs partial or full fill Transaction with correct residual output Box |
| **Refund path** | Each order Box has a guarded refund branch executable by the user's PK after a timeout | Bot ignores timed-out Boxes; user's wallet handles the refund branch independently |

**ErgoScript context** variables and **Context extension** fields are read during transaction construction to satisfy the spending conditions on swap and partial-fill contracts. No new ErgoScript is authored here; the bot's job is to supply valid witnesses and correctly-formed output Boxes that satisfy the on-chain **Sigma protocols**.

---

## Integration Guide

### Prerequisites

- A synced **Ergo node** (full or pruned via **NiPoPoW**) with the REST API enabled.
- Docker + Docker Compose.
- A funded operator wallet (mnemonic); the address can be derived with the bundled `HowTo.scala` utility.

### Configuration

Copy `config-example.env` to `config.env` and set:

```env
OPERATOR_MNEMONIC="word1 word2 ... word15"   # wallet that pays miner fees
NODE_URI=http://192.168.1.x:9053             # local LAN IP preferred inside Docker
EXPLORER_URI=https://api.ergoplatform.com    # optional: fallback Box lookup
```

The mnemonic wallet must hold enough ERG to cover **Minimum transaction fee** and **Minimum box value** for each execution transaction. In SPF-fee mode, SPF tokens must also be present.

### Starting the Stack

```bash
# Linux
sudo -E docker-compose up -d

# Verify
sudo docker-compose logs -f amm-executor
```

### Programmatic Interaction (Scala)

The core execution entry point is `Execution.scala`:

```scala
// Simplified call-site pattern
executionService
  .execute(order, poolState)   // builds unsigned Tx
  .flatMap(node.submitTransaction)  // submits to Ergo node
```

To integrate a custom strategy, implement the `Execution[F]` algebra and wire it into the fs2 stream pipeline in the executor module.

### Kafka Topics

| Topic | Producer | Consumer |
|---|---|---|
| `amm.orders` | UTXO Tracker | AMM Executor |
| `amm.pool-updates` | UTXO Tracker | Pool Resolver, AMM Executor |
| `orderbook.orders` | UTXO Tracker | Matcher |
| `orderbook.matches` | Matcher | Orders Executor |

Topic names are configurable via `config.env`. Consumers use Kafka consumer groups, so multiple executor