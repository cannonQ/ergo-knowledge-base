---
title: kushti/dexy-stable — main.es
description: "ErgoScript contract analysis: contracts/lp/pool/main.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/main.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Dexy Liquidity Pool

## Purpose

This contract manages a decentralized liquidity pool (LP) for the Dexy stablecoin protocol, serving as the core state machine that facilitates token swaps, LP token minting/redemption, and protocol interventions. Unlike ErgoDex, it modularizes actions into separate scripts and incorporates Dexy-specific features like a 2% redemption fee, oracle-gated redemption, and bank intervention mechanisms.

---

## Inputs / Outputs

### Inputs (Variable per Transaction Type)
- **Index 0**: The LP Box itself (SELF) – contains pool reserves and state
- **Index 1**: Action Box (Swap/Mint/Redeem) or Extract Box – triggers the specific pool operation
- **Index 2** (conditional): Intervention Box – for bank-driven rebalancing

### Data Inputs (Read-Only Context)
- **Oracle Box** (for Redeem/Extract/Release actions) – provides off-chain price feed
- **Bank Box** (for Extract actions) – coordinates with bank contract
- **Tracking Box** (for Extract/Release actions, 95%/101% modes) – tracks extraction state

### Outputs
- **Index 0**: The successor LP Box – mutated state with updated reserves, same script and NFTs
- Action Box outputs – handled by respective action scripts (swap.es, mint.es, redeem.es, etc.)

---

## Key Logic

### Invariant Preservation (Core Validation)

The contract enforces six critical invariants that all actions must satisfy:

1. **`preservedScript`**: Successor box must execute the same ErgoScript (no script mutation)
2. **`preservedLpNft`**: The LP NFT (Tokens(0)) remains identical – ensures box identity via Singleton pattern
3. **`preservedLpTokenId`**: LP token ID (Tokens(1)._1) never changes – prevents token substitution
4. **`preservedDexyTokenId`**: Dexy/Y token ID (Tokens(2)._1) never changes – ensures Y-reserve authenticity
5. **`noMoreTokens`**: Exactly 3 tokens remain (NFT + LP tokens + Y tokens) – prevents token smuggling
6. **`(lpAction || dexyAction)`**: Transaction must be one of 6 authorized action types

### Action Validation

**LP Actions** (mutate reserves, change LP supply):
- **Swap** (validSwap): Requires Swap action NFT at input index 1
- **Mint** (validMint): Requires Mint action NFT at input index 1
- **Redeem** (validRedeem): Requires Redeem action NFT at input index 1

**Dexy Actions** (protocol maintenance, no LP supply change):
- **Intervention** (validIntervention): Requires Intervention NFT, checked for token presence
- **Extraction** (validExtraction): Requires Extraction NFT for fund extraction to futures

Both dexy actions enforce `deltaSupplyLp == 0` to prevent LP token leakage during protocol operations.

### LP Supply Tracking

```
deltaSupplyLp = lpReservesIn._2 - lpReservesOut._2
```

Calculates net LP token movement by inverting the reserve pool logic:
- Positive delta = LP tokens burned (redemption)
- Negative delta = LP tokens minted (liquidity provision)
- Zero delta = No LP circulation change (dexy actions)

---

## Registers Used

**No R4-R9 registers are directly read/written in this contract.**

The contract relies entirely on:
- **Token metadata** (Tokens array) for state representation
- **Box value (NanoErgs)** – implicitly carries X-reserve quantity
- **Proposition bytes** – for script immutability verification

*Note: Action scripts (swap.es, mint.es, redeem.es, etc.) likely use registers for price parameters, fees, and swap coefficients.*

---

## Tokens

### Token Structure (3-token invariant)

| Index | Role | Type | Purpose |
|-------|------|------|---------|
| **0** | LP NFT | Native Token (singleton) | **Unique box identifier** – enables deterministic data input selection and prevents double-spending via NFT uniqueness rule |
| **1** | LP Tokens | Native Token (supply-tracked) | **Liquidity provider shares** – amount tracks circulating LP supply; reserves held in pool for redemption |
| **2** | Y Tokens (Dexy) | Native Token (reserves) | **Collateral/stablecoin reserves** – for SigmaUSD/Dexy, this is USD token; quantity = Y-reserve |

### Token ID Rules (Sigma Protocol Constraint)

- **LP NFT** must be **preserved exactly** across all transactions (prevents unauthorized pool swaps)
- **LP Token ID** and **Y Token ID** are immutable by script – ensures fungibility and prevents substitution attacks
- **No token repetition** allowed – `noMoreTokens == 3` prevents double-counting reserves

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Requirements

The off-chain coordinator must construct transactions respecting these constraints:

#### For **Swap** Actions:
1. Locate the LP Box (identified by LP NFT)
2. Create a **Swap Action Box** with `lpSwapNFT` token
3. Construct transaction: `[LP, Swap] → [LP']`
4. Calculate new reserves post-swap and verify `preservedLpTokenId` in output
5. Ensure X and Y reserves are updated per AMM formula (handled by swap.es)

#### For **Mint** Actions:
1. Create Mint Action Box with `lpMintNFT`
2. Construct transaction: `[LP, Mint] → [LP']`
3. Calculate LP tokens minted (negative `deltaSupplyLp`)
4. Verify successor box holds fewer LP tokens in reserve

#### For **Redeem** Actions:
1. Create Redeem Action Box with `lpRedeemNFT`
2. **Provide Oracle as data input** for price validation
3. Construct transaction: `[LP, Redeem] → [LP']`
4. Enforce: **redemption only valid if** `lpPrice >= 0.98 *