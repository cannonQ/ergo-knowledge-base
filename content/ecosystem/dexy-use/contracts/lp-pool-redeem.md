---
title: kushti/dexy-stable — redeem.es
description: "ErgoScript contract analysis: contracts/lp/pool/redeem.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/redeem.es
project: dexy-use
---
# ErgoScript Contract Analysis: LP Redeem Subcontract

## Purpose

This contract validates **LP token redemption** in a liquidity pool, ensuring that when users burn LP tokens, they receive proportional amounts of the underlying reserve assets (X and Y tokens) according to the pool's current exchange rate. It enforces a 2% redemption fee and rate validation against an oracle to prevent sandwich attacks or manipulation.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0) — LP Pool Box**: The main liquidity pool box holding:
  - Native ERGs (reserve X)
  - Token(1): LP token reserves (fungible token tracking burned/outstanding supply)
  - Token(2): Reserve Y token (the second asset in the pair)

### Data Inputs
- **CONTEXT.dataInputs(0) — Oracle Box**: A singleton box from an oracle pool contract that provides the current exchange rate (nanoErgs per USD equivalent). Authenticated by its NFT.

### Outputs
- **OUTPUTS(0) — Updated LP Pool Box**: The pool box after liquidity removal, with:
  - Reduced ERG reserves
  - Reduced LP token reserve quantity (user's burned tokens returned to pool)
  - Reduced Y token reserves
- **OUTPUTS(1) — Redeem Contract Successor**: The redeem contract itself, preserved with same proposition and token state, but with increased ERG value (redemption proceeds).

---

## Key Logic

### Rate Validation
```
lpRateXyIn = reservesXIn / reservesYIn
oracleRateXy = oracleBox.R4[Long].get / 1000
validRateForRedeemingLp: lpRateXyIn ≥ 0.98 × oracleRateXy
```
The pool's X:Y exchange rate must stay within 2% of the oracle price. This prevents users from redeeming during severe price slippage (e.g., after a large swap that hasn't been arbitraged back).

### Redemption Proportionality with Fee
The contract enforces that reserves decrease proportionally to LP token burn, accounting for a **2% redemption fee**:

```
deltaSupplyLp = lpReservesIn - lpReservesOut  (positive: tokens burned)
deltaReservesX = reservesXOut - reservesXIn   (negative: X removed)
deltaReservesY = reservesYOut - reservesYIn   (negative: Y removed)

Validation:
  deltaReservesX × supplyLpIn × 100 / 98 ≥ deltaSupplyLp × reservesXIn
  deltaReservesY × supplyLpIn × 100 / 98 ≥ deltaSupplyLp × reservesYIn
```

This ensures:
- The user receives **at least** (deltaSupplyLp / supplyLpIn) of each reserve, minus 2% fee
- No funds are leaked from the pool
- The proportionality formula: `user_share = burned_lp / circulating_lp`

### State Continuity
```
selfPreserved: successor.propositionBytes == SELF.propositionBytes
             ∧ successor.value ≥ SELF.value
             ∧ successor.tokens == SELF.tokens
```
The redeem contract itself must persist unchanged (singleton pattern via NFT token), ensuring it can handle future redemptions.

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** (Oracle Box) | `Long` | Exchange rate in nanoErgs per 1 USD. Divided by 1000 to derive rate per USE token (3 decimals). |
| **Implicit Constant** | `Long` | `$initialLp` — total LP tokens minted at bootstrap. Used to compute circulating supply: `supplyLpIn = initialLp - lpReservesIn._2` |

---

## Tokens

### Token Structure

| Token Index | Location | Type | Purpose |
|-------------|----------|------|---------|
| **tokens(0)** | Redeem box | **NFT (Singleton)** | Uniquely identifies this redeem contract box; ensures only one authoritative redeem script exists. |
| **tokens(1)** | LP Pool box | **Fungible (LP tokens)** | Tracks LP token supply in pool; burned tokens are "in circulation." Quantity decreases as users redeem. |
| **tokens(2)** | LP Pool box | **Fungible (Reserve Y)** | The second reserve asset. Its quantity decreases proportionally during redemption. |

The **Token ID rule** ensures the LP and Oracle NFTs are stable identifiers across transactions in this state machine.

---

## Integration Pattern

### Off-Chain Bot / dApp Responsibilities

1. **Oracle Data Input Construction**
   - Fetch the current oracle pool box (identified by `oracleNFT`)
   - Read its **R4 register** (exchange rate)
   - Include it as a **data input** (CONTEXT.dataInputs(0)) — read-only, no signature required

2. **Pool Input Selection**
   - Select the LP pool UTXO at INPUTS(0)
   - Verify it holds tokens(1) and tokens(2)

3. **Output Construction**
   - **OUTPUTS(0)**: Decrement LP pool's value, lpReservesIn._2, and reservesYIn based on redemption amount
   - **OUTPUTS(1)**: Create successor box with same NFT, preserved proposition, updated ERG value
   - Calculate: `user_redemption = (lpTokensBurned / supplyLpIn) × reservesX/Y - 2% fee`

4. **Verify Invariants**
   - All three deltas are negative (reserves shrink, LP supply increases)
   - Rate check passes: `lpRateXyIn ≥ 0.98 × oracleRateXy`
   - Fee math holds exactly as per the formula

5. **Sign & Submit**
   - User signs the transaction (spends their LP tokens separately)
   - Protocol fees (storage rent) covered by outputs

### State Machine Pattern
This is a **multi-stage contract**: the redeem box is a **subcontract** of a larger liquidity pool dApp. Each redemption advances the