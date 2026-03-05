---
title: duckpools/off-chain-bot — add_liquidity.md
description: "ErgoScript contract analysis: optionPools/contracts/proxy_contracts/add_liquidity.md"
tags: [duckpools, off-chain-bot, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/off-chain-bot"
contract_file: optionPools/contracts/proxy_contracts/add_liquidity.md
project: duckpools-off-chain-bot
---
# ErgoScript Contract Analysis: Add Liquidity Proxy

## Purpose

This contract manages liquidity addition requests in an option pool system, acting as a proxy that validates either a successful token exchange to the user or a refund of collateral. It enforces time-locked refund eligibility and ensures atomic composition with downstream liquidity provision contracts through singleton token tracking.

## Inputs / Outputs

### Input
- **SELF**: A request box (eUTXO) containing:
  - ERG collateral (value)
  - A singleton Native token (state NFT) for tracking
  - User address, request parameters, and refund deadline in registers

### Outputs (Two Paths)

**Refund Path** (fewer than 3 outputs):
- **OUTPUTS(0)**: Refund box sent to user
  - Contains ERG refund (minus transaction fee)
  - May contain the same singleton token (multibox refund scenario)
  - Locked to user's script

**Exchange Path** (3+ outputs):
- **OUTPUTS(1)**: Successor box (liquidity position or exchange result)
  - Contains lend pool tokens (minimum `requestAmount`)
  - Locked to user's script
  - Contains reference to SELF via register for chain safety

## Key Logic

The contract enforces **branching validation** based on output count:

### Refund Validation (OUTPUTS.size < 3)
1. **validRefundScript**: OUTPUTS(0) must be locked to the user's address (from R4)
2. **validDeltaErg**: ERG decrease ≤ minimum transaction fee (1,000,000 Ergs) — no dust loss
3. **validHeight**: Current blockchain HEIGHT ≥ `publicRefund` deadline (from R6) — time-lock satisfied
4. **multiBoxRefund**: If OUTPUTS(0) has R4 defined, it must equal SELF.id (singleton continuity for multi-box refunds)
5. **validTokens**: If refund box contains tokens, first token must match SELF's token (state NFT preservation)

### Exchange Validation (OUTPUTS.size ≥ 3)
1. **validSuccessorScript**: OUTPUTS(1) must be locked to user's address
2. **validTokens**: 
   - First token in successor must equal `lendPoolToken` (from R7)
   - Token quantity ≥ `requestAmount` (from R5)
3. **multiBoxSpendSafety**: If OUTPUTS(1) has R7 defined, it must reference SELF.id (prevents double-spending or orphaned requests)

**Logic Gate**: Accept if all conditions in chosen path (refund OR exchange) are satisfied; otherwise reject.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User's address (recipient of refund or successor box) |
| **R5** | `Long` | Minimum token amount requested in exchange |
| **R6** | `Long` | Block height deadline for refund eligibility |
| **R7** | `Coll[Byte]` | Token ID of lend pool tokens expected in exchange |

*R0–R3 implicit: value, tokens, id, serialized tree (standard)*

## Tokens

- **Singleton Token (SELF.tokens(0))**: 
  - Acts as a **state NFT** identifying this request uniquely
  - Enforced to be present and transferred to refund or successor box
  - Prevents double-spending and enables multi-box transaction safety (via register chain references)
  
- **Lend Pool Token (R7)**: 
  - Native token minted/controlled by lending pool contracts
  - Must be received in exchange path with quantity ≥ requestAmount

## Integration Pattern

### Off-Chain Bot Responsibilities

1. **Monitor**: Watch for request boxes with this script locked
2. **Decision Logic**:
   - If current HEIGHT < publicRefund: construct exchange transaction
   - If current HEIGHT ≥ publicRefund: construct refund transaction
3. **Transaction Construction**:
   - **Refund TX**: 
     - Input: SELF
     - Output(0): Refund box (user address, ERG – minTxFee, singleton token, R4=SELF.id if multi-box)
     - Must satisfy: validHeight ✓
   - **Exchange TX**:
     - Input: SELF
     - Input: Lend pool state box (data input or spent box)
     - Output(0): Service fee or auxiliary box (if needed)
     - Output(1): Successor box (user address, lend pool tokens, R7=SELF.id)
     - Output(2+): Pool state update or change (total ≥3 outputs)
4. **Validation**: Sign transaction with user's private key (if user refund) or pool operator's key (if exchange)

### Compositional Constraints

- This proxy **does not execute the actual liquidity addition**; it validates the transition
- Downstream contracts (lend pool state machine) must verify:
  - Successor box tokens came from legitimate mint/reserve
  - Invariants on pool reserves and share pricing
  - Singleton NFT continuity to prevent state divergence

## Related Contracts

Based on naming and register patterns, this contract composes with:

1. **Lend Pool Contract** (implied):
   - Holds reserve of `lendPoolToken`
   - Validates liquidity addition in successor state
   - Referenced via lendPoolToken ID in R7

2. **User Refund/Account Contract** (implicit):
   - Script locked to user address (R4)
   - May enforce additional signature checks or time-locks

3. **Multi-Box Request Orchestrator** (inferred):
   - If R4/R7 register checks trigger, indicates this request may span multiple boxes
   - Suggests atomic composition with other request/settlement contracts

4. **Pool State Machine**:
   - OUTPUTS(1) successor box likely feeds into a pool state update transaction
   - Singleton token (SELF.tokens(0)) ensures exactly one active request per lifecycle

---

## Security Notes

- **Storage Rent**: Refund path incentivizes timely execution (user can self-refund after `publicRefund` height)
- **Multi-Box Safety**: Register-based parent tracking