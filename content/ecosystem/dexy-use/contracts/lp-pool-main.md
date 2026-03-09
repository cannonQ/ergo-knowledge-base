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
project: dexy-use
---
# ErgoScript Contract Analysis: Dexy Liquidity Pool Main

## Purpose

This contract governs the **primary liquidity pool (LP) box** for the Dexy stablecoin system. It validates state transitions across six transaction types (Intervention, Swap, Redeem, Mint, Extract-to-Future, Release-Extracted) while preserving the LP box's identity, script, and token composition. The contract acts as a **State machine** that enforces atomic invariants across multi-stage composable actions.

## Inputs / Outputs

### Expected Inputs
- **Input[0]**: Self (LP box containing the NFT, LP tokens, and Dexy token reserves)
- **Input[1]**: Action box (Swap/Mint/Redeem/Extract box, identified by NFT)
- **Input[2]** *(optional)*: Intervention box (identified by Intervention NFT)

### Expected Outputs
- **Output[0]**: Successor LP box (self-replica with mutated token amounts)

### Data Inputs *(context references, not consumed)*
- **Oracle box** (for Redeem, Extract, and Release actions)
- **Bank box** (for Extract action)
- **Tracking box** (for Extract and Release actions, referenced at 95% or 101% states)

## Key Logic

### Core Invariants (Always Enforced)
1. **`preservedScript`**: The successor box must have identical `propositionBytes` (same ErgoTree), ensuring the LP remains locked under this contract.
2. **`preservedLpNft`**: The LP box's NFT (Tokens[0]) must be identical in/out, maintaining **Singleton** pattern for box identification.
3. **`preservedLpTokenId`**: LP token ID (Tokens[1]._1) must not change.
4. **`preservedDexyTokenId`**: Dexy token (USD) ID (Tokens[2]._1) must not change.
5. **`noMoreTokens`**: Exactly 3 tokens must remain in successor (prevents token injection).

### Action Routing Logic
The contract validates **exactly one** of two mutually exclusive action classes:

#### **LP Action** (`lpAction = true`)
Triggered when Input[1] holds one of three action NFTs:
- **Swap** (`validSwap`): Exchange X↔Y reserves; LP supply unchanged
- **Mint** (`validMint`): Deposit X+Y, receive LP tokens; increases LP supply
- **Redeem** (`validRedeem`): Burn LP tokens, withdraw X+Y; decreases LP supply
  - *Note: Inactive when LP price < 0.98 × Oracle price* (enforced in redeem.es action script)
  - *Incurs 2% redemption fee* (collected in redeem.es)

#### **Dexy Action** (`dexyAction = true`)
Triggered when Inputs include Intervention or Extraction, with critical constraint:
- **`deltaSupplyLp == 0`**: LP token supply must remain constant (no extraction of LP tokens during bank interventions or token extraction)
- **Intervention**: Bank interacts with LP during collateral rebalancing (oracle data-input required)
- **Extract-to-Future**: Remove Y tokens to future release escrow (oracle + bank + tracking data-inputs)
- **Release-Extracted**: Unlock previously extracted tokens (oracle + tracking data-input at 101% state)

### Execution Flow
```
sigmaProp(
    preservedScript && preservedLpNft && preservedLpTokenId && 
    preservedDexyTokenId && noMoreTokens && 
    (lpAction || dexyAction)
)
```
All invariants **must** hold, AND at least one action category must be valid.

## Registers Used

**No custom registers (R4-R9) are explicitly read or written in this contract.**

The contract relies entirely on:
- **Box tokens** (Tokens[0], Tokens[1], Tokens[2]) for state encoding
- **Box.propositionBytes** for script identity
- **Box.value** (NanoErgs, implicit in token reserves) for X-token tracking

*Note: Related action scripts (swap.es, mint.es, redeem.es, intervention.es, extract.es) may use registers for parameters; those are stored in Input[1] (action box) or data-inputs.*

## Tokens

| Position | Token Type | Purpose | Constraint |
|----------|-----------|---------|-----------|
| **Tokens[0]** | **Singleton NFT** (Intervention, Extraction, Swap, Mint, or Redeem NFT IDs stored as constants) | Uniquely identifies LP box; also identifies action boxes by NFT matching | Must be identical in/out; **preservedLpNft** |
| **Tokens[1]** | **LP Token** (custom native token) | Represents liquidity provider shares; supply tracked as `initialLp - amount` | ID immutable; quantity changes on Mint/Redeem; frozen on Swap/Intervention/Extract |
| **Tokens[2]** | **Dexy Token (Y)** — typically USD stablecoin | Secondary reserve asset (X = NanoErgs in DexyUSD) | ID immutable; quantity mutable on Swap/Redeem/Mint/Extract |

### NFT Constants (Injected at Compile Time)
```ergoscript
$interventionNFT, $extractionNFT, $lpSwapNFT, $lpMintNFT, $lpRedeemNFT
```
These are **base64-encoded token IDs** used for action authorization via **Token ID rule** pattern.

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Construct Action Box** (Input[1]):
   - Embed the appropriate NFT (Swap/Mint/Redeem/Intervention/Extraction)
   - Include action-specific parameters in registers (R4-R9)
   - Calculate X and Y deltas based on oracle or user intent

2. **Construct/Attach Data-Inputs**:
   - **For Redeem**: Provide Oracle box (data-input) to fetch current price; validate LP price ≥ 0.98 × oracle price
   - **For Extract/Release**: Provide Oracle, Bank,