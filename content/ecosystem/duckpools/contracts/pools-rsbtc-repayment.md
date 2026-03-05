---
title: duckpools/lend-protocol-contracts — repayment.md
description: "ErgoScript contract analysis: contracts/pools/rsbtc/repayment.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsbtc/repayment.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Repayment (duckpools/lend-protocol-contracts)

## Purpose

This contract validates the repayment of borrowed assets in a lending pool. It ensures that when a borrower repays their loan, the correct amount of assets are returned to the pool, borrowed token balances are properly decremented, and the pool's value is correctly updated to reflect the repayment transaction.

## Inputs / Outputs

**Inputs:**
- `INPUTS(0)`: Initial pool Box containing the pool's state before repayment
  - Token index 0: Pool NFT (Singleton / State NFT)
  - Token index 2: Remaining borrow tokens (capacity tracker)
  - Token index 3: Pool asset reserves
- `INPUTS(1)`: The repayment UTXO itself (`SELF`), containing:
  - Token index 0: Borrowed tokens being repaid
  - Token index 1: Repayment assets to return to pool
- Additional inputs: May include user's change or other supporting boxes

**Outputs:**
- `OUTPUTS(0)`: Final pool Box reflecting the post-repayment state
  - Token index 0: Pool NFT (must match initial)
  - Token index 2: Updated borrow token balance (decreased)
  - Token index 3: Updated pool asset reserves (increased)
  - Value: Increased by repayment amount minus transaction fee

## Key Logic

The contract enforces six core validation rules:

1. **Pool NFT Validation**: Both initial and final pool boxes must carry the correct Pool NFT token ID (`PoolNft`), ensuring only the legitimate pool is being updated.

2. **Borrow Balance Reconciliation**: Calculates the change in available borrow tokens:
   - `borrow0 = MaxBorrowTokens - initalPool.tokens(2)._2` (initial borrowed amount)
   - `borrow1 = MaxBorrowTokens - finalPool.tokens(2)._2` (final borrowed amount)
   - `deltaBorrowed == loanAmount` (reduction in borrowed amount must equal loan repaid)

3. **Asset Pool Reconciliation**: The increase in pool asset reserves (`deltaPoolAssets`) must exactly equal the repayment amount being submitted.

4. **Value Balance**: The increase in the pool's ERG value (`deltaValue`) must be at least `SELF.value - transactionFee`, accounting for the minimum transaction fee (1,000,000 nanoErgs).

5. **Token ID Matching**: The repayment asset token ID must match the pool's asset token ID (`repaymentTokens._1 == initalPool.tokens(3)._1`), ensuring the correct asset type is being repaid.

6. **Multi-Box Spend Safety**: `INPUTS(1) == SELF` ensures this specific box is at input index 1, preventing double-spend attacks where a single UTXOmight be used in multiple spending paths.

All conditions must be satisfied (AND logic) for the transaction to be valid.

## Registers Used

**Registers Not Explicitly Used in This Contract:**

This contract does not read or write R4–R9 registers. It operates entirely through:
- **Token arrays** in box token fields
- **Box value** (ERG balance)
- **INPUTS/OUTPUTS arrays** for multi-box state machine coordination

The contract relies on **Constant segregation** for:
- `transactionFee` (1,000,000 nanoErgs)
- `MaxBorrowTokens` (9,000,000,000,000,000 — likely representing max borrow capacity)
- `PoolNft` (fromBase58-encoded token ID)

## Tokens

**Pool NFT (Singleton / State NFT):**
- Token ID: `PoolNft` (from Base58: `6wu6NgonXKFYQ32mvLbwj9XGzURVB7Z4r1QEhdUmHRcD`)
- Role: Identifies the canonical pool box in a multi-box state machine
- Location: Index 0 in both input and output pool boxes
- Quantity: Typically 1 (enforces singleton pattern)

**Borrow Token Tracker:**
- Location: Index 2 in pool box
- Role: Represents remaining borrow capacity (capacity = `MaxBorrowTokens - balance`)
- Updated: Decremented when repayment occurs (borrowed amount increases in remaining tokens)

**Asset Token:**
- Location: Index 3 in pool box (reserves) and index 1 in repayment UTXO
- Role: Tracks the pool's principal asset and repaid assets
- Validation: Token IDs must match to ensure correct asset type

**Repayment Tokens:**
- Location: Index 0 in `SELF` (the repayment box)
- Role: Represents the borrowed tokens being returned/settled

## Integration Pattern

**Off-Chain Bot / Headless dApp Responsibilities:**

1. **Monitor**: Watch the pool box (`INPUTS(0)`) to identify active loans and pool state.

2. **Construct Repayment UTXO**: Create the repayment box (`INPUTS(1)` / `SELF`) containing:
   - Borrowed tokens (original loan amount)
   - Repayment assets (the pool's asset token, correct quantity)
   - Sufficient ERG value to cover transaction fees

3. **Build Multi-Box Transaction**:
   - Ensure `INPUTS(0)` = pool box (initial state)
   - Ensure `INPUTS(1)` = repayment UTXO (this contract)
   - `OUTPUTS(0)` = pool box with updated state:
     - Borrow token balance incremented (available borrow decreased)
     - Asset token balance incremented (reserves increased)
     - Value increased by repayment amount minus fee

4. **Verify Invariants**:
   - `deltaBorrowed == repaymentAmount` (1:1 repayment)
   - Pool NFT is preserved
   - All token IDs match expected values
   - Transaction fee is accounted for

5. **Submit**: Broadcast the signed transaction with necessary Sigma protocol proofs.

## Related Contracts

While this file itself is a markdown/documentation artifact, the contract likely composes with:

- **Pool Contract** (`contracts/pools/rsbtc/pool