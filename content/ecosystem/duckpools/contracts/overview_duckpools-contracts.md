---
title: duckpools/lend-protocol-contracts — Overview
description: Duckpools — lending pools, collateralized borrowing, interest rate algorithms, liquidation, treasury voting
tags: [duckpools, lend-protocol-contracts, defi, ergoscript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
project: duckpools-lend-protocol-contracts
group: defi
priority: high
languages: [ergoscript]
contract_count: 66
pattern_match_count: 0
---
# DuckPools Lend Protocol Contracts — Developer Overview

## Overview

DuckPools is a non-custodial, collateralized lending protocol built on the Ergo blockchain, implemented entirely in ErgoScript. The protocol enables users to deposit ERG into shared lending pools in exchange for LP tokens (lend tokens), and allows borrowers to lock collateral assets to draw ERG loans against them. All protocol logic—including interest accrual, collateral valuation, liquidation, and repayment—is enforced on-chain through a coordinated system of eUTXO contracts, with no trusted intermediary or upgradeable proxy pattern.

The protocol's role in the Ergo DeFi ecosystem is significant: it introduces on-chain compound interest tracking through a hierarchical parent/child interest rate state machine, collateral pricing via Spectrum DEX pool boxes used as data inputs, and a tiered service fee model. Liquidation logic is embedded directly in the collateral contract, allowing permissionless liquidators to earn rewards when a borrower's LTV ratio breaches the configured threshold. This design makes DuckPools a composable primitive that other Ergo applications can integrate with through standard eUTXO transaction patterns.

The protocol follows a strict headless dApp architecture. All state-sensitive operations—interest rate updates, loan origination, partial repayments, and liquidations—are initiated by off-chain bots that construct and submit transactions satisfying the on-chain script invariants. Proxy contracts handle the asynchronous, multi-step nature of user requests by acting as intermediate eUTXO stages that either complete successfully or time out and return funds to users after a configurable block height deadline.

---

## Architecture

### Component Map

```
┌──────────────────────────────────────────────────────────────────┐
│                        Lending Pool (lendPool)                    │
│  Pool NFT (Singleton) │ Lend Tokens │ Borrow Tokens │ ERG Value  │
└───────────┬──────────────────────────────────┬───────────────────┘
            │ data input                        │ loan origination
            ▼                                  ▼
┌────────────────────┐              ┌─────────────────────────────┐
│  Interest Rate     │              │  Collateral Contract         │
│  Child Box         │◄─────────── │  (per-loan state machine)    │
│  (history: R4)     │  data input  │  Collateral + Borrow Tokens  │
└────────┬───────────┘              └──────────────┬──────────────┘
         │ aggregated by                           │ repayment
         ▼                                        ▼
┌────────────────────┐              ┌─────────────────────────────┐
│  Parent Interest   │              │  Repayment Contract          │
│  Box (accumulator) │              │  (validates pool state update)│
└────────────────────┘              └─────────────────────────────┘

       Proxy Layer (one box per pending user request)
┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  proxyLend   │  │ proxyBorrow  │  │  proxyRepay     │  │  proxyWithdraw  │
│  proxyPartial│  │              │  │  proxyPartialR  │  │                 │
└──────────────┘  └──────────────┘  └─────────────────┘  └─────────────────┘
```

### Key Components and Relationships

**Pool Box (`lendPool` contract)**
The central singleton box, identified by the Pool NFT (State NFT). It holds the protocol's pooled ERG, the full supply of lend tokens (LP shares) and borrow tokens (loan trackers). Every deposit, withdrawal, and loan origination passes through this box, which enforces the core lend token valuation invariant and service fee accounting.

**Collateral Box (`collateralContract`)**
One box per active loan. Holds the borrower's collateral tokens and a quantity of borrow tokens equal to the outstanding loan amount. Registers encode the borrower's public key, the interest rate indices at origination, liquidation thresholds and penalties, and the DEX pool NFT for collateral pricing. This box is a self-contained loan state machine that handles adjustment, repayment, and liquidation in a single contract.

**Interest Rate System (child + parent boxes)**
A two-tier hierarchical state machine tracks compound interest without an external oracle:
- **Child interest rate boxes** (`interestRateContract`): Each child is a singleton (identified by a Child Interest NFT) that appends a computed interest rate to its R4 history every 120 blocks. The rate is a 6-term polynomial function of pool utilization, with coefficients read from a Parameter Box via data input.
- **Parent interest rate box** (`parentInterest`): Aggregates completed child histories by folding all child rates multiplicatively, appending the compound total to its own R4 history, then spawning a new child box. This chain-of-custody structure allows any loan to reconstruct total accrued interest from three data inputs (base child, head child, parent) regardless of when the loan was originated.

**Repayment Contract**
A small contract attached to the repayment box that validates the pool state transition during loan repayment: borrow token balance increases by exactly the loan amount, and the pool's ERG value increases by at least the repayment value minus fees.

**Proxy Contracts**
Each user-facing operation (lend, borrow, repay, partial repay, withdraw) has a corresponding proxy contract. A proxy box is created by the user or their wallet and acts as a pending request. An off-chain bot observes pending proxies and constructs the completing transaction. If no bot acts within the refund deadline height (`publicRefund`), the user can reclaim their ERG. This pattern decouples user intent from atomic on-chain execution.

### Data Flow — Loan Lifecycle

```
1. User creates proxyBorrow box (R4=borrower, R5=amount, R6=refund height, tokens=collateral)
2. Bot fetches: pool box, parent interest box, head child box, DEX pool box
3. Bot constructs transaction:
   - Input: proxyBorrow (SELF), pool box (INPUTS(0))
   - Data Inputs: DEX pool, parent interest, child interest, parameter box
   - Output 0: updated pool box (borrow tokens reduced by loan amount)
   - Output 1: collateral box (locked, registers populated, borrow tokens + collateral)
   - Output 2: user box receiving borrowed ERG
4. Collateral box is now active; interest accrues in child/parent boxes
5. On repayment: proxyRepay created → bot spends collateral box + repayment box → pool updated
```

---

## Smart Contracts

### `lendPool` — Lending Pool Contract

**Responsibilities:**
- Enforces the lend token valuation invariant: `LendTokenValue = LendTokenMultiplier × (PooledERG + TotalBorrowed) / CirculatingLendTokens`. This value must strictly increase across every state transition, protecting LP token holders.
- Validates exchange (deposit/withdrawal), deposit-only (repayment routing), and loan origination paths.
- Computes tiered service fees (0.625% / 0.5% / 0.4%) based on deposit size and routes them to the fee recipient specified in the Parameter Box.
- On loan origination, reads DEX pool price data, interest rate indices from parent/child boxes, and collateral configuration from the Parameter Box, then validates LTV against liquidation thresholds before creating the collateral box.

**Key Tokens:**
| Token | Position | Role |
|---|---|---|
| Pool NFT | `tokens(0)` | Singleton / State NFT — identifies canonical pool box |
| Lend Token | `tokens(1)` | LP shares — minted on deposit, burned on withdrawal |
| Borrow Token | `tokens(2)` | Loan trackers — reduced on borrow, restored on repayment |

---

### `collateralContract` — Per-Loan State Machine

**Responsibilities:**
- Manages three spending paths: coll