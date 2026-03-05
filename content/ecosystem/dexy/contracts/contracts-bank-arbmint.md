---
title: kushti/dexy-stable — arbmint.es
description: "ErgoScript contract analysis: contracts/bank/arbmint.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/arbmint.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `arbmint.es`

## Purpose

This contract enforces arbitrage-triggered minting of Dexy stablecoins through a rate-monitoring mechanism. It ensures that Dexy tokens are only minted when the LP pool price deviates significantly above the oracle rate, maintaining stability by allowing arbitrageurs to mint and sell back to the pool when profitable to do so. The contract tracks a counter that resets periodically to limit minting volume per epoch.

---

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **ArbitrageMint** (SELF) | State box holding counter and minting allowance; authenticated by Arbitrage-mint NFT |
| 1 | **Bank** | Bank vault box containing Dexy token supply; identified by Bank NFT |
| 2 | **BuyBack** | Buyback box (likely a reserve); identified by Buyback NFT |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **ArbitrageMint** (successor) | Updated state box; preserves NFT, script, registers, and value |
| 1 | **Bank** | Updated bank box after Dexy minting and erg deposit |
| 2 | **BuyBack** | Updated buyback box after erg allocation |

### Data Inputs (non-spent, read-only)
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Oracle Pool** | Provides current exchange rate (nanoErgs per USD) in R4 |
| 1 | **LP Pool** | Provides current LP reserves (ergs and Dexy) to calculate pool rate |
| 2 | **Tracking101** | References the height when arbitrage monitoring began; contains Tracking101 NFT |

---

## Key Logic

### 1. **Rate Comparison & Threshold Check**
```
validThreshold = lpRate * 100 > thresholdPercent * oracleRateWithFee
```
- **LP Rate**: `lpReservesX / lpReservesY` (ergs per Dexy in the pool)
- **Oracle Rate with Fee**: `oracleRate * (3 + 2) / 1000` (0.5% total fee)
- **Condition**: LP pool price must exceed oracle price by >1% to trigger minting
- **Purpose**: Only allows arbitrage minting when profitable (pool overpriced relative to oracle)

### 2. **Delay Validation**
```
validDelay = tracking101Height < HEIGHT - T_arb
```
- Enforces that at least **30 blocks (~1 hour)** have passed since tracking started
- Prevents rapid successive arbitrage operations
- `T_buffer = 5` blocks allows for network confirmation delays

### 3. **Counter Reset Logic**
```
isCounterReset = HEIGHT > selfInR4
```
- If current height exceeds R4 (reset height), counter resets; otherwise accumulates
- **On reset**: `maxAllowedIfReset = (lpReservesX - oracleRateWithFee * lpReservesY) / oracleRateWithFee`
  - Calculates max Dexy that can be minted without dropping pool price below oracle rate
- **No reset**: Uses remaining allowance from R5

### 4. **Minting Amount Validation**
```
validAmount = dexyMinted <= availableToMint
```
- Ensures minted Dexy does not exceed per-epoch allowance
- Prevents excessive supply inflation in a single period

### 5. **Fee Distribution**
```
bankRate = oracleRate * (3 + 2) / 1000 = oracleRate * 5 / 1000
validBankDelta = ergsAdded >= dexyMinted * bankRate
validBuybackDelta = buybackErgsAdded >= dexyMinted * buybackFeeNum / feeDenom
```
- **Bank receives**: 3/1000 (0.3%) of minted Dexy value in ergs
- **Buyback receives**: 2/1000 (0.2%) of minted Dexy value in ergs
- Both must be satisfied; funds compensate protocol for minting

### 6. **Successor Box Validation**
```
validSuccessor = (tokens preserved) && (script preserved) && (value >= input value) &&
                 (validSuccessorR5 && validSuccessorR4)
```
- **Immutability**: NFT and ErgoScript must remain unchanged (State NFT pattern)
- **Value preservation**: Output value ≥ input value (accounting for tx fees)
- **Register updates**:
  - **R4 (next reset height)**: If reset occurs, set to `HEIGHT + 30 + [0..5]`; else unchanged
  - **R5 (remaining allowance)**: `availableToMint - dexyMinted`

---

## Registers Used

| Register | Type | Input Value | Output Value | Purpose |
|----------|------|------------|--------------|---------|
| **R4** | `Int` | `selfInR4` | `successorR4` | **Height at which counter resets**; triggers minting allowance recalculation |
| **R5** | `Long` | `selfInR5` | `successorR5` | **Remaining Dexy tokens available to mint** in current epoch |

**No other registers (R6–R9) are used in this contract.**

---

## Tokens

### NFTs (Authentication/State)
| NFT ID | Carried By | Purpose |
|--------|-----------|---------|
| **Arbitrage-mint NFT** | SELF (ArbitrageMint box) | Authenticates this box as the official arbitrage-mint state machine; prevents spoofing |
| **Bank NFT** | Bank input/output | Authenticates the bank vault box |
| **Buyback NFT** | BuyBack input/output | Authenticates the buyback reserve box |
| **Oracle NFT** | Oracle data-input | Authenticates the oracle pool box (read-only) |
| **LP NFT** | LP data