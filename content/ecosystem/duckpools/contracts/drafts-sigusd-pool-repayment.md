---
title: duckpools/lend-protocol-contracts — repayment.md
description: "ErgoScript contract analysis: contracts/pools/drafts/SIGUSD-POOL/repayment.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/drafts/SIGUSD-POOL/repayment.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: SIGUSD-POOL Repayment

## Purpose

This contract validates **loan repayment transactions** in a lending pool protocol. It ensures that when a borrower repays a loan, the repayment amount correctly flows back to the pool, the pool's borrowed token balance decreases appropriately, and the pool receives the correct asset compensation in exchange.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Initial Pool Box
  - Contains Pool NFT (token index 0), borrow token supply tracking (token index 2), and pool asset reserves (token index 3)
  - Carries ERG value representing the pool's liquidity reserves

- **INPUTS(1)**: SELF (Repayment Box)
  - The box spending this contract
  - Contains loan tokens (SELF.tokens(0)) and repayment tokens (SELF.tokens(1))
  - Carries ERG value equal to transaction fees

### Outputs
- **OUTPUTS(0)**: Final Pool Box
  - Updated pool state post-repayment
  - Pool NFT preserved (token index 0)
  - Borrow token supply decreased (token index 2)
  - Pool asset reserves increased (token index 3)
  - ERG value increased by repayment amount minus transaction fee

## Key Logic

The contract enforces six atomic conditions that must all be satisfied (AND logic via `sigmaProp`):

1. **Pool NFT Validation (Initial)**: Verify `INPUTS(0)` holds the correct Pool NFT singleton token to authenticate the legitimate pool box.

2. **Pool NFT Validation (Final)**: Verify `OUTPUTS(0)` holds the same Pool NFT, ensuring state continuity and preventing pool replacement attacks.

3. **Borrow Token Reconciliation**: Calculate the change in borrowed tokens:
   - `borrow0 = MaxBorrowTokens - initalPool.tokens(2)._2` (initial borrowed amount)
   - `borrow1 = MaxBorrowTokens - finalPool.tokens(2)._2` (final borrowed amount)
   - Enforce: `deltaBorrowed == loanAmount` (repaid loan must equal decrease in borrowed tokens)

4. **Repayment Asset Flow**: Verify repayment tokens go to the pool:
   - Repayment amount must equal increase in pool asset reserves: `repaymentAmount == deltaPoolAssets`
   - Repayment token ID must match pool's asset token ID: `repaymentTokens._1 == initalPool.tokens(3)._1`

5. **ERG Value Conservation**: Ensure the pool's ERG reserves increase by at least the loan value:
   - `deltaValue >= SELF.value - transactionFee`
   - This accounts for the transaction fee deducted from the repayment box

6. **Multi-Box Spend Safety**: Enforce `INPUTS(1) == SELF` to prevent the same contract instance from being spent multiple times in a single transaction (replay protection).

## Registers Used

**No R4-R9 registers are used in this contract.**

All state tracking relies on:
- Native tokens (Token IDs) stored in box token lists
- Box values (ERG amounts)
- Constant values (transaction fee, maximum borrow limit, Pool NFT ID)

## Tokens

### Pool NFT (Singleton State Token)
- **Token ID**: `UiocPX2UskC22zEyjduKAtm7XLWrfhDXn2KZrgAGbga`
- **Purpose**: Authenticates the legitimate pool box across transaction sequence
- **Circulation**: Exactly 1 unit, moves from input pool to output pool
- **Role**: Prevents spoofing attacks by ensuring only the canonical pool box state is updated

### Borrow Tokens
- **Location**: `initalPool.tokens(2)` and `finalPool.tokens(2)`
- **Purpose**: Track total borrowed amount using a balance-of pattern
- **Mechanism**: Stored as `MaxBorrowTokens - actual_borrowed_amount` to enable subtraction-based accounting

### Repayment / Pool Asset Tokens
- **Location**: 
  - Loan tokens: `SELF.tokens(0)`
  - Repayment tokens: `SELF.tokens(1)`
  - Pool assets: `initalPool.tokens(3)` and `finalPool.tokens(3)`
- **Purpose**: Represent the asset being repaid to the pool
- **Mechanism**: Token ID matching enforces the correct asset type flows back

## Integration Pattern

### Off-Chain Bot / Transaction Constructor Requirements

1. **Pool Lookup**: Query the blockchain to fetch the current pool box (holds Pool NFT singleton).

2. **Borrow State Query**: Read `initalPool.tokens(2)._2` to determine current borrow capacity.

3. **Construct Repayment Box** (`INPUTS(1)` / `SELF`):
   - Mint or transfer in loan tokens matching the amount being repaid
   - Include repayment tokens (the asset owed to the pool) at the repayment amount
   - Set ERG value to at least `transactionFee (1,000,000)` plus minimum box value

4. **Construct Output Pool Box** (`OUTPUTS(0)`):
   - Copy Pool NFT from input pool to output pool
   - Decrease borrow token amount by exactly `loanAmount`
   - Increase asset token amount by exactly `repaymentAmount`
   - Increase ERG value by `repaymentAmount - transactionFee`
   - Ensure minimum box value (2 ERG + token storage rent) is maintained

5. **Transaction Assembly**:
   - Set `INPUTS(0)` = current pool box
   - Set `INPUTS(1)` = repayment box (spending this contract)
   - Set `OUTPUTS(0)` = updated pool box
   - Additional outputs for change/fees as needed

6. **Validation Points**:
   - Verify `deltaBorrowed > 0` to prevent zero repayments
   - Verify `borrow1 >= 0` to prevent over-repayment
   - Verify pool retains minimum ERG after repayment
   - Verify transaction fee is paid to miners

### Example Off-Chain Flow
```
1. User selects loan to repay (obtains l
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
