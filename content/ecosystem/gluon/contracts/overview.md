---
title: StabilityNexus/Gluon-Ergo-Contracts — Overview
description: Gluon Gold stablecoin ErgoScript contracts — fission/fusion/transmute mechanics
tags: [stabilitynexus, gluon-ergo-contracts, defi, ergoscript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Gluon-Ergo-Contracts"
project: stabilitynexus-gluon-ergo-contracts
group: defi
priority: medium
languages: [ergoscript]
contract_count: 4
pattern_match_count: 0
---
# StabilityNexus/Gluon-Ergo-Contracts: Developer Overview

---

## Overview

Gluon-Ergo-Contracts implements the on-chain ErgoScript layer for the **GluonW** protocol — a dual synthetic asset system built on Ergo that issues two native tokens, **Neutrons** and **Protons**, backed by ERG collateral. The protocol is modelled on nuclear physics metaphors: a central **reactor box** (a Singleton / State NFT-anchored eUTXO) governs the minting and redemption of both assets through four distinct transaction types — **Fission** (ERG → Neutrons + Protons), **Fusion** (Neutrons + Protons → ERG), **Beta Decay Plus / β⁺** (Protons → Neutrons), and **Beta Decay Minus / β⁻** (Neutrons → Protons). Each transaction type is distinguished by the directional change in token balances and ERG value held within the reactor box, with ErgoScript invariants enforcing correctness entirely on-chain.

Within the Ergo DeFi ecosystem, GluonW occupies a position analogous to **SigmaUSD** and **Dexy** as a collateralised stablecoin primitive, but it introduces a dual-token supply model with volume-weighted fee mechanics. The Neutron token represents one exposure side and the Proton token the other; the ratio between them reflects oracle-priced gold exposure, targeting a gold-pegged stablecoin outcome. The reactor box accumulates ERG reserves and tracks historical trade volume across 14-day rolling buckets (stored in Registers R7 and R8), enabling dynamic fee computation without off-chain state. Treasury governance is managed through a multisig `SigmaProp` stored in R5 of the reactor box, updateable only via an authorised treasury input.

The project is structured as a **Scala / Play Framework** backend service (built on the Ergo Play Boilerplate) with ErgoScript contract sources maintained under `modules/gluonw-base/src/main/resources/ErgoContracts/`. The off-chain layer assembles, validates, and broadcasts transactions against a PostgreSQL-backed state store, following a **headless dApp / off-chain bot** architecture pattern consistent with EIP-12 and broader Ergo dApp conventions.

---

## Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│                   Off-Chain Layer (Scala / Play)                │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐   │
│  │  REST API    │   │  Off-Chain   │   │  PostgreSQL DB   │   │
│  │  (Play HTTP) │──▶│  Bot / Txn   │──▶│  (State cache,  │   │
│  │              │   │  Assembler   │   │   UTXO index)   │   │
│  └──────────────┘   └──────┬───────┘   └──────────────────┘   │
│                            │                                    │
└────────────────────────────┼───────────────────────────────────┘
                             │ Ergo Node / Explorer API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   On-Chain eUTXO Model                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               GluonW Reactor Box (Singleton)            │   │
│  │  Token[0]: GluonWNFT (1)   ← State NFT                  │   │
│  │  Token[1]: Neutrons (variable)                          │   │
│  │  Token[2]: Protons  (variable)                          │   │
│  │  ERG value: collateral reserve                          │   │
│  │  R4: (Total Neutron Supply, Total Proton Supply)        │   │
│  │  R5: Treasury multisig SigmaProp                        │   │
│  │  R6: (Dev fees accumulated, Max dev fee cap)            │   │
│  │  R7: β⁺ volume history  [14 × Long buckets]            │   │
│  │  R8: β⁻ volume history  [14 × Long buckets]            │   │
│  │  R9: Last bucket update block height                    │   │
│  │  Guard: GluonWBoxGuardScript.es                         │   │
│  └──────────────┬───────────────────────────────────────── ┘   │
│                 │ consumed / recreated each transaction         │
│  ┌──────────────▼──────────────┐  ┌──────────────────────┐    │
│  │  GluonWTxProxyContract.es   │  │  Gold Price Oracle   │    │
│  │  (Proxy Box, optional)      │  │  Box (Data Input)    │    │
│  └─────────────────────────────┘  └──────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────┐                               │
│  │  DummyErgoScript.es         │                               │
│  │  (Test / fixture boxes)     │                               │
│  └─────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Per Transaction Type

| Phase | Actor | Action |
|---|---|---|
| **1. UTXO Discovery** | Off-chain bot | Locate reactor box by GluonWNFT Token ID (Singleton lookup) |
| **2. Oracle Read** | Off-chain bot | Fetch current gold price oracle box (read as Data Input) |
| **3. State Extraction** | Off-chain bot | Deserialise R4–R9 from reactor box |
| **4. Tx Construction** | Off-chain bot | Build Input(reactor box) + DataInput(oracle) + Output(new reactor box) + Output(user box) |
| **5. Register Computation** | Off-chain bot | Compute updated R4, R6, R7/R8/R9 values based on transaction type and volume buckets |
| **6. Validation** | ErgoScript (on-chain) | Guard script evaluates all invariants, type-discriminates transaction, confirms oracle |
| **7. Broadcast** | Off-chain bot | Submit to Ergo node mempool; index new reactor box UTXO in PostgreSQL |

The reactor box is **consumed and recreated in every protocol transaction**, forming a linear state machine chain anchored by the immutable GluonWNFT singleton.

---

## Smart Contracts

### `GluonWBoxGuardScript.es`
**Location:** `modules/gluonw-base/src/main/resources/ErgoContracts/GluonW/Ergs/BoxGuardScripts/`

This is the primary on-chain contract and the most critical piece of the system. It guards the reactor box and is responsible for validating all five transaction types recognised by the protocol.

**Transaction type discrimination** is performed purely from observable Box deltas — no off-chain flags or Context extensions are required:

| Transaction | Neutrons Δ | Protons Δ | ERG Value Δ |
|---|---|---|---|
| Fission | Decreases (in box) | Decreases (in box) | Increases |
| Fusion | Increases (in box) | Increases (in box) | Decreases |
| Beta Decay Plus (β⁺) | Decreases (in box) | Increases (in box) | Unchanged |
| Beta Decay Minus (β⁻) | Increases (in box) | Decreases (in box) | Unchanged |
| Treasury Update | Any (locked) | Any (