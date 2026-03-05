---
title: duckpools/lend-protocol-contracts — partialRepay.md
description: "ErgoScript contract analysis: contracts/pools/Generic-Token-Pool/proxy-contracts/partialRepay.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/Generic-Token-Pool/proxy-contracts/partialRepay.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: `partialRepay.md`

## Purpose

This contract serves as a **proxy validator** for partial loan repayment transactions in the DuckPools lending protocol. It enforces two mutually exclusive paths: either a **refund** (if conditions aren't met by deadline) or a **partial repayment** that reduces the outstanding borrow token amount while preserving the collateral box's state integrity.

## Inputs / Outputs

### Inputs
- **SELF (INPUTS(0))**: The proxy box itself, containing:
  - Token: partial repayment amount (token ID and quantity)
  - R4: Collateral box ID (Coll[Byte])
  - R5: Final borrow token amount after repayment (Long)
  - R6: User script/credential (Coll[Byte])
  - R7: Refund deadline height (Long)

- **INPUTS(1)** (conditional, partial repayment path only): The **collateral box** being updated, containing:
  - R4: Current borrower (Coll[Byte])
  - R5: Index tuple (Int, Int) — likely tracking loan position/state
  - R6: Threshold penalty tuple (Long, Long) — liquidation thresholds
  - R7: DEX NFT ID (Coll[Byte]) — oracle/pricing authority
  - R8: User public key (GroupElement) — borrower identity
  - R9: Forced liquidation flag (Long)
  - Borrow tokens (native tokens tracking loan amount)

### Outputs

**Refund Path** (OUTPUTS.size ≤ 2):
- **OUTPUTS(0)**: Refund box sent to user, containing:
  - Script: User's original script (matches R6 of SELF)
  - Value: Full ERG amount minus MinTxFee
  - Tokens: All proxy box tokens returned

**Partial Repayment Path** (OUTPUTS.size > 2):
- **OUTPUTS(0)**: Updated collateral box (successor), with:
  - Reduced borrow token quantity (set to `finalBorrowTokens`)
  - All other state (registers, script, ERG value) preserved from input

## Key Logic

### Refund Branch (Time-locked Escape)
Executed when `OUTPUTS.size ≤ 2` **AND** `HEIGHT >= refundHeight`:
1. Verify refund box destination matches the user's stored script (R6)
2. Ensure refund value covers ERG input minus minimum transaction fee
3. Confirm all tokens are returned intact
4. **Effect**: Borrower recovers collateral if repayment window expires

### Partial Repayment Branch (Loan Reduction)
Executed when `OUTPUTS.size > 2`:
1. **Collateral Box Validation**:
   - Verify INPUTS(1) matches the pre-recorded collateral box ID (R4 of SELF)
2. **Successor Box Invariants**:
   - Script unchanged (same contract controls future state)
   - ERG value ≥ current value (no value loss to fees)
   - Borrow token ID preserved (same loan asset)
   - **Borrow token quantity reduced to exactly `finalBorrowTokens`** (principal reduction)
   - All auxiliary registers (R4–R9) frozen to prevent unauthorized loan term changes
3. **Effect**: Loan amount decreases atomically; collateral remains locked under same terms

## Registers Used

| Register | Type | Purpose | Path |
|----------|------|---------|------|
| R4 | Coll[Byte] | Collateral box ID (SELF only) | Both |
| R5 | Long | Final borrow token amount post-repayment (SELF only) | Both |
| R6 | Coll[Byte] | User script/credential (SELF only) | Refund validation |
| R7 | Long | Refund deadline height (SELF only) | Timeout check |
| R4 | Coll[Byte] | Current borrower (collateral box) | Partial repayment preservation |
| R5 | (Int, Int) | Loan indexes (collateral box) | Partial repayment preservation |
| R6 | (Long, Long) | Threshold penalties (collateral box) | Partial repayment preservation |
| R7 | Coll[Byte] | DEX NFT for pricing (collateral box) | Partial repayment preservation |
| R8 | GroupElement | Borrower public key (collateral box) | Partial repayment preservation |
| R9 | Long | Forced liquidation status (collateral box) | Partial repayment preservation |

## Tokens

### Native Tokens
- **Proxy Box Token (SELF)**: 
  - Quantity stored as `partialRepayment` (SELF.tokens(0)._2)
  - Represents the repayment amount
  - Returned to user on refund; consumed/credited on partial repayment

- **Borrow Token (Collateral Box)**:
  - ID preserved across successor state
  - Quantity decremented from `currentLoanAmount` to `finalBorrowTokens`
  - Acts as state machine token tracking outstanding principal

### NFT / Authentication Tokens
- **DEX NFT** (R7 of collateral box): Oracle/pricing authority; must remain unchanged

## Integration Pattern

### Off-Chain Construction Requirements
The off-chain bot/dApp must:

1. **For Refund Scenario** (timeout):
   - Construct transaction with `OUTPUTS.size ≤ 2`
   - Ensure `HEIGHT >= SELF.R7` (check blockchain height)
   - Build refund box with script matching `SELF.R6` and full token amount
   - Sign with user credentials if required

2. **For Partial Repayment Scenario** (normal flow):
   - Construct transaction with `OUTPUTS.size > 2`
   - Retrieve collateral box by ID from `SELF.R4`
   - Calculate `finalBorrowTokens = currentLoanAmount - repaymentAmount`
   - Clone collateral box as successor with:
     - **Same script** (copy `propositionBytes`)
     - **Same