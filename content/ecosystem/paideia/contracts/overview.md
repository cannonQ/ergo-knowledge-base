---
title: paideiadao/paideia-contracts — Overview
description: Paideia DAO contracts — staking, voting, proposal lifecycle, treasury management, config boxes
tags: [paideiadao, paideia-contracts, dao, ergoscript, python]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
project: paideiadao-paideia-contracts
group: dao
priority: high
languages: [ergoscript, python]
contract_count: 25
pattern_match_count: 0
---
# Paideia Contracts — Developer Overview

## Overview

Paideia Contracts is the on-chain backbone of the Paideia DAO platform on Ergo, implementing a complete governance lifecycle in ErgoScript — from token staking and reward emission to proposal voting, action execution, and treasury management. Each DAO instantiated through Paideia receives a suite of authenticated, interacting contract boxes that collectively enforce the rules of decentralized governance without any trusted intermediary. The project is published as both a reference implementation and a Python library (`pip install paideia-contracts`), making it accessible for off-chain tooling, bot development, and protocol integration.

Within the Ergo ecosystem, Paideia occupies the role of a full-stack DAO framework analogous to Compound or Aragon on EVM chains, but designed natively around eUTXO semantics. Rather than relying on shared mutable state, every protocol component is a discrete Box whose validity is proven at spend time through ErgoScript predicates and cryptographic proofs (Sigma protocols). The multi-stage contract design means that individual boxes — staking state, stake pool, emission, config, treasury — form a directed graph of state transitions, each transition atomically advancing the protocol with all invariants enforced on-chain.

Paideia also ships EIP-6 protocol specifications alongside every contract, making it an example of documentation-driven smart contract development on Ergo. The Python library wraps contract construction, AVL tree proof generation, and transaction assembly, enabling headless dApp patterns where off-chain bots monitor the chain and submit protocol-advancing transactions without user interaction for routine operations such as emission and compounding.

---

## Architecture

### Module Hierarchy

```
Paideia (root registry)
│   Mints DAO creation tokens; verifies new DAOs meet platform requirements
│
└── DAO Module
    │   Core state box (State NFT); controls treasury and sub-module creation
    │   Config boxes act as on-chain oracles for all sub-contracts
    │
    ├── Staking Module
    │   ├── stakeState      — Central state machine (Singleton / State NFT)
    │   ├── stakePool       — Token emission reserve (Singleton / State NFT)
    │   ├── emission        — Per-cycle distribution box (Singleton)
    │   ├── stakingIncentive— Operator reward pool; dust consolidation
    │   ├── stake           — Per-user staking position box
    │   ├── stakeProxy      — User intent box: initial stake
    │   ├── addStakeProxy   — User intent box: add to existing stake
    │   └── unstakeProxy    — User intent box: full or partial withdrawal
    │
    ├── Plasma Staking Module
    │   └── plasmaStaking   — AVL-tree-based staking state machine (alternative backend)
    │
    ├── Proposals Module
    │   └── Proposal boxes with associated Action boxes
    │
    ├── Voting Module
    │   └── Vote boxes holding stake key; use stake box as data input
    │
    ├── Config Module
    │   └── Config boxes: on-chain parameter oracles for all contracts
    │
    └── Profit Sharing Module
        └── Hooks into staking module for automatic profit distribution
```

### Data Flow: Staking Lifecycle

```
User Wallet
    │  creates
    ▼
stakeProxy / addStakeProxy / unstakeProxy
    │  consumed by off-chain bot in
    ▼
State-advancing Transaction
    │  inputs: stakeState (INPUTS(0)) + proxy box
    │  outputs:
    ├─► new stakeState box     (State NFT forwarded, counters updated)
    ├─► new / updated stake box (Stake Token NFT + DAO tokens)
    ├─► user wallet box         (receives stake key NFT)
    ├─► stakingIncentive box    (protocol fee)
    ├─► executor reward box     (off-chain bot compensation)
    └─► miner fee box
```

### Data Flow: Emission Cycle

```
(Time trigger — off-chain bot)
    │
    ▼
Emit Transaction
    INPUTS:  stakeState, stakePool, emission, stakingIncentive
    OUTPUTS: new stakeState, new stakePool, new emission, fee box,
             new stakingIncentive, operator box

    ▼
Compound Transaction (per batch of stake boxes)
    INPUTS:  emission, [stake box × N], stakingIncentive
    OUTPUTS: new emission, [new stake box × N], operator box, miner fee
```

### Box Relationships

| Box | Singleton / State NFT | Depends On | Consumed By |
|---|---|---|---|
| `stakeState` | Yes — Stake State NFT | stakeProxy outputs | emit, stake, unstake txs |
| `stakePool` | Yes — Stake Pool NFT | stakeState in emit tx | emit tx |
| `emission` | Yes — Emission NFT | stakeState + stakePool | compound tx |
| `stakingIncentive` | No (value pool) | all tx types | consolidate, emit, compound |
| `stake` | Yes — Stake Token NFT | stakeState | compound, unstake |
| `plasmaStaking` | Yes — State NFT | AVL tree proofs | stake, change, unstake, snapshot, compound |

Config boxes are referenced as **data inputs** by proposal and voting contracts, never consumed, acting as on-chain parameter oracles.

---

## Smart Contracts

### `stakeState.es` — Core State Machine

The central Singleton box governing the staking protocol. Holds a Stake State NFT (token index 0) and a Stake Token minting authority (token index 1). Register R4 encodes the full protocol state as `Coll[Long]`: `[totalAmountStaked, checkpoint, stakers, checkpointTimestamp, cycleDuration]`.

Enforces invariants across four transaction types:

- **Stake Tx**: Detects initial vs. add-stake by checking whether `OUTPUTS(1).tokens(0)._1 == stakeTokenID` and whether the Stake Token supply decreases. Increments `totalAmountStaked` and `stakers` (initial only); updates `checkpoint`.
- **Add-Stake Tx**: Validates existing stake box in inputs; increments `totalAmountStaked`, leaves `stakers` unchanged.
- **Emit Tx**: Advances `checkpoint` and `checkpointTimestamp` by `cycleDuration`; verifies Stake Pool and Emission boxes are present.
- **Unstake Tx (full/partial)**: Decrements `totalAmountStaked` by withdrawn amount; decrements `stakers` on full unstake; validates Stake Key in proxy box matches stake box R5.

**Key invariant**: Every output stakeState box must preserve the ErgoTree (`propositionBytes`), the State NFT, the Stake Token ID, `cycleDuration`, and exactly two tokens.

---

### `stakePool.es` — Emission Reserve

Singleton box holding DAO tokens reserved for emission. R4 (`Long`) encodes the per-cycle emission amount; R5 (`Coll[Byte]`) holds the Stake Pool Key for governance-controlled withdrawal.

- **Emit Tx**: Validates `INPUTS(0)` holds the Stake State NFT and `INPUTS(1)` is SELF. Computes `emissionFee = emissionAmount / 100` (1% to `EmissionFeeAddress`). Decrements token reserve by `emissionAmount`; if reserve exhausted, token array shrinks to NFT only.
- **Remove Funds Tx**: Permissioned by Stake Pool Key presence in any output; allows governance withdrawal.

**Token conservation**: `newStakePoolTokens = SELF.tokens(1)._2 + emissionDust - emissionAmount`. Dust accounting prevents rounding loss.

---

### `emission.es` — Distribution State Box

Singleton managing per-cycle reward distribution. R4 encodes `[totalAmountStaked, checkpoint, stakers, emissionAmount]`.

- **Emit Tx**: Receives `emissionAmount - emissionFee` DAO tokens from stakePool. Copies state snapshot from stakeState. Enforces `