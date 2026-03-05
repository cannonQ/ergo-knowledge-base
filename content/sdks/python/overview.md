---
title: ergo-pad/ergo-python-appkit — Overview
description: Python AppKit wrapper (ergpy) — JPype bridge, transaction building patterns
tags: [ergo-pad, ergo-python-appkit, sdk, python]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergo-pad/ergo-python-appkit"
project: ergo-pad-ergo-python-appkit
group: sdk
priority: medium
languages: [python]
contract_count: 0
pattern_match_count: 4
---
# ergo-pad/ergo-python-appkit — Developer Overview

---

## Overview

`ergo-python-appkit` (published as `ergpy`) is a Python wrapper around the official Ergo AppKit — the primary JVM-based SDK for interacting with the Ergo blockchain. Because Ergo's core tooling is written in Scala/Java, Python developers historically had no ergonomic path to building dApps, transaction assemblers, or off-chain bots. This library solves that by using **JPype** to bridge the Python runtime directly to a running JVM, loading the AppKit JAR and exposing its full class hierarchy to Python code. The result is that developers can import Java classes such as `org.ergoplatform.appkit.Address` or `org.ergoplatform.appkit.UnsignedTransaction` natively in Python scripts, while also benefiting from higher-level Python convenience wrappers for the most common operations.

Within the Ergo ecosystem, `ergo-python-appkit` occupies the **off-chain computation layer** of the eUTXO model. It is responsible for constructing unsigned transactions — selecting input Boxes, composing output Boxes with correct values, Registers, and token assignments, computing change, and enforcing the Minimum box value and Minimum transaction fee constraints — before submitting them to a node for signing or handling signing externally. This makes it the natural foundation for headless dApps, off-chain bots, and backend services that need to interact with Ergo smart contracts written in ErgoScript without requiring a browser wallet.

The library targets developers building in the `ergo-pad` ecosystem (IDO launchpad, staking contracts, token vesting) but is general-purpose. Any Python-based project that needs to mint Native tokens, read on-chain Box state, assemble Multi-stage contract transactions, or automate recurring contract interactions (such as a Sigma protocol participant or an AVL tree updater) can use it as a foundation. Its dependency on a locally or remotely accessible Ergo full node means it fits cleanly into bot architectures that poll chain state and react to eUTXO transitions.

---

## Architecture

### Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                   Python Application Layer                   │
│  (dApp logic, off-chain bots, scripts, test harnesses)      │
└───────────────────────┬─────────────────────────────────────┘
                        │ imports
┌───────────────────────▼─────────────────────────────────────┐
│              ergo_python_appkit  (this library)              │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │  appkit.py   │  │  ErgoBox.py  │  │ErgoTransaction.py │ │
│  │ ErgoAppKit   │  │  ErgoBox     │  │  ErgoTransaction  │ │
│  │ (façade)     │  │  (wrapper)   │  │  (assembler)      │ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘ │
│         │                 │                   │             │
│  ┌──────▼─────────────────▼───────────────────▼──────────┐ │
│  │          ErgoContractBase.py                           │ │
│  │   (ErgoTree / contract address resolution helpers)     │ │
│  └──────────────────────────────────────────────────────-─┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │ JPype bridge (JVM in-process)
┌───────────────────────▼─────────────────────────────────────┐
│              Ergo AppKit JAR  (Scala/Java)                   │
│  BlockchainContext · UnsignedTransactionBuilder              │
│  InputBox · OutBox · ErgoToken · Address · ErgoContract      │
│  ErgoProver · ErgoClient · RestApiErgoClient                 │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST
          ┌─────────────┴──────────────┐
          │                            │
┌─────────▼──────────┐    ┌────────────▼───────────┐
│  Ergo Full Node    │    │  Ergo Explorer API      │
│  (port 9053)       │    │  (api.ergoplatform.org) │
│  /wallet, /tx,     │    │  Box lookup, UTxO set   │
│  /blocks …         │    │  queries                │
└────────────────────┘    └────────────────────────┘
```

### Core Modules

| Module | Class | Responsibility |
|---|---|---|
| `appkit.py` | `ErgoAppKit` | Central façade. Initialises the JPype JVM, constructs a `BlockchainContext` via `RestApiErgoClient`, and exposes Python-friendly methods for box selection, output construction, unsigned transaction building, node-side signing, and submission. |
| `ErgoBox.py` | `ErgoBox` | Python-side wrapper around AppKit's `InputBox`. Provides ergonomic access to Box ID, ERG value, token list (Native tokens), and decoded Registers (R4–R9). |
| `ErgoTransaction.py` | `ErgoTransaction` | Assembles `UnsignedTransaction` objects. Accepts lists of input Boxes and output Box specifications, delegates to `UnsignedTransactionBuilder`, and enforces fee and change-output rules. |
| `ErgoContractBase.py` | `ErgoContractBase` | Utility layer for resolving P2PK and P2S addresses to their `ErgoTree` representation, and for compiling inline ErgoScript strings into `ErgoContract` objects usable as Box guards. |

### Data Flow — Transaction Assembly

```
1. boxesToSpend()
   └─► Query node /wallet/boxes or Explorer UTxO API
       └─► Return List[InputBox]  (AppKit JVM objects)

2. buildOutBox()
   └─► Accept (value, tokens, registers, contract)
       └─► Call OutBoxBuilder → OutBox

3. buildUnsignedTransaction()
   └─► UnsignedTransactionBuilder
       ├─ .addInputs(inputs)
       ├─ .addOutputs(outputs)
       ├─ .fee(feeAmount)         ← enforces Minimum transaction fee
       └─ .sendChangeTo(address)  ← change Box satisfies Minimum box value

4. signTransactionWithNode()
   └─► POST /wallet/transaction/sign  → SignedTransaction

5. sendTransaction()
   └─► POST /transactions → TxId (broadcast to mempool)
```

---

## Smart Contracts

`ergo-python-appkit` is a **transaction-building and off-chain SDK**; it does not define or deploy ErgoScript contracts of its own. Its role is to *interact with* contracts that already exist on-chain. Key contract-facing capabilities include:

- **ErgoTree resolution** — `ErgoContractBase` converts a Base58 address to its underlying `ErgoTree` bytes, which is the canonical on-chain representation of a Box guard script. This is required when constructing output Boxes whose guard must match a specific contract.
- **P2S compilation** — Developers can pass raw ErgoScript source strings through `appkit.compileErgoScript()` (backed by AppKit's `ErgoScriptCompiler`), producing an `ErgoContract` object. This supports deploying new contract instances or building outputs locked to a custom script hash without leaving Python.
- **Register encoding** — When building output Boxes that will be consumed by Multi-stage contracts (e.g., state-machine transitions where R4–R9 carry typed state), the library exposes AppKit's `ErgoValue` encoding for `Long`, `Coll[Byte]`, `SigmaProp`,