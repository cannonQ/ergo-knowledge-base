---
title: kushti/dexy-stable — redeem.es
description: "ErgoScript contract analysis: contracts/lp/pool/redeem.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/redeem.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: LP Redeem (kushti/dexy-stable)

## Purpose

This contract validates the redemption of Liquidity Provider (LP) tokens from a liquidity pool, ensuring that when LPs burn their tokens, they receive a proportional share of the pool's reserves (gold and ERG) at a fair exchange rate. It acts as a sub-contract protecting the LP pool box during redemption operations, enforcing mathematical invariants and oracle-backed pricing to prevent arbitrage exploitation.

---

## Inputs / Outputs

### Inputs
- **Primary Input (Index 0)**: The LP pool box containing:
  - `value`: Reserve quantity of X (ERG in nanoErgs)
  - `tokens(1)`: LP token with remaining supply quantity
  - `tokens(2)`: Y reserve (gold/Dexy token) with its quantity

### Data Inputs
- **Oracle Box (Index 0)**: Read-only data input containing:
  - `tokens(0)`: Oracle NFT (for authentication)
  - `R4`: Long value representing the current exchange rate (nanoErgs per kg gold)

### Outputs
- **Output 0 (LP Pool Box)**: Successor state with updated reserves after redemption
- **Output 1 (Redeem Contract)**: The redeem contract box itself (successor), preserving its state and value

---

## Key Logic

### 1. **Oracle Authentication & Rate Validation**
```
validOracleBox = oracleBox.tokens(0)._1 == oracleNFT
validRateForRedeemingLp = validOracleBox && lpRateXyIn > oracleRateXy * 98 / 100
```
- Verifies the oracle box carries the expected NFT
- Ensures the current pool exchange rate (reserves ratio) stays within 98% of the oracle-provided fair price
- Prevents redemption when pool is significantly overpriced or underpriced relative to market

### 2. **LP Supply Calculation**
```
supplyLpIn = initialLp - lpReservesIn._2
```
- Circulating LP supply = initial minted amount minus LP tokens held in reserve
- Accounts for initial token burning (UniSwap v2 pattern)

### 3. **Redemption Invariant**
```
deltaSupplyLp < 0 && deltaReservesX < 0 && deltaReservesY < 0
```
- All deltas must be **negative** (tokens burned, reserves decrease)
- Prevents minting disguised as redemption

### 4. **Fair Proportional Exchange** (Core Validation)
```
deltaReservesX.toBigInt * supplyLpIn * 100 / 98 >= _deltaSupplyLp * reservesXIn &&
deltaReservesY.toBigInt * supplyLpIn * 100 / 98 >= _deltaSupplyLp * reservesYIn
```
- Ensures redeemer receives **at least** the proportional share of each reserve
- Formula: `|ΔReserve| * supply * 100/98 ≥ |ΔLpSupply| * initialReserve`
- The `100/98` factor implements a **2% liquidity provider fee** (redeemers pay, LPs earn)
- Uses `BigInt` to prevent overflow on large redemptions

### 5. **State Preservation**
```
selfPreserved = successor.propositionBytes == SELF.propositionBytes &&
                successor.value >= SELF.value &&
                successor.tokens == SELF.tokens
```
- Redeem contract box must pass forward with identical script, sufficient ERG, and same tokens
- Ensures singleton pattern integrity

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** (Oracle Box) | `Long` | Exchange rate from oracle: nanoErgs per kg of gold (scaled; divided by 1,000,000 for per-Dexy rate) |
| **R4-R9** (Redeem Box) | *Not used* | All transient state flows through token quantities in INPUTS/OUTPUTS |

---

## Tokens

### Token Roles

| Position | Token Type | Purpose | Box Location |
|----------|-----------|---------|---|
| **tokens(0)** | Singleton NFT | Unique identifier for redeem contract box | Redeem box itself |
| **tokens(1)** | LP Token (native) | Represents liquidity provider share; burned during redemption | LP pool box |
| **tokens(2)** | Y Reserve (gold/Dexy) | Second reserve asset | LP pool box |

### Token ID Rule Implications
- The oracle NFT (`oracleNFT`) is a Singleton used for **authentication** (prevents accepting rates from arbitrary boxes)
- LP tokens and Y tokens are **fungible** (standard native tokens with quantities)

---

## Integration Pattern

### Off-Chain Construction (Bot/Headless dApp Requirements)

1. **Fetch Current State**
   - Query the LP pool box (identified by singleton NFT in tokens(0))
   - Query the oracle pool box (identified by `oracleNFT`)

2. **Calculate Redemption Parameters**
   ```
   - User provides: lpTokensToBurn (amount)
   - Compute:
     - reserveXShare = (lpTokensToBurn / supplyLp) * reservesX
     - reserveYShare = (lpTokensToBurn / supplyLp) * reservesY
     - Apply 2% fee: actual amounts = reserves * 100/98
   ```

3. **Validate Rate**
   - Check: `lpRateXyIn = reservesX / reservesY > oracleRate * 0.98`
   - If false, reject (pool is mispriced; redeemer would receive unfair value)

4. **Build Transaction**
   - **Inputs**: LP pool box, Redeem contract box (SELF)
   - **Data Inputs**: Oracle box (for rate validation)
   - **Outputs**:
     - Updated LP pool box (reduced reserves, reduced LP supply)
     - Updated Redeem box (unchanged state, preserved singleton)
     - User payment box (receives X and Y reserves)

5. **Fee Handling**
   