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
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `tracking.es`

## Purpose

This contract implements a **state machine tracker** that monitors the price ratio between an Oracle pool rate and an LP (Liquidity Pool) rate, triggering and resetting state transitions when the ratio crosses predefined thresholds. It serves as a monitoring mechanism for the Dexy stable asset protocol, detecting when arbitrage or liquidation conditions should occur.

## Inputs / Outputs

### Inputs
- **Input 0**: The Tracking box itself (SELF) — a Singleton box authenticated by a Tracking NFT

### Outputs
- **Output 0**: A successor Tracking box with identical NFT, script, and increased or equal value

### Data Inputs (referenced but not spent)
- **Data Input 0**: Oracle pool box — provides current exchange rate (R4) in nanoErgs per unit
- **Data Input 1**: LP box — provides current reserve balances and Dexy token supply for ratio calculation

## Key Logic

The contract enforces a **state machine** with two states: **triggered** and **reset** (via `trackerHeightOut`).

### Core Validation Rules:

1. **Successor Box Validation**
   - Successor must hold identical tokens (Tracking NFT)
   - Successor must execute the same ErgoScript (same `propositionBytes`)
   - Successor value must be ≥ SELF value (no value erosion beyond storage rent)

2. **Data Input Authentication**
   - LP box must carry the LP NFT (stored in base64 constant `$lpNFT`)
   - Oracle box must carry the Oracle NFT (stored in base64 constant `$oracleNFT`)

3. **Ratio Computation**
   ```
   oracleRateXY = oracleBox.R4 / 1,000,000  (nanoErgs per Dexy token, i.e., per mg of gold)
   lpRateXY = reservesX / reservesY  (Ergs per Dexy token from LP reserves)
   ```

4. **Trigger Condition** (transition from reset → triggered)
   - Input state: `trackerHeightIn == Int.MaxValue` (not previously triggered)
   - Output state: `trackerHeightOut` ∈ [HEIGHT - threshold, HEIGHT] (triggered at current or recent block)
   - Ratio cross: Depends on `isBelowIn` flag:
     - If **below-tracking** (`isBelowIn == true`): ratio must cross **downward** (x < y)
     - If **above-tracking** (`isBelowIn == false`): ratio must cross **upward** (x > y)

5. **Reset Condition** (transition from triggered → reset)
   - Input state: `trackerHeightIn < Int.MaxValue` (previously triggered)
   - Output state: `trackerHeightOut == Int.MaxValue` (reset to "infinity")
   - Ratio cross: Opposite direction of trigger
     - If **below-tracking**: ratio must recover **upward** (x ≥ y)
     - If **above-tracking**: ratio must decline **downward** (x ≤ y)

6. **Immutable Tracking Configuration**
   - `numOut == numIn` (threshold numerator unchanged)
   - `denomOut == denomIn` (threshold denominator unchanged)
   - `isBelowOut == isBelowIn` (tracking direction unchanged)

### Error Threshold
- `threshold = 3` blocks: `trackerHeightOut` can lag current HEIGHT by up to 3 blocks to account for block propagation delays

## Registers Used

| Register | Type | Input/Output | Purpose |
|----------|------|--------------|---------|
| **R4** | `Int` | Both | Numerator of tracking threshold ratio (e.g., 95 for 95%) |
| **R5** | `Int` | Both | Denominator of tracking threshold ratio (e.g., 100 for 95/100) |
| **R6** | `Boolean` | Both | `true` = monitor ratio falling **below** threshold; `false` = falling **above** |
| **R7** | `Int` | Both | Trigger height (`Int.MaxValue` if reset, otherwise HEIGHT when triggered) |

## Tokens

### Tracking NFT (`tokens(0)`)
- **Type**: Native token (singleton)
- **Purpose**: Authenticate this box as the unique Tracking instance for this monitoring rule
- **Value**: Extracted from base64 constant `$lpNFT` (filled via script parameterization)
- **Uniqueness**: Only one Tracking box per configuration can exist; successive boxes must preserve this token

### Dexy Token Reference (from LP box)
- **Type**: Native token (`lpBox.tokens(2)`)
- **Purpose**: Supplies reserve quantity (`tokenY._2`) to compute LP rate
- **Role**: Not directly held by Tracking box; used as data input reference

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities:

1. **Observe State**
   - Read current Tracking box from blockchain
   - Fetch Oracle box and LP box as data inputs
   - Compute `lpRateXY` and `oracleRateXY`

2. **Detect State Change**
   - Compare ratio against threshold (`numIn / denomIn`)
   - Determine if trigger or reset condition is now satisfied

3. **Construct Transaction**
   - If trigger: set `trackerHeightOut = HEIGHT` (or within threshold window) and `isBelowOut == isBelowIn`
   - If reset: set `trackerHeightOut = Int.MaxValue`
   - Preserve R4, R5, R6 registers
   - Ensure output value ≥ input value (cover storage rent)

4. **Sign & Submit**
   - Create a valid transaction spending Tracking box and including Oracle + LP as data inputs
   - Must satisfy **Sigma protocol** proof to unlock SELF's script

### External Contracts / Processes
- **Oracle Pool**: Provides live exchange rate in R4
- **LP Contract**: Provides reserve data; must output box with LP NFT
- **Arbitrage/Liquidation Contract**: Likely triggered by state changes in `trackerHeightOut`

## Related Contracts

Based on code structure