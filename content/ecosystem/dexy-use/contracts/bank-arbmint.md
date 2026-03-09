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
project: dexy-use
---
# ErgoScript Contract Analysis: `arbmint.es`

## Purpose

This contract governs **Arbitrage Mint actions** in the Dexy stablecoin system. It validates conditions under which new Dexy tokens can be minted by arbitrageurs when LP reserves deviate from oracle prices, maintaining price stability through an automated counter-reset mechanism that limits mint volume per epoch.

---

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| **0** | ArbitrageMint (SELF) | State box holding arbitrage mint NFT, counter height (R4), and remaining mint quota (R5) |
| **1** | Bank | Holds bank-side collateral and Dexy token reserve |
| **2** | BuyBack | Holds buyback reserve for redemption support |

### Data Inputs (Read-Only)
| Index | Box Type | Purpose |
|-------|----------|---------|
| **0** | Oracle Pool | Provides current USD/nanoErg exchange rate in R4 |
| **1** | LP Box | Liquidity pool reserves (X=nanoErgs, Y=Dexy tokens) for rate calculation |
| **2** | Tracking101 | Tracks time elapsed since mint epoch started; triggers counter reset validation |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| **0** | ArbitrageMint (successor) | Updated state box with adjusted counter and remaining quota |
| **1** | Bank | Updated with received nanoErgs, reduced Dexy balance |
| **2** | BuyBack | Updated with received nanoErgs for buyback reserve |

---

## Key Logic

### 1. **Counter & Quota Management**
- Reads R4 (reset height) and R5 (remaining mintable Dexy) from SELF
- If `HEIGHT > R4`, counter has expired → recalculate maximum allowable mint from LP reserves
- Otherwise, use remaining quota from R5
- **Invariant**: `dexyMinted ≤ availableToMint`

### 2. **Price Validation via LP Rate**
```
lpRate = lpReservesX / lpReservesY
validThreshold = lpRate * 100 > thresholdPercent * oracleRateWithFee
```
- Only mints when LP rate exceeds oracle rate by >1% (threshold = 101%)
- This ensures arbitrage only occurs when LP is significantly overvalued vs. oracle

### 3. **Fee & Delta Validation**
Minting incurs composite fees split between Bank (0.3%) and BuyBack (0.2%):
```
bankRate = oracleRate × (3 + 1000) / 1000
buybackRate = oracleRate × 2 / 1000
```
- Bank receives: `ergsAdded ≥ dexyMinted × bankRate`
- BuyBack receives: `buybackErgsAdded ≥ dexyMinted × buybackRate`
- Both deltas must be positive (non-negative ergs deposited)

### 4. **Quota Calculation (Reset Case)**
```
maxAllowedIfReset = (lpReservesX - oracleRateWithFee × lpReservesY) / oracleRateWithFee
```
Ensures post-mint LP rate does not fall below oracle rate with fees:
- Before: `lpReservesX / lpReservesY > oracleRateWithFee`
- After: `lpReservesX / (lpReservesY + dexyMinted) ≤ oracleRateWithFee`

### 5. **Time-Lock & Delay Validation**
- `validDelay`: Requires ≥30 blocks (`T_arb`) since tracking started (from tracking101Box.R7)
- `validSuccessorR4`: If no reset, preserve R4; if reset, set to `HEIGHT + 30..35` (1-hour epoch + 5-block buffer)
- Prevents rapid successive arbitrage exploits

### 6. **State Preservation & NFT Authentication**
- Successor must preserve NFT, script, and value ≥ input value
- All reference boxes validated by their singleton NFTs (bankNFT, lpNFT, oracleNFT, etc.)
- **State machine invariant**: NFT identity ensures this box cannot be forked

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Int` | **Counter reset height** – when mint quota resets to maximum. Updated on counter expiry to `HEIGHT + 30` |
| **R5** | `Long` | **Remaining mintable Dexy tokens** – quota balance decremented by each mint. Reset to `maxAllowedIfReset` when counter expires |

---

## Tokens

| Token Slot | Token ID Variable | Purpose |
|------------|-------------------|---------|
| **SELF.tokens(0)** | `Arbitrage-mint NFT` (base64 constant) | **Singleton NFT** – ensures this contract instance is unique; prevents double-spending of the state box |
| **Bank.tokens(0)** | `bankNFT` | Identifies the Bank box; required data validation |
| **Bank.tokens(1)** | Dexy token ID | Tracks Dexy balance changes (`dexyMinted = inBalance - outBalance`) |
| **BuyBack.tokens(0)** | `buybackNft` | Identifies BuyBack box |
| **LP.tokens(0)** | `lpNFT` | Identifies LP box |
| **LP.tokens(2)** | Dexy token ID | LP's Dexy reserves (used in rate calculations) |
| **Oracle.tokens(0)** | `oracleNFT` | Identifies Oracle pool box |
| **Tracking101.tokens(0)** | `tracking101NFT` | Identifies tracking box |

---

## Integration Pattern

### Off-Chain Bot Responsibilities

1. **Monitor Conditions**
   - Poll Oracle pool for current USD rate
   - Poll LP box for reserve imbalance
   - Check if `lpRate > 1.01 × orac