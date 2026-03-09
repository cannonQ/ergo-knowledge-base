---
title: kushti/dexy-stable — redeem.es
description: "ErgoScript contract analysis: contracts/lp/pool/redeem.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/redeem.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: LP Redeem (kushti/dexy-stable)

## Purpose

This contract validates LP (Liquidity Provider) token redemption transactions in a decentralized exchange pool. It ensures that when users burn LP tokens, they receive proportional amounts of the underlying reserve assets (X and Y tokens) while maintaining pool invariants and oracle-based price constraints.

## Inputs / Outputs

| Component | Role | Details |
|-----------|------|---------|
| **Input[0]** | LP Pool Box | Contains reserve tokens (X, Y) and circulating LP tokens; identified by State NFT at `tokens(0)` |
| **Data Input[0]** | Oracle Box | Provides current exchange rate between assets; identified by Oracle NFT in `tokens(0)` |
| **Output[0]** | Updated LP Pool Box | Reduced reserves after redemption; updated LP token quantity |
| **Output[1]** | Successor Redeem Box | This contract box itself, preserved for future redemptions |

**State NFT (Singleton):** The NFT in `lpBoxIn.tokens(0)` ensures only one authoritative LP pool box exists; its preservation in the successor enforces state continuity.

## Key Logic

The contract validates redemptions through four layered checks:

### 1. **Oracle Authentication**
```
validOracleBox = oracleBox.tokens(0)._1 == oracleNFT
```
Ensures the data input providing the price rate is the authentic oracle pool, not a malicious substitute.

### 2. **Price Sanity Check**
```
lpRateXyIn = reservesXIn / reservesYIn
validRateForRedeemingLp = lpRateXyIn > oracleRateXy * 98 / 100
```
Prevents redemptions when the LP pool's internal price ratio deviates >2% below the oracle rate (protects against manipulation or stale oracle data). The oracle delivers `nanoErgs per 1 kg gold`, normalized by dividing by 1,000,000 to get `nanoErgs per Dexy (1mg gold)`.

### 3. **Proportional Redemption**
```
deltaSupplyLp < 0  &&  deltaReservesX < 0  &&  deltaReservesY < 0
```
All deltas must be negative (LP tokens burned, reserves withdrawn). The mathematical invariant enforces fair redemption:
$$\frac{\Delta X}{X_{in}} \approx \frac{\Delta Y}{Y_{in}} \approx \frac{\Delta LP}{LP_{supply}}$$

With a 2% protocol fee factored in:
$$\Delta X \cdot LP_{supply} \cdot \frac{100}{98} \geq |\Delta LP| \cdot X_{in}$$

This ensures users receive at least their proportional share minus the 2% fee.

### 4. **Self-Preservation**
```
selfPreserved = successor.propositionBytes == SELF.propositionBytes  &&
                successor.value >= SELF.value              &&
                successor.tokens == SELF.tokens
```
The redeem contract's logic, minimum box value, and State NFT must be preserved in the successor output. This maintains the state machine invariant.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | Oracle box rate (nanoErgs per 1 kg gold); read via `oracleBox.R4[Long].get` |
| **R5–R9** | — | Not used in this contract |

Constants are injected at contract deployment via `$` syntax (`$initialLp`, `$oracleNFT`), not stored in registers.

## Tokens

| Token Position | Type | Purpose |
|---|---|---|
| **lpBoxIn.tokens(0)** | State NFT | Identifies the canonical LP pool box; enforces singleton pattern |
| **lpBoxIn.tokens(1)** | LP Token | Represents user share; quantity = circulating supply; burned on redemption |
| **lpBoxIn.tokens(2)** | Reserve Y Asset | One side of liquidity pair (e.g., Dexy or gold-backed token) |
| **lpBoxIn.value** | Ergs (Native Token) | Reserve X Asset (measured in nanoErgs); pool liquidity in base currency |
| **oracleBox.tokens(0)** | Oracle NFT | Authenticates the oracle data source |

**Circulating Supply Calculation:**
$$LP_{circulating} = initialLp - LP_{stored\ in\ box}$$
This accounts for initial token burning (similar to Uniswap V2 mechanism).

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Construct Redemption Transaction:**
   - Input: Select the LP pool box (identified by State NFT)
   - Data Input: Fetch the current oracle box
   - Outputs: 
     - New LP pool box with reduced reserves and fewer LP tokens
     - Successor redeem box with identical guard script and tokens
   
2. **Calculate Fair Redemption:**
   - Determine how many LP tokens the user burns (`deltaSupplyLp`)
   - Compute proportional withdrawals: `deltaX = (deltaSupplyLp / supplyLpIn) * reservesXIn * 0.98`
   - Apply 2% protocol fee
   
3. **Verify Pre-Conditions:**
   - Confirm `lpRateXyIn > oracleRateXy * 0.98` before submitting (off-chain optimization)
   - Ensure oracle box is recent (not stale; oracle management is external)
   
4. **Handle Outputs:**
   - Send withdrawn assets (X, Y) to user wallet
   - Preserve redeem box with Minimum box value (likely 1 Erg per 4 bytes or configured floor)

### Transaction Context

- **Atomic Execution:** Redemption and reserve transfer occur in a single transaction (eUTXO atomicity).
- **No Signature Requirement in Contract:** The redeem contract is **non-custodial**; it validates invariants only. User signatures authorize spending the withdrawn assets (enforced by output address, not shown here).

## Related Contracts

Based on the code structure