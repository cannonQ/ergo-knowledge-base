---
title: Ergo-Lend/ergo-lend-documentation — Overview
description: Exle — decentralized P2P lending, lend/borrow contracts, proxy contracts, service contract
tags: [ergo-lend, ergo-lend-documentation, defi, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/Ergo-Lend/ergo-lend-documentation"
project: ergo-lend-ergo-lend-documentation
group: defi
priority: medium
languages: [scala]
contract_count: 0
pattern_match_count: 3
---
# Ergo-Lend (Exle) — Developer Overview

---

## Overview

Ergo-Lend, branded as **Exle**, is a decentralized peer-to-peer lending protocol built on the Ergo blockchain. It enables borrowers to create on-chain lending requests and receive funds directly from lenders, with all terms — interest rate, repayment deadline, funding goal, and borrower identity — encoded directly into eUTXO Boxes and enforced by ErgoScript contracts. The platform is designed with a charitable lending philosophy, meaning repayment terms are transparent and community participation in debt repayment is explicitly supported.

The protocol operates as a **multi-stage contract system** where each phase of a loan's lifecycle (creation, funding, disbursement, repayment, closure) is represented by a distinct on-chain Box type and governed by its own ErgoScript contract. State transitions between phases are atomic transactions that consume one set of Boxes and produce the next, ensuring that loan state is always fully represented and verifiable on-chain without any off-chain oracle dependency for core logic.

Within the Ergo DeFi ecosystem, Ergo-Lend occupies the credit/lending layer, complementing AMM-based and stablecoin protocols. It demonstrates how **Native tokens** (used as service and pool identity tokens), **Registers**, and **proxy contract** patterns can be composed into a complete financial product using only ErgoScript primitives and the eUTXO model.

---

## Architecture

The system is organized around three categories of on-chain components — a singleton service box, per-loan lifecycle boxes, and proxy contracts — plus off-chain Scala code that constructs and submits transactions.

### Core On-Chain Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Lend Service Box                        │
│  (Singleton / State NFT pattern)                            │
│  Contains: LendServiceNFT (unique), LendServiceTokens (LST) │
│  Registers: service fee, team PK, protocol parameters       │
└──────────────────────┬──────────────────────────────────────┘
                       │ consumed/recreated in phase transitions
          ┌────────────┴────────────┐
          ▼                         ▼
┌──────────────────┐     ┌──────────────────────┐
│   Lending Box    │────▶│   Repayment Box       │
│  (Funding phase) │     │  (Repayment phase)    │
│  Holds: LST      │     │  Holds: LST           │
│  Registers: goal,│     │  Registers: lender PKs│
│  deadline, PKs,  │     │  amounts, interest,   │
│  interest rate   │     │  repayment deadline   │
└──────────────────┘     └──────────────────────┘
          ▲                         ▲
          │                         │
┌─────────┴──────────────────────────────────────┐
│              Proxy Contracts (×3)               │
│  1. Create Lending Box Proxy                    │
│  2. Fund Lending Box Proxy                      │
│  3. Fund Repayment Box Proxy                    │
└─────────────────────────────────────────────────┘
```

### Data Flow

1. **Borrower → Create Proxy → (Service Box + Lending Box):** A borrower pays ERG to the creation proxy. An off-chain bot (or the borrower's client) constructs a transaction consuming the proxy Box and one Service Box, outputting a recreated Service Box (LST count decremented) and a new Lending Box carrying one LST.

2. **Lenders → Fund Proxy → Lending Box:** Lenders send ERG to the Fund Lending Box proxy. Each funding transaction merges the proxy value into the Lending Box, appending the lender's PK and funded amount into the Lending Box's Registers.

3. **Borrower spends full Lending Box → (Service Box + Repayment Box + Service Fee Box + Borrower Box):** When the Lending Box reaches its funding goal, the borrower constructs the disbursement transaction, burning the Lending Box and producing a Repayment Box with loan metadata in Registers.

4. **Repayment Proxy → Repayment Box:** The borrower (or any charitable contributor) sends ERG through the repayment proxy into the Repayment Box incrementally.

5. **Full Repayment → Lender Boxes + Service Box (LST +1):** When the Repayment Box holds the full owed amount, the closing transaction distributes ERG proportionally back to all lenders and returns the LST to the Service Box.

---

## Smart Contracts

All contracts are implemented in **ErgoScript** and their compiled **ErgoTree** representations are managed through Scala wrappers in the `contracts/` directory.

### `ServiceContract.scala` — Lend Service Box Contract

- Guards the **Singleton / State NFT** pattern: the Service Box is valid if and only if it carries the `LendServiceNFT` (verified by **Token ID rule**).
- Enforces that the LST supply decrements by exactly one on Lending Box creation and increments by one on loan closure.
- Stores global protocol parameters (minimum box value for loans, service fee percentage, team address) as **Registers** (`R4`–`R7`), making them readable as **Data inputs** where mutation is not needed.
- Acts as an **Invariant** anchor: no lending pool Box is considered legitimate unless it carries an LST that originated from this service Box.

### `LendContracts.scala` — Lending Box Contract

- Validates that a Lending Box carries exactly one LST issued by the service.
- Enforces the **funding invariant**: the Box value may only increase up to the declared goal (stored in `R4`); excess ERG is returned to the sender via change output.
- Appends lender PK and amount pairs to `R6` (a collection register) on each partial funding transaction.
- On full funding, permits the borrower (PK in `R5`) to spend the Box, enforcing three outputs: service fee Box, Repayment Box, and borrower payout Box.
- On deadline expiry without full funding (Phase 3.1), permits a refund transaction that returns ERG proportionally to each recorded lender PK.

### `ProxyContracts.scala` — Proxy Contracts (×3)

- Implements the **proxy contract pattern**: each proxy Box holds user funds and metadata temporarily, acting as an unambiguous intent signal for off-chain bots to complete.
- **Creation Proxy:** Holds the borrower's creation fee and encoded loan parameters. Refundable to the borrower if not consumed within a block window.
- **Fund Lending Proxy:** Holds a lender's ERG and their PK. The contract ensures that if the funding transaction is not constructed correctly (wrong output Box, wrong register encoding), funds remain claimable by the lender after a timeout.
- **Fund Repayment Proxy:** Analogous to the fund lending proxy but targets the Repayment Box. Allows any third party to contribute, supporting the charitable repayment model.

All proxy contracts enforce a **minimum box value** floor consistent with Ergo's **Storage rent** mechanism, ensuring proxies remain spendable before rent reclamation.

---

## Integration Guide

### Off-Chain Perspective (Scala / AppKit)

The off-chain layer is written in Scala and follows the **Headless dApp** pattern: transaction building logic is separated from any UI or wallet connector, making it composable and testable.

**Transaction Construction Pattern:**

```scala
// Conceptual structure — actual API mirrors AppKit patterns
val serviceBox: InputBox = client.getBoxById(serviceBoxId)
val proxyBox: InputBox   = client.getUnspentBoxesByAddress(createProxyAddress).head

val lendingBox: OutBox = txBuilder.outBoxBuilder()
  .value(Parameters.MinFee)
  .tokens(new ErgoToken(lendServiceTokenId, 1))
  .registers(
    borrowerPK,      // R4
    fundingGoal,     // R5
    deadline,        // R6
    interestRate,    // R7
    lenderCollection // R8 