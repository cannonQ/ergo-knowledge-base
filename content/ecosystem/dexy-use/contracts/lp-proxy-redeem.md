---
title: kushti/dexy-stable — Redeem.es
description: "ErgoScript contract analysis: contracts/lp/proxy/Redeem.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/Redeem.es
project: dexy-use
---
# ErgoScript Contract Analysis: Redeem Proxy (kushti/dexy-stable)

## Purpose

This contract validates LP (liquidity provider) token redemptions from a CFMM (Constant Function Market Maker) n2t pool with a 2% redemption fee. It ensures users receive fair minimum returns of both reserve assets (ERG and custom tokens) when burning their LP tokens, while protecting against excessive miner fees.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Pool box — contains the Pool NFT (State NFT), LP tokens, and reserve token Y
- **INPUTS(1+)**: User's LP tokens (SELF) — the box being spent, holding LP tokens to redeem
- **Data inputs** (optional): None explicitly required

### Outputs
- **OUTPUTS(0)**: Updated Pool box (implied, part of multi-stage contract)
- **OUTPUTS(1)**: Action/state box (reserved in Dexy)
- **OUTPUTS(2)**: Return box — receives redeemed ERG and reserve token Y, locked to user's public key (`Pk`)
- **OUTPUTS(3+)**: Miner fee box (variable)

---

## Key Logic

The contract validates a redemption transaction through these conditions:

1. **Structural Requirements**:
   - At least 2 inputs present (`INPUTS.size >= 2`)
   - Pool input has exactly 3 tokens: [Pool NFT, LP tokens, Reserve token Y]

2. **LP Supply & Fair Pricing**:
   - Calculates total LP supply: `InitiallyLockedLP - poolLP._2`
   - Each reserve return is proportional: `(LP_burned / LP_supply) × reserve_amount`

3. **Minimum Return Enforcement** (with 2% fee):
   - Minimum ERG (X): `(selfLP_amount / supplyLP) × reservesXAmount × 0.98`
   - Minimum token Y: `(selfLP_amount / supplyLP) × reservesY × 0.98`
   - Actual returns must **exceed or equal** minimums to prevent slippage abuse

4. **Output Validation**:
   - Return box locked to `Pk.propBytes` (user's public key)
   - Returned token ID matches pool's reserve token Y
   - ERG amount: `returnOut.value - SELF.value + DexFee` ≥ `minReturnX`
   - Token amount: `returnY._2` ≥ `minReturnY`

5. **Miner Fee Cap**:
   - Sum of all outputs with `MinerPropBytes` ≤ `MaxMinerFee`
   - Prevents griefing via excessive transaction fees

6. **Authentication**:
   - Either signed by `Pk` (direct unlock) **OR** `validRedeem` (contract-validated redemption)
   - Uses `sigmaProp(Pk || validRedeem)` for OR-gate logic

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | (Not used) | — |
| **R5** | (Not used) | — |
| **R6** | (Not used) | — |
| **R7** | (Not used) | — |
| **R8** | (Not used) | — |
| **R9** | (Not used) | — |

**Note**: This contract uses only constant-segregated values (no box-level registers). All state is encoded in box structure and token amounts.

---

## Tokens

### Pool NFT
- **Role**: Singleton / State NFT identifying the unique pool instance
- **Matched as**: `poolIn.tokens(0)._1 == PoolNFT`
- **Purpose**: Ensures transactions reference the correct pool (prevents pool confusion attacks)

### LP Tokens
- **Location**: `SELF.tokens(0)` in the input being redeemed
- **Amount**: `selfLP._2` — quantity burned
- **Role**: Track user's liquidity share; burned during redemption

### Reserve Token Y
- **Location**: `poolIn.tokens(2)` (pool) → `returnOut.tokens(0)` (user output)
- **Amount**: Calculated based on `selfLP._2 / supplyLP`
- **Validation**: Token ID must match (`returnY._1 == reservesY._1`)

### DexFee & MaxMinerFee
- **DexFee**: Likely a constant or context parameter representing the 2% redemption fee
- **MaxMinerFee**: Protocol-enforced upper bound on transaction costs

---

## Integration Pattern

### Off-Chain Bot / dApp Responsibilities

1. **Build the Redemption Transaction**:
   - Input: User's LP token box + Pool state box (data input or INPUTS(0))
   - Output: Return box with calculated minimums

2. **Calculate Fair Minimums** (client-side):
   ```
   minReturnX = (lp_amount / total_supply) × erg_reserves × 0.98
   minReturnY = (lp_amount / total_supply) × token_reserves × 0.98
   ```
   - Apply user's slippage tolerance (off-chain; contract enforces minimums)

3. **Construct Return Box**:
   - Value: `minReturnX` (ERG)
   - Tokens: `[(tokenY_id, minReturnY)]`
   - Locked to: `Pk.propBytes` (user's public key)

4. **Sign Transaction**:
   - If using contract validation: construct inputs/outputs satisfying all conditions
   - Alternative: user signs with `Pk` for direct unlock (simplest path)

5. **Broadcast & Fee Management**:
   - Ensure total miner fees ≤ `MaxMinerFee`
   - Include miner box in outputs with `MinerPropBytes`

---

## Related Contracts

Based on references and pattern:

- **Pool Contract** (`contracts/lp/pool/Pool.es` implied): 
  - The CFMM n2t pool being redeemed from
  - Holds Pool NFT, LP tokens, reserve Y
  - Validates incoming redemption swaps

- **Action/