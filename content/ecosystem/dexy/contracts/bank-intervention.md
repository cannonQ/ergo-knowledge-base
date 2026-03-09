---
title: kushti/dexy-stable — intervention.es
description: "ErgoScript contract analysis: contracts/bank/intervention.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/intervention.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `intervention.es`

## Purpose

This contract implements the **bank intervention mechanism** in the Dexy protocol, where the bank automatically buys back Dexy tokens from the Liquidity Pool (LP) to restore the peg when the token price falls to ≤98% of the oracle rate. Interventions are rate-limited to occur at most every 360 blocks to prevent excessive rebalancing.

---

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose | NFT Marker |
|-------|----------|---------|-----------|
| 0 | LP Box | Liquidity Pool holding Dexy tokens and ERG reserves | `lpNFT` |
| 1 | Bank Box | Bank reserves (ERGs and Dexy tokens) being spent for buyback | `bankNFT` |
| 2 | **Self** (Intervention) | State machine box encoding intervention authorization rules | `interventionNFT` |

### Data Inputs
| Index | Box Type | Purpose | NFT Marker |
|-------|----------|---------|-----------|
| 0 | Oracle Box | Current exchange rate (nanoErgs per USD in R4) | `oracleNFT` |
| 1 | Tracking Box | Records last trigger event height for rate-limiting | `tracking98NFT` |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | LP Box (updated) | LP with reduced Dexy reserves, increased ERG reserves (price moved up) |
| 1 | Bank Box (updated) | Bank with increased Dexy reserves, reduced ERG reserves |
| 2 | **Self** (Intervention) | Successor state box, unchanged or with preserved state |

---

## Key Logic

### 1. **Update Gate (Fast Path)**
```ergoscript
val validUpdate = INPUTS(0).tokens(0)._1 == updateNFT
```
- If the LP input carries an `updateNFT`, the transaction is automatically valid (bypass all checks).
- This allows authorized updates without re-validating intervention conditions.

### 2. **Price Threshold Check**
```ergoscript
val validThreshold = lpReservesXInBigInt * 100 < oracleRateXy * thresholdPercent * lpReservesYIn
```
- Validates that Dexy price in LP ≤ 98% of oracle price.
- Numerically: `(ERG_reserves / Dexy_reserves) < (oracle_rate × 0.98)`.
- **This is the trigger condition for intervention**.

### 3. **Time-Gap Enforcement**
```ergoscript
val validGap = lastIntervention < HEIGHT - T  // T = 360 blocks
```
- Ensures at least 360 blocks have passed since the last intervention creation.
- Prevents spam and allows market conditions to stabilize.

### 4. **Tracking Cooldown**
```ergoscript
val validTracking = trackingHeight < HEIGHT - T_int  // T_int = 20 blocks
```
- At least 20 blocks must have passed since tracking was initiated.
- Prevents rapid successive interventions within the same tracking window.

### 5. **Reserve Spending Limits**
```ergoscript
val validMaxSpending = 
  lpReservesXOutBigInt * 1000 <= oracleRateXy * lpReservesYOut * 995 &&
  deltaBankErgs <= bankBoxIn.value / 100
```
- **Post-swap rate constraint**: New LP rate ≤ 99.5% of oracle rate (prevents over-correction).
- **Reserve cap**: No more than 1% of bank ERG reserves spent per intervention.

### 6. **Atomic Swap Invariant**
```ergoscript
deltaLpY.toBigInt * lpReservesXIn <= deltaLpX.toBigInt * lpReservesYIn
```
- Enforces constant-product formula: `X × Y = k` (before fees).
- Ensures LP swap is mathematically valid.

### 7. **Delta Consistency**
```ergoscript
deltaBankErgs <= deltaLpX  &&  // ergs out of bank ≤ ergs into LP
deltaBankTokens >= deltaLpY &&  // tokens into bank ≥ tokens out of LP
deltaLpX > 0 &&
deltaBankErgs <= price * deltaBankTokens / 100 * 102  // max 2% slippage
```
- Ensures tokens flow correctly between bank and LP.
- Enforces maximum 2% slippage tolerance on the swap execution.

### 8. **Successor Validation**
```ergoscript
val validSuccessor = 
  successor.propositionBytes == SELF.propositionBytes  &&
  successor.tokens == SELF.tokens                      &&
  successor.value >= SELF.value                        &&
  successor.creationInfo._1 >= HEIGHT - buffer  // buffer = 5 blocks
```
- The successor intervention box must:
  - Carry the same script (propositionBytes).
  - Preserve all tokens (no token loss).
  - Preserve or increase ERG value.
  - Be created recently (within 5-block window).

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** (Oracle Box) | `Long` | Exchange rate in nanoErgs per USD; divided by 1,000,000 to get rate per Dexy token |
| **R7** (Tracking Box) | `Int` | Height at which the tracking event was initiated; used to enforce `T_int` cooldown |
| **creationInfo._1** (Self) | `Int` | Height at which this intervention box was created; compared against `T = 360` to enforce intervention gap |

---

## Tokens

| Token Type | Qty | Role |
|------------|-----|------|
| **lpNFT** | 1 | State marker (Singleton) identifying the authoritative LP box |
| **bankNFT** | 1 | State marker (Singleton) identifying the authoritative bank box |
| **interventionNFT** | 