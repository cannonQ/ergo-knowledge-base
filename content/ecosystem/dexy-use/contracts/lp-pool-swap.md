---
title: kushti/dexy-stable — swap.es
description: "ErgoScript contract analysis: contracts/lp/pool/swap.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/swap.es
project: dexy-use
---
# ErgoScript Contract Analysis: Dexy Stable LP Swap

## Purpose

This contract validates liquidity pool (LP) token swaps in the Dexy stable protocol. It ensures that users receive fair market rates when exchanging one token for another through an LP, with a configurable fee mechanism applied to the sold amount. The contract enforces constant-product AMM (automated market maker) invariants while preserving the LP box singleton state.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: LP Box — the liquidity pool UTXO holding reserves of both token pairs and LP tokens
- **INPUTS(1+)**: User's input boxes (implicitly; not directly referenced in validation logic)

### Outputs
- **OUTPUTS(0)**: Updated LP Box — the same LP pool after reserve adjustments from the swap
- **OUTPUTS(1)**: Swap Box (SELF) — successor to the current swap contract box, preserving state and value
- **OUTPUTS(2+)**: User's change/output boxes (constructed off-chain)

---

## Key Logic

### Swap Validation Conditions

The contract enforces three core invariants:

1. **LP Supply Preservation**
   ```
   deltaSupplyLp == 0
   ```
   The total LP token supply must not change during a swap (only swaps allowed, not liquidity adds/removes).

2. **Fee Deduction Before Pricing**
   - User deposits amount `sold` of one token
   - Actual amount used for rate calculation: `actualSold = sold * (1 - feeNum/feeDenom)`
   - Fee is `sold * (feeNum/feeDenom)`, retained by LP
   - The received amount is calculated from `actualSold`, not `sold`

3. **Constant-Product Invariant (Fee-Adjusted)**
   
   The contract splits into two branches based on swap direction:

   **If selling Token X (deltaReservesX > 0):**
   ```
   reservesY_in * deltaX * feeNum >= -deltaY * (reservesX_in * feeDenom + deltaX * feeNum)
   ```
   
   **If selling Token Y (deltaReservesX ≤ 0):**
   ```
   reservesX_in * deltaY * feeNum >= -deltaX * (reservesY_in * feeDenom + deltaY * feeNum)
   ```

   These inequalities encode:
   ```
   reservesX_out * reservesY_out >= reservesX_in * reservesY_in * (1 - fee)²
   ```
   (adjusted for fee application on input side only)

4. **Swap Box Continuity**
   - Successor box must have identical ErgoScript proposition bytes (contract code unchanged)
   - Successor must retain ≥ same value (NanoErgs) — prevents loss of minimum box value
   - Successor must hold identical tokens (preserves singleton NFT identity)

---

## Registers Used

**None explicitly.** All parameters are compile-time constants:
- `$feeNumLp` — numerator of fee fraction (e.g., `3`)
- `$feeDenomLp` — denominator of fee fraction (e.g., `1000`)

These are **constant-segregated** values injected by the off-chain code at contract deployment, allowing fee tuning without re-deploying the contract tree.

---

## Tokens

### Token Structure in LP Box

| Index | Token | Purpose |
|-------|-------|---------|
| **0** | NFT (singleton) | Uniquely identifies the LP pool; ensures only one active instance |
| **1** | LP Token (fungible) | Represents LP ownership; amount tracked in registers to compute supply |
| **2** | Reserve Token Y (fungible) | One side of the trading pair (e.g., Dexy stablecoin) |

**Reserve Token X** is represented as the box's **native NanoErg value** (`value` field).

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Construct Swap Transaction**
   - Fetch LP box from UTXO set (identified by singleton NFT token ID)
   - Read `lpBoxIn.value` (reservesX) and `lpBoxIn.tokens(2)._2` (reservesY)
   - Calculate swap output using constant-product formula with fee
   - Construct outputs:
     - **OUTPUTS(0)**: updated LP box with new reserves
     - **OUTPUTS(1)**: successor swap box (copy of SELF with identical ErgoTree)
     - **OUTPUTS(2+)**: user's output tokens + change

2. **Fee Calculation**
   - `actualSold = sold * (feeDenom - feeNum) / feeDenom`
   - `received = actualSold * reservesYIn / reservesXIn` (approximately)
   - Verify slippage tolerance client-side before signing

3. **Transaction Verification**
   - Ensure LP pool UTXO is spent (INPUTS(0) references the LP singleton)
   - Verify successor box is created with identical tokens and `value >= SELF.value`
   - Validate proposition bytes match: `SELF.propositionBytes` (prevents contract upgrade attacks)

4. **Atomic Swap Guarantee**
   - Transaction atomicity ensures either both LP and swap box update, or neither
   - Prevents partial execution; user cannot be charged fee without receiving tokens

---

## Related Contracts

### Composition Pattern (Inferred)

This swap contract is part of a **multi-stage state machine** alongside:

1. **LP Pool Contract** (`lpBoxOut` validates as peer)
   - Holds reserves and LP token supply
   - Must accept swaps that satisfy constant-product invariant
   - Likely validates incoming reserve deltas match outgoing user tokens

2. **Liquidity Add/Remove Contracts** (not shown here)
   - Handle minting/burning of LP tokens
   - Protected by `deltaSupplyLp == 0` invariant (rejected in this swap contract)

3. **Dexy Stablecoin Contract** (implied by token references)
   - The "Dexy" token (reserve token Y in many pools)
   - Participates in AMM pricing; likely has its own minting/collateral contracts