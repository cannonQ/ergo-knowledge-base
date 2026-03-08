---
title: DjedAlliance/Djed-Ergo — Overview
description: SigmaUSD / AgeUSD — stablecoin protocol, headless dApp pattern, reserve management
tags: [djedalliance, djed-ergo, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/DjedAlliance/Djed-Ergo"
project: djedalliance-djed-ergo
group: defi
priority: high
languages: [ergoscript, scala]
contract_count: 0
pattern_match_count: 0
---
# DjedAlliance/Djed-Ergo: Developer Overview

---

## Overview

The **Djed-Ergo** project (originally authored as **AgeUSD**) is the reference implementation of the **AgeUSD / SigmaUSD stablecoin protocol** on the Ergo blockchain, developed in a three-way partnership between the Ergo Foundation, EMURGO, and IOG. It is a crypto-backed, algorithmic stablecoin protocol that operates entirely without collateralized debt positions (CDPs), instead relying on a reserve management model enforced directly through **ErgoScript** smart contracts and the **eUTXO** model. The protocol supports two synthetic assets: a price-stable coin (AgeUSD / SigmaUSD) pegged to the US dollar, and a reserve share token (ReserveCoin / SigmaRSV) that gives holders leveraged exposure to ERG. Reserve ratios, price pegging, fee collection, and minting/redemption authorization are all expressed as on-chain **invariants** enforced at the contract level rather than through dynamic liquidation bots.

A central design motivation is resilience under adversarial conditions—specifically, the elimination of liquidation cascades (as seen in MakerDAO's "Black Thursday" event). Because there are no CDP liquidation events, the protocol does not depend on third-party keepers posting transactions under congestion. All economic safety guarantees are encoded in the reserve ratio mathematics and are enforced atomically within each **Transaction**, making the protocol's correctness a function of the ErgoScript constraints rather than of off-chain liveness.

The repository is structured as a trio of interacting layers: the **AgeUSD Specs** (formal EUTXO protocol design), the **AgeUSD Smart Contracts** (ErgoScript on-chain logic), and the **AgeUSD Headless dApp** (a portable Scala library for off-chain state reading and action construction). This layered separation has made Djed-Ergo one of the canonical examples of the **headless dApp pattern** in the Ergo ecosystem, and it continues to serve as the reference architecture for DeFi protocol developers on Ergo.

---

## Architecture

The system is organized into three distinct layers that interact through well-defined interfaces:

### Protocol / Specification Layer (`ageusd-specs`)

Versioned EUTXO-model specifications (`v0.1` onward) that define:

- The **state machine** governing all valid protocol transitions (mint stablecoin, mint reservecoin, redeem stablecoin, redeem reservecoin).
- The **invariants** that must hold across every transition: minimum reserve ratio, maximum reserve ratio (ceiling on reservecoin minting), and correct fee accounting.
- The roles of all **Box** types in the protocol and which registers they use.

### Smart Contract Layer (`ageusd-smart-contracts`)

ErgoScript contracts deployed on-chain. The central protocol state is maintained in a **Singleton / State NFT** box—a single UTXO identified by a unique **Token ID** that acts as the authoritative on-chain state root. The contracts enforce:

- Valid state transitions via spending conditions on the state box.
- Oracle data consumption through **Data inputs** (read-only box references) from the ERG/USD oracle pool.
- Fee splitting between the protocol reserve and frontend implementors.
- Reserve ratio bounds at every mint/redeem operation.

### Off-Chain Layer (`ageusd-headless` + `ageusd-cli`)

A **headless dApp** Scala library that provides:

- **State reading**: Queries the current state box (identified by the State NFT) to derive all protocol metrics (base reserves, liabilities, equity, circulating supply, nominal prices).
- **Action construction**: Assembles unsigned `Transaction` objects for each of the four protocol actions, populating all required input boxes, data inputs, output boxes with correct values and tokens.
- **Helper calculations**: Cost/amount estimates for minting or redeeming, enabling frontend UIs to show users accurate previews before submitting.
- **CLI frontend** (`ageusd-cli`): A reference command-line implementation that uses an Ergo Node for UTXO-set scanning and transaction posting.

### Data Flow

```
ERG/USD Oracle Pool Box (Data Input)
         │
         ▼
[State NFT Box] ──(spending transaction)──► [New State NFT Box]
         │                                           │
    (read by Headless dApp)                  (enforces invariants via ErgoScript)
         │
         ▼
Headless dApp (Scala)
  ├── State reading (liabilities, equity, prices)
  ├── Action builders (unsigned Tx construction)
  └── CLI / GUI / bot consumers
```

The oracle box is consumed as a **Data input**—it is referenced within the transaction's context but not spent, so its ERG/USD price datum is available to the ErgoScript **context** during contract evaluation without modifying the oracle's UTXO.

---

## Smart Contracts

All contracts are written in **ErgoScript** and versioned from `v0.1` upward inside `ageusd-smart-contracts/`. The primary contracts are:

### Bank Contract (State Box / Singleton)

The core contract guarding the **State NFT** box, which holds:

- The entire ERG reserve (nanoERGs in the box value).
- The **Native tokens** representing circulating SigmaUSD and SigmaRSV supplies tracked via token quantities in the box.
- Protocol parameters (fee rates, reserve ratio bounds) encoded in **Registers** (R4–R7).

**Spending conditions enforced by the contract:**

| Condition | Description |
|---|---|
| State NFT continuity | Output state box must carry the same State NFT Token ID (singleton enforcement). |
| Reserve ratio lower bound | Minting SigmaUSD is only permitted if `reserves / liabilities ≥ minReserveRatio` after the action. |
| Reserve ratio upper bound | Minting SigmaRSV is only permitted if `reserves / liabilities ≤ maxReserveRatio` after the action. |
| Correct price calculation | Amount of ERG in/out must match the oracle-supplied exchange rate read from the Data input. |
| Fee routing | Protocol fee ERG must remain in the bank box; frontend implementor fee must be sent to the address provided in **Context extension** by the calling transaction. |
| Oracle validity | The Data input box must carry the correct oracle pool NFT Token ID to prevent price spoofing. |

### Token Logic (Token ID Rule)

SigmaUSD and SigmaRSV are **Native tokens** whose supply is managed entirely by the bank contract. The contract verifies token deltas in inputs and outputs to ensure exactly the declared quantity is minted or burned in each transaction, implementing the **Token ID rule** to prevent counterfeit issuance.

### No Separate Liquidation Contract

Because there are no CDPs, there is no liquidation contract. Stability guarantees emerge from the reserve ratio invariants alone, eliminating an entire attack surface.

---

## Integration Guide

### Prerequisites

- **Ergo Node** (for UTXO-set scanning and transaction submission) or a compatible **Explorer API**.
- **Scala / SBT** build environment for the `ageusd-headless` library.
- Access to the deployed **State NFT Token ID** and **Oracle Pool NFT Token ID** for the target network.

### Using the Headless dApp Library

The `ageusd-headless` Scala library is the primary integration surface. It is intentionally decoupled from any specific wallet or node implementation—it produces unsigned transactions and raw box representations that callers are responsible for signing and submitting.

**Step 1: Locate the State Box**

Find the current State NFT box by scanning the UTXO set for the known State NFT Token ID. The headless dApp provides helpers that accept a box-fetching function as a parameter, keeping the library node-agnostic.

```scala
// Pseudocode — inject your own box-fetching function
val ageusdBank: AgeUSDBank = AgeUSDBank.fromStateBox(
  stateBox      = fetchBoxByNFT(STATE_NFT_TOKEN_ID),
  oracleBox     = fetchBoxByNFT(ORACLE_POOL_NFT_TOKEN_ID),
  params        = ProtocolParameters.default
)
```

**Step 2: Read Protocol State**

```scala
val