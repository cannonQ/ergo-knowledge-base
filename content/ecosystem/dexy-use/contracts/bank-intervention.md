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
project: dexy-use
---
# ErgoScript Contract Analysis: `intervention.es`

## Purpose

This contract enforces the **bank's buyback mechanism** to restore the Dexy stablecoin peg when its price in the LP falls to ≤98% of the oracle price. The intervention occurs at most every 360 blocks, with the bank purchasing Dexy tokens from the LP using its ERG reserves to restore equilibrium.

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | LP Box | Liquidity pool holding ERG reserves and Dexy tokens; state updated after buyback |
| 1 | Bank Box | Bank's reserve box holding ERG and Dexy tokens; state updated after spending ERGs |
| 2 (SELF) | Intervention Box | Singleton state machine box encoding the intervention NFT and tracking height |

### Data Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | Oracle Box | Provides current ERG/USD rate in `R4` (nanoErgs per USD); read-only |
| 1 | Tracking Box | Sentinel box tracking when a price-drop event was detected; validates minimum block gap |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | LP Box | Updated LP state with increased ERG reserves, decreased Dexy token supply |
| 1 | Bank Box | Updated bank state with decreased ERG reserves, increased Dexy tokens |
| 2 (SELF) | Intervention Box | Successor state machine box with same NFT, same tokens, same or higher value |

---

## Key Logic

### Core Validation Flow

1. **Update Check** (Fast Path):
   - If input #0 carries an `updateNFT`, validation succeeds immediately (off-chain bot trigger).

2. **Threshold Validation**:
   - Reads oracle rate from data input box: `oracleRateXy = oracleBox.R4[Long] / 1000` (nanoErgs per USE, accounting for 3 decimal places).
   - Computes LP price: `lpReservesXIn / lpReservesYIn`.
   - **Trigger condition**: `lpReservesXIn * 100 < oracleRateXy * 98 * lpReservesYIn` (price ≤98% of oracle).

3. **Temporal Constraints**:
   - **Gap check**: `lastIntervention < HEIGHT - 360` (at least 360 blocks since last intervention).
   - **Tracking check**: `trackingHeight < HEIGHT - 20` (at least 20 blocks since price-drop event was detected in tracking box).
   - **Height buffer**: Successor creation height within 5 blocks of current height.

4. **Atomic Swap Invariants**:
   - Bank spends ERGs (`deltaBankErgs`) to acquire Dexy tokens (`deltaBankTokens > 0`).
   - **Flow conservation**: 
     - ERGs reduced in bank ≤ ERGs gained in LP: `deltaBankErgs ≤ deltaLpX`.
     - Dexy gained in bank ≥ Dexy reduced in LP: `deltaBankTokens ≥ deltaLpY`.
   - **AMM invariant** (constant product without fees): 
     - `deltaLpY * lpReservesXIn ≤ deltaLpX * lpReservesYIn`.
   - **Slippage limit** (2%): `deltaLpX ≤ price * deltaBankTokens / 100 * 102`.

5. **Spending Limits**:
   - **Rate recovery**: New LP rate must not exceed 99.5% of oracle: `lpReservesXOut * 1000 ≤ oracleRateXy * lpReservesYOut * 995`.
   - **Reserve drain limit**: Bank spends no more than 1% of its ERG reserves per intervention: `deltaBankErgs ≤ bankBoxIn.value / 100`.

6. **Box Authentication**:
   - LP box identified by `lpNFT` in `tokens(0)`.
   - Bank box identified by `bankNFT` in `tokens(0)`.
   - Oracle box identified by `oracleNFT` in `tokens(0)`.
   - Tracking box identified by `tracking98NFT` in `tokens(0)`.
   - Successor replicates proposition and tokens, preserves or increases value.

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| `R4` (Oracle) | `Long` | **Oracle rate**: nanoErgs per 1 USD; read from data input oracle box |
| `R7` (Tracking) | `Int` | **Tracking height**: Block height when price-drop event was triggered; read from data input tracking box |
| `creationInfo._1` (SELF) | `Int` | **Last intervention height**: Block height when current intervention box was created; used for gap enforcement |

---

## Tokens

### NFTs (State Machine Singletons)

| Token ID | Register | Purpose | Held By |
|----------|----------|---------|---------|
| `bankNFT` | Constant (parameterized) | Authenticates the bank box | Bank Box (input #1) |
| `lpNFT` | Constant (parameterized) | Authenticates the LP box | LP Box (input #0) |
| `oracleNFT` | Constant (parameterized) | Authenticates the oracle data input | Oracle Box (data input #0) |
| `tracking98NFT` | Constant (parameterized) | Authenticates the tracking box | Tracking Box (data input #1) |
| `interventionNFT` | `SELF.tokens(0)` | Singleton identifying this intervention state machine | Intervention Box (SELF) |
| `updateNFT` | Fast-path trigger | Optional: if input #0 carries this, intervention is approved | External trigger (if used) |

### Token Flows

- **Dexy tokens**: Transferred from LP → Bank during buyback (`deltaBankTokens