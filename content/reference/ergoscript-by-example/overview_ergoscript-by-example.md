---
title: ergoplatform/ergoscript-by-example — Overview
description: 13 annotated ErgoScript contract examples — pin lock, escrow, token sale, swaps, stealth addresses, timed funds
tags: [ergoplatform, ergoscript-by-example, reference, markdown]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repo: "https://github.com/ergoplatform/ergoscript-by-example"
project: ergoplatform-ergoscript-by-example
group: reference
priority: high
languages: [markdown]
contract_count: 0
pattern_match_count: 0
---
# ErgoScript By Example — Developer Overview

---

## Overview

**ErgoScript By Example** is a curated, annotated reference library of ErgoScript smart contract examples designed to accelerate developer onboarding into the Ergo eUTXO ecosystem. The repository provides 13 progressively difficulty-ranked contracts — from basic pin locks and timed fund release to expert-level stealth addresses and parallelized game contracts — each paired with a live, browser-executable **Ergo Playground** (via Scastie) link. This design eliminates local toolchain setup as a barrier to entry, allowing developers to read, modify, and run ErgoScript directly in their browser.

Within the Ergo ecosystem, this project occupies the **reference layer**: it serves neither as a deployed protocol nor a production SDK, but as the canonical starting point for developers learning how Boxes, Registers, ErgoScript context variables, and Sigma protocols compose into real spending conditions. The examples bridge the gap between the formal [ErgoScript Language Specification](https://github.com/ScorexFoundation/sigmastate-interpreter/blob/develop/docs/LangSpec.md) and practical contract design, grounding abstract eUTXO concepts in concrete, executable patterns.

The project complements Ergo's broader documentation ecosystem alongside the ErgoScript Whitepaper and the Advanced ErgoScript Tutorial. By covering patterns from single-chain atomic swaps to multi-stage self-replicating token sale contracts and Sigma-protocol-based stealth addresses, the repository reflects the full expressive range of ErgoScript — making it an essential reference for protocol designers, dApp developers, and smart contract auditors working on the Ergo platform.

---

## Architecture

The repository is purely a **documentation and educational artifact** — there are no compiled binaries, off-chain services, or deployed contracts. Its architecture is flat and content-centric:

```
ergoscript-by-example/
├── README.md                        # Index and contributor guide
├── example_template.md              # Contribution scaffold
├── pinLockContract.md               # Example 1 (Beginner)
├── simpleSend.md                    # Example 3 (Starter)
├── timedFund.md                     # Example 5 (Beginner)
├── escrowDepositContract.md         # Example 7 (Beginner)
├── singleChainSwap.md               # Example 2 (Intermediate)
├── doubleChainSwap.md               # Example 4 (Intermediate)
├── headsOrTails.md                  # Example 10 (Intermediate)
├── tokenSalesService.md             # Example 8 (Expert)
├── selfReplicatingTokenSale.md      # Example 9 (Beginner)
├── grantorBeneficiaryPinLock.md     # Example 6 (Beginner)
├── stealthAddress.md                # Example 11 (Expert)
└── headsOrTailsParallel.md          # Example 12 (Expert)
```

Each Markdown file is self-contained and structured around a consistent pattern:

1. **Concept introduction** — explanation of the problem being solved in eUTXO terms
2. **ErgoScript contract code** — the on-chain spending condition (ErgoTree source)
3. **Off-chain test scenario** — Scala code (runnable in Ergo Playground / Scastie) demonstrating Box construction, transaction assembly, and context provision
4. **Inline annotations** — comments explaining ErgoScript context variables (`SELF`, `INPUTS`, `OUTPUTS`, `HEIGHT`), Register usage, and Sigma protocol expressions

Data flow in each example follows the standard Ergo transaction model: an off-chain actor constructs a **Transaction** spending one or more input **Boxes**, optionally referencing **Data inputs**, and produces output Boxes whose values satisfy the ErgoScript spending condition evaluated against the **ErgoScript context**.

---

## Smart Contracts

All contracts are written in **ErgoScript** and compiled to **ErgoTree** for on-chain representation. The following table summarizes each contract, its core mechanism, and the key ErgoScript/eUTXO features it demonstrates:

| # | Title | Difficulty | Core Mechanism | Key Features |
|---|-------|------------|----------------|--------------|
| 1 | **Pin Lock Contract** | Beginner | Funds unlocked only when a secret integer is provided whose hash matches a committed value | `blake2b256`, Registers (`R4`), `CONTEXT.extension` / Context extension |
| 2 | **Single-Chain Swap** | Intermediate | Two-party atomic swap of Native tokens within a single Ergo chain transaction | Atomic swaps, `OUTPUTS`, token ID matching, Token ID rule enforcement |
| 3 | **Simple Send** | Starter | Trivially spendable Box demonstrating base transaction anatomy | `INPUTS`, `OUTPUTS`, `SELF`, minimum box value |
| 4 | **Double-Chain Swap** | Intermediate | Cross-chain swap pattern coordinated via hash-locked contracts on two chains | Hash preimage locks, Sigma protocols, timelock fallback |
| 5 | **Timed Fund Contract** | Beginner | Funds claimable by a beneficiary before a deadline; refundable to creator after | `HEIGHT`, `sigmaProp`, deadline enforcement |
| 6 | **Grantor/Beneficiary Pin Lock** | Beginner | Two-party pin lock where both grantor and beneficiary must cooperate or supply pin | `&&` / `\|\|` composition of `SigmaProp`, multi-party spending |
| 7 | **Escrow Deposit Contract** | Beginner | Three-party escrow where an arbitrator decides fund routing | `proveDlog`, Sigma protocol composition, multi-party authorization |
| 8 | **Token Sales Service Contract** | Expert | Stateful token vending machine enforcing price invariants across output Boxes | Invariant checking across `OUTPUTS`, Native tokens, minimum transaction fee |
| 9 | **Self-Replicating Sale Contract** | Beginner | Token sale Box that reproduces itself (minus sold tokens) in each transaction | Self-replication / State machine pattern, `OUTPUTS(0).propositionBytes == SELF.propositionBytes` |
| 10 | **Heads or Tails Game** | Intermediate | Two-player commit-reveal game with ERG wagering | Multi-stage contracts, commit-reveal, `blake2b256` |
| 11 | **Stealth Address** | Expert | Receiver publishes a stealth public key; sender derives a one-time address only the receiver can spend | Sigma protocols, `proveDlog`, Diffie-Hellman tuple (`proveDHTuple`) |
| 12 | **Heads or Tails (Parallelized)** | Expert | Extension of the game contract supporting concurrent game instances | Parallelization pattern, multiple UTXO state machines |

### Contract Responsibility Highlights

**Pin Lock (`pinLockContract.md`)**
The spending condition verifies `blake2b256(pinBytes) == committedHash` where `pinBytes` is supplied via a **Context extension** variable at spend time. This pattern demonstrates how to commit to secret data on-chain without revealing it, using Registers to store the committed hash in `R4` of the guarded Box.

**Timed Fund (`timedFund.md`)**
```
(sigmaProp(HEIGHT < deadline) && beneficiaryPubKey) || (sigmaProp(HEIGHT >= deadline) && grantorPubKey)
```
A canonical demonstration of `HEIGHT`-based timelocks, composing `SigmaProp` values with `&&` and `||` to express conditional ownership.

**Self-Replicating Sale (`selfReplicatingTokenSale.md`)**
The contract enforces that `OUTPUTS(0).propositionBytes == SELF.propositionBytes` (contract replication) and that the token balance in the output equals `SELF.tokens(0)._2 - soldAmount`. This is a foundational **State machine** / **Singleton** pattern without a State NFT — the contract identity is preserved through proposition byte equality.

**Stealth Address (`stealthAddress.md`)**
Implements a `proveDHTuple(g, h, u, v)` Sigma protocol proof, where the sender derives a one-time key `u = g^r`, `v = h^r` for a recipient's published stealth public key `h = g^