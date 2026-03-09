---
title: kushti/dexy-stable — tracking.es
description: "ErgoScript contract analysis: contracts/tracking.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/tracking.es
project: dexy-use
---
# ErgoScript Contract Analysis: `tracking.es`

## Purpose

This contract implements a **state machine tracking box** that monitors the ratio between an oracle pool rate and an LP (liquidity pool) rate, triggering or resetting an alarm when the ratio crosses a defined threshold. It serves as a sentinel mechanism to detect and flag market conditions (e.g., price deviations) that may warrant intervention by other contracts in the Dexy protocol.

---

## Inputs / Outputs

### Inputs
- **Self (Index 0):** The Tracking box itself—a UTXO holding:
  - **Token:** Tracking NFT (singleton identifier)
  - **Registers:** Threshold ratio (R4, R5), tracking mode (R6), trigger height (R7)
  - **Value:** ERG balance (must not decrease in output)

### Data Inputs (Read-Only)
- **Data Input 0 (Oracle Box):** Oracle pool box identified by `oracleNFT`
  - **R4:** Current exchange rate in nanoErgs per USD (Long)
- **Data Input 1 (LP Box):** Liquidity pool box identified by `lpNFT`
  - **Tokens(0):** LP NFT (singleton)
  - **Tokens(2):** Dexy token reserves (amount)
  - **Value:** ERG reserves

### Outputs
- **Output 0 (Successor Tracking Box):** Updated tracking box
  - **Token:** Must match SELF (same Tracking NFT)
  - **Registers:** May transition R7 (trigger height) only; R4, R5, R6 immutable
  - **Value:** Must be ≥ SELF value
  - **Proposition:** Must match SELF (same lock script)

---

## Key Logic

### State Transitions

The contract enforces exactly **two types of state transitions**:

#### 1. **Trigger Transition** (Not Triggered → Triggered)
- **Precondition:** `trackerHeightIn == Int.MaxValue` (alarm not currently ringing)
- **Action:** Ratio crosses threshold in the monitored direction
  - If `isBelow == true`: `lpRateXY * denomIn < numIn * oracleRateXY` (ratio falls below threshold)
  - If `isBelow == false`: `lpRateXY * denomIn > numIn * oracleRateXY` (ratio rises above threshold)
- **Result:** `trackerHeightOut` set to current block height (within `threshold` error margin)

#### 2. **Reset Transition** (Triggered → Not Triggered)
- **Precondition:** `trackerHeightIn < Int.MaxValue` (alarm currently ringing)
- **Action:** Ratio crosses back over threshold in the opposite direction
  - If `isBelow == true`: `lpRateXY * denomIn >= numIn * oracleRateXY` (ratio rises back above)
  - If `isBelow == false`: `lpRateXY * denomIn <= numIn * oracleRateXY` (ratio falls back below)
- **Result:** `trackerHeightOut` reset to `Int.MaxValue` (infinity)

### Invariants

1. **Ratio Parameters Immutable:** `numOut == numIn`, `denomOut == denomIn`, `isBelowOut == isBelowIn`
2. **No Silent Changes:** Exactly one transition must occur; no state change without explicit trigger/reset
3. **Box Continuity:** Successor must hold identical Tracking NFT and lock script
4. **Value Preservation:** Output ERG value ≥ input ERG value (covers storage rent)
5. **Oracle & LP Validation:** Both data inputs verified by their respective NFT tokens
6. **Height Tolerance:** Trigger height must fall within `[HEIGHT - threshold, HEIGHT]` (3-block grace period)

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|------------|
| **R4** | `Int` | Numerator of threshold ratio | Immutable |
| **R5** | `Int` | Denominator of threshold ratio | Immutable |
| **R6** | `Boolean` | Tracking mode: `true` = below threshold, `false` = above threshold | Immutable |
| **R7** | `Int` | Trigger height (block when threshold crossed) or `Int.MaxValue` if reset | **Mutable** |

### Example Register Configurations

Three tracking boxes are deployed:
| Box | R4 | R5 | R6 | Purpose |
|-----|----|----|-----|---------|
| Box 1 | 95 | 100 | `true` | Monitor for oracle ≤ 95% of LP (extract-to-future condition) |
| Box 2 | 98 | 100 | `true` | Monitor for oracle ≤ 98% of LP (mint arbitrage condition) |
| Box 3 | 101 | 100 | `false` | Monitor for oracle > 101% of LP (release-in-future condition) |

---

## Tokens

### Tracking NFT
- **Holder:** This box (tokens(0))
- **Purpose:** Singleton identifier ensuring only one instance of this tracker exists
- **Rule:** Must be preserved in successor box (Token ID rule)

### Dexy Tokens (USE)
- **Holder:** LP Box (via data input, tokens(2))
- **Purpose:** Y-side reserves; used in `lpRateXY` calculation
- **Note:** Assumed to have 3 decimal places (USE denomination)

### Oracle NFT
- **Holder:** Oracle box (via data input, tokens(0))
- **Purpose:** Authenticates oracle data source
- **Data Provided:** Nanoergs per USD (R4)

### LP NFT
- **Holder:** LP box (via data input, tokens(0))
- **Purpose:** Authenticates liquidity pool state
- **Data Provided:** ERG reserves (box value) and Dexy reserves (tokens(2))

---

## Integration Pattern

### Off-Chain Bot Responsibilities

1. **Monitor Market Conditions:** Continuously fetch:
   - Oracle rate from oracle pool box R4
   - LP rate from LP box (ERG