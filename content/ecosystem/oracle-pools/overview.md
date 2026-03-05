---
title: ergoplatform/oracle-core — Overview
description: Oracle pool v2 architecture, connector patterns, data posting
tags: [ergoplatform, oracle-core, core-protocol, rust]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergoplatform/oracle-core"
project: ergoplatform-oracle-core
group: core-protocol
priority: high
languages: [rust]
contract_count: 0
pattern_match_count: 4
---
# Oracle Core v2 — Developer Overview

---

## Overview

Oracle Core v2 is the reference off-chain implementation of the **EIP-0023** oracle pool protocol on the Ergo blockchain. It orchestrates a decentralized network of independent data providers (oracles) that collectively agree on an off-chain value — such as ERG/USD, ERG/XAU, or ERG/ADA exchange rates — and post that consensus value on-chain inside a **pool box** (eUTXO). Each oracle operator runs a dedicated instance of this daemon, which monitors the chain, collects data from a configured source, posts individual **datapoint boxes**, and participates in the multi-stage refresh cycle that updates the canonical pool box.

Within the Ergo ecosystem, oracle pools are foundational infrastructure. SigmaUSD, Dexy, and any protocol requiring a trusted price feed consume the pool box as a **data input** — a read-only reference to a box that does not need to be spent in the consuming transaction. This design means that dozens of DeFi transactions per block can reference the same pool box simultaneously without contention, a direct benefit of Ergo's eUTXO model. Oracle Core v2 supersedes the v1 design with a cleaner token-based incentive model, on-chain governance for parameter updates, and a modular connector architecture that makes it straightforward to add new data sources.

The project is written entirely in Rust and ships as a single binary (`oracle-core`) with subcommands covering the full operator lifecycle: bootstrapping a new pool, joining an existing one, posting data, voting on upgrades, extracting reward tokens, and verifying contract hashes against the canonical EIP-0023 specification. It depends on a locally accessible Ergo full node (with the transaction-creation API enabled) and communicates with it over HTTP using the node's REST API.

---

## Architecture

### High-Level Data Flow

```
External Data Source
        │
        ▼
  DataPointSource (connector)
        │  f64 / integer value
        ▼
Oracle Core Daemon  ──── Ergo Node REST API ────► Ergo P2P Network
        │                                               │
        │   reads chain state                           │
        ▼                                               ▼
  State Machine (OraclePool)                    On-Chain Boxes
   ├── PoolBox (Singleton/State NFT)
   ├── RefreshBox
   ├── OracleBox (per oracle)
   ├── BallotBox (per oracle, governance)
   └── UpdateBox
```

### Key Components

#### `core/src/state.rs` — Oracle Pool State Machine

The central abstraction is the **OraclePool** state machine. It reads the current set of eUTXO boxes from the node, classifies them by their **Token ID** (pool NFT, oracle token, refresh token, update token, ballot token, reward token), and determines which **action** is due in the current block. State transitions are strictly driven by on-chain box contents — there is no off-chain mutable state beyond configuration.

Possible states and transitions:

| Current State | Condition | Action |
|---|---|---|
| `WaitingForDataPoint` | Oracle's own datapoint box is stale or absent | `PostDataPoint` tx |
| `WaitingForRefresh` | Epoch length elapsed + min_data_points posted | `Refresh` tx |
| `NeedsVote` | Pending update proposal | `VoteUpdate` tx |
| `NeedsUpdate` | Voting threshold met | `UpdatePool` tx |

#### `core/src/actions.rs` — Transaction Builders

Each state transition maps to a transaction builder function. These functions assemble Ergo transactions by:

1. Selecting input boxes (pool box, oracle box, refresh box) from the node's UTXO set.
2. Attaching the correct **Native tokens** in output boxes.
3. Setting the appropriate **Registers** (R4–R7) on output boxes to carry oracle data, epoch counters, and reward accounting.
4. Including required **data inputs** (e.g., the pool box referenced during a datapoint post is a data input to the refresh transaction).
5. Computing **Minimum box value** and **Minimum transaction fee** to ensure outputs are valid.

#### `core/src/connectors/` — Data Source Connectors

Each connector implements a `DataPointSource` trait returning a single integer value (e.g., nanoERG per USD). The connector is selected at bootstrap time via `data_point_source` in `bootstrap.yaml`. Connectors are stateless and are called once per epoch to produce the oracle's contribution.

#### `core/src/api.rs` — HTTP API / Prometheus Metrics

Exposes a local REST API (default port 9010) for operator introspection — current pool state, oracle box contents, accumulated reward tokens. An optional Prometheus metrics endpoint (configurable port) enables Grafana dashboards for fleet monitoring.

#### `core/src/cli_commands/` — Operator CLI

Subcommands implement the full operator workflow. Each subcommand is a thin wrapper that resolves configuration, queries node state, and invokes the appropriate action builder or contract deployment routine.

### Box Relationships

```
PoolBox (holds Pool NFT)
  ├── R4: current pool data value (Long)
  ├── R5: epoch counter (Int)
  └── data-input-of → consuming DeFi transactions

RefreshBox (holds Refresh Token)
  └── guards the refresh logic (min_data_points, max_deviation_percent, epoch_length)

OracleBox (holds Oracle Token + Reward Tokens)
  ├── R4: oracle's public key (GroupElement)
  ├── R5: epoch counter at post time (Int)
  └── R6: posted data value (Long)

BallotBox (holds Ballot Token)
  ├── R4: oracle's public key (GroupElement)
  ├── R5: new pool box contract hash (Coll[Byte])
  └── R6: update box creation height (Int)

UpdateBox (holds Update Token)
  └── guards governance update, checks min_votes ballot threshold
```

---

## Smart Contracts

Oracle Core v2 implements the contract suite defined in **EIP-0023**. All contracts are written in **ErgoScript** and compiled to **ErgoTree** at bootstrap time. Contract hashes can be verified against EIP-0023 with `oracle-core print-contract-hashes`.

### Pool Contract

Guards the **pool box** (identified by the Pool NFT — a **Singleton / State NFT**). Enforces:
- The box can only be updated ("refreshed") by a transaction that also spends the **RefreshBox**.
- The output pool box retains the Pool NFT.
- R4 of the output pool box is set to the median of valid oracle datapoints.

The Pool NFT implements the **Token ID rule**: because it was minted in a specific bootstrap transaction with quantity 1, its uniqueness is guaranteed by Ergo's native token ledger — no ErgoScript check on creation height is needed.

### Refresh Contract

Guards the **refresh box** (holds Refresh Token). Enforces:
- At least `min_data_points` valid oracle boxes are presented as inputs.
- Each oracle box's epoch counter (R5) matches the current epoch.
- Datapoints outside `max_deviation_percent` of the median are excluded.
- `epoch_length` blocks have elapsed since the last refresh (checked via **ErgoScript context** `HEIGHT`).
- Reward tokens are distributed to contributing oracle boxes.

The deviation filter and median computation are expressed as ErgoScript predicates over the collection of input oracle boxes using `INPUTS.filter(...)` and sorting/fold operations — a notable example of **multi-stage contract** logic encoded entirely on-chain.

### Oracle Contract

Guards each **oracle box** (holds Oracle Token + accumulated Reward Tokens). Enforces:
- The spending oracle (identified by the GroupElement in R4 and verified via **Sigma protocols** — specifically `proveDlog`) signs the transaction.
- On a datapoint post, the output oracle box retains exactly 1 Oracle Token and at least 1 Reward Token (required by the Refresh contract).
- On reward extraction, the owner can sweep reward tokens minus 1 to any address.

### Ballot Contract

Guards each **ballot box**. Enforces:
- The oracle owner signs the vote.
- R5 carries the