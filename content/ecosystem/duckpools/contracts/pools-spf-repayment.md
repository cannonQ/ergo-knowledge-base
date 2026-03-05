---
title: duckpools/lend-protocol-contracts — repayment.md
description: "ErgoScript contract analysis: contracts/pools/spf/repayment.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/spf/repayment.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Repayment

## Purpose

This contract validates repayment transactions in a lending protocol where borrowers return borrowed tokens to a liquidity pool. It ensures the repayment amount matches the borrowed amount, pool state transitions are consistent, and the pool receives the correct assets back while accounting for transaction fees.

## Inputs / Outputs

**Inputs:**
- `INPUTS(0)` – Initial Pool Box: Contains the Pool State NFT and pool asset tokens before repayment
- `INPUTS(1)` – Repayment Box (SELF): The box being spent, containing borrowed tokens and repayment tokens
- Additional inputs may be present (not constrained by this contract)

**Outputs:**
- `OUTPUTS(0)` – Final Pool Box: The updated pool state after repayment, holding the pool's NFT and refreshed asset/borrow token counts

## Key Logic

1. **Pool Identity Verification:** Both initial and final pool boxes must hold the Pool NFT (`PoolNft`) in their first token slot to ensure the correct pool is being updated.

2. **Borrow Token Reconciliation:** The contract calculates how much was borrowed by comparing `MaxBorrowTokens - tokens(2)._2` before and after. The delta must equal the loan amount in SELF's first token (`loanAmount`).

3. **Asset Repayment Validation:** The repayment tokens in SELF must match the asset token type of the pool (`initalPool.tokens(3)._1`), and the repayment amount must equal the net increase in pool assets (`deltaPoolAssets`).

4. **Value Balance:** The ERG value increase in the final pool must be at least equal to the repayment box's ERG value minus the transaction fee (`transactionFee = 1,000,000 nanoERG`).

5. **Multi-Box Spend Safety:** The contract enforces that SELF is located at `INPUTS(1)` to prevent a single malicious box from being spent multiple times in the same transaction (same-box attack prevention).

## Registers Used

No explicit registers (R4–R9) are read or written in this contract. The validation relies entirely on:
- **Box values** (ERG amounts)
- **Token slots** (native tokens stored in each box)

The contract assumes a fixed token arrangement:
- `tokens(0)` – Pool NFT (identifier)
- `tokens(2)` – Borrow token balance
- `tokens(3)` – Pool asset tokens

## Tokens

- **Pool NFT (`PoolNft`):** A singleton State NFT hardcoded as `fromBase58("o7mKcicqmdpUNzVHAhWTAK3JsZHJzWr3mi1zPnCxyf4")`. Serves as the immutable identifier for the pool and must be present in both initial and final pool boxes.
- **Borrow Tokens (`tokens(2)`):** Tracks outstanding borrowed amount; the contract verifies the borrow balance decreases by exactly `loanAmount`.
- **Asset Tokens (`tokens(3)`):** The actual repayment asset (e.g., a stablecoin or loan currency). The contract ensures the repayment amount equals the net increase in the pool's asset holdings.
- **Loan Amount (`SELF.tokens(0)._2`):** The quantity of borrowed tokens being repaid.
- **Repayment Amount (`SELF.tokens(1)._2`):** The quantity of assets being returned.

## Integration Pattern

**Off-chain Dapp / Bot workflow:**

1. **Construct Transaction:**
   - Retrieve the current pool box state from the blockchain (to become `INPUTS(0)`).
   - Create the repayment box (SELF) with:
     - Token slot 0: borrowed token type and amount (`loanAmount`)
     - Token slot 1: asset token type and repayment amount
     - Sufficient ERG to cover the transaction fee + minimum box value
   - Construct the final pool box by:
     - Copying the pool NFT from the initial pool
     - Decreasing borrow token count by `loanAmount`
     - Increasing asset token count by `repaymentAmount`
     - Adding ERG from SELF (minus transaction fee)

2. **Verify Invariants:**
   - `loanAmount == (MaxBorrowTokens - initalPool.tokens(2)._2) - (MaxBorrowTokens - finalPool.tokens(2)._2)`
   - `repaymentAmount == finalPool.tokens(3)._2 - initalPool.tokens(3)._2`
   - `finalPool.value >= SELF.value - 1,000,000`
   - Pool NFT is present in both pool boxes
   - SELF is positioned at index 1 in INPUTS

3. **Sign & Submit:**
   - The borrower signs the transaction with their private key.
   - Transaction is submitted to the Ergo blockchain.

## Related Contracts

Based on naming conventions and structure, this contract is part of a multi-stage lending protocol:

- **Pool Contract:** Likely manages the initial and final pool box logic independently (receives the repayment box as input and validates state transitions).
- **Loan Issuance Contract:** Presumably validates the initial borrow transaction, creating the loan box that later gets spent as `SELF` in a repayment.
- **Liquidation / Default Contract:** May enforce penalties or asset seizure if repayment is not made by a deadline (not visible in this file but typical for lending protocols).

The singleton Pool NFT pattern suggests a **State Machine** design where the pool box serves as the mutable state token, transitioning between valid states across transactions.