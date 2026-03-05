---
title: duckpools/off-chain-bot — standard_deviation.md
description: "ErgoScript contract analysis: optionPools/contracts/standard_deviation.md"
tags: [duckpools, off-chain-bot, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/off-chain-bot"
contract_file: optionPools/contracts/standard_deviation.md
project: duckpools-off-chain-bot
---
# ErgoScript Contract Analysis: standard_deviation.md

## Purpose

This contract implements a **rolling-window volatility oracle** that maintains a historical log-returns buffer and computes annualized volatility estimates for an options pool. It validates price updates from a DEX NFT-authenticated data source, cyclically rotates a ring buffer of log-returns, and ensures volatility calculations remain within acceptable error margins using approximate square-root validation.

## Inputs / Outputs

### Inputs
- **SELF (spending box):** The current oracle state box, protected by this contract's ErgoTree
- **Data Input (CONTEXT.dataInputs(0)):** An authenticated price report box containing:
  - Token(0): DEX NFT (identity proof)
  - Token(2): Price token with amount encoding the current price
  - Box value: Used as denominator for price ratio calculation

### Outputs
- **OUTPUTS(0) (successor box):** The next oracle state, must retain:
  - Same proposition bytes (ErgoTree) as SELF
  - Same native tokens as SELF
  - Value ≥ SELF.value - 1,000,000 nanoErgs (accounting for transaction fees)

## Key Logic

The contract enforces these invariants:

1. **Time-lock:** Block height must advance (`iHeight < HEIGHT`) and successor height must equal current height + `updateFrequency` (292 blocks)

2. **Ring-buffer rotation:** 
   - The `iLogReturns` collection (size *n*=100) is rotated circularly
   - Elements at indices [0, iStart) and (iStart, n) remain unchanged
   - The element at index `iStart` is replaced with the newly calculated log-return
   - `fStart` advances to `(iStart + 1) % n`, preparing the next rotation slot

3. **Log-return calculation:**
   - `newEntry = lnX((currentPrice * p / previousPrice) - p)` computes the natural logarithm of the price ratio using a 6-term Taylor series approximation with precision `p = 1,000,000`

4. **Volatility computation:**
   - Sample variance = Σ(logReturn - mean)² / (n - 1) (Bessel's correction)
   - Mean = Σ(logReturns) / n
   - Standard deviation (volatility) is approximated via `isValidSquareRoot()`, which validates that `(supposedSquareRoot)² ≈ sampleVariance` within ±20p error margin

5. **Annualization:**
   - `annualizedVolatility = fVolatility * sqrtUpdatesInAYear` (30 per year, implying ~12-day update frequency)
   - Assumes 900 updates/year and annualization factor derived from √(252 trading days) ≈ 30× scaling

6. **Price authentication:**
   - `reportedValue` is decoded from the data input's token(2) amount: `(10¹⁴ * tokenAmount) / boxValue`
   - Must match the decoded `currentPrice` from successor R8
   - DEX NFT in token(0) must match hardcoded `dexNFT` constant (`BJbaZ...`)

7. **State preservation:**
   - Script, tokens, and value must be retained across the transaction

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Rolling-window buffer of log-returns (size 100) |
| **R5** | `Int` | Current insertion index (0–99) for cyclic buffer rotation |
| **R6** | `Long` | Current volatility estimate (standard deviation approximation) |
| **R7** | `Long` | Block height of last update |
| **R8** | `Long` | Previous price (used to compute next log-return) |
| **R9** | `Long` | Annualized volatility (R6 * 30) |

## Tokens

- **DEX NFT (token(0) in data input):** Singleton token (State NFT pattern) authenticating the price oracle source. Hardcoded ID: `BJbaZAXMoFm9gi2MBXA9eyPi38ugjKZ66SQrnwQmoDNj`
- **Pool NFT (token(0) in SELF):** Retained across transitions; likely identifies this oracle instance within the options pool
- **Price token (token(2) in data input):** Carries price information encoded in its token amount; ratio-decoded against box value

## Integration Pattern

The off-chain bot must:

1. **Monitor the oracle box** for state changes
2. **Fetch current price** from an external DEX (likely via DEX NFT holder)
3. **Construct data input** with:
   - DEX NFT in token(0)
   - Price-bearing token in token(2) with amount = `(price * boxValue) / 10¹⁴`
4. **Compute next log-return** using the Taylor-series `lnX()` function
5. **Calculate sample variance** of the rotated buffer
6. **Compute square root** of variance (off-chain, must satisfy error bound) and annualize
7. **Build successor box** with:
   - Rotated R4 buffer
   - Incremented R5 index (mod 100)
   - New R6 volatility
   - Updated R7, R8, R9 registers
8. **Submit transaction** every ~292 blocks (≈4.8 hours on mainnet, ~1.2 hours on testnet)

## Related Contracts

- **Options pool contracts:** This oracle likely feeds volatility data to Black-Scholes or similar options pricing contracts in `optionPools/`
- **DEX contracts:** The authenticated data source (likely a liquidity pool contract or price oracle in the duckpools ecosystem)
- **Multi-stage state machine:** Participates in a headless dApp architecture where off-chain bots trigger deterministic state transitions via valid transactions

---

### Notes

- **Precision handling:** Fixed-point arithmetic with `p = 10⁶` avoids floating-point; all BigInt operations
- **Error margins:** TODO comment suggests `isValidSquareRoot()` error