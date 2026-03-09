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
project: dexy-use
---
# ErgoScript Contract Analysis: LP Mint Subcontract

## Purpose

This contract validates **LP token minting** (deposit liquidity) transactions in a Uniswap V2–style automated market maker (AMM). It ensures that when a user deposits reserve assets (X and Y tokens) into a liquidity pool, the number of LP tokens minted respects the constant product formula and pool invariants.

## Inputs / Outputs

### Inputs
- **INPUTS(0)** – LP Pool Box: Contains the liquidity pool state, including:
  - Native ERG value (`reservesXIn`)
  - Token(1): LP token reserves (remaining unminted LP tokens)
  - Token(2): Y-reserve asset and its quantity
  
- **INPUTS(1+)** – User deposit box(es): Supplies additional X and Y reserves (not directly validated in this contract; handled by transaction context)

### Outputs
- **OUTPUTS(0)** – Updated LP Pool Box: Reflects new reserve levels after deposit
  - Updated ERG value (`reservesXOut`)
  - Reduced LP token reserves (tokens minted are removed from this pool)
  - Updated Y-reserve quantity
  
- **OUTPUTS(1)** – Successor box (self-preservation check): The mint contract's continuation or guardian box that must preserve this contract's logic

---

## Key Logic

1. **Reserve Delta Calculation**
   - `deltaSupplyLp`: LP tokens minted (decrease in reserve pool)
   - `deltaReservesX`, `deltaReservesY`: Increases in X and Y reserves from user deposit

2. **Uniswap V2 Mint Formula Validation** (`validMintLp`)
   - ✅ All deltas must be positive (non-zero deposits)
   - ✅ LP tokens minted must not exceed the **"shares unlocked"** computed as:
     ```
     sharesUnlocked = min(
         deltaReservesX × supplyLpIn / reservesXIn,
         deltaReservesY × supplyLpIn / reservesYIn
     )
     ```
     This ensures minting is proportional to the smaller deposit relative to current reserves, preventing arbitrage through imbalanced deposits.

3. **Self-Preservation** (`selfPreserved`)
   - The successor box (OUTPUTS(1)) must have **identical** ErgoScript code (`propositionBytes`)
   - Successor's ERG value must be ≥ current box value (covers storage rent)
   - Successor's tokens must be identical (preserves NFT singleton and guards)

4. **Atomic Validation**
   - Both conditions must hold: `sigmaProp(validMintLp && selfPreserved)`

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `BigInt` (`$initialLp`) | **Pool initialization constant**: Total LP token supply issued at genesis. Used to compute unminted reserves as `initialLp - lpReserves._2`. This constant is **segregated** (hardcoded at deployment). |
| **R5–R9** | — | *Not used in this contract* |

> **Note:** The `$initialLp` syntax indicates **constant segregation** – this value is baked into the compiled ErgoTree and cannot be modified.

---

## Tokens

| Token Slot | Role | Purpose |
|------------|------|---------|
| **Token(0)** | **NFT (Singleton)** | Uniquely identifies and locks this LP Pool box. Only one such NFT exists; it authenticates the pool. |
| **Token(1)** | **LP Token Reserves** | Represents unminted LP tokens. Quantity decreases as users deposit; `initialLp - token(1)._2 = circulating supply`. |
| **Token(2)** | **Y-Reserve Asset** | The second reserve asset (e.g., USDT, SigmaUSD). Paired with ERG (X-reserve). Quantity increases on deposit. |

---

## Integration Pattern

### Off-Chain Bot / DApp Responsibilities

1. **Construct Transaction**
   - Input the current LP Pool box (INPUTS(0))
   - Input user's deposit box with X (ERG) and Y (token) amounts
   - Output a new LP Pool box with:
     - Updated ERG balance: `reservesXOut = reservesXIn + depositX`
     - Updated Y-reserve: `reservesYOut = reservesYIn + depositY`
     - Reduced LP reserves: `lpReservesOut = lpReservesIn - lpTokensMinted`
   - Output a successor box (OUTPUTS(1)) replicating this contract

2. **Pre-Validation**
   - Compute `supplyLpIn = initialLp - lpReservesIn._2`
   - Calculate `sharesUnlocked` using the formula
   - Verify off-chain that proposed `deltaSupplyLp ≤ sharesUnlocked`
   - Ensure slippage tolerance is respected (if applicable)

3. **User Experience**
   - Send minted LP tokens to user's wallet (typically in a separate output or via a user-defined script)
   - The contract itself does **not** directly allocate tokens to users; that's handled upstream

---

## Related Contracts

Based on the file path `contracts/lp/pool/mint.es` in the **kushti/dexy-stable** project:

- **`swap.es`** (inferred): Validates token swaps (X ↔ Y) while maintaining the constant product formula `reservesX × reservesY = k`
- **`redeem.es`** or **burn.es** (inferred): Inverse operation—burns LP tokens to withdraw reserves
- **`pool.es`** or **pool-init.es`** (inferred): Initializes the LP pool with bootstrap liquidity and sets `initialLp`
- **`fee-pool.es`** (inferred): Collects and distributes protocol fees from swaps
- **`price-feed.es`** or oracle contract (inferred): May provide reserve snapshots for off-chain validation

> **Integration Model**: This is a **multi-stage contract** where the LP Pool box transitions through states (mint → swap → burn) via atomic eUTXO transactions, enforcing the U