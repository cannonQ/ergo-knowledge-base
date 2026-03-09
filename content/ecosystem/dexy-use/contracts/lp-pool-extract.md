---
title: kushti/dexy-stable — extract.es
description: "ErgoScript contract analysis: contracts/lp/pool/extract.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/extract.es
project: dexy-use
---
# ErgoScript Contract Analysis: `extract.es`

## Purpose

This contract manages **Dexy token extraction and release operations** in the Dexy LP pool during peg instability. It allows Dexy to be extracted from the LP when reserves are depleted and the peg falls below 95%, then released back when the peg recovers above 101%—implementing a **state machine** that enforces timing constraints and peg thresholds to stabilize the stablecoin.

---

## Inputs / Outputs

### Inputs
| Index | Box | Purpose |
|-------|-----|---------|
| 0 | LP Box | The liquidity pool itself; reserves must be updated to reflect Dexy extraction/release |
| 1 | Extract Box (SELF) | This contract's box; holds extraction NFT and Dexy tokens; persists across transactions |
| — | — | — |

### Outputs
| Index | Box | Purpose |
|-------|-----|---------|
| 0 | LP Box | Updated LP with adjusted Dexy reserves after extraction/release |
| 1 | Extract Box (successor) | SELF preserved with updated Dexy token quantity |

### Data Inputs
| Index | Box | Purpose |
|-------|-----|---------|
| 0 | Oracle Box | Provides current price feed (nanoErgs per USD) in R4 |
| 1 | Tracking Box (95% or 101%) | Records height when peg crossed 95% or 101% threshold |
| 2 | Bank Box *(optional)* | Validates that bank reserves are depleted (≤ 10,000 ERG) |

---

## Key Logic

### Two Execution Paths

#### **Path 1: Update via updateNFT (Bypass)**
```
validUpdate = INPUTS(0).tokens(0)._1 == updateNFT
↓
If true → validAction = true (protocol update, skip all checks)
```
Allows authorized operators to update contract state during protocol upgrades.

#### **Path 2: Extract or Release (Standard Operation)**

**Prerequisite Checks:**
- **Successor validity**: The output Extract box must:
  - Preserve extraction NFT and Dexy token ID
  - Keep proposition bytes unchanged
  - Maintain minimum box value
  - Have creation height within `buffer` (5 blocks) of current HEIGHT
  
- **Delay enforcement**: `lastBurnOrRelease < HEIGHT - T_delay`
  - At least 360 blocks must elapse between any two operations

- **LP box integrity**: 
  - NFT, LP tokens, Dexy token ID all preserved
  - Dexy reserves adjust by `deltaDexy`: `reservesYOut = reservesYIn - deltaDexy`
  - ERG reserves (X) unchanged
  - Proposition bytes unchanged

- **Oracle & Tracking validation**:
  - Oracle box holds oracleNFT
  - Tracking box holds appropriate NFT (95% or 101%)

---

### **EXTRACT Operation** (Restore depleted reserves)
Triggered when `deltaDexy > 0` (Dexy tokens added to Extract box):

1. **Peg threshold check**:
   ```
   oracleRateXY × 97 < lpRateXYOut × 100    (peg < 0.97 × oracle price)
   oracleRateXY × 98 > lpRateXYOut × 100    (peg > 0.98 × oracle price)
   ↓ (peg between 97% and 98%)
   ```

2. **Time-lock check**:
   ```
   (HEIGHT - tracker95Height) > T_extract (720 blocks)
   ↓ Dexy has been < 95% peg for at least 720 blocks
   ```

3. **Bank reserve check**:
   ```
   Bank box value ≤ minBankNanoErgs (10,000 ERG)
   ↓ Vault is depleted, justify extraction
   ```

---

### **RELEASE Operation** (Return extracted Dexy)
Triggered when `deltaDexy < 0` (Dexy tokens removed from Extract box):

1. **Peg threshold check**:
   ```
   oracleRateXY × 101 > lpRateXYOut × 100
   ↓ (peg > 1.01, recovered above peg)
   ```

2. **Time-lock check**:
   ```
   HEIGHT - tracker101Height > T_release (2 blocks)
   ↓ Dexy has been > 101% for at least 2 blocks
   ```

---

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R3** | CreationInfo | Stores box creation height and transaction ID; used to enforce `T_delay` via `SELF.creationInfo._1` | Read |
| **R4** (Oracle) | Long | Nanoergs per 1 USD; scaled down by ÷1000 to get nanoErg per USE (3 decimals) | Read (data input) |
| **R7** (Tracking) | Int | Height at which peg crossed 95% or 101% threshold; used for `T_extract` / `T_release` enforcement | Read (data input) |

---

## Tokens

### Extract Box
| Position | Token | Purpose |
|----------|-------|---------|
| tokens(0) | **extractionNFT** | Singleton identity; proves this is the authorized Extract box; preserved across all transactions |
| tokens(1) | **Dexy token ID** | The stablecoin being managed; quantity varies with extraction/release (`deltaDexy`) |

### Related Token IDs (Constants)
```
tracking95NFT    → Identifies Tracking box monitoring < 95% peg
tracking101NFT   → Identifies Tracking box monitoring > 101% peg
bankNFT          → Identifies Bank/Vault box
lpNFT            → Identifies LP box
oracleNFT        → Identifies Oracle price feed box
updateNFT        → Identifies update authorization (bypass path)
```

---

## Integration Pattern

### Off-Chain Bot Responsibilities

1