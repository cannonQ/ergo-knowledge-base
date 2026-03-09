---
title: kushti/dexy-stable — emission.es
description: "ErgoScript contract analysis: contracts/gort-dev/emission.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/gort-dev/emission.es
project: dexy-use
---
# ErgoScript Contract Analysis: GORT Emission (kushti/dexy-stable)

## Purpose

This contract manages the emission and withdrawal of GORT tokens to developers from a cooperative treasury, enforcing a rate limit of **1 GORT per block**. It supports two state-preserving actions: topping up the box's GORT reserves, and withdrawing accrued GORT subject to the per-block constraint.

## Inputs / Outputs

### Inputs
- **SELF** (the spending box): Contains the Singleton NFT (#0), GORT token reserve (#1), last payout height (R4), and authorization SigmaProp (R5).
- **Context data**: 
  - `getVar[Short](0)` → output index of the state box (to locate OUTPUTS(selfOutIndex))
  - `getVar[Byte](1)` → action code (0 = top-up, 1 = withdrawal)

### Outputs
- **OUTPUTS(selfOutIndex)**: The successor state box, which must:
  - Preserve the Singleton NFT token
  - Preserve the GORT token ID (though quantity changes based on action)
  - Preserve the ErgoTree (script unchanged)
  - Maintain or increase ERG value (min box value + storage rent)
  - Update R4 (payout height) and R5 (auth) as specified by action

## Key Logic

### Common Preservation Rules (both actions)
All transitions must satisfy:
1. **Singleton NFT preserved**: `selfOut.tokens(0) == SELF.tokens(0)` — ensures this is the canonical state box
2. **GORT token ID preserved**: `selfOut.tokens(1)._1 == SELF.tokens(1)._1` — same token stays tracked
3. **Script preserved**: ErgoTree (minus header byte) identical in input and output — no unilateral code changes
4. **Value non-decreasing**: `selfOut.value >= SELF.value` — protects against theft via ERG extraction

### Action 0: Top-Up (Refill GORT Reserve)
**Purpose**: Cooperative adds more GORT to the box.

**Conditions**:
- GORT quantity increases: `selfOut.tokens(1)._2 > SELF.tokens(1)._2`
- Payout height frozen: `selfOut.R4[Int].get == lastHeight`
- Auth SigmaProp unchanged: `selfOut.R5[SigmaProp].get == SELF.R5[SigmaProp].get`
- **No signature required** — cooperative members can top-up freely

### Action 1: Withdrawal (Claim Accrued GORT)
**Purpose**: Developers withdraw earned GORT, rate-limited to emission schedule.

**Conditions**:
- GORT quantity decreases: `SELF.tokens(1)._2 > selfOut.tokens(1)._2`
- **Rate limit enforced**: 
  ```
  SELF.tokens(1)._2 - selfOut.tokens(1)._2 <= newHeight - lastHeight
  ```
  — maximum 1 GORT per block elapsed since last withdrawal
- Payout height advances: `newHeight > lastHeight`
- No future claims: `newHeight <= HEIGHT` — can only claim up to current block
- **Signature required**: `SELF.R5[SigmaProp].get` — auth key must sign the withdrawal
- **R5 can be updated**: Unlike top-up, the auth SigmaProp is not checked in the output, allowing key rotation on withdrawal

## Registers Used

| Register | Type | Purpose | Mutable? |
|----------|------|---------|----------|
| **R4** | `Int` | Last payment height — records the block height of the previous withdrawal | Yes (withdrawal only) |
| **R5** | `SigmaProp` | Authorization key — SigmaProp that must sign withdrawals; can be changed during withdrawal | Yes (withdrawal only) |

Registers R6–R9 are unused.

## Tokens

| Index | Role | Purpose |
|-------|------|---------|
| **#0** | **Singleton NFT** | State identifier — ensures only one authoritative emission box exists (Token ID rule: box ID of this contract becomes the NFT ID) |
| **#1** | **GORT Token** | Emission asset — variable quantity tracks available/released GORT; preserved but quantity changes per action |

## Integration Pattern

### Off-Chain Bot / Dapp Responsibilities

1. **Construct Top-Up Transaction**:
   - Source GORT from cooperative treasury
   - Set `getVar[Byte](1) = 0`
   - Ensure output preserves R4, R5, and all tokens
   - Increase GORT quantity in output
   - No signature from R5 needed

2. **Construct Withdrawal Transaction**:
   - Calculate withdrawable GORT: `min(reserve, HEIGHT - lastHeight)`
   - Set `getVar[Byte](1) = 1`
   - Update `selfOut.R4[Int] = HEIGHT` (or any height > lastHeight, ≤ HEIGHT)
   - Decrease GORT quantity in output
   - **Sign with SELF.R5[SigmaProp]** (the stored auth key)
   - Optionally update R5 to a new SigmaProp (key rotation)
   - Route withdrawn GORT to recipient address

3. **Context Extension Construction**:
   - `getVar[Short](0)` → locate output in OUTPUTS
   - `getVar[Byte](1)` → specify action code

### Verification Off-Chain
- Confirm `newHeight - lastHeight` blocks have passed since last withdrawal
- Validate that withdrawal amount ≤ elapsed blocks
- Check Singleton NFT ID matches known state box

## Related Contracts

**Inferred relationships** (from project structure):

- **SigmaUSD / Dexy contracts**: Likely integrated with a broader stablecoin system; GORT may be governance/incentive token for Dexy protocol (based on project name *dexy-stable*)
- **Potential oracle or feeder contracts**: May receive price/height data via data inputs for emission rate adjustment (not visible in this excerpt)
- **