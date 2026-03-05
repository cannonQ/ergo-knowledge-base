---
title: kushti/dexy-stable — swap.es
description: "ErgoScript contract analysis: contracts/lp/pool/swap.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/swap.es
project: kushti-dexy-stable
---
# ErgoScript Analysis: `contracts/lp/pool/swap.es`

## Purpose

This contract validates AMM (Automated Market Maker) liquidity pool swaps in the Dexy stable ecosystem. It enforces that token exchanges occur at a fair rate after fee deduction, and that the swap box (Swap box) maintains its identity and value through the transaction.

## Inputs / Outputs

| Component | Description |
|-----------|-------------|
| **Input Box 0** | LP Pool box containing reserves (X and Y token balances) and LP supply token |
| **Input Box (SELF)** | Swap box (authenticated by NFT in Token(0)) |
| **Output Box 0** | Updated LP Pool box with modified reserves post-swap |
| **Output Box 1** | Successor Swap box (must equal input Swap box) |

## Key Logic

### Core Invariant: Constant Product Formula with Fees

The contract enforces the generalized constant product invariant:

**For selling X, buying Y:**
```
reservesY_in × ΔreservesX × feeNum ≥ 
  -ΔreservesY × (reservesX_in × feeDenom + ΔreservesX × feeNum)
```

**For selling Y, buying X:**
```
reservesX_in × ΔreservesY × feeNum ≥ 
  -ΔreservesX × (reservesY_in × feeDenom + ΔreservesY × feeNum)
```

### Validation Conditions

1. **No LP Supply Change**: `deltaSupplyLp == 0` — swap must not mint/burn LP tokens
2. **Fair Exchange Rate**: Directional constant product formula ensures:
   - Fee is applied to the sold amount: `actualSold = sold × (1 - feeNum/feeDenom)`
   - Buyer receives at least: `actualSold × rate` where `rate = reservesY / reservesX`
3. **Swap Box Preservation**: Successor box must:
   - Execute the same ErgoScript (same `propositionBytes`)
   - Maintain minimum value (`successor.value ≥ SELF.value`)
   - Preserve all tokens (NFT identity + any additional tokens)

## Registers Used

| Register | Type | Usage |
|----------|------|-------|
| **$feeNumLp** | Long (Constant) | Numerator of fee fraction (e.g., 3 for 0.3%) |
| **$feeDenomLp** | Long (Constant) | Denominator of fee fraction (e.g., 1000 for 0.3%) |

Both are **context extension constants** injected by off-chain code at transaction construction time.

## Tokens

| Token Slot | Purpose |
|------------|---------|
| **Tokens(0) in SELF** | **Swap Box NFT** — singleton identifier, proves this is *the* authorized swap contract instance |
| **Tokens(1) in LP Box** | **LP Token ID** — represents LP share; amount tracked as `lpReservesIn._2` (quantity) |
| **Tokens(2) in LP Box** | **Reserve Token Y** — the non-Erg asset in the pool (e.g., Dexy stablecoin); amount is `._2` component |
| **NanoErg (box.value)** | **Reserve X** — Erg reserves; primary pool asset |

The **Token ID rule** ensures LP tokens and reserve tokens are immutable identifiers.

## Integration Pattern

### Off-Chain (Bot/dApp) Construction

1. **Read LP state** from input LP Box (register scan + token balances)
2. **Compute swap parameters**:
   - Determine `deltaReservesX` (user input amount)
   - Calculate minimum acceptable `deltaReservesY` using constant product formula
3. **Construct transaction**:
   - Input 0: Current LP box (UTXO lookup by NFT)
   - Input 1: Current Swap box (UTXO lookup by Swap NFT)
   - Output 0: New LP box with updated reserves
   - Output 1: New Swap box (copy of input, preserves value/tokens)
   - Context extensions: `$feeNumLp`, `$feeDenomLp`
4. **Invoke proof of work**: Sign with private key; Sigma protocol verifies `sigmaProp(validSwap && selfPreserved)`

### Verification

Contract verifies:
- Reserve arithmetic matches constant product formula
- LP supply unchanged (no mint/burn)
- Swap box identity & value preserved
- Fee applied correctly to sold amount

## Related Contracts

Based on naming convention and structure:

| Related Contract | Likely Purpose |
|------------------|----------------|
| **LP Pool Contract** | Input Box 0; manages reserves, minting/burning, composition with swap |
| **Dexy Protocol** | Likely consumer of swaps; Y-token may be stablecoin |
| **Liquidity Provision (Mint/Burn)** | Separate contract handling LP token issuance; this contract assumes fixed supply |
| **Multi-Stage Composition** | This is a **stateless validator**; paired with stateful LP box for multi-stage execution |

---

## Key Design Insights

- **Fee Model**: Deducted from input amount (slippage-aware); uses fraction to avoid precision loss
- **State Machine Pattern**: Swap box acts as a **singleton** (NFT-authenticated); LP box is the actual state holder
- **eUTXO Composability**: Two-box input model (LP + Swap) allows atomic, trustless DEX swaps
- **Headless dApp Compatible**: Off-chain bot can construct valid swaps without private keys (except final signing)
- **Storage Rent Neutral**: Swap box value preserved ensures sustainable operation across blocks