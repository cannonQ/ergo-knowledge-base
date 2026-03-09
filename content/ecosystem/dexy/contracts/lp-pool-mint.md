---
title: kushti/dexy-stable — mint.es
description: "ErgoScript contract analysis: contracts/lp/pool/mint.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/mint.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: LP Mint (kushti/dexy-stable)

## Purpose

This contract validates **LP token minting** (liquidity provider deposit) transactions in a Uniswap v2-style automated market maker (AMM) pool. It ensures that when users deposit paired assets (X and Y tokens) into the liquidity pool, they receive a proportional amount of LP tokens without violating the constant product invariant.

## Inputs / Outputs

| Direction | Box | Purpose |
|-----------|-----|---------|
| **Input** | `INPUTS(0)` = `lpBoxIn` | The Pool Box holding current reserve balances and LP token supply |
| **Input** | `INPUTS(1+)` | User deposit box (implicit; contains X and Y tokens to deposit) |
| **Output** | `OUTPUTS(0)` = `lpBoxOut` | Updated Pool Box with new reserves and reduced LP token supply |
| **Output** | `OUTPUTS(1)` = `successor` | This mint contract box (preserved for future deposits) |

**Token Flows:**
- Pool box tokens: NFT (idx 0), LP reserve tokens (idx 1), Y-reserve tokens (idx 2)
- User supplies: X tokens (as ergs/nanoERG) and Y tokens (native tokens)

## Key Logic

### Reserve Tracking
```
supplyLpIn = initialLp - lpReservesIn._2
```
LP token supply is inverted: total supply minus tokens held in reserves equals circulating supply.

### Mint Validation (`validMintLp`)
**All conditions must hold:**

1. **Non-negative deposit:** `deltaSupplyLp > 0 && deltaReservesX > 0 && deltaReservesY > 0`
   - Liquidity must increase in both assets
   - LP token supply must decrease (tokens burned from reserves)

2. **Constant Product Invariant (Uniswap v2):**
   ```
   sharesUnlocked = min(
       deltaReservesX * supplyLpIn / reservesXIn,
       deltaReservesY * supplyLpIn / reservesYIn
   )
   deltaSupplyLp ≤ sharesUnlocked
   ```
   - User deposits `deltaReservesX` and `deltaReservesY`
   - Proportional LP shares unlocked is the **minimum** of the two ratios
   - Minted shares cannot exceed the unlocked amount (prevents arbitrage)

### Contract Preservation (`selfPreserved`)
The successor box must:
- Retain identical **ErgoTree** (same proposition bytes)
- Maintain **minimum box value** at least equal to current value
- Preserve all **native tokens** (no token theft)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| `$initialLp` | Long | **Constant**: Total LP token supply (set at pool bootstrap) |
| `R0`–`R3` | Implicit | Standard box fields (value, tokens, scriptBytes, guarded box ID) |
| `R4`–`R9` | *Not used* | Available for future state extensions |

The contract uses **constant segregation** via `$initialLp` placeholder, allowing the ErgoScript to be compiled once with pool-specific initialization data injected at deployment.

## Tokens

| Position | Type | Purpose |
|----------|------|---------|
| `tokens(0)` | **State NFT** | Uniquely identifies this pool box; enforces singleton pattern |
| `tokens(1)` | **LP Token** | Represents LP share ownership; amount tracks circulating supply |
| `tokens(2)` | **Y-Reserve Token** | Second asset in the pair (X is nERG/erg value) |

**Token ID Rule Invariant:**
- Pool box's NFT must match across all transactions (enforced by `successor.tokens == SELF.tokens`)
- This prevents switching to a different pool contract

## Integration Pattern

### Off-Chain Bot / Headless dApp Construction

1. **Read Pool State:**
   - Fetch Pool box (UTXO with matching NFT)
   - Extract `reservesXIn`, `reservesYIn`, `supplyLpIn` from box value and tokens

2. **User Input:**
   - User specifies deposit amount for one asset (e.g., X)
   - Compute required paired deposit using: `deltaY = deltaX * reservesYIn / reservesXIn`
   - Calculate LP shares unlocked: `min(deltaX * supplyLpIn / reservesXIn, deltaY * supplyLpIn / reservesYIn)`

3. **Construct Transaction:**
   - **Input 0:** Pool box (with LP mint contract)
   - **Input 1+:** User's deposit box containing X (ergs) and Y tokens
   - **Output 0:** New Pool box with:
     - `value = reservesXIn + deltaX`
     - `tokens(1) = (lpTokenId, lpReservesIn - lpSharesMinted)` ← LP tokens burned
     - `tokens(2) = (yTokenId, reservesYIn + deltaY)`
   - **Output 1:** Successor mint contract (unchanged)
   - **Outputs 2+:** User receives LP tokens in separate box

4. **Verify:**
   - Ensure `deltaSupplyLp = lpReservesIn - lpReservesOut > 0`
   - Check `validMintLp` condition locally before signing
   - Verify successor contract ErgoTree matches (constant segregation)

### Minimum Transaction Fee & Storage Rent
- Pool box must maintain **minimum box value** (≥ 1,000,000 nanoERG on mainnet)
- Off-chain code must account for **storage rent**: pool box value may decrease over time if not touched; redeposits may fail if reserves fall below minimum

## Related Contracts

**Multi-stage State Machine (implied):**
- **Pool Contracts (interconnected):**
  - `mint.es` (this file) — LP deposit logic
  - `swap.es` — Token swap validation (uses same pool box)
  - `burn.es` — LP withdrawal logic (reverse of mint)
  - Pool initialization contract — Bootstrap with `$initialLp` constant

**Integration Points