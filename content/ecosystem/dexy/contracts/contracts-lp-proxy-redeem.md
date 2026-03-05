---
title: kushti/dexy-stable — Redeem.es
description: "ErgoScript contract analysis: contracts/lp/proxy/Redeem.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/Redeem.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Redeem Proxy (kushti/dexy-stable)

## Purpose

This contract validates LP (Liquidity Provider) token redemptions from a CFMM (Constant Function Market Maker) n2t (native-to-token) pool on the Dexy protocol. It ensures users receive fair minimum returns of both reserve assets (ERG and a secondary token) after deducting a 2% redemption fee, while preventing excessive miner fees.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Pool box containing:
  - `tokens(0)`: PoolNFT (singleton state NFT for pool authentication)
  - `tokens(1)`: LP token with current supply state (`poolLP._2`)
  - `tokens(2)`: Reserve token Y (secondary asset)
  - `value`: Reserve X amount (ERG in nanoERG)
  
- **SELF**: Proxy box holding LP tokens to be redeemed
  - `tokens(0)`: LP token with redemption quantity (`selfLP._2`)
  - `value`: ERG locked for transaction fees

- **Implicit data/context inputs**: User signature (Pk)

### Outputs
- **OUTPUTS(0)**: Pool box (updated state post-redemption)
- **OUTPUTS(1)**: Action box (Dexy protocol-specific)
- **OUTPUTS(2)**: Return box to user containing:
  - `value`: Redeemed ERG (minReturnX)
  - `tokens(0)`: Redeemed token Y (minReturnY)
  - `propositionBytes`: Must match `Pk.propBytes` (user's public key)
  
- **Implicit**: Miner fee box(es) with `MinerPropBytes`

## Key Logic

### Core Validation Flow

1. **Transaction Structure Check**
   ```
   INPUTS.size >= 2  → Ensures pool box + proxy box present
   poolIn.tokens.size == 3 → Verifies pool has NFT, LP token, reserve token
   ```

2. **Pool Authentication**
   ```
   poolIn.tokens(0)._1 == PoolNFT → Validates pool's singleton state NFT
   ```

3. **Minimum Return Calculation (with 2% fee)**
   - **ERG return**: `(selfLP._2 / supplyLP) × reservesXAmount × 0.98`
   - **Token Y return**: `(selfLP._2 / supplyLP) × reservesY._2 × 0.98`
   - Where `supplyLP = InitiallyLockedLP - poolLP._2` (effective circulating supply, accounting for burned LP)

4. **Actual Return Verification**
   ```
   returnXAmount = returnOut.value - SELF.value + DexFee
   ```
   - Subtracts proxy's held ERG and adds back DexFee constant
   - Asserts: `returnXAmount >= minReturnX` and `returnY._2 >= minReturnY`

5. **Token Identity Matching**
   ```
   returnY._1 == reservesY._1 → Ensures correct token returned
   ```

6. **Return Destination Validation**
   ```
   returnOut.propositionBytes == Pk.propBytes → Enforces user receives their own address
   ```

7. **Fee Constraint**
   ```
   Total miner fees ≤ MaxMinerFee → Bounds transaction costs
   ```

### Authorization
```
Pk || validRedeem
```
- **OR** condition: Either user signs directly (Pk) **OR** all redeem validations pass
- Allows both manual withdrawal (Pk signature alone) and automated redemption (bot-executed via proxy validation)

## Registers Used

**No R4-R9 registers are explicitly read in this contract.**

- Uses only **standard box properties**: `tokens`, `value`, `propositionBytes`
- Constants (`PoolNFT`, `DexFee`, `MaxMinerFee`, `MinerPropBytes`, `Pk`) are **segregated as compile-time constants** (not stored in registers—part of ErgoTree)

## Tokens

### Native Tokens Referenced

| Token | Role | Type |
|-------|------|------|
| **PoolNFT** | Pool singleton state identifier | NFT (quantity = 1) |
| **LP token** | User's liquidity share; stored in `poolIn.tokens(1)` and `SELF.tokens(0)` | Native token; quantity = amount to redeem |
| **Reserve Token Y** | Secondary pool asset; in `poolIn.tokens(2)` | Native token; quantity tracks reserve balance |

### Token ID Rule Enforcement
- Token ID matching (`returnY._1 == reservesY._1`) ensures the correct reserve asset is returned
- PoolNFT validates pool authenticity via singleton pattern

## Integration Pattern

### Off-Chain Bot/Headless dApp Requirements

The off-chain system must:

1. **Construct Transaction**
   - Fetch pool box (INPUTS(0)) with current reserve state
   - Create proxy box (INPUTS(1)) holding user's LP tokens
   - Calculate minReturnX, minReturnY using the formula above
   - Create return box (OUTPUTS(2)) with validated amounts and user's public key
   - Estimate miner fees and ensure total ≤ MaxMinerFee

2. **Verify Pre-Conditions**
   - Confirm INPUTS(1) is SELF (the proxy box itself)
   - Read PoolNFT from constant segregation (compile-time)
   - Parse user's public key (Pk) for return destination

3. **Execute & Sign**
   - If using `Pk || validRedeem` branch:
     - Construct valid redeem transaction → contract validates automatically
     - Or: Sign with Pk directly → bypasses redeem validation
   - Broadcast signed transaction to mempool

4. **Context Extension** (if needed)
   - Pool NFT ID may be provided via Context extension if not hardcoded

### Integration with Spectrum CFMM
- Contract is adapted from **Spectrum protocol** (DEX aggregator)
- Dexy applies **2% redemption fee** (vs. Spectrum's original rate)
- Maintains