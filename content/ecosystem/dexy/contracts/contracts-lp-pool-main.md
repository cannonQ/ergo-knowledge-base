---
title: kushti/dexy-stable — main.es
description: "ErgoScript contract analysis: contracts/lp/pool/main.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/main.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Dexy Liquidity Pool Main Contract

## Purpose

This contract manages the core Liquidity Pool (LP) box for the Dexy stablecoin protocol. It acts as a state machine that validates all transactions affecting the pool's reserves (NanoErgs and Dexy tokens) and LP token supply, while delegating specific action logic (swaps, mints, redeems, interventions, extractions) to separate action scripts via the eUTXO composition pattern.

## Inputs / Outputs

### Inputs
- **Input 0 (SELF)**: The LP box itself—contains:
  - **Tokens(0)**: LP NFT (singleton identifier)
  - **Tokens(1)**: LP reserve tokens (fungible, quantity tracks unminted LP supply)
  - **Tokens(2)**: Dexy token reserves (Y token, counterpart to NanoErg reserves in value field)
- **Input 1** (lpActionBoxIndex): Action box—one of:
  - Swap box (has `lpSwapNFT`)
  - Mint box (has `lpMintNFT`)
  - Redeem box (has `lpRedeemNFT`)
- **Input 2** (interventionBoxIndex, conditional): Intervention box (has `interventionNFT`)
- **Extract box** (conditional, indexed as extractBoxIndex): Extraction box (has `extractionNFT`)

### Data Inputs (read-only)
- **Oracle box**: Consulted during Redeem and Extract-to-Future actions (via Data-Input)
- **Bank box**: Consulted during Extract-to-Future (via Data-Input)
- **Tracking box**: Consulted during Extract and Release-Extracted actions (via Data-Input)

### Outputs
- **Output 0** (selfOutIndex): Updated LP box—must be an identical copy of SELF with:
  - Same script (propositionBytes)
  - Same LP NFT
  - Same LP token ID
  - Same Dexy token ID
  - Modified token quantities (reserves adjusted by the action)
  - Exactly 3 tokens (no dust or unrelated assets)

## Key Logic

### Invariants (All transactions must satisfy)
1. **Script Immutability**: `successor.propositionBytes == SELF.propositionBytes`
   - Ensures the LP box's validation logic cannot be replaced.

2. **NFT Preservation**: `lpNftIn == lpNftOut`
   - The singleton NFT identifying this LP box cannot be removed or duplicated.

3. **Token ID Preservation**: 
   - LP token ID: `lpReservesOut._1 == lpReservesIn._1`
   - Dexy token ID: `tokenYOut._1 == tokenYIn._1`
   - Token types cannot be swapped or replaced.

4. **No Extra Tokens**: `successor.tokens.size == 3`
   - Prevents injection of dust or unrelated assets.

### Conditional Validation
The transaction is valid if **exactly one** of two action categories is satisfied:

#### Category A: **LP Action** (Liquidity provisioning)
- `lpAction = validSwap || validMint || validRedeem`
- **validSwap**: `swapBox.tokens(0)._1 == swapNFT`
  - Swap action box present and authenticated.
  - Reserve quantities change; LP supply unchanged.
- **validMint**: `mintBox.tokens(0)._1 == mintNFT`
  - Mint action box present and authenticated.
  - LP supply increases; reserves adjusted proportionally.
- **validRedeem**: `redeemBox.tokens(0)._1 == redeemNFT`
  - Redeem action box present and authenticated.
  - LP supply decreases (with 2% redemption fee); reserves decrease.
  - Inactive when LP price < 0.98 × oracle price (enforced in redeem.es).

#### Category B: **Dexy Action** (Bank/Treasury interaction)
- `dexyAction = (validIntervention || validExtraction) && deltaSupplyLp == 0`
- **validIntervention**: `interventionBox.tokens.size > 0 && interventionBox.tokens(0)._1 == interventionNFT`
  - Bank intervention box present and authenticated.
  - LP supply must not change (`deltaSupplyLp == 0`).
  - Allows bank to rebalance reserves without minting/burning LP tokens.
- **validExtraction**: `extractBox.tokens(0)._1 == extractionNFT`
  - Extraction box present and authenticated.
  - LP supply must not change (`deltaSupplyLp == 0`).
  - Extracts collateral to future (via Tracking box) for future release.

### Delta Supply Calculation
```
deltaSupplyLp = lpReservesIn._2 - lpReservesOut._2
```
- Positive: LP tokens burned (redemption).
- Negative: LP tokens minted.
- Zero: No supply change (dexyAction only).

## Registers Used

**No registers (R4–R9) are explicitly read or written in this contract.**

- The contract relies entirely on **token quantities** in the successor box to enforce state transitions.
- R4–R9 are assumed to be delegated to action scripts (swap.es, mint.es, redeem.es, etc.) for detailed validation.

## Tokens

### Token 0: LP NFT
- **Type**: Native token (singleton NFT)
- **Purpose**: Uniquely identifies and locks this LP box; prevents spoofing.
- **Constraint**: Must be preserved exactly across all transactions.

### Token 1: LP Reserve Tokens
- **Type**: Native fungible token
- **Purpose**: Tracks unminted LP supply; quantity = `initialLp - circulatingLp`.
- **Constraint**: Token ID immutable; quantity changes only on mint/redeem.

### Token 2: Dexy Token (Y)
- **Type**: Native fungible token (in DexyUSD, the USD stablecoin)
- **Purpose**: Counterpart to NanoErg reserves (X); pools liquidity for swaps.
- **Constraint**: Token ID immutable; quantity adjusted by swaps, mints,