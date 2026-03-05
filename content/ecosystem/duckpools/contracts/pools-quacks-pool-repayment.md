---
title: duckpools/lend-protocol-contracts — repayment.md
description: "ErgoScript contract analysis: contracts/pools/QUACKS-POOL/repayment.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/QUACKS-POOL/repayment.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: QUACKS-POOL Repayment

## Purpose

This contract validates the repayment of borrowed tokens back to a liquidity pool within the DuckPools lending protocol. It ensures that when a borrower repays their loan, the correct amount of tokens is returned to the pool, the pool's state is properly updated, and no value is lost in the process.

## Inputs / Outputs

**Inputs:**
- **INPUTS(0)**: Initial Pool box (contains Pool NFT, borrow token tracking, asset reserves)
- **INPUTS(1)**: Self (the borrower's repayment box) — must be the repayment contract box holding borrowed tokens and repayment tokens
- **Additional inputs**: Potentially borrower's wallet or intermediary boxes (not explicitly validated)

**Outputs:**
- **OUTPUTS(0)**: Final Pool box (updated with repaid tokens and reduced borrow tracking)
- **Additional outputs**: Change boxes or borrower state boxes (not directly constrained by this contract)

**Data Inputs:**
- None explicitly used

## Key Logic

The contract validates six core conditions, all of which must be true (AND logic):

1. **Pool NFT Verification** (`validFinalPool`, `validInitialPool`):
   - Confirms the Pool State NFT (singleton identifier) is present in both the initial and final pool boxes at token index 0
   - Ensures the correct pool is being updated (no pool switching attacks)

2. **Borrow Reduction Validation** (`validBorrowed`):
   - Calculates initial borrowed amount: `borrow0 = MaxBorrowTokens - initalPool.tokens(2)._2`
   - Calculates final borrowed amount: `borrow1 = MaxBorrowTokens - finalPool.tokens(2)._2`
   - Verifies: `deltaBorrowed == loanAmount`
   - Confirms the reduction in the pool's outstanding borrow tokens exactly matches the repayment amount

3. **Asset Repayment Validation** (`validRepayment`):
   - Ensures repayment tokens flow to the pool: `repaymentAmount == deltaPoolAssets`
   - Verifies the repaid token type matches the pool's asset token: `repaymentTokens._1 == initalPool.tokens(3)._1`
   - Prevents token ID spoofing and ensures correct asset type repayment

4. **Value Conservation** (`validValue`):
   - Validates: `deltaValue >= SELF.value - transactionFee`
   - Confirms the pool receives at least the ERG value originally locked in the repayment box (minus protocol transaction fee)
   - Prevents value extraction attacks

5. **Multi-Box Spend Safety** (`multiBoxSpendSafety`):
   - Requires: `INPUTS(1) == SELF`
   - Ensures this repayment box is the second input, preventing same-box spending attacks where one box could be used to satisfy multiple contract conditions in a single transaction

## Registers Used

**No custom registers (R4-R9) are explicitly read or written.** 

The contract relies entirely on:
- **Box value** (`box.value` — native ERG in nanoErgs)
- **Token arrays** (`box.tokens` — tuples of TokenID and amount)
- **Standard box properties**

This is a **stateless validation contract**—it doesn't maintain dApp state in registers; state is encoded in token balances and the Pool NFT singleton pattern.

## Tokens

1. **Pool NFT** (State Singleton):
   - Token ID: `CDFbkWeJdXSxbWys91ojhnuD395cYHk1N2c5t6m7qWBz`
   - Purpose: Uniquely identifies the pool box (enforces single-pool state machine)
   - Location: `initalPool.tokens(0)._1` and `finalPool.tokens(0)._1`

2. **Borrow Token Tracking** (Index 2):
   - Purpose: Tracks remaining borrowable capacity
   - Logic: Stored as `MaxBorrowTokens - currentBorrowed`
   - Decreases in the final pool as loans are repaid

3. **Asset Token** (Index 3):
   - Purpose: The pool's reserve asset being lent out
   - Used in: Repayment validation (`repaymentTokens._1 == initalPool.tokens(3)._1`)
   - Increases in the final pool as repayments arrive

4. **Loan Token** (Self, Index 0):
   - Purpose: Represents the original borrowed amount held by borrower
   - Amount: `SELF.tokens(0)._2 == loanAmount`

## Integration Pattern

**Off-chain bot responsibilities:**

1. **Transaction Construction**:
   - Fetch the current pool box from the blockchain
   - Fetch the borrower's repayment box (containing loan tokens and asset repayment tokens)
   - Calculate new pool state:
     - Reduce borrow token amount by `loanAmount`
     - Increase asset token amount by `repaymentAmount`
     - Update ERG value: `finalPool.value = initalPool.value + SELF.value - transactionFee`

2. **Invariants to enforce**:
   - Pool NFT remains at `tokens(0)`
   - Borrow token at `tokens(2)` is decremented
   - Asset token at `tokens(3)` is incremented
   - No token ID substitution (especially for asset token)

3. **Context Extension** (if used):
   - Not required by this contract
   - Optional: borrower could sign with additional proofs in context extension for privacy

4. **Spending condition**:
   - Only valid when the repayment box is at **INPUTS(1)** (second input)
   - Pool box must be at **INPUTS(0)** (first input)

5. **Verification checks**:
   - Off-chain code must ensure `SELF.tokens(1)._2 >= debt amount owed`
   - Must account for `transactionFee` in ERG calculations
   - Should validate borrow tracking hasn't exceeded `MaxBorrowTokens`

## Related Contracts

Based on typical DuckPools architecture (inferred from contract structure):

1. **Pool Initialization Contract**: