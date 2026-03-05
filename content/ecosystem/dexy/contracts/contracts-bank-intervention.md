---
title: kushti/dexy-stable — intervention.es
description: "ErgoScript contract analysis: contracts/bank/intervention.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/intervention.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `intervention.es`

## Purpose

This contract enforces the **intervention action** mechanism in the Dexy stablecoin system, where the bank automatically buys back Dexy tokens from the liquidity pool (LP) to restore the peg when the price falls to or below 98% of the oracle price. Interventions are rate-limited to occur at most once every 360 blocks, acting as an automated stabilization circuit breaker for the protocol.

---

## Inputs / Outputs

### Inputs
| Index | Box | Purpose |
|-------|-----|---------|
| 0 | **LP Box** | Liquidity pool; holds Erg reserves (X) and Dexy token reserves (Y). Updated after intervention swap. |
| 1 | **Bank Box** | Bank reserve box; holds Dexy tokens and Ergs. Spends Ergs to purchase Dexy from LP. |
| 2 | **Intervention Box (SELF)** | State box tracking the last intervention height; must have Intervention NFT in token(0). |

### Data Inputs
| Index | Box | Purpose |
|-------|-----|---------|
| 0 | **Oracle Box** | Contains current exchange rate (nanoErgs per USD) in R4. Authenticated by Oracle NFT. |
| 1 | **Tracking Box** | Contains trigger event metadata; authenticated by Tracking 98% NFT. R7 holds the height when tracking began. |

### Outputs
| Index | Box | Purpose |
|-------|-----|---------|
| 0 | **LP Box (updated)** | New LP state after Dexy purchase; Erg reserves increase, Dexy reserves decrease. |
| 1 | **Bank Box (updated)** | New bank state after Dexy sale; Erg reserves decrease, Dexy token reserves increase. |
| 2 | **Intervention Box (successor)** | New state box; must preserve script, tokens, and value; creationInfo height must be recent (within 5 blocks). |

---

## Key Logic

### Main Validation Path

The contract validates one of two scenarios:

#### **Scenario A: Valid Update (Bypass)**
```
validUpdate = INPUTS(0).tokens(0)._1 == updateNFT
```
If the first input carries an **Update NFT**, the entire intervention is approved without further checks. This provides an escape hatch for governance or emergency updates.

#### **Scenario B: Standard Intervention Action** (detailed below)

### Threshold Check
```
validThreshold = lpReservesXInBigInt * 100 < oracleRateXy * thresholdPercent * lpReservesYIn
```
- Dexy price in LP = Ergs / Dexy tokens
- Condition triggers when: **price × 100 < oracle rate × 98**
- In other words: price ≤ 98% of oracle rate → intervention is justified

### Time-Gap Enforcement
```
validGap = lastIntervention < HEIGHT - T   // T = 360 blocks
```
Ensures at least 360 blocks have passed since the last intervention (from SELF's creation height). Prevents rapid-fire interventions.

### Trigger Tracking Validation
```
validTracking = trackingHeight < HEIGHT - T_int   // T_int = 20 blocks
```
The trigger event must have been recorded at least 20 blocks ago in the Tracking Box (R7). This prevents immediate re-triggering.

### Swap Invariant (Constant Product)
```
deltaLpY.toBigInt * lpReservesXIn <= deltaLpX.toBigInt * lpReservesYIn
```
Ensures the swap respects the AMM formula without fees: `ΔY × ReserveX ≤ ΔX × ReserveY`. This prevents sandwiching or unfair pricing.

### Maximum Spending Caps
```
validMaxSpending = 
  lpReservesXOutBigInt * 1000 <= oracleRateXy * lpReservesYOut * 995  &&
  deltaBankErgs <= bankBoxIn.value / 100
```
- **Price cap**: New LP rate must not exceed 99.5% of oracle rate (prevents overpayment).
- **Reserve cap**: Bank can spend at most 1% of its Erg reserves per intervention (prevents depletion).

### Delta Consistency
```
validDeltas = 
  deltaBankErgs <= deltaLpX                    &&  // Ergs out of bank ≤ Ergs into LP
  deltaBankTokens >= deltaLpY                  &&  // Dexy into bank ≥ Dexy out of LP
  deltaLpY.toBigInt * lpReservesXIn <= deltaLpX.toBigInt * lpReservesYIn  &&
  deltaLpX > 0                                 &&
  deltaBankErgs <= price * deltaBankTokens / 100 * 102  // max 2% slippage
```
Ensures:
- Flow balance: ergs and tokens move in expected directions
- AMM swap condition holds
- Slippage ≤ 2% (prevents bad execution)

### Successor State Validation
```
validSuccessor = 
  successor.propositionBytes == SELF.propositionBytes  &&  // Same script
  successor.tokens == SELF.tokens                      &&  // Same NFT
  successor.value >= SELF.value                        &&  // Value preserved or increased
  successor.creationInfo._1 >= HEIGHT - buffer          // Recently created (within 5 blocks)
```
The Intervention box must persist as a state machine singleton, ensuring continuity for the next intervention cycle.

### Final Assertion
All conditions AND'd together; all must pass for the transaction to be valid.

---

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R4** | `Long` | Oracle Box | Exchange rate in nanoErgs per USD; divided by 1,000,000 to get rate per Dexy. |
| **R7** | `Int` | Tracking Box | Height at which the 98% trigger event was recorded. Used to enforce the T_int (20-block) cool