---
title: kushti/dexy-stable — freemint.es
description: "ErgoScript contract analysis: contracts/bank/freemint.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/freemint.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `freemint.es`

## Purpose

This contract manages the **free minting mechanism** for Dexy stablecoins within the bank subsystem. It enforces periodic minting limits tied to oracle prices, ensures fees are properly distributed to Bank and Buyback boxes, and resets minting quotas at regular intervals. This implements the price-stability and collateralization guarantees of the Dexy protocol.

---

## Inputs / Outputs

### Inputs
| Index | Box Type | Role | Key Tokens |
|-------|----------|------|-----------|
| **0** | FreeMint (SELF) | State machine for free-mint tracking | Free-mint NFT (Singleton) |
| **1** | Bank | Collateral holder & fee recipient | Bank NFT |
| **2** | Buyback | Stability mechanism & fee recipient | Buyback NFT |

### Data Inputs (Context References)
| Index | Box Type | Role | Key Data |
|-------|----------|------|----------|
| **0** | Oracle Pool | Price feed source | R4: nanoErgs per USD (Long) |
| **1** | LP Pool | Dexy reserve state | R4+: reserves for rate validation |

### Outputs
| Index | Box Type | Role |
|-------|----------|------|
| **0** | FreeMint (successor) | Updated state with reset counter/quota |
| **1** | Bank | Updated collateral after fee deposit |
| **2** | Buyback | Updated reserves after fee deposit |

---

## Key Logic

### 1. **Counter Reset Mechanism**
```
isCounterReset = HEIGHT > selfInR4
```
- If current block height exceeds R4 (reset height), the minting quota resets
- New quota = 1% of LP's Dexy reserves (`maxAllowedIfReset = lpReservesY / 100`)
- New reset height set to `HEIGHT + T_free + T_buffer` (360 + 5 blocks on mainnet = ~180.5 min window)

### 2. **Rate Validation (Peg Protection)**
```
validRateFreeMint = lpRate * 100 > oracleRate * 98
```
- Ensures LP's internal rate (nanoErgs/Dexy) stays within **2% spread** of oracle rate
- Prevents free minting when Dexy price deviates significantly from collateral value
- Protects against pool manipulation or stale oracle data

### 3. **Fee Distribution to Bank & Buyback**
Both the Bank and Buyback boxes receive ERG contributions proportional to Dexy minted:

**Bank Fee:**
```
bankRate = oracleRate * (bankFeeNum + feeDenom) / feeDenom
validBankDelta = ergsAdded >= dexyMinted * bankRate
```
With default constants: fee = 3/1000 = 0.3% of oracle rate

**Buyback Fee:**
```
buybackRate = oracleRate * buybackFeeNum / feeDenom
validBuybackDelta = buybackErgsAdded >= dexyMinted * buybackRate
```
With default constants: fee = 2/1000 = 0.2% of oracle rate

Total fee: **0.5%** of minted Dexy's oracle value (in ERGs)

### 4. **Quota Enforcement**
```
validAmount = dexyMinted <= availableToMint
```
- `availableToMint` = remaining quota from R5 (if not reset) or 1% of LP reserves (if reset)
- Single transaction cannot exceed available quota

### 5. **State Machine Invariants**
```
validSuccessor:
  - NFT preserved (Singleton constraint)
  - Script preserved (UTXO must retain same ErgoScript)
  - Value ≥ input value (no ERG extraction)
  - R5 updated: availableToMint - dexyMinted (quota decrements)
  - R4 updated: 
    - If no reset: unchanged
    - If reset: set to HEIGHT + T_free ± T_buffer (5 block window for broadcast delay)
```

---

## Registers Used

| Register | Type | Purpose | Input→Output Behavior |
|----------|------|---------|----------------------|
| **R4** | `Int` | Block height at which quota resets | Preserved or set to `HEIGHT + T_free` (360 blocks ≈ 3 hours) |
| **R5** | `Long` | Remaining Dexy tokens available to mint | Decremented: `R5_out = R5_in - dexyMinted` |
| **R6-R9** | — | *Unused* | — |

---

## Tokens

| Token Type | Purpose | Box | Constraint |
|------------|---------|-----|-----------|
| **Free-mint NFT** | Singleton identifier for this contract state | FreeMint (SELF) | Must be preserved in successor (token ID immutable) |
| **Bank NFT** | Identifies the Bank collateral box | Input #1 | Validated via `validBankBoxInOut` |
| **Buyback NFT** | Identifies the Buyback fee recipient box | Input #2 | Validated via `validBuyBackIn` |
| **Oracle NFT** | Authenticates oracle-pool data input | DataInput #0 | Validated via `validOracleBox` |
| **LP NFT** | Authenticates LP pool data input | DataInput #1 | Validated via `validLpBox` |
| **Dexy Token** | Stablecoin output to user (off-chain) | Bank output (tokens(1)) | Tracked via `bankBoxIn.tokens(1)._2 - bankBoxOut.tokens(1)._2` |

**Token ID Rule:** All NFTs are embedded as Base64 constants (`$bankNFT`, `$buybackNFT`, etc.), set during contract deployment.

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

The off-chain executor must:

1. **Fetch Oracle Data**
   - Read Oracle pool box containing current rate in R4 (nanoErgs per USD)
   - Validate