---
title: duckpools/off-chain-bot — Overview
description: DuckPools option pools — on-chain Black-Scholes pricing via Taylor series (ln, exp, sqrt, CDF), dual-asset option pool, volatility tracker
tags: [duckpools, off-chain-bot, defi, ergoscript, python]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/off-chain-bot"
project: duckpools-off-chain-bot
group: defi
priority: high
languages: [ergoscript, python]
contract_count: 7
pattern_match_count: 10
---
# duckpools Off-Chain Bot — Developer Overview

---

## Overview

The **duckpools off-chain bot** is the automation layer for the duckpools.io decentralized options protocol on Ergo. It implements a **headless dApp** pattern in which user-submitted orders — placed through the duckpools UI and locked into eUTXO Boxes on-chain — are discovered, validated, and fulfilled by an off-chain Python process that constructs and submits Transactions to the Ergo node. This separation of concerns allows the on-chain ErgoScript contracts to remain purely declarative while the off-chain bot handles order matching, Black-Scholes pricing hint computation, and liquidation monitoring.

The protocol's most technically distinctive feature is its **on-chain implementation of the Black-Scholes options pricing model** entirely within ErgoScript. Because ErgoScript cannot call external libraries or use floating-point arithmetic, the pricing logic approximates `ln(x)`, `e^x`, `sqrt(x)`, and the Normal CDF using Taylor series expansions with fixed-point precision (`p = 1,000,000`). The off-chain bot's Python layer pre-computes the necessary hints — square-root witnesses, CDF lookup indices, volatility readings — and injects them into Transaction Registers and Data inputs so that the on-chain contract can verify correctness without performing the full computation independently.

The system supports two primary pool products: a **dual-asset options pool** that prices and settles European-style call and put options using Black-Scholes, and a **rolling-window volatility oracle** that maintains a 100-sample ring buffer of log-returns, computing annualized volatility every 292 blocks. Together these components form a self-contained, permissionless options market where any operator can run an off-chain bot, earn processing fees, and contribute to decentralized order fulfillment.

---

## Architecture

### Component Map

```
┌─────────────────────────────────────────────────────────┐
│                    Ergo Blockchain                       │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Pool Box   │  │  Option Box  │  │ Std-Dev Oracle│  │
│  │ (State NFT) │  │ (per option) │  │ (ring buffer) │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                │                   │          │
│  ┌──────┴──────────────┴───────────────────┴──────┐    │
│  │           Proxy Contract Boxes                   │    │
│  │  add_liquidity · withdraw_liquidity · repayment  │    │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────┘
                          │ Ergo Node RPC
┌─────────────────────────▼───────────────────────────────┐
│                  Off-Chain Bot (Python)                  │
│                                                         │
│  main.py ──► helpers/platform_functions.py              │
│     │                                                   │
│     ├──► optionPools/actions/add_liquidity.py           │
│     ├──► optionPools/actions/withdraw_liquidity.py      │
│     ├──► optionPools/actions/standard_deviation.py      │
│     ├──► optionPools/bootstrapping/buy_option.py        │
│     ├──► optionPools/bootstrapping/sell_option.py       │
│     └──► optionPools/bootstrapping/exercise_option.py   │
│                                                         │
│  client_consts.py · option_consts.py · consts.py        │
│  setup.py (one-time) · collection.py (teardown)         │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Discovery.** `main.py` polls the Ergo node (and optionally the explorer) for unspent Boxes whose ErgoTree matches known duckpools contract addresses.
2. **Hint computation.** For trade/swap operations requiring Black-Scholes pricing, the Python layer computes `ln(S/K)`, `sqrt(t)`, `(S/K)^(1/8)`, and the relevant Normal CDF index lookup values using the same Taylor series logic mirrored from the on-chain contracts.
3. **Transaction construction.** The bot assembles an unsigned Transaction with the appropriate Inputs, Data inputs (price oracle box, volatility oracle box, CDF lookup boxes), Outputs, and Register values — including the computed hints placed in R6 and R7 of the pool Box.
4. **Signing and submission.** The unsigned Transaction is submitted to the node's `/wallet/transaction/sign` endpoint, then broadcast via `/transactions`.
5. **State machine continuation.** The successor pool Box carries the same State NFT (Singleton), preserving the contract's ErgoTree and all invariant tokens.

---

## Smart Contracts

### `pool` (Options Pool State Machine)

The central multi-stage contract managing ERG and Y-token reserves, LP token minting/burning, and option issuance. It enforces:

- **Script preservation:** Successor Box `propositionBytes` must equal SELF's, implementing the State machine continuation invariant.
- **Singleton / State NFT:** Pool NFT at `tokens(0)` must appear in every successor Box, preventing pool identity spoofing.
- **Black-Scholes validation (trade path, `dataInputs.size > 2`):** Verifies d1/d2 using inline `lnX()`, `eX()`, `isValidSquareRoot()`, and `isValidTripleSquareRoot()` Taylor-series functions. The off-chain bot supplies witnesses in R6 (`[curr_height, y, yp, sqrtT]`) and CDF indices in R7.
- **Deposit path (`dataInputs.size ≤ 2`):** Simpler invariant — LP token supply unchanged, reserves non-decreasing.
- **Register layout:**

| Register | Type | Purpose | Mutable |
|----------|------|---------|---------|
| R4 | `Long` | Risk-free rate (r) | No |
| R5 | `Coll[Long]` | Strike prices and expiry data | Yes |
| R6 | `Coll[Long]` | Off-chain computation hints: `[height, y, yp, sqrtT]` | Yes |
| R7 | `Coll[Int]` | CDF lookup indices `[CDFIndex1, CDFIndex2]` | Yes |

### `optionBox` (European Option Lifecycle)

A per-option Box enforcing three mutually exclusive state transitions gated on `HEIGHT`:

- **Before expiry (`HEIGHT < t`):** Requires `proveDlog(userPK)` (R6); interacts with pool state to update counter token at `tokens(3)`.
- **Exercise window (`t ≤ HEIGHT ≤ t + optionExerciseRange`):** Holder signature required; repayment Box sent to `repaymentAddress` carrying option token, Y-asset amount (`optionSize * strikePrice / optionUnitSize`), and original Box ID in R4.
- **After expiry (`HEIGHT > t + optionExerciseRange`):** Permissionless; forfeited ERG returned to pool via repayment Box.

Register layout:

| Register | Type | Purpose |
|----------|------|---------|
| R4 | `Long` | Strike price (K) |
| R5 | `Long` | Expiry block height (t) |
| R6 | `GroupElement` | Holder's Sigma protocol public key |

### `repayment` (Option Settlement)

Validates atomic settlement when a user repays into the pool. Key invariants:

- `PoolNft` must appear in both `INPUTS(0)` and `OUTPUTS(0)` (Singleton continuity).
- Option token count at `tokens(