---
title: kushti/dexy-stable — emission.es
description: "ErgoScript contract analysis: contracts/gort-dev/emission.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/gort-dev/emission.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `emission.es`

## Purpose

This contract manages the **time-locked release of GORT tokens to developers** at a rate of 1 GORT per block. It enforces two actions—top-up (adding GORT reserves) and withdrawal (claiming accrued GORT)—while maintaining strict state invariants through a Singleton NFT and signature-based authorization.

---

## Inputs / Outputs

### Inputs
- **SELF**: The emission box itself, containing:
  - Native tokens: Box ID NFT (#0) and GORT token (#1)
  - Registers: `R4` (last payout height), `R5` (authorized SigmaProp)
  - ERG value for storage rent

### Outputs
- **OUTPUTS(selfOutIndex)**: The updated emission box (same logical contract instance):
  - Must preserve the Box ID NFT and GORT token ID
  - Must preserve the ErgoTree script
  - May contain updated GORT quantity and payout height in R4
  - May have modified R5 authorization (on withdrawal only)
  - ERG value must not decrease

---

## Key Logic

### Common Preservation Rules (Both Actions)
All transactions must satisfy:
1. **Singleton preservation**: The Box ID NFT (#0) stays in the output box
2. **Token ID invariance**: GORT token ID remains unchanged
3. **Script immutability**: The ErgoTree (proposition bytes, minus header) is identical
4. **Value non-decrease**: Output ERG ≥ input ERG (covers storage rent)

### Action 0: Top-Up
- **Condition**: `action == 0`
- **Validation**:
  - GORT quantity in output **must increase** (new tokens added)
  - R4 (last payout height) **must not change**
  - R5 (authorization key) **must not change**
- **Signature**: None required (top-up is permissionless or auth-agnostic in signature requirement)

### Action 1: Withdrawal
- **Condition**: `action == 1`
- **Validation**:
  - GORT quantity in output **must decrease** (tokens withdrawn to recipient)
  - **Release rate limit**: `withdrawn_amount ≤ (newHeight - lastHeight)`
    - Enforces exactly 1 GORT released per block since last payout
  - R4 **must strictly increase** to the new payout height
  - New height **must be ≤ HEIGHT** (cannot claim future rewards)
  - **R5 authorization may change** (no preservation check)
- **Signature**: **Required** – `SELF.R5[SigmaProp]` must be satisfied (the stored SigmaProp proves withdrawal legitimacy)

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|-----------|
| **R4** | `Int` | Last payout height (block where GORT was last withdrawn) | Mutable on withdrawal only; increases to current or prior block |
| **R5** | `SigmaProp` | Authorization key (Sigma proposition required to sign withdrawals) | Immutable on top-up; mutable on withdrawal |

---

## Tokens

| Index | Type | Purpose |
|-------|------|---------|
| **#0** | **Box ID NFT** | Singleton token ensuring exactly one emission box exists across all chain state (prevents double-spending of GORT emission) |
| **#1** | **GORT Token** | The released governance/cooperative token; quantity increases via top-up, decreases via withdrawal |

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Top-Up Transaction**:
   - Fetch the current emission box (identified by Box ID NFT #0)
   - Construct output box with:
     - Same NFT and script
     - Increased GORT token quantity
     - Unchanged R4 and R5
     - Minimum ERG for storage rent
   - Set context variable `#0` = output index of self
   - Set context variable `#1` = `0` (top-up action)
   - Submit transaction (no signature required by contract)

2. **Withdrawal Transaction**:
   - Fetch emission box and current blockchain height
   - Calculate allowed withdrawal: `min(available_gort, current_height - R4)`
   - Construct output box with:
     - Same NFT and script
     - Decreased GORT quantity
     - R4 updated to `current_height` (or intermediate height)
     - R5 optionally updated (new authorization key)
   - Send withdrawn GORT to recipient box(es)
   - Set context variable `#0` = output index of self
   - Set context variable `#1` = `1` (withdrawal action)
   - **Provide proof of R5 SigmaProp** (sign with the private key corresponding to R5)
   - Submit transaction

3. **Data Inputs**: None (no external data oracle required)

### Validation by Ergo Node
- Verifies ErgoTree bytecode against SELF and OUTPUTS(selfOutIndex)
- Checks NFT and token IDs
- Validates register values and types
- Enforces Sigma protocol signature for withdrawal (R5)

---

## Related Contracts

- **Recipient contracts**: Not specified in this code, but withdrawal transactions must send GORT to valid outputs (likely a distribution or governance contract)
- **GORT token minting/burning**: Assumed to be handled outside this contract (possibly a separate reserve or treasury box)
- **Dexy ecosystem contracts**: This emission box likely feeds GORT into the broader **Dexy stablecoin** project ecosystem (based on project name `dexy-stable`)

### State Machine Pattern
This contract implements a **Multi-stage state machine** where:
- **State**: (GORT balance, payout height, authorization key)
- **Transitions**: Top-up (reserves) → Withdrawal (release)
- **Invariant**: Total GORT released per block ≤ 1 (hard cap enforced by contract)

---

## Summary Table

| Aspect | Details |
|--------|---------|
| **Contract Type** | State machine, Singleton-guarded emitter |
| **