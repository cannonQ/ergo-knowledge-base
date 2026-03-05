---
title: duckpools/lend-protocol-contracts — proxyLend.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/proxy-contracts/proxyLend.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/proxy-contracts/proxyLend.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: proxyLend

## Purpose

This contract acts as a **lending request proxy** that validates either a **refund** (if the lending pool cannot fulfill the request) or a **successful loan disbursement** (if the pool provides the requested tokens). It protects against double-spending in multi-box transactions by tracking the originating UTXO via IDs stored in successor box registers.

---

## Inputs / Outputs

### Inputs
- **SELF**: The proxy request box containing:
  - User address (R4)
  - Requested loan amount in lend pool tokens (R5)
  - Refund deadline height (R6)
  - Native ERG value to cover transaction fees

### Outputs

**Scenario 1: Refund Path** (outputs.size < 3)
- **OUTPUTS(0)**: Refund box sent back to the user
  - Must contain remaining ERG after fee deduction
  - Must reference SELF.id in R4 (multi-box safety check)
  - Must be lockable by the user's script

**Scenario 2: Loan Disbursement Path** (outputs.size ≥ 3)
- **OUTPUTS(0), OUTPUTS(1)**: Other transaction outputs (fee/state boxes)
- **OUTPUTS(2)**: Successor box (loan grant box) to the user containing:
  - Lend pool tokens at minimum the requested amount
  - Reference to SELF.id in R7 (multi-box safety check)
  - User's script as locking condition

---

## Key Logic

The contract enforces an **either-or** branching logic:

### Branch 1: Refund Execution (`OUTPUTS.size < 3`)
All of the following must be **true**:
1. **validRefundScript**: `OUTPUTS(0).propositionBytes == user` — Refund box is locked to the requesting user
2. **validDeltaErg**: `(SELF.value - OUTPUTS(0).value) <= minTxFee` — Only transaction fees (1 ERG) are consumed
3. **validHeight**: `HEIGHT >= publicRefund` — Current blockchain height has reached or exceeded the refund deadline, authorizing recovery
4. **multiBoxRefund**: `OUTPUTS(0).R4 == SELF.id` — Refund box explicitly references this proxy box's ID, preventing reuse across multiple requests

### Branch 2: Loan Disbursement (`OUTPUTS.size ≥ 3`)
All of the following must be **true**:
1. **validSuccessorScript**: `OUTPUTS(2).propositionBytes == user` — Successor box is locked to the requesting user
2. **validTokens**: 
   - First token in `OUTPUTS(2).tokens` has ID == `lendPoolToken` (hard-coded singleton)
   - Token amount >= `requestAmount` (at least the requested quantity is provided)
3. **multiBoxSpendSafety**: `OUTPUTS(2).R7 == SELF.id` — Successor box explicitly references this proxy box's ID, ensuring atomic consumption

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User's script bytes / public key (authentication target) |
| **R5** | `Long` | Requested loan amount in lend pool tokens |
| **R6** | `Long` | Refund deadline height (absolute block height trigger) |
| **R7** (successor) | `Coll[Byte]` | SELF.id for multi-box atomic safety in loan path |
| **R4** (refund box) | `Coll[Byte]` | SELF.id for multi-box atomic safety in refund path |

---

## Tokens

### Lend Pool Token
- **Token ID**: `4Ft2Y28ioPCfjXBkFXwZrfXu2wLMtSVCDEuuJSk6h6J3` (hard-coded constant)
- **Role**: Payment / collateral asset for the loan
- **Validation**: 
  - Must be present in `OUTPUTS(2).tokens(0)` (first token position)
  - Minimum quantity must satisfy `requestAmount`
  - Acts as a **State NFT** or **singleton token** to identify legitimate pool disbursements

### Native ERG
- Covers minimum transaction fee and minimum box value (`1000000L` each)
- Used for incentivizing on-chain validation

---

## Integration Pattern

### Off-Chain Bot / dApp Workflow

1. **Request Construction**:
   - User calls off-chain API with desired loan amount
   - Bot creates proxy request box with:
     - R4 = user's PK / script
     - R5 = loan amount
     - R6 = current HEIGHT + N (refund deadline, e.g., 72 blocks ahead)
     - Value = minTxFee (1 ERG) to cover execution

2. **Lending Pool Response** (one of two paths):

   **Success Path**:
   - Pool spends this box and provides a successor (OUTPUTS(2))
   - Successor contains lend pool tokens meeting requestAmount
   - Successor locked to user's script
   - Successor.R7 = SELF.id (atomic linking)

   **Refund Path**:
   - After HEIGHT >= R6, user or liquidator broadcasts refund transaction
   - Spends proxy box, returns ERG to user (OUTPUTS(0))
   - OUTPUTS(0).R4 = SELF.id (idempotency check)

3. **Constant Segregation**:
   - `lendPoolToken`, `minTxFee`, `minBoxValue` are hard-coded contract constants
   - No context extensions required for deterministic validation

4. **Multi-Stage Composition**:
   - This proxy is **Stage 1** of a multi-stage contract pattern
   - Output(2) may be spent by a collateral release or loan repayment contract (**Stage 2**)

---

## Related Contracts

Based on directory structure and patterns, this proxy likely composes with:

1. **Lending Pool Contract** (`ERG-POOL/poolLend.md` or similar)
   -