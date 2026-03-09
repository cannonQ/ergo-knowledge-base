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
project: dexy-use
---
# ErgoScript Contract Analysis: `freemint.es`

## Purpose

This contract manages the **free mint action** for the Dexy stablecoin system, allowing controlled minting of Dexy tokens during designated free-mint periods. It validates that minted tokens are collateralized with sufficient ergs distributed to both the Bank and Buyback reserves, while enforcing per-period minting caps based on LP reserves and rate integrity checks against an oracle.

---

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **FreeMint Box** (SELF) | State machine singleton holding free-mint NFT; tracks remaining mintable tokens and reset height |
| 1 | **Bank Box** | Reserve box holding Dexy tokens; receives erg collateral from minting |
| 2 | **Buyback Box** | Buyback reserve; receives erg fees from minting |

### Data Inputs (Oracle / Reference Boxes)
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Oracle Pool Box** | Delivers current erg/USD exchange rate in R4; used to validate collateralization |
| 1 | **LP Box** | Liquidity pool reserves; provides market rate and minting cap (1% of Dexy reserves per period) |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **FreeMint Box (successor)** | Updated state machine; decremented R5 (remaining mintable tokens), updated R4 if period reset |
| 1 | **Bank Box** | Dexy token supply decreased; erg value increased by collateral |
| 2 | **Buyback Box** | Erg reserves increased by buyback fee |

---

## Key Logic

### 1. **Counter Reset Detection**
- If `HEIGHT > R4` (current block height exceeds reset height), the counter resets and allows a fresh `maxAllowedIfReset` amount to be minted.
- Otherwise, remaining mintable tokens come from `R5` (decrements across transactions).

### 2. **Rate Validation (LP vs. Oracle)**
```
validRateFreeMint: lpRate * 100 > oracleRate * 98
```
- LP rate must be within 2% of oracle rate to prevent arbitrage during minting.
- Protects against stale/manipulated oracle data.

### 3. **Collateralization Validation**
- **Bank collateral:** `ergsAdded >= dexyMinted × bankRate`
  - `bankRate = oracleRate × (bankFeeNum + 1000) / 1000` (0.3% fee embedded)
- **Buyback collateral:** `ergsAdded >= dexyMinted × buybackRate`
  - `buybackRate = oracleRate × buybackFeeNum / 1000` (0.2% fee embedded)
- Both conditions must hold; ensures backing ratio and fee collection.

### 4. **Minting Cap Enforcement**
```
availableToMint = isCounterReset ? (lpReservesY / 100) : selfInR5
validAmount: dexyMinted <= availableToMint
```
- Per-period max is **1% of LP Dexy reserves** (prevents rapid dilution).
- Enforced by tracking remaining quota in `R5`.

### 5. **State Transition Validation**

| Condition | Logic |
|-----------|-------|
| **R4 (reset height)** | If no reset: unchanged. If reset: set to `HEIGHT + T_free + T_buffer` (360 + 5 blocks = ~half-day + buffer) |
| **R5 (remaining quota)** | `successorR5 = availableToMint - dexyMinted` |
| **NFT preservation** | Free-mint NFT token ID must remain in successor |
| **Script preservation** | `propositionBytes` unchanged (singleton immutability) |
| **Value preservation** | `successor.value >= SELF.value` (no erg leakage) |

### 6. **Box Authentication**
- Validates NFT presence in Bank, Buyback, Oracle, and LP boxes via hardcoded token IDs.
- Ensures correct boxes are being spent/referenced.

---

## Registers Used

| Register | Type | Purpose | Access Pattern |
|----------|------|---------|-----------------|
| **R4** (Input) | `Int` | Block height at which minting counter resets | Read as `selfInR4`; compared to `HEIGHT` |
| **R4** (Output) | `Int` | Updated reset height for next period | Validated in `validSuccessorR4` |
| **R5** (Input) | `Long` | Remaining Dexy tokens available to mint in current period | Read as `selfInR5`; used in quota calculation |
| **R5** (Output) | `Long` | Decremented remaining quota | `successorR5 = availableToMint - dexyMinted` |
| **R4** (Oracle data input) | `Long` | Exchange rate: nanoErgs per USD | Read as `oracleRate / 1000` for USE-denominated calculations |

---

## Tokens

### Free-Mint Box
- **Token(0):** `Free-mint NFT` (singleton identifier)
  - Prevents multiple simultaneous free-mint states.
  - Must be preserved in successor box.

### Bank Box
- **Token(0):** `bankNFT` (state machine authentication)
- **Token(1):** **Dexy tokens** (`DEXY`)
  - Quantity decreases on mint: `dexyMinted = tokens(1)._2[in] - tokens(1)._2[out]`

### Buyback Box
- **Token(0):** `buybackNFT` (state machine authentication)

### LP Box (Data Input)
- **Token(0):** `lpNFT` (identifies liquidity pool)
- **Token(2):** **Dexy tokens in LP**
  - Read as `lpBox.tokens(2)._2` for reserve balance.

### Oracle Box (Data Input)
- **Token(0):** `o