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
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `extract.es`

## Purpose

This contract manages **"Extract-to-the-Future"** operations for the Dexy stablecoin within an Automated Market Maker (AMM) liquidity pool. It allows controlled extraction of Dexy tokens from the LP when the stablecoin is depegged below its oracle-backed peg, and later release of those tokens back when the peg is restored. The contract enforces time-delays and peg-band thresholds to prevent arbitrage and maintain reserve stability.

---

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | LP Box | Liquidity pool holding reserves (nanoErgs and Dexy tokens) |
| 1 | Extract Box (SELF) | State box holding Dexy tokens to be extracted/released; carries `extractionNFT` |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | LP Box | Updated LP with adjusted Dexy reserves after extraction/release |
| 1 | Extract Box (successor) | Updated state box preserving `extractionNFT` and tracking tokens |

### Data Inputs
| Index | Box Type | Role |
|-------|----------|------|
| 0 | Oracle Box | Provides `nanoErgs per 1 mg of gold` rate (R4); validates peg pricing |
| 1 | Tracking Box (95% or 101%) | Records block height when exchange rate crossed 95% or 101% threshold |
| 2 | Bank Box (optional) | Confirms bank reserves are "lean" (< 10,000 ERG) to authorize extraction |

---

## Key Logic

### Action Validation (`validAction`)

The contract supports **two distinct transaction types**:

#### 1. **Extract-to-Future** (Dexy extraction during depeg)
```
Condition: deltaDexy > 0 (Dexy tokens increase in Extract box)
```
- **Peg Threshold**: Tracking box must record ≥ `T_extract` (720) blocks at rate < 95%
- **Price Band**: Oracle rate must satisfy: `0.97 × lpRate < oracleRate < 0.98 × lpRate`  
  - Ensures extraction occurs only when Dexy is moderately depegged (3-2% below peg)
- **Bank Check**: Bank box must exist AND hold < 10,000 ERG (reserves are depleted)
- **Timestamp Guard**: At least `T_delay` (360) blocks must elapse since last burn/release

#### 2. **Reverse Extract** (Release when peg recovers)
```
Condition: deltaDexy < 0 (Dexy tokens decrease from Extract box)
```
- **Peg Threshold**: Tracking box must record ≥ `T_release` (2) blocks at rate > 101%
- **Price Condition**: Oracle rate must satisfy: `oracleRate > 1.01 × lpRate`
  - Signals Dexy is premium; safe to release extracted tokens

#### **Common Invariants** (both actions)
- ✅ NFTs preserved: `extractionNFT` in successor box
- ✅ Dexy token ID invariant: LP output's Dexy token = Extract box's token(1)
- ✅ LP reserves conservation: `reservesY_out = reservesY_in - deltaDexy` (Dexy balance)
- ✅ Ergs conservation: `reservesX_out = reservesX_in` (nanoErg balance unchanged)
- ✅ No script change: `propositionBytes` preserved for both LP and Extract boxes
- ✅ Value non-decreasing: `successor.value ≥ SELF.value`
- ✅ Creation height recent: `creationInfo._1 ≥ HEIGHT - buffer` (congestion tolerance)

#### **Update Bypass** (Privileged Operation)
```
if (INPUTS(0).tokens(0)._1 == updateNFT) { validAction = true }
```
An `updateNFT` in input[0] bypasses all validation—allows administrative corrections.

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R3** | *CreationInfo* | Built-in: box creation block height; used for `lastBurnOrRelease = SELF.creationInfo._1` to enforce `T_delay` |
| **R4** (Oracle) | Long | Oracle rate: **nanoErgs per 1 mg of gold** (divided by 1,000,000 from original per-kg rate) |
| **R7** (Tracking) | Int | Block height when peg threshold (95% or 101%) was crossed; enables time-window enforcement |

---

## Tokens

### Extract Box Tokens
| Index | Token | Purpose |
|-------|-------|---------|
| 0 | `extractionNFT` | **State singleton NFT**; identifies this contract instance; must be preserved in successor |
| 1 | Dexy (native token) | **Value carrier**; quantity varies per action (increases in extract, decreases in release); ID constant |

### Validator Tokens (Data Inputs)
| NFT | Source Box | Role |
|-----|-----------|------|
| `tracking95NFT` | Tracking Box (95%) | Oracle rate below 95% for ≥ 720 blocks; enables extraction |
| `tracking101NFT` | Tracking Box (101%) | Oracle rate above 101% for ≥ 2 blocks; enables release |
| `bankNFT` | Bank Box | Identifies reserve account; must be < 10k ERG to permit extraction |
| `lpNFT` | LP Box | Identifies liquidity pool; verified as input[0] |
| `oracleNFT` | Oracle Box | Identifies price feed; validated in data input |
| `updateNFT` | Input[0] (optional) | Privileged override; if present, bypasses all validation |

---

## Integration Pattern

### Off-Chain Responsibilities (Bot / Headless dApp)

1. **Monitor