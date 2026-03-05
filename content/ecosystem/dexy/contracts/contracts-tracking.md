---
title: kushti/dexy-stable — tracking.es
description: "ErgoScript contract analysis: contracts/tracking.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/tracking.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `tracking.es`

## Purpose

This contract implements a **state machine tracker** that monitors the ratio between an Oracle pool rate and an LP (Liquidity Pool) rate, triggering an alarm when the ratio crosses a configured threshold. The tracker maintains a boolean state (triggered/reset) and ensures state transitions only occur when the monitored event genuinely occurs, enabling downstream contracts to react to significant price deviations.

---

## Inputs / Outputs

### Inputs
- **Box 0 (SELF)**: The Tracking box itself
  - Contains the Tracking NFT (tokens(0))
  - Holds threshold ratio parameters and state in R4–R7
  
### Data Inputs (Immutable References)
- **Data Input 0**: Oracle box (identified by `oracleNFT`)
  - R4: `Long` — Oracle rate in nanoErgs per 1 kg of gold
  
- **Data Input 1**: LP box (identified by `lpNFT`)
  - tokens(2): Dexy token ID and reserve quantity
  - value: ERG reserves (nanoErgs)

### Outputs
- **Box 0 (successor)**: Updated Tracking box
  - Must preserve the Tracking NFT
  - Must preserve the contract (propositionBytes)
  - Must preserve or increase value (no funds extracted)
  - R4–R7: Updated registers reflecting new tracker state

---

## Key Logic

### State Machine: Trigger ↔ Reset

The tracker operates in two states, stored in **R7 (trackerHeight)**:
- **Triggered**: `trackerHeight < Int.MaxValue` (stores block height when triggered)
- **Reset**: `trackerHeight == Int.MaxValue` (no active trigger)

### Ratio Monitoring

1. **Compute Rates**:
   - `oracleRateXY = oracleBox.R4 / 1,000,000` (nanoErgs per Dexy/mg of gold)
   - `lpRateXY = reservesX / reservesY` (ERG reserves ÷ Dexy token supply)

2. **Define Threshold**:
   - Register R4: numerator (`numIn`)
   - Register R5: denominator (`denomIn`)
   - Ratio threshold: `t = numIn / denomIn`

3. **Determine Direction** (R6: `isBelowIn`):
   - **If `isBelowIn == true`** (lower tracking):
     - Trigger when: `lpRateXY / oracleRateXY < t`
     - Reset when: `lpRateXY / oracleRateXY >= t`
   
   - **If `isBelowIn == false`** (upper tracking):
     - Trigger when: `lpRateXY / oracleRateXY > t`
     - Reset when: `lpRateXY / oracleRateXY <= t`

### Hysteresis & Height Validation

- **Error Threshold**: ±3 blocks tolerance
- On trigger: `trackerHeightOut` must fall within `[HEIGHT - 3, HEIGHT]`
- On reset: `trackerHeightOut` must equal `Int.MaxValue`
- Prevents rapid re-triggering and accommodates blockchain latency

### Transition Validity Table

| Event   | isBelow | Condition (Input) | Condition (Output) | New Height |
|---------|---------|-------------------|--------------------|------------|
| Trigger | true    | x ≥ y             | x < y              | [HEIGHT-3, HEIGHT] |
| Reset   | true    | x < y             | x ≥ y              | Int.MaxValue |
| Trigger | false   | x ≤ y             | x > y              | [HEIGHT-3, HEIGHT] |
| Reset   | false   | x > y             | x ≤ y              | Int.MaxValue |

Where: `x = lpRateXY × denomIn`, `y = numIn × oracleRateXY`

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Int` | Numerator of threshold ratio (e.g., 95 for 95%) |
| **R5** | `Int` | Denominator of threshold ratio (e.g., 100 for 95/100) |
| **R6** | `Boolean` | Direction flag: `true` = track below threshold; `false` = track above |
| **R7** | `Int` | Tracker height: block height when triggered, or `Int.MaxValue` (2,147,483,647) if reset |

---

## Tokens

### Singleton Tokens (NFTs)

1. **Tracking NFT** (tokens(0) of SELF)
   - Stored in base64-encoded constant `$lpNFT`
   - Ensures exactly one authoritative Tracking box exists
   - Must be preserved in successor output

2. **Oracle NFT** (referenced in data input)
   - Stored in base64-encoded constant `$oracleNFT`
   - Authenticates the Oracle box feeding price data
   - Validated via `validOracleBox` check

### Value Tokens

- **Dexy tokens** (LP box tokens(2))
  - Represents the reserve quantity of the stablecoin in the LP
  - Used to compute `lpRateXY = reservesX / reservesY`

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Monitor Ratio Changes**:
   - Subscribe to UTXO updates for the Tracking box and Oracle/LP boxes
   - Off-chain: compute `lpRateXY / oracleRateXY` and compare to `numIn / denomIn`

2. **Construct Transaction**:
   - When ratio crosses threshold:
     - Build transaction with Tracking box as input (INPUTS(0))
     - Attach Oracle box as data input (CONTEXT.dataInputs(0))
     - Attach LP box as data input (CONTEXT.dataInputs(1))
     - Create successor Tracking box (OUTPUTS(0)) with updated R7
   
3. **