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
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Dexy Stable LP Swap

## Purpose

This contract validates liquidity pool (LP) swaps in the Dexy stable coin protocol. It enforces the constant product market maker (CPMM) formula with a configurable fee mechanism, ensuring that trades maintain the LP's invariant while collecting a protocol fee from the input token amount.

## Inputs / Outputs

**Inputs:**
- `INPUTS(0)`: The **LP Pool Box** — holds reserves in two tokens (X and Y) and tracks outstanding LP tokens
- `INPUTS(1+)`: User's input box(es) containing tokens to swap
- `SELF`: The swap box itself (this contract instance), passed through the transaction

**Outputs:**
- `OUTPUTS(0)`: The **updated LP Pool Box** — reflects new reserves after the swap
- `OUTPUTS(1)`: The **successor swap box** — preserves this contract's state and validates its continuation

## Key Logic

The contract enforces **fee-inclusive constant product invariant**:

1. **Fee Deduction**: If user sells amount `s`, only `s × (1 − feeNum/feeDenom)` is used in the rate calculation; the remainder is the protocol fee.

2. **Invariant Validation**: The core condition depends on which reserve is increasing:
   - **If selling X (buying Y):**  
     `reservesYIn × deltaReservesX × feeNum ≥ −deltaReservesY × (reservesXIn × feeDenom + deltaReservesX × feeNum)`
   
   - **If selling Y (buying X):**  
     `reservesXIn × deltaReservesY × feeNum ≥ −deltaReservesX × (reservesYIn × feeDenom + deltaReservesY × feeNum)`

3. **No LP Issuance/Burning**: `deltaSupplyLp == 0` ensures this swap does not interact with LP token minting (pure exchange, not liquidity provision/withdrawal).

4. **Box Preservation**: The successor swap box must:
   - Have the same ErgoScript code (`propositionBytes`)
   - Retain at least the original value (nanoErgs)
   - Preserve the same tokens (State NFT + tokens)

## Registers Used

**No explicit R4–R9 usage** in this contract. All parameters are **constant-segregated**:
- `$feeNumLp`: fee numerator (Const[Long])
- `$feeDenomLp`: fee denominator (Const[Long])

These are embedded at compile time to ensure the fee structure is immutable and cannot be altered by off-chain code.

## Tokens

**LP Pool Box Tokens:**
- `tokens(0)`: **State NFT** — uniquely identifies the LP pool box across transactions
- `tokens(1)`: **LP Token** — tracks outstanding LP supply via amount; spent tokens represent circulating LP
- `tokens(2)`: **Reserve Token Y** — the non-Erg token in the pool; amount represents reserve balance

**Swap Box Tokens:**
- `tokens(0)`: **State NFT** — identifies this swap box to prevent double-spending and ensure singleton behavior

## Integration Pattern

**Off-chain Bot / dApp Construction:**

1. **Read Current State**: Query the UTXO set for:
   - LP pool box (identified by its State NFT)
   - Swap box (identified by its State NFT)

2. **Calculate Swap Output**: Given user input amount and current reserves, compute:
   ```
   actualSold = sold × (1 − feeNum / feeDenom)
   deltaBought = actualSold × (reservesYIn / reservesXIn)
   ```

3. **Build Transaction**:
   - Input: LP pool box + swap box + user funding box
   - Output: Updated LP pool box + successor swap box (with updated reserves) + user output box
   - The off-chain code calculates `reservesXOut` and `reservesYOut`; the contract validates the invariant

4. **Constraint Verification**: Off-chain code must ensure:
   - `deltaSupplyLp == 0` (no LP minting)
   - Invariant inequality holds (contract re-checks in validation)
   - User receives at least slippage-adjusted minimum output
   - Minimum box value (1 Erg) is preserved

## Related Contracts

**Likely Composition:**
- **LP Deposit/Withdrawal Contracts** (`contracts/lp/pool/deposit.es`, `withdraw.es`) — interact with the same LP pool box; coordinate on State NFT and reserve tokens
- **Pool Registry / Factory** — manages creation of new pool instances with unique State NFTs
- **Dexy Oracle / Pricing Module** — may feed off-chain pricing data for slippage calculations (not directly called, but context for off-chain logic)
- **Token Bridge / Emission** — coordinates on native token issuance if Y is a Dexy-issued token

---

## Technical Notes

- **Multi-stage pattern**: This contract enforces invariants on a **State Machine** where the LP pool box and swap box are co-singletons, ensuring atomic state transitions.
- **Constant Product Variant**: The fee is applied to the input amount *before* pricing, not after, which is the **standard Uniswap V2 pattern**.
- **Sigma Protocol**: Validation occurs in-protocol via ErgoTree evaluation; no explicit ring signatures or multi-sig, but the State NFT mechanism provides singleton enforcement.