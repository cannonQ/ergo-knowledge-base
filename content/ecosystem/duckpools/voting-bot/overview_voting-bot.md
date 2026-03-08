---
title: duckpools/voting-bot — Overview
description: "DuckPools DAO voting bot \u2014 off-chain governance state machine: proposals, vote counting, treasury distribution"
tags: [duckpools, voting-bot, defi, python]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/voting-bot"
project: duckpools-voting-bot
group: defi
priority: medium
languages: [python]
contract_count: 0
pattern_match_count: 11
---
# duckpools/voting-bot — Developer Overview

---

## Overview

The **duckpools/voting-bot** is the off-chain governance engine for the DuckPools DAO on Ergo. It implements a fully automated **state machine** that shepherds DAO proposals through their complete lifecycle — from submission and vote counting through to treasury distribution and optional airdrop disbursement — without requiring manual operator intervention at each transition. The bot monitors the Ergo blockchain continuously, detects relevant Boxes matching governance contracts, and constructs, signs, and submits the appropriate Transactions to advance state.

Within the Ergo DeFi ecosystem, this project occupies the **off-chain bot** role that is characteristic of eUTXO-based dApp architectures: because Ergo's execution model is stateless and transaction-driven rather than contract-driven, complex multi-step workflows must be orchestrated by an off-chain process that reads on-chain state, satisfies ErgoScript guard conditions, and produces valid spending Transactions. The voting-bot is therefore the authoritative keeper of governance liveness — if it is offline, proposals stall on-chain but on-chain funds remain secure under their ErgoScript guards.

The bot is written in Python and communicates with a local or remote Ergo **full node** via its REST API, using node-side wallet signing rather than raw key management. This makes it a practical reference implementation for developers building similar off-chain coordination bots on Ergo: it demonstrates how to sequence multi-stage contract interactions, handle the **Singleton / State NFT** pattern for unique mutable state, and perform conditional treasury disbursement atomically within a single Transaction.

---

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│  (event loop — polls chain, dispatches state handlers)  │
└────────────────┬────────────────────────────────────────┘
                 │ dispatches to
        ┌────────▼──────────────────────────┐
        │         State Handlers            │
        │  states/new_proposal.py           │
        │  states/initiation.py             │
        │  states/counting.py               │
        │  states/validation.py             │
        └────────┬──────────────────────────┘
                 │ uses
        ┌────────▼──────────────────────────┐
        │       helpers/                    │
        │  node_calls.py     — Node REST    │
        │  platform_functions.py — domain   │
        └────────┬──────────────────────────┘
                 │
        ┌────────▼──────────────────────────┐
        │  aidrop_deposit.py                │
        │  collection.py                    │
        │  consts.py                        │
        └───────────────────────────────────┘
```

### Core Modules

| Module | Responsibility |
|---|---|
| `main.py` | Top-level polling loop; reads current on-chain state; routes to the correct state handler |
| `consts.py` | All protocol constants: contract addresses, Token IDs, timing parameters, treasury thresholds, airdrop parameters |
| `helpers/node_calls.py` | Thin wrapper around the Ergo node REST API — Box queries, Transaction submission, `sign_tx` calls |
| `helpers/platform_functions.py` | Domain-level helpers: proposal Box discovery, counter_box construction, treasury accounting |
| `states/new_proposal.py` | Handles the **New Proposal** state: validates a submitted proposal Box, creates the counter_box, signs and submits |
| `states/initiation.py` | Handles **Initiation**: sets up the initial on-chain voting epoch, initialises the counter_box, anchors treasury reference |
| `states/counting.py` | Handles **Vote Counting**: aggregates votes from voter Boxes into the counter_box via signed Transactions |
| `states/validation.py` | Handles **Validation**: finalises the vote count, determines pass/fail, triggers treasury or rejection path |
| `aidrop_deposit.py` | Constructs and submits the airdrop disbursement Transaction after a successful proposal |
| `collection.py` | Token/NFT collection utilities used across state transitions |

### Data Flow

```
Chain (Boxes)
    │
    ▼
node_calls.py — getUnspentBoxes(), getBoxById()
    │
    ▼
main.py — identify current state via counter_box Registers
    │
    ▼
states/[current_state].py
    ├── reads: proposal Box, counter_box, voter Boxes (Data inputs where read-only)
    ├── builds: unsigned Transaction (inputs, outputs, context extensions)
    ├── calls: node_calls.sign_tx()
    └── calls: node_calls.submit_tx()
    │
    ▼
New Boxes on chain (updated counter_box, treasury output, airdrop output)
```

**State identity** is tracked via a **Singleton / State NFT** — a unique Token whose Token ID is fixed at genesis and travels with the `counter_box` through every state transition. The bot locates the current authoritative state by finding the unspent Box holding this NFT.

---

## Smart Contracts

> *The README does not publish full ErgoScript source in this repository; the following is inferred from the module structure, naming conventions, and Ergo architectural norms.*

### Proposal Box Contract

Guards a submitted governance proposal. Its ErgoScript enforces:
- The counter_box NFT must appear in the same Transaction's inputs or outputs (ensuring the proposal can only be advanced by the authorised state machine).
- Proposal metadata (title, description hash, voting deadline, quorum threshold) is stored in **Registers** R4–R7.
- Spending is only permitted when the bot-controlled key co-signs (Sigma protocol `proveDlog`), preventing arbitrary spending.

### Counter Box Contract (State Machine Box)

The central mutable state carrier. Key invariants enforced by ErgoScript:
- The **Singleton / State NFT** must be preserved in the self-output (Token ID rule: same Token ID, same quantity).
- R4 encodes the current **state enum** (NEW_PROPOSAL / INITIATION / COUNTING / VALIDATION).
- R5 accumulates the running vote tally.
- R6 carries the current epoch deadline (block height).
- **Storage rent** considerations mean the bot must ensure the Box value meets the **Minimum box value** at every transition to prevent the Box being claimed by miners after the storage rent period.

### Treasury Distribution Contract

Holds DAO funds. Spending conditions require:
- A valid passing-vote outcome as proven by the counter_box output (used as a **Data input** to read state without spending it where the pattern allows, or as a spent input where atomicity demands it).
- The correct treasury recipient address encoded in the proposal Box Registers.
- The bot key co-signature.

### Airdrop Contract

Governs per-voter reward distribution post-proposal. Enforces proportional disbursement relative to recorded vote weight; the `aidrop_deposit.py` module constructs the fan-out Transaction satisfying this guard.

---

## Integration Guide

### Prerequisites

- Ergo full node with wallet unlocked (`/wallet/unlock`), accessible at a configurable endpoint.
- The DAO's governance NFT Token ID and contract addresses configured in `consts.py`.
- Python 3.x environment with dependencies installed.

### Node Interaction Pattern

All chain reads and writes go through `helpers/node_calls.py`. The primary patterns used:

```python
# Box discovery — find the live counter_box by NFT Token ID
boxes = node_calls.get_unspent_boxes_by_token_id(COUNTER_NFT_TOKEN_ID)

# Build an unsigned transaction dict (Ergo node /transactions/unsigned endpoint style)
unsigned_tx = {
    "inputs": [...],        # Box IDs to spend
    "dataInputs": [...],    # Read-only Data inputs (Box IDs)
    "outputs": [...],       # New Box descriptors with value, ergoTree, assets, additionalRegisters
}

# Sign via node wallet (node holds the bot key)
signed_tx = node_calls.sign_tx(unsigned_tx)