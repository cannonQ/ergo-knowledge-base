---
title: duckpools/lend-protocol-contracts — repayment.md
description: "ErgoScript contract analysis: contracts/pools/RSN-POOL/repayment.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/RSN-POOL/repayment.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: RSN-POOL Repayment

## Purpose

This contract validates loan repayments in a decentralized lending pool protocol. It ensures that when a borrower repays their loan, the correct amount of assets is returned to the pool, borrowed token balances are properly decremented, and pool value increases by at least the repayment amount minus transaction fees.

## Inputs / Outputs

**Inputs:**
- `INPUTS(0)`: Initial Pool box—contains the Pool State NFT and tracks borrow token reserves and pool assets
- `INPUTS(1)`: SELF (the Repayment Request box)—holds the original loan amount (token at index 0) and repayment tokens (token at index 1) to be returned to the pool

**Outputs:**
- `OUTPUTS(0)`: Final Pool box—updated state with decremented borrow tokens and increased asset reserves

## Key Logic

The contract enforces six validation conditions (all must be true):

1. **Pool NFT Validation (Initial & Final):**  
   Both the input pool box and output pool box must contain the same Pool NFT token (`BJt8g3gZqEhCL9rzfDsfp7Me67DTuM8HvYBW5yHoHxs`). This ensures the correct pool is being updated.

2. **Borrow Token Decrement:**  
   Calculates the change in outstanding borrow tokens using a "supply ceiling" model:
   - `borrow0 = MaxBorrowTokens - initalPool.tokens(2)._2` (initial borrowed amount)
   - `borrow1 = MaxBorrowTokens - finalPool.tokens(2)._2` (final borrowed amount)
   - `deltaBorrowed` must equal `loanAmount` (the loan is fully repaid)

3. **Repayment Asset Transfer:**  
   The amount of repayment tokens transferred must exactly match the increase in pool assets (`deltaPoolAssets`), and the token ID must be the same as the pool's asset token.

4. **Pool Value Increase:**  
   The difference in ERG value between the output and input pool boxes must be ≥ `SELF.value - transactionFee`. This ensures the borrower contributes sufficient value to cover repayment plus fees.

5. **Double-Spend Prevention (Multi-Box Safety):**  
   `INPUTS(1) == SELF` enforces that this repayment box is the second input (index 1), preventing the same box from being spent multiple times in a single transaction.

6. **Sigma Proposition Combination:**  
   All conditions are combined into a single AND (`sigmaProp`), requiring unanimous satisfaction for transaction validity.

## Registers Used

**No R4–R9 registers are explicitly read or written** in this contract. All state tracking is performed via:
- **Token positions** in the `tokens` array of boxes (indices 0–3)
- **Box value** (ERG balance)
- **Context variables** (`SELF`, `INPUTS`, `OUTPUTS`)

## Tokens

| Token Index | Box Location | Purpose | Role |
|---|---|---|---|
| 0 | Pool box (all inputs/outputs) | Pool State NFT | Singleton identifier; prevents interaction with wrong pool |
| 1 | — | — | (Not used directly in this contract) |
| 2 | Pool box (all inputs/outputs) | Borrow Token Reserve | Tracks total borrowed tokens; supply ceiling model uses `MaxBorrowTokens` |
| 3 | Pool box (all inputs/outputs) | Asset Token (Pool Collateral) | Represents deposited assets; validated in repayment flow |
| 0 | SELF (Repayment box) | Loan Amount Token | The original borrowed amount being repaid |
| 1 | SELF (Repayment box) | Repayment Token | The asset token being returned to the pool |

**Token ID Rule:** The repayment token ID must match the pool's asset token ID to ensure homogeneous repayments.

## Integration Pattern

**Off-chain Bot / Transaction Constructor Responsibilities:**

1. **Box Selection:**
   - Locate the current Pool box (identified by Pool NFT `BJt8g3gZqEhCL9rzfDsfp7Me67DTuM8HvYBW5yHoHxs`)
   - Create a new Repayment Request box containing:
     - Token at index 0: loan token with amount `loanAmount`
     - Token at index 1: asset token with amount `repaymentAmount`
     - Value: at least `loanAmount + transactionFee` in ERGs

2. **Box Construction:**
   - Build the output Pool box with:
     - Pool NFT at index 0 (unchanged)
     - Borrow token at index 2, decremented by `loanAmount`
     - Asset token at index 3, incremented by `repaymentAmount`
     - Value increased by `repaymentAmount` (in ERGs or equivalent)

3. **Transaction Structure:**
   - Input order is critical: `INPUTS(0)` = Pool box, `INPUTS(1)` = Repayment box (SELF)
   - Ensure total transaction fee ≤ `transactionFee` constant (1 ERG)
   - Verify ERG arithmetic: `finalPool.value - initialPool.value >= SELF.value - 1000000L`

4. **Verification Steps:**
   - Match Pool NFT token IDs
   - Verify `deltaBorrowed == loanAmount` (loan fully repaid)
   - Confirm repayment token amount equals pool asset increase
   - Validate minimum box values (storage rent) are maintained

## Related Contracts

**Inferred Relationships (from state machine pattern):**

- **Pool Initialization Contract:** Creates the initial Pool box with the Pool NFT singleton and initializes `MaxBorrowTokens` ceiling
- **Borrow Contract:** Decrements borrow token reserves and distributes loan amounts to borrowers (inverse of repayment)
- **Deposit/Withdrawal Contracts:** Manage the asset token (`tokens(3)`) balance and pool collateral
- **Interest Accrual Contract:** Likely modifies pool value or asset reserves between borrows and repayments (not directly invoked here)

**Pattern:** This