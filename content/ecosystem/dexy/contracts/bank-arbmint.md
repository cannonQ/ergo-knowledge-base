---
title: kushti/dexy-stable — arbmint.es
description: "ErgoScript contract analysis: contracts/bank/arbmint.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/arbmint.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `arbmint.es`

## Purpose

This contract governs **arbitrage minting** of Dexy stablecoin tokens in response to LP pool imbalance. It enforces that Dexy can only be minted when the LP pool rate exceeds the oracle rate by a threshold (101%), ensuring the protocol maintains price stability through controlled arbitrage. The contract rate-limits minting via a counter that resets every ~1 hour (30 blocks).

---

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **ArbitrageMint** (SELF) | State box holding minting counter and limits; carries Arbitrage-mint NFT |
| 1 | **Bank** | Protocol bank box; receives ergs, loses Dexy tokens |
| 2 | **BuyBack** | Buyback/stabilization box; receives ergs for protocol stability |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **ArbitrageMint** (successor) | Updated state box with decremented counter and reset height |
| 1 | **Bank** | Bank box after minting (ergs added, Dexy decreased) |
| 2 | **BuyBack** | Buyback box after fee distribution (ergs added) |

### Data Inputs (read-only, verify external state)
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Oracle Pool** | Contains current oracle rate in R4 (nanoErgs per USD) |
| 1 | **LP Box** | Contains LP pool reserves (ergs and Dexy); computes current LP rate |
| 2 | **Tracking101 Box** | Contains R7 (height at which arbitrage tracking began) |

---

## Key Logic

### 1. **Counter Reset Mechanism**
- **R4 (Int)**: Height at which counter resets
- **R5 (Long)**: Remaining Dexy tokens available to mint before reset
- If `HEIGHT > R4_in`, counter is reset: R4 is set to `HEIGHT + T_arb ± T_buffer` (≈30-35 blocks ≈ 1 hour ± 5 blocks), and R5 is recalculated from fresh LP state
- Otherwise, R4 is preserved and R5 decrements

### 2. **Rate Validation (Core Arbitrage Trigger)**

**Oracle Rate** (from data input):
```
oracleRate = oracleBox.R4[Long] / 1000000  (nanoErgs per Dexy/mg)
```

**LP Rate** (from data input):
```
lpRate = lpReserves_ergs / lpReserves_dexy
```

**Trigger Condition**:
```
lpRate * 100 > 101 * (oracleRate + feeRate)
```
- LP rate must exceed oracle rate by >1% to justify minting
- This signals the pool is erg-heavy (Dexy underpriced), allowing arbitrage mint

### 3. **Erg Payment Validation**

Ergs added must exceed Dexy minted × oracle rate + fees:

**Bank Fee Rate**:
```
bankRate = oracleRate * (3 + 1000) / 1000 = oracleRate * 1.003
validBankDelta: ergsAdded_bank ≥ dexyMinted * bankRate
```

**Buyback Fee Rate**:
```
buybackRate = oracleRate * 2 / 1000 = oracleRate * 0.002
validBuybackDelta: ergsAdded_buyback ≥ dexyMinted * buybackRate
```

**Combined**: Both conditions must hold; total fee = 0.5%

### 4. **Minting Cap (Per-Period Limit)**

After counter reset, max Dexy that can be minted is:
```
maxAllowedIfReset = (lpReserves_ergs - oracleRateWithFee * lpReserves_dexy) 
                    / oracleRateWithFee
```

**Invariant**: After minting, LP rate ≤ oracle rate + fees, restoring balance:
```
lpReserves_ergs / (lpReserves_dexy + dexyMinted) ≤ oracleRateWithFee
```

Actual limit = `maxAllowedIfReset` if counter reset, else `R5_in` (remaining from prior period).

### 5. **Delay Requirement**

Minting only allowed if arbitrage tracking started ≥ 30 blocks ago:
```
tracking101Height < HEIGHT - 30
```
Prevents flash-loan or rapid-fire arbitrage exploits.

### 6. **State Machine Transitions**

**Successor Box (R4/R5 Updates)**:
- If **no reset**: R4 unchanged, R5 decrements by `dexyMinted`
- If **reset**: R4 set to `[HEIGHT + 30, HEIGHT + 35]`, R5 recalculated
- Successor must preserve NFT, script, and maintain/increase erg value

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Int` | Reset height; determines when counter resets (~30 blocks / 1 hour) |
| **R5** | `Long` | Remaining Dexy minting quota before next reset |
| **R7** (tracking101Box) | `Int` | Height at which arbitrage opportunity was first tracked |

---

## Tokens

### Singleton NFTs (Authentication)
| Token | Purpose | Carried By |
|-------|---------|-----------|
| **Arbitrage-mint NFT** | Identifies this contract's state box | ArbitrageMint (tokens(0)) |
| **Bank NFT** | Identifies protocol bank box | Bank input/output (tokens(0)) |
| **BuyBack NFT** | Identifies buyback/stabilization box | BuyBack input/output (tokens(0)) |
| **Oracle NFT