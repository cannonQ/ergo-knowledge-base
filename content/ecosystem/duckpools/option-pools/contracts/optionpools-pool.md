---
title: duckpools/off-chain-bot — pool.md
description: "ErgoScript contract analysis: optionPools/contracts/pool.md"
tags: [duckpools, off-chain-bot, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/off-chain-bot"
contract_file: optionPools/contracts/pool.md
project: duckpools-off-chain-bot
---
# ErgoScript Contract Analysis: Duck Pools Option Pool

## Purpose

This contract implements a **decentralized options pool** using the Black-Scholes pricing model on the Ergo blockchain. It manages deposits/withdrawals of liquidity (X and Y tokens), mints/burns LP tokens, and processes call/put option trades while maintaining invariant checks on reserves and fees. The pool uses data inputs (oracle prices, volatility, CDF values) to validate fair pricing and execute hedged option settlements.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Pool box itself (SELF) — the state machine box containing reserves, LP tokens, option tokens, and registers
- **INPUTS(1)**: Input box with call/put option tokens (during deposit/trade operations)
- **Additional inputs** (operation-dependent): User boxes providing collateral or receiving payouts

### Data Inputs (Oracle/Reference Boxes)
- **CONTEXT.dataInputs(0)**: Price oracle box — contains spot price (S) in tokens(2), value in ERG
- **CONTEXT.dataInputs(1)**: Volatility oracle box — contains sigma (σ) in R9[Long]
- **CONTEXT.dataInputs(2+)**: CDF (Cumulative Distribution Function) lookup boxes — validate N(d1) and N(d2) probability values

### Outputs
- **OUTPUTS(0)**: Successor pool box — updated reserves, LP/option token amounts, and registers
- **Additional outputs** (operation-dependent): LP token mints to users, option settlements, excess collateral refunds

---

## Key Logic

### Core Invariants

1. **Script Preservation**: Successor box must have identical `propositionBytes` (contract code unchanged)
2. **NFT/Token ID Preservation**: Pool NFT, LP token ID, Y token ID, and option token IDs must remain unchanged across transactions
3. **Minimum Box Value**: Successor must maintain ≥ 1,000,000 nanoERG
4. **Risk-Free Rate Immutability**: R4[Long] (interest rate) cannot change

### Deposit Operation (`CONTEXT.dataInputs.size <= 2`)
- **Condition**: Only 0–2 data inputs (no CDF lookups needed)
- **Validations**:
  - LP tokens unchanged (no minting/burning)
  - Pool X value (ERG) increases
  - Pool Y value increases or stays constant
  - INPUTS(0) is the self-box
  - INPUTS(1) contains a call option token
  - Call option token amount increments by 1
- **Purpose**: Simple liquidity provision without option pricing

### Trade/Swap Operation (`CONTEXT.dataInputs.size > 2`)
- **Condition**: 3+ data inputs (includes price oracle, volatility oracle, CDF boxes)
- **Complex Validations**:
  - **Black-Scholes d1 calculation**: 
    ```
    d1 = [ln(S/K) + (r·t + σ²/2)·t] / (σ·√t)
    ```
    where K = strike, S = spot price, σ = volatility, r = risk-free rate, t = time to expiry
  - **CDF lookups**: Uses indices to verify N(d1) and N(d2) from oracle boxes
  - **Option pricing**: Call and put prices derived from Black-Scholes formula with risk-neutral valuation
  - **Collateral validation**: Ensures sufficient premium paid and excess refunded
  - **LP share calculations**: Verify LP token burns match reserve changes (constant product curve or similar)

### Mathematical Functions (Approximations)

| Function | Purpose | Method |
|----------|---------|--------|
| `lnX(x)` | Natural logarithm | Taylor series: x − x²/2p + x³/3p² − … (6 terms) |
| `eX(x)` | e^−x exponential | Taylor series: 1 − x + x²/2p − x³/6p² + x⁴/24p³ |
| `isValidSquareRoot(values, p)` | Verify √a ≈ b | Check (b² / p) ≈ a within margin 2b+1 |
| `isValidTripleSquareRoot(values)` | Verify (S/K)^(1/8) | Check y^8 / p^7 ≈ S/K within ±12·(S/K) margin |
| `getD1(values)` | Black-Scholes d1 | Decomposes fraction: [p²·ln(S/K)] / (σ·√t) + [p·r·t] / (σ·√t) + σ·t / (2√t) |

---

## Registers Used

| Register | Type | Purpose | Mutable? |
|----------|------|---------|----------|
| **R4** | `Long` | Risk-free rate (r) in basis points or per-minute scale | ✗ No |
| **R5** | `Coll[Long]` | Strike prices and expiry data; structure: `[Expiry, Strike1, Amount1, Strike2, Amount2, …]` | ✓ Yes (updated on trades) |
| **R6** | `Coll[Long]` | Hints for Black-Scholes computation: `[curr_height, y, yp, sqrtT]` where y = hint for (S/K)^(1/8), sqrtT = √(t) | ✓ Yes (off-chain supplied) |
| **R7** | `Coll[Int]` | CDF lookup indices: `[CDFIndex1, CDFIndex2]` pointing to rows in oracle CDF boxes | ✓ Yes (off-chain supplied) |
| **R8** | (Implied) | Reserve tracking or additional state (if present in full contract) | — |
| **R9** | (Implied) | Additional state (if present; volatility σ is read from dataInputs(1).R9) | — |

---

## Tokens

### Native Token Types

| Token Position | Type | ID | Purpose | Rules |
|---|---|---|---|---|
| **