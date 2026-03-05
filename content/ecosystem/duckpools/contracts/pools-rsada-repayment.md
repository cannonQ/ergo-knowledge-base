---
title: duckpools/lend-protocol-contracts — repayment.md
description: "ErgoScript contract analysis: contracts/pools/rsAda/repayment.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsAda/repayment.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: rsAda Repayment Contract

## Purpose

This contract validates the repayment of a loan within the duckpools lending protocol. It ensures that when a borrower repays their loan, the repayment tokens are correctly transferred to the pool, the borrowed tokens are returned in the correct amount, and the pool's state NFT and balances are properly updated.

## Inputs / Outputs

**Inputs:**
- `INPUTS(0)`: The initial pool box (before repayment), containing the Pool NFT and token balances
- `INPUTS(1)`: **SELF** – the repayment box, holding the loan tokens being repaid and the repayment asset tokens
- Additional inputs may include borrower funds or other state boxes

**Outputs:**
- `OUTPUTS(0)`: The final pool box (after repayment), with updated token balances and the same Pool NFT

## Key Logic

The contract validates six core conditions that must **all** be true:

1. **Pool NFT Verification (Initial & Final)**: Both the input pool box and output pool box contain the correct Pool NFT token (`PoolNft`), ensuring continuity of the pool's identity.

2. **Borrow Token Return**: Calculates the change in "available borrow tokens" by comparing `MaxBorrowTokens` minus tokens at index 2 before and after. Validates that the decrease in borrowed amount equals the `loanAmount` being repaid.

3. **Repayment Amount Matches Pool Assets**: Ensures the repayment tokens (at index 1 in SELF) match the increase in pool assets (at index 3), meaning the correct quantity of repayment tokens flows into the pool.

4. **Value Conservation**: Verifies the pool's Ergo value (nanoERG) increases by at least `SELF.value - transactionFee`, accounting for transaction fees and the loan's collateral or principal in Ergo.

5. **Repayment Token Type Verification**: Confirms the repayment token ID matches the pool's asset token ID, preventing substitution attacks.

6. **Multi-Box Spend Safety**: Enforces that SELF is exactly at `INPUTS(1)`, preventing a single malicious box from being referenced twice in the same transaction (a common eUTXO vulnerability).

## Registers Used

No explicit R4–R9 registers are read or written in this contract. The contract operates solely on:
- Box properties: `value`, `tokens`
- Native Ergo value (in nanoERG)
- Token tuple structure: `tokens(index)._1` (token ID) and `tokens(index)._2` (token amount)

If pool state (e.g., interest rates, borrower IDs) is needed, it would reside in registers of `INPUTS(0)` or `OUTPUTS(0)`, but this contract does not examine them.

## Tokens

**Tokens used:**

| Index | Token | Purpose |
|-------|-------|---------|
| 0 (initial/final pool) | `PoolNft` | State NFT singleton identifying the unique pool box; required for pool state transitions |
| 2 (pool tokens) | Borrow token | Tracks available borrowing capacity; decrements as loans are made, increments as they're repaid |
| 3 (pool tokens) | Asset/repayment token | The token borrowers owe; increases in the pool when repayment occurs |
| 0 (SELF tokens) | Loan token | The original borrowed amount being returned in this transaction |
| 1 (SELF tokens) | Repayment token | The tokens the borrower sends back to the pool as repayment |

The Pool NFT acts as a Singleton / State NFT, ensuring only one pool box is active at a time.

## Integration Pattern

**Off-chain bot / dApp must:**

1. **Locate the active pool box**: Query the blockchain for the box holding the `PoolNft` token.

2. **Construct the repayment transaction**:
   - Input the current pool box (`INPUTS(0)`)
   - Input the repayment box containing the borrower's repayment tokens (`INPUTS(1)` = SELF in the contract context)
   - Output a new pool box with updated token balances:
     - Borrow token amount decreases (available borrowing increases)
     - Asset token amount increases (pool receives repayment)
     - Pool value increases by repayment amount minus transaction fee
   - Ensure the Pool NFT moves to `OUTPUTS(0)`

3. **Calculate amounts**:
   - `deltaBorrowed = borrow0 - borrow1` must equal `loanAmount`
   - `deltaPoolAssets = assetsInPool1 - assetsInPool0` must equal `repaymentAmount`
   - `deltaValue` must be ≥ `SELF.value - transactionFee`

4. **Sign the transaction** with the borrower's private key to authorize repayment.

5. **Verify constraints**:
   - Sufficient Ergo value in the repayment box to cover transaction fees
   - Correct token IDs and amounts before submission

## Related Contracts

Based on the code structure, this contract integrates with:

- **Pool State Contract** (`INPUTS(0)` / `OUTPUTS(0)`): Manages the active pool box and its NFT. Likely has a separate contract validating pool state transitions (interest accrual, liquidations, etc.).

- **Borrowing Contract**: Presumably issues loans, creating the initial loan box with tokens at index 0. The repayment contract is its inverse operation.

- **Collateral / Deposit Contracts** (implied): Borrowers may have collateral boxes backing their loans; this contract assumes the loan and repayment boxes exist but does not validate collateral separately.

The pattern suggests a **multi-stage contract** state machine where:
- **Stage 1 (Borrow)**: Borrowing contract validates loan creation and collateral lock
- **Stage 2 (Repay)** ← **This contract**: Validates repayment and pool asset increase
- **Stage 3 (Liquidate)** (not shown): Likely liquidates collateral if repayment fails

---

**Key Ergo Concepts Applied:**
- **eUTXO Model**: Each pool and loan is a distinct box with independent state
- **Singleton Pattern**: Pool NF