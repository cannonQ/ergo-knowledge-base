---
title: duckpools/lend-protocol-contracts — partial_repay.md
description: "ErgoScript contract analysis: contracts/v2-generics/partial_repay.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/v2-generics/partial_repay.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: `partial_repay.md`

## Purpose

This contract manages partial loan repayments in the duckpools lending protocol. It validates two transaction paths: either a **refund** of the original loan box (if conditions aren't met by a deadline), or a **partial repayment** that reduces the outstanding borrow token amount while preserving the collateral box state and maintaining loan invariants.

## Inputs / Outputs

### Inputs
- **SELF** (Input 0): The repayment box containing:
  - Native token (amount = partial repayment amount)
  - Borrow token reference
  - Collateral box ID (R4)
  - Final borrow token amount (R5)
  - User script/proposition (R6)
  - Refund deadline height (R7)

- **INPUTS(1)** (collateral box, only in repayment path): The active collateral box containing:
  - Borrow tokens (primary token)
  - Collateral tokens (secondary tokens)
  - Borrower script (R4)
  - Loan indexes (R5)
  - Threshold/penalty data (R6)
  - DEX NFT (R7)
  - User public key (R8)
  - Forced liquidation flag (R9)

### Outputs

**Refund Path** (`OUTPUTS.size <= 2`):
- **OUTPUTS(0)**: Refund box sent to borrower with:
  - All original ERG and tokens returned
  - Recipient: `userScript` (borrower's address)
  - Value: ≥ SELF.value − MinTxFee

**Repayment Path** (`OUTPUTS.size > 2`):
- **OUTPUTS(0)**: Successor collateral box with:
  - Updated borrow token amount (`finalBorrowTokens`)
  - All other state preserved (script, registers R4–R9, collateral tokens)
  - ERG value ≥ original collateral box value

## Key Logic

### Refund Path (HEIGHT ≥ refundHeight)
The transaction is valid if **all** of the following hold:
1. **validBorrowerScript**: Output box is locked to the original borrower (`userScript`)
2. **validRefundValue**: Output receives at least the input value minus the minimum transaction fee
3. **validTokensRefunded**: All native and borrow tokens are returned intact
4. **HEIGHT ≥ refundHeight**: The refund deadline has been reached

**Purpose**: Protects the borrower by allowing them to recover collateral if the repayment was not completed within the agreed timeframe.

### Partial Repayment Path (HEIGHT < refundHeight)
The successor collateral box must satisfy **all** of:
1. **validInputCollateral**: The referenced collateral box (INPUTS(1)) matches the stored box ID
2. **validSuccessorScript**: The output uses the same locking script as the input collateral box (state machine invariant)
3. **retainMinValue**: Output ERG value ≥ input ERG value (no value leakage)
4. **retainBorrowTokenId**: The borrow token ID remains unchanged
5. **validBorrowTokens**: The borrow token amount equals `finalBorrowTokens` (the repayment amount is deducted)
6. **collateralTokens == successorTokens**: All collateral tokens (secondary tokens) are preserved
7. **retainRegisters**: All registers R4–R9 are unchanged (loan terms, borrower identity, liquidation state, DEX reference)

**Purpose**: Ensures that partial repayments atomically reduce debt while maintaining all other loan state and preventing unauthorized modifications.

## Registers Used

| Register | Type | Purpose | Path |
|----------|------|---------|------|
| **R4** | `Coll[Byte]` | Collateral box ID (repay box) / Borrower script (collateral box) | Both |
| **R5** | `Long` | Final borrow token amount (repay box) / Loan indexes tuple (collateral box) | Both |
| **R6** | `Coll[Byte]` | User script/borrower address (repay box) / Threshold/penalty data (collateral box) | Both |
| **R7** | `Long` | Refund deadline height (repay box) / DEX NFT identifier (collateral box) | Both |
| **R8** | `GroupElement` | — (repay box) / User public key (collateral box) | Collateral only |
| **R9** | `Long` | — (repay box) / Forced liquidation flag (collateral box) | Collateral only |

**Note**: The repay box and collateral box use registers for different purposes; the contract maps them contextually.

## Tokens

### Borrow Token
- **Token ID**: Extracted as `SELF.tokens(0)._1` (primary token in repay box)
- **Role**: Represents the outstanding loan amount
- **Invariant**: Must be preserved across the state transition (same token ID in successor box)
- **Amount Change**: Reduced from `currentLoanAmount` to `finalBorrowTokens` (the repayment reduces debt)

### Collateral Tokens
- **Token IDs**: `currentCollateralBox.tokens.slice(1, size)` (secondary tokens)
- **Role**: Alternative collateral backing the loan (e.g., other native tokens)
- **Invariant**: Must remain unchanged and in the same order in the successor box
- **Purpose**: Ensures borrower cannot extract collateral during repayment

### DEX NFT
- **Register**: R7 (collateral box)
- **Role**: Identifies the DEX pair used for liquidation pricing
- **Invariant**: Preserved across repayment (fixed during loan lifecycle)

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Construct Refund Transaction** (if HEIGHT ≥ refundHeight):
   - Create OUTPUTS(0) with borrower's script
   - Return all ERG and tokens from SELF
   - Calculate MinTxFee and ensure value >= SELF.value - MinTxFee
   - Sign with borrower's key

2. **Construct Rep