---
title: ergonames/ergo-names-contracts — Overview
description: Ergo Names — decentralized domain name registration contracts
tags: [ergonames, ergo-names-contracts, infrastructure, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ergonames/ergo-names-contracts"
project: ergonames-ergo-names-contracts
group: infrastructure
priority: low
languages: [scala]
contract_count: 0
pattern_match_count: 0
---
# Ergo Names Contracts — Developer Overview

---

## Overview

**ergonames/ergo-names-contracts** contains the ErgoScript smart contracts that power Ergo Names, a decentralized domain name registration system built on the Ergo blockchain. The project enables users to register human-readable names and bind them to Ergo addresses, functioning as a DNS-like layer within the eUTXO model. Rather than relying on a centralized registry, ownership of a name is represented directly as a Native token (NFT) held in a user's wallet, making name ownership fully self-custodied and verifiable on-chain.

Within the Ergo ecosystem, Ergo Names fills a critical UX gap by allowing wallets, dApps, and services to resolve memorable names rather than raw addresses. Because Ergo's eUTXO model treats each Box as a first-class citizen carrying tokens, Registers, and guards, the name-as-NFT pattern is a natural fit: the token's Token ID uniquely identifies the name, and its presence in a Box proves ownership without any additional oracle or trusted party.

The contract layer is written in Scala (compiled to ErgoScript / ErgoTree) and is intended to be paired with off-chain tooling that constructs, signs, and submits transactions. The contracts themselves enforce the registration invariants—ensuring names are unique, correctly minted, and that ownership transfers preserve the protocol rules—while the off-chain layer handles discovery and user interaction.

---

## Architecture

The system is organized around a small set of interacting contract roles following a **Multi-stage contract** pattern common in Ergo dApp design:

```
┌─────────────────────────────────────────────┐
│              Off-chain Layer                │
│  (transaction builders, resolvers, bots)    │
└────────────┬──────────────┬─────────────────┘
             │              │
     ┌───────▼──────┐  ┌────▼──────────────┐
     │  Registry    │  │  Minting Contract  │
     │  Contract    │  │  (Name NFT Mint)   │
     │  (State Box) │  └───────────────────┘
     └───────┬──────┘
             │ Data input / spending
     ┌───────▼──────────────┐
     │  Name Owner Box      │
     │  (user wallet UTxO   │
     │   holding Name NFT)  │
     └──────────────────────┘
```

**Registry Contract (State Box / Singleton):**  
A **Singleton / State NFT** pattern is used to maintain a single authoritative registry Box. This Box acts as the canonical on-chain state, using an **AVL tree** (stored in a Register) to map name hashes to their associated data (owner address, metadata). Every registration or transfer transaction must consume and re-create this State Box, preserving the AVL tree invariant and advancing the state machine.

**Minting Contract:**  
Governs the creation of new Name NFTs. It enforces the **Token ID rule** — that the minted token is unique and derived from the registration input Box's ID — preventing duplicate name registration. The minting guard script validates name format constraints and ensures the correct fee is paid.

**Name Owner Box:**  
After a successful registration, the user's wallet holds a Box containing the Name NFT. The token's presence acts as the unforgeable proof of ownership. Transfers are simple token transfers; the registry's AVL tree is updated in the same transaction to reflect the new owner.

**Data Flow:**  
1. Off-chain builder constructs a registration transaction referencing the current Registry State Box.  
2. The Minting Contract validates name uniqueness via the AVL tree proof (provided as a Context extension or Register).  
3. On success, a new Name NFT is deposited into the user's Box; the Registry State Box is recreated with an updated AVL tree root.

---

## Smart Contracts

All contracts are authored in **ErgoScript** (Scala DSL compiling to **ErgoTree**) and enforce the following responsibilities:

### Registry Contract
- Guards the Singleton State Box carrying the AVL tree of registered names.
- Enforces the **State machine** transition: the output Registry Box must contain a valid AVL tree update proof for the new name entry.
- Validates that the minted Name NFT Token ID matches the expected derivation from the current input Box ID (**Token ID rule**).
- Ensures **Minimum box value** (storage rent safety) is maintained in the recreated State Box.
- Uses **Sigma protocols** for authorization: only valid registration or admin transactions may spend the State Box.

### Minting Contract
- Enforces that exactly one new token is minted per registration transaction.
- Validates name string encoding and length constraints stored in a Register.
- Checks fee outputs, enforcing the **Minimum transaction fee** and protocol fee routing to the treasury.
- Prevents double-minting by tying the Token ID to the input UTXO identity (eUTXO uniqueness guarantee).

### Name Resolution Helper (Read-only / Data Input)
- The Registry State Box may be used as a **Data input** in downstream transactions, allowing any dApp to resolve a name without spending or mutating the registry — a key eUTXO composability pattern.
- No script spending is required; the ErgoTree simply allows reading Register contents containing the AVL tree root for off-chain proof verification.

### Transfer / Burn Guard
- Optionally constrains Name NFT transfers to ensure the Registry AVL tree is updated atomically in the same transaction, keeping on-chain state consistent with token ownership.

---

## Integration Guide

### Off-chain Interaction Pattern

Ergo Names follows a **Headless dApp** architecture: the contracts contain all consensus-critical logic, and the off-chain layer is responsible for:

1. **Fetching the current Registry State Box** via the Ergo Node REST API (`/utxo/byId` or `/boxes/unspent/byAddress`).
2. **Constructing AVL tree proofs** for insertion of the new name, using the current tree state deserialized from the Box's Register (e.g., `R4`).
3. **Building the unsigned transaction** using AppKit (the Ergo Scala/Java SDK), specifying:
   - Input: Registry State Box + user input Box (covering fees and Minimum box value).
   - Output: Updated Registry State Box + Name NFT Box (to user address).
   - Context extensions carrying the AVL tree proof bytes.
4. **Signing** via the user's wallet (EIP-12 connector for browser wallets, or AppKit `prover` for backend).
5. **Submitting** to the Ergo node or an explorer API.

### Key SDK Calls (AppKit / Scala)

```scala
// Deserialize registry box and AVL tree
val registryBox: InputBox = ctx.getBoxesById(registryBoxId).head
val avlTreeBytes: Array[Byte] = registryBox.getRegisters.get(0).getValue

// Build registration transaction
val txBuilder = ctx.newTxBuilder()
val outRegistryBox = txBuilder.outBoxBuilder()
  .value(registryBox.getValue)
  .contract(registryContract)
  .registers(updatedAvlTreeRegister)
  .build()

// Attach AVL proof as ContextExtension
val contextExt = ContextExtension.of(Map(1.toByte -> avlProofValue))
```

### Name Resolution (off-chain)

To resolve a name without submitting a transaction, fetch the Registry State Box as a **Data input**, deserialize the AVL tree from its Register, and perform a local lookup using the name's hash. No on-chain transaction is required for resolution.

### EIP-12 / Browser Integration

For front-end dApps, the unsigned transaction serialized from AppKit can be passed to an **EIP-12**-compatible connector (e.g., Nautilus Wallet) for user signing, following the standard `ergo_sign_tx` flow.

---

## Key Patterns

| Pattern | Usage in Ergo Names |
|---|---|
| **Singleton / State NFT** | Registry State Box identified by a unique NFT, ensuring only one authoritative registry exists on-chain |
| **State machine** | Each registration is a valid state transition: old registry → new registry with updated AVL tree |
| **AVL tree** | Efficient authenticated on-chain key-value store mapping name hashes to owner