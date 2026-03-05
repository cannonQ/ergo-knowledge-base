---
title: duckpools/lend-protocol-contracts — repayment.md
description: "ErgoScript contract analysis: contracts/pools/eSIGUSD-POOL/repayment.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/eSIGUSD-POOL/repayment.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: eSIGUSD-POOL Repayment

## Purpose

This contract validates **loan repayment transactions** in a lending protocol where borrowers must return borrowed tokens plus accrued assets to the pool. It ensures that the pool's token balances and ERG reserves are correctly updated to reflect the repayment, preventing protocol invariant violations.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: The pool Box (initial state) containing:
  - Token(0): Pool NFT (State NFT for singleton)
  - Token(2): Remaining borrow-eligible tokens (tracked via deficit from MaxBorrowTokens)
  - Token(3): Pool asset reserves (collateral or accrued interest)
- **INPUTS(1)**: The borrower's loan Box (SELF) containing:
  - Token(0): Borrowed token amount
  - Token(1): Repayment token amount (must match pool's asset token)
- **INPUTS(1)** again via `multiBoxSpendSafety` check (prevents duplicate box spending)

### Outputs
- **OUTPUTS(0)**: The updated pool Box (final state) with:
  - Increased ERG value by loan amount (minus transaction fee)
  - Reduced borrow token availability (increased borrow0 → borrow1)
  - Increased asset reserves (repayment tokens added)

---

## Key Logic

### Core Validation Conditions (in order):

1. **Pool NFT Identity Check (`validFinalPool` & `validInitialPool`)**
   - Verifies token(0) in both initial and final pool boxes matches the hardcoded `PoolNft`
   - Ensures the same pool singleton is being mutated (state machine continuity)

2. **ERG Value Repayment (`validValue`)**
   - Checks: `finalPool.value - initialPool.value >= SELF.value - transactionFee`
   - The pool must receive at least the loan box's remaining ERG balance minus 1 network transaction fee
   - Accounts for transaction fee burn

3. **Borrow Token Settlement (`validBorrowed`)**
   - Calculates: `borrow0 = MaxBorrowTokens - initialPool.tokens(2)._2` (initial borrow deficit)
   - Calculates: `borrow1 = MaxBorrowTokens - finalPool.tokens(2)._2` (final borrow deficit)
   - Validates: `deltaBorrowed == loanAmount`
   - Ensures borrowed tokens are "returned" by reducing the borrow deficit in the pool by exactly the loan amount

4. **Asset Token Repayment (`validRepayment`)**
   - Checks: `repaymentAmount == deltaPoolAssets` (token(1) from loan box matches token(3) increase in pool)
   - Checks: `repaymentTokens._1 == initialPool.tokens(3)._1` (repayment token ID matches pool's asset token)
   - Ensures accrued interest/fees are deposited into pool reserves

5. **Multi-Box Spend Safety (`multiBoxSpendSafety`)**
   - Verifies: `INPUTS(1) == SELF`
   - Confirms the loan box being spent is at position INPUTS(1)
   - Prevents same-box double-spending exploits where malicious scripts could reference SELF multiple times

---

## Registers Used

**No registers (R4-R9) are explicitly read or written in this contract.**

The contract relies entirely on **box tokens and ERG value** for state tracking. This is a stateless validation approach using token amounts as the source of truth.

---

## Tokens

### Token(0): Pool NFT
- **Type**: Singleton State NFT
- **Purpose**: Identifies the unique pool box across transactions
- **Requirement**: Must be present in both input and output pools with identical token ID
- **Token ID**: `8A5R3bhY16TCJXPF8cCNL5bgdBg1vHZyM3f8W1PqAvdM`

### Token(2): Borrow-Eligible Tokens
- **Type**: Semi-fungible tracking token
- **Purpose**: Tracks the remaining borrow capacity in the pool
- **Logic**: Amount is derived as `MaxBorrowTokens - token(2)._2`, indicating a "deficit model"
- **Invariant**: `borrow0 - borrow1 == loanAmount` (deficit must decrease by loan amount)

### Token(3): Pool Asset Reserves
- **Type**: Fungible asset/interest token
- **Purpose**: Accumulates repaid interest or collateral
- **Logic**: `assetsInPool1 - assetsInPool0 == repaymentAmount`
- **Invariant**: Must match the token type being repaid by borrower

---

## Integration Pattern

### Off-Chain Requirements

The off-chain dApp or bot must:

1. **Construct the Repayment Transaction**
   - Fetch current pool box (INPUTS(0)) from blockchain
   - Identify the borrower's loan box (INPUTS(1) / SELF)
   - Calculate repayment amounts based on loan duration and accrued interest
   - Assemble transaction with:
     - Pool box as INPUTS(0)
     - Loan box as INPUTS(1)
     - Updated pool box as OUTPUTS(0)

2. **Verify Pre-Conditions**
   - Ensure borrower has sufficient tokens for repayment (token(1) amount ≥ repaymentAmount)
   - Ensure borrower has sufficient ERG (SELF.value ≥ transactionFee)
   - Calculate: `repaymentAmount = (loanAmount * interestRate) / 100` or similar formula

3. **Validate Post-Transaction State**
   - Confirm final pool NFT is preserved
   - Confirm borrow token deficit increases by exactly `loanAmount`
   - Confirm asset reserves increase by exactly `repaymentAmount`
   - Confirm pool ERG balance increases by `loanAmount - transactionFee`

4. **Transaction Signing**
   - Signer must control INPUTS(1) to authorize loan repayment
   - Likely requires borrower's private key for Sigma protocol proof

---

## Related Contracts