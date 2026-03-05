---
title: ergoplatform/ergo-appkit — Overview
description: JVM SDK — transaction building, contract compilation, wallet interaction
tags: [ergoplatform, ergo-appkit, sdk, java, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergoplatform/ergo-appkit"
project: ergoplatform-ergo-appkit
group: sdk
priority: high
languages: [java, scala]
contract_count: 0
pattern_match_count: 20
---
# Ergo Appkit — Developer Overview

## Overview

Ergo Appkit is the canonical JVM SDK for building applications that interact with the Ergo blockchain. It provides idiomatic Java and Scala APIs for the full lifecycle of off-chain application logic: querying the blockchain state, constructing and signing Transactions, compiling ErgoScript contracts into ErgoTree, managing wallets and addresses, and broadcasting signed transactions to the network. Appkit acts as a thin but complete wrapper over two core Ergo infrastructure libraries — the [sigmastate-interpreter](https://github.com/ScorexFoundation/sigmastate-interpreter) (which implements Sigma protocols, ErgoTree evaluation, and proof generation) and the [ergo](https://github.com/ergoplatform/ergo) node reference implementation — exposing their capabilities through a stable, developer-friendly API without requiring direct dependency on internal Scala implementation details.

Within the Ergo ecosystem, Appkit occupies the foundational SDK layer. It is intentionally non-opinionated: it does not prescribe any particular dApp architecture but instead provides the primitive operations — Box selection, input/output construction, Register encoding, Data input attachment, prover configuration, and context construction — from which any application pattern can be composed. Higher-level libraries (Kiosk, ergo-jde, GetBlok-Plasma), command-line tools (ergo-tool), wallet applications (Ergo Wallet App), and full dApps (ErgoMixer, SigmaFi) are all built on top of Appkit, making it the single most widely depended-upon SDK in the Ergo developer ecosystem.

Appkit is cross-compiled against Scala 2.11 (targeting JVM 7 and Android) and Scala 2.12 (targeting JVM 8+), published to Maven Central, and compatible with GraalVM native-image compilation. This broad platform support enables Appkit-based applications to run on Android, iOS (via RoboVM), desktop JVMs, cloud servers, and as GraalVM polyglot guests callable from JavaScript, Python, Ruby, and C. Python developers may also access Appkit via the `ergpy` wrapper, which bridges Appkit through JPype.

---

## Architecture

Appkit is organized into four sub-modules with a clear dependency hierarchy:

```
common
  └─► lib-api
        └─► lib-impl
              └─► java-client-generated
examples (depends on lib-impl)
```

### `common`
Shared utility classes used across all other modules: serialization helpers, address encoding/decoding (Base58Check, P2PK, P2S, P2SH address types), cryptographic primitives, and type-safe wrappers over Ergo's internal data model including `ErgoValue`, `ErgoType`, `Iso` isomorphisms between Java and Scala types.

### `java-client-generated`
A Swagger-generated, typed REST Java client covering the complete [Ergo node OpenAPI](https://github.com/ergoplatform/ergo/blob/master/src/main/resources/api/openapi.yaml). All node communication (Box queries, Transaction submission, peer info, mempool queries, wallet endpoints) flows through this module. It is the sole point of network I/O in the default implementation.

### `lib-api`
Pure Java interfaces defining the Appkit programming model. Key abstractions:

| Interface | Responsibility |
|---|---|
| `ErgoClient` | Entry point; provides a `BlockchainContext` and manages node/network configuration |
| `BlockchainContext` | Snapshot of chain state; factory for `UnsignedTransactionBuilder`, `ErgoProverBuilder`, and `InputBox` queries |
| `UnsignedTransactionBuilder` (`newTxBuilder`) | Fluent builder for assembling `UnsignedTransaction` from inputs, outputs, Data inputs, and fee |
| `OutBoxBuilder` (`outBoxBuilder`) | Constructs output Boxes with value, tokens (Native tokens), Registers (R4–R9), and ErgoTree or contract |
| `ErgoProverBuilder` | Configures signing secrets (mnemonic, extended secret key, DHT tuples, DLog) producing an `ErgoProver` |
| `ErgoProver` | Signs `UnsignedTransaction`, producing a `SignedTransaction` containing proofs for Sigma protocols |
| `ErgoContract` | Wraps an ErgoTree with its address |

### `lib-impl`
Concrete implementations of all `lib-api` interfaces. Two `ErgoClient` implementations:

- **`RestApiErgoClient`** — Live client connecting to a running Ergo node or public API endpoint. Wraps `java-client-generated` calls, hydrates `InputBox` objects from node responses, and submits signed transactions.
- **`ColdErgoClient`** — Offline client that operates without network access. Accepts pre-fetched Box data and a `BlockchainParameters` snapshot, enabling air-gapped transaction signing workflows.

### Data Flow

```
Node REST API (java-client-generated)
        │
        ▼
RestApiErgoClient.execute(ctx -> {
    BlockchainContext ctx
        │
        ├── ctx.getUnspentBoxesFor(address)    → List<InputBox>   (eUTXO inputs)
        ├── ctx.newTxBuilder()
        │       ├── .boxesToSpend(inputs)
        │       ├── .outputs(outBoxBuilder
        │       │       .value(nanoErgs)
        │       │       .tokens(token)         → Native token attachment
        │       │       .registers(R4, R5...)  → Register encoding
        │       │       .contract(ergoTree))
        │       ├── .withDataInputs(dataInputs) → Data input (read-only Box reference)
        │       ├── .fee(MinFee)               → Minimum transaction fee
        │       └── .build()                   → UnsignedTransaction
        │
        └── ctx.newProverBuilder()
                ├── .withMnemonic(...)
                ├── .withDHTData(...)          → DHT Sigma protocol
                └── .build()                  → ErgoProver
                        └── .sign(unsignedTx) → SignedTransaction
                                └── ctx.sendTransaction(signedTx)
})
```

Context extension values, used to supply additional data to ErgoScript during verification, are attached at the `ContextVar` level on individual inputs before signing.

---

## Smart Contracts

Appkit itself does not deploy on-chain ErgoScript contracts; it is the off-chain tooling layer. However, it provides complete infrastructure for compiling, representing, and interacting with ErgoScript contracts:

- **`ErgoScript.create(ctx, scriptText)`** — Compiles an ErgoScript source string into an `ErgoTree` (the canonical serialized form of a Sigma proposition stored in a Box's guarding script). The compilation is performed by the embedded sigmastate-interpreter.
- **`Address.fromErgoTree(ergoTree, networkType)`** / **`Address.toErgoContract()`** — Converts between ErgoTree byte representations and human-readable P2S (pay-to-script) addresses.
- **`ErgoValue` and `Values`** — Encode and decode typed constant values placed in Box Registers (R4–R9). Supports all ErgoScript data types including `SigmaProp`, `GroupElement`, `Coll[Byte]`, `Long`, `Tuple`, `AVL tree` digests, and more.
- **Constant segregation** — Appkit leverages the sigmastate-interpreter's support for constant segregation, where constants embedded in an ErgoTree can be substituted at spend time, enabling parameterized contract reuse from a single compiled template.
- **Context extension** — The `ContextVar` API attaches key-value pairs to a spending input, making them available inside the ErgoScript context as `getVar[T](id)` calls. This is the primary mechanism for passing spend-time arguments to contracts without embedding them in the ErgoTree.

Appkit-based projects commonly interact with the following contract patterns at the off-chain layer:

| Pattern | Off-chain role in Appkit |
|---|---|
| **Singleton / State NFT** | Locate the unique Box by Token ID rule; use it as a Data input or spending input to advance