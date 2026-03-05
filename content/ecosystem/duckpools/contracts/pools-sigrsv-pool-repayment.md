---
title: duckpools/lend-protocol-contracts — repayment.md
description: "ErgoScript contract analysis: contracts/pools/SIGRSV-POOL/repayment.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/SIGRSV-POOL/repayment.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: SIGRSV-POOL Repayment

## Purpose

This contract validates **loan repayment transactions** in a lending pool protocol. It ensures that when a borrower repays a loan, the correct amount of repayment tokens is returned to the pool, the pool's borrow token supply is decremented appropriately, and the pool receives its collateral/asset compensation. This contract acts as the spending validator for a **borrower's loan box** during repayment.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: The **initial Pool box** (contains pool state with tokens and ERG reserves)
- **INPUTS(1)**: **SELF** — the Borrower's loan box (must be at index 1 for safety, contains loan amount in token(0) and repayment tokens in token(1))
- Implicitly: The borrower's wallet for fee coverage

### Outputs
- **OUTPUTS(0)**: The **final Pool box** (updated state after repayment, with decremented borrow tokens and incremented pool assets)
- Implicitly: Change outputs to borrower's address

---

## Key Logic

The contract enforces these **invariants** via Sigma proposition conjunction (`&&`):

1. **Pool NFT Validation** (`validInitialPool` && `validFinalPool`)
   - Both initial and final pool boxes must carry the same **State NFT** (PoolNft token ID)
   - Ensures the boxes are the canonical, authorized pool instances

2. **Borrow Token Reconciliation** (`validBorrowed`)
   - Calculates `borrow0` = MaxBorrowTokens − initial pool's borrow token supply
   - Calculates `borrow1` = MaxBorrowTokens − final pool's borrow token supply
   - Verifies: `deltaBorrowed == loanAmount`
   - Ensures the pool's borrow token balance decreases by exactly the amount being repaid

3. **Repayment Asset Flow** (`validRepayment`)
   - Checks that repayment token amount equals the change in pool's asset reserves
   - Validates the repayment token ID matches the pool's asset token ID
   - Ensures borrowed assets (or stablecoins) flow into the pool

4. **ERG Value Transfer** (`validValue`)
   - Verifies: `deltaValue >= SELF.value - transactionFee`
   - The pool's ERG balance must increase by at least the borrower's ERG contribution (after transaction fee)
   - Ensures minimum box value (storage rent) and fee structure are respected

5. **Multi-Box Spend Prevention** (`multiBoxSpendSafety`)
   - Requires `INPUTS(1) == SELF`
   - Forces the borrower's loan box to be at exactly index 1
   - Prevents replay attacks where a single UTXO spending proof is reused across multiple transactions

---

## Registers Used

**None explicitly read/written in this contract.**

- The contract relies entirely on **token fields** (`SELF.tokens(i)`, `OUTPUTS(0).tokens(i)`) and **value field** (`SELF.value`, `OUTPUTS(0).value`)
- R4–R9 are not used; this is a simple **value-based state machine** without custom data
- Pool state is encoded in token quantities (position 0 = NFT, position 2 = borrow tokens, position 3 = asset tokens)

---

## Tokens

### Token Positions in Boxes

| Position | Token | Purpose |
|----------|-------|---------|
| 0 | **PoolNft** (`8txwdGRnbi6...`) | **Singleton State NFT** — identifies the canonical pool box; transferred from INPUTS(0) to OUTPUTS(0) |
| 1 | — | Reserved (unused in this contract) |
| 2 | **Borrow Token** | Represents borrowed capital; supply tracking via `MaxBorrowTokens - balance` (inverted accounting) |
| 3 | **Asset Token** | The underlying asset (loan collateral or stablecoin); repayment amount flows in |

### Token Flow
- Borrow tokens are **burned/reduced** from pool (supply decreases)
- Repayment asset tokens are **deposited** into pool (balance increases)
- Pool NFT is **preserved** as Singleton token (guarantees state coherence)

---

## Integration Pattern

### Off-Chain Bot / DApp Construction

A headless dApp or off-chain bot must:

1. **Fetch the current pool box**
   - Use Ergo blockchain indexer to locate box with PoolNft token
   - Extract: `borrow_token_balance`, `asset_token_balance`, `pool_erg_value`

2. **Construct the repayment transaction**
   - **Input 0**: Current pool box (INPUTS(0))
   - **Input 1**: Borrower's loan box containing:
     - `tokens(0)` = (loan token ID, loanAmount)
     - `tokens(1)` = (asset token ID, repaymentAmount)
   - **Output 0**: Updated pool box with:
     - Same PoolNft token
     - Incremented borrow token balance (via `MaxBorrowTokens - (old_balance - repaymentAmount)`)
     - Incremented asset token balance (by repaymentAmount)
     - Increased ERG value (≥ SELF.value − 1,000,000)

3. **Satisfy the contract**
   - Bot calculates: `deltaBorrowed`, `deltaPoolAssets`, `deltaValue`
   - Verifies all conditions before signing
   - Adds transaction fee (1,000,000 nanoERG) to fee input

4. **Ensure INPUTS(1) == SELF**
   - The borrower's loan box must be placed at index 1 exactly
   - Prevents multi-box replay

---

## Related Contracts

Based on naming and token structure, this contract likely composes with:

1. **Pool initialization / state contract** — Creates the initial PoolNft box with token reserves
2. **Borrowing contract** (`borrow.md` presumed) — Mints the borrower's loan box; inverse of this repayment logic
3. **Liquidation contract**