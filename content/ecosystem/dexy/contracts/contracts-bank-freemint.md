---
title: kushti/dexy-stable — freemint.es
description: "ErgoScript contract analysis: contracts/bank/freemint.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/freemint.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `freemint.es`

## Purpose

This contract implements the **Free Mint mechanism** for the Dexy stablecoin system, allowing controlled issuance of Dexy tokens during designated free-mint periods. It enforces rate validation against an oracle, distributes fees to Bank and Buyback reserves, and rate-limits minting to 1% of LP reserves per period to maintain system stability.

---

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Free-Mint Box** (SELF) | Stateful singleton holding minting authority and period counters |
| 1 | **Bank Box** | Reserve accumulating Dexy tokens; receives ERG fees |
| 2 | **Buyback Box** | Reserve accumulating buyback fees in ERG |

### Data Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Oracle Pool Box** | Provides current exchange rate (nanoErgs per USD) in R4 |
| 1 | **LP Box** | Provides liquidity pool reserves for rate validation and mint caps |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Free-Mint Box Successor** | Updated singleton with reset counter and remaining mint quota |
| 1 | **Bank Box Successor** | Updated reserves after fee allocation |
| 2 | **Buyback Box Successor** | Updated reserves after buyback fee allocation |

---

## Key Logic

### 1. **Counter Reset Detection**
```
isCounterReset = HEIGHT > selfInR4
```
Determines if the current block height exceeds the reset threshold. If true, a new minting period begins and quotas are refreshed.

### 2. **Rate Validation (Oracle vs. LP)**
```
validRateFreeMint = lpRate * 100 > oracleRate * 98
```
Ensures the LP price (ERG per Dexy) remains within 2% above the oracle rate. This prevents minting at unfavorable prices and protects the system from arbitrage attacks.

**Rate Calculation:**
- `oracleRate` = Oracle R4 / 1,000,000 (converts nanoErgs/USD to nanoErgs/Dexy, assuming 1 Dexy ≈ 1 mg gold)
- `lpRate` = lpReservesX (ERG) / lpReservesY (Dexy tokens)

### 3. **Fee Distribution**
Two separate fee mechanisms apply to minted Dexy:

**Bank Fee:**
```
bankRate = oracleRate * (bankFeeNum + feeDenom) / feeDenom
validBankDelta = ergsAdded >= dexyMinted * bankRate && ergsAdded > 0
```
Charges 0.3% (3/1000) additional ERG per Dexy minted; ERGs flow into Bank reserve.

**Buyback Fee:**
```
buybackRate = oracleRate * buybackFeeNum / feeDenom
validBuybackDelta = buybackErgsAdded >= dexyMinted * buybackRate && buybackErgsAdded > 0
```
Charges 0.2% (2/1000) additional ERG per Dexy minted; ERGs flow into Buyback reserve.

**Total Fee:** 0.5% (5/1000)

### 4. **Minting Quota & Rate Limiting**
```
maxAllowedIfReset = lpReservesY / 100  // 1% of LP Dexy reserves
availableToMint = if (isCounterReset) maxAllowedIfReset else selfInR5
validAmount = dexyMinted <= availableToMint
```
- On period reset: quota = 1% of current LP reserves
- Otherwise: quota = remaining balance from previous period (R5)
- Prevents excessive minting in a single period

### 5. **Register Updates (State Machine)**
```
validSuccessorR4 = if (!isCounterReset) {
    successorR4 == selfInR4  // No change if period active
} else {
    successorR4 >= HEIGHT + T_free &&
    successorR4 <= HEIGHT + T_free + T_buffer
}
validSuccessorR5 = successorR5 == availableToMint - dexyMinted
```
- **R4 (reset height):** Updated to `HEIGHT + 360 blocks (±5 buffer)` only on reset; locked otherwise
- **R5 (remaining quota):** Decremented by minted amount

### 6. **Singleton Preservation**
```
successor.tokens == SELF.tokens
successor.propositionBytes == SELF.propositionBytes
successor.value >= SELF.value
```
Ensures the Free-Mint NFT is carried forward, the script hash is unchanged, and min box value is maintained.

### 7. **NFT Validation**
```
validBankBoxInOut = bankBoxIn.tokens(0)._1 == bankNFT
validBuyBackIn = buybackBoxIn.tokens(0)._1 == buybackNft
validLpBox = lpBox.tokens(0)._1 == lpNFT
validOracleBox = oracleBox.tokens(0)._1 == oracleNFT
```
Confirms identity of all participating boxes via embedded NFT token IDs (Singleton pattern / State NFT).

---

## Registers Used

| Register | Type | Purpose | Usage |
|----------|------|---------|-------|
| **R4** | `Int` | Block height at which minting counter resets | Read: `selfInR4`; Written: `successorR4` |
| **R5** | `Long` | Remaining Dexy tokens available to mint before next reset | Read: `selfInR5`; Written: `successorR5` |

Both registers implement a **State Machine** pattern:
- R4 advances every `T_free` (360 blocks) with tolerance `T_buffer` (5 blocks)
- R5 tracks quota depletion and resets to 1% of LP