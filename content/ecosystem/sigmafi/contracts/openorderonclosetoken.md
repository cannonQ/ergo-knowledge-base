---
title: K-Singh/Sigma-Finance — OpenOrderOnCloseToken.ergo
description: "ErgoScript contract analysis: contracts/OpenOrderOnCloseToken.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/OpenOrderOnCloseToken.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: OpenOrderOnCloseToken

## Purpose

This contract manages collateralized bond orders in the Sigma-Finance lending protocol. When a borrower deposits ERG and/or tokens with specified bond terms (principal, repayment amount, maturity), the contract either closes the order by creating a Bond box and distributing protocol fees, or allows the borrower to reclaim their collateral if the order remains unmatched.

## Inputs / Outputs

### Inputs
- **SELF (Open Order Box)**: 
  - **Value**: ERG collateral (`totalERG`)
  - **Tokens**: Token collateral (`totalAssets`)
  - **R4**: Borrower's `SigmaProp` (public key)
  - **R5**: Bond principal amount (Long, in raw SIGUSD)
  - **R6**: Total repayment amount (Long, in raw SIGUSD)
  - **R7**: Bond maturity height (Int)

### Outputs (Order Closed Path)

1. **OUTPUTS(0) - Bond Box**:
   - **Value**: Original ERG collateral
   - **Tokens**: Original token collateral
   - **R4**: Open order box ID (transaction reference)
   - **R5**: Borrower's `SigmaProp`
   - **R6**: Repayment amount
   - **R7**: Maturity height
   - **R8**: Lender's `SigmaProp` (must be defined)

2. **OUTPUTS(1) - Loan Box**:
   - **Value**: 1,000,000 nanoERG (minimum box value)
   - **Tokens**: Single token with ID `_tokenId`, quantity = `principal`
   - **Recipient**: Borrower (locked to `borrowerPK`)

3. **OUTPUTS(2) - Dev Fee Output** (conditional):
   - **Value**: 1,000,000 nanoERG
   - **Tokens**: Dev fee (0.5% of principal)
   - **Recipient**: `_devPK`

4. **OUTPUTS(3) - UI Fee Output** (optional, if `optUIFee` is defined):
   - **Value**: 1,000,000 nanoERG
   - **Tokens**: UI fee (0.4% of principal)
   - **Recipient**: Caller-specified UI address

### Outputs (Refund Path)
- Single output locked to `borrowerPK`, returning original collateral and tokens

## Key Logic

The contract implements a **state machine pattern** with two execution branches:

### Order Closed Path (`orderIsClosed == true`)
Succeeds if ALL conditions are met:

1. **Bond Box Validation**:
   - Output box (0) must be locked to `_bondContractHash` (the Bond contract)
   - Bond box R4 must reference the current open order (`SELF.id`)
   - Bond box R5 must match the borrower's `SigmaProp`
   - Bond box R6 must match the specified repayment amount
   - Bond box R8 must be defined (lender's signature)
   - All collateral (tokens + ERG) must transfer to bond box unchanged

2. **Maturity Validation**:
   - Bond duration must be ≥ 30 blocks
   - Maturity height deviation: `(HEIGHT + maturityLength) - bondBox.R7[Int] ∈ [0, 8]`
   - Allows 8-block confirmation window to prevent mempool transaction loss

3. **Loan Distribution**:
   - Borrower receives `principal` amount of `_tokenId` in a separate box
   - Box locked to borrower, with minimum ERG value (1,000,000 nanoERG)

4. **Fee Distribution**:
   - **Dev Fee**: 0.5% of principal (500 basis points ÷ 100,000)
   - **UI Fee**: 0.4% of principal (400 basis points), only if `optUIFee` context variable is set
   - Fees calculated using `BigInt` to prevent overflow on large principals
   - Fee outputs include minimum ERG value; fees ≤ 0 are skipped (graceful degradation)

### Refund Path
- If order is not closed, borrower can spend the box with their signature
- Returns all collateral unchanged

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R4** | `SigmaProp` | Borrower's public key / signing proposition | Read from SELF |
| **R5** | `Long` | Bond principal (raw tokens to be issued) | Read from SELF |
| **R6** | `Long` | Total repayment obligation | Read from SELF; validated in output |
| **R7** | `Int` | Bond maturity height | Read from SELF; validated against output |
| **R8** | `SigmaProp` | Lender's signature (defined in Bond output) | Checked as defined in OUTPUTS(0) |

## Tokens

1. **`_tokenId` (Constant)**:
   - The bond currency token (likely SigmaUSD or similar stablecoin)
   - Used for principal distribution to borrower
   - Used for fee payments to dev and UI
   - Principal amount = `OUTPUTS(1).tokens(0)._2`

2. **Collateral Tokens**:
   - Arbitrary tokens in `SELF.tokens` pass through to Bond box
   - May include native Ergo tokens or other NFTs
   - Serve as additional collateral backing the bond

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Order Matching**:
   - Monitor open order boxes
   - Identify lender willing to match terms
   - Construct Bond box with lender's `SigmaProp` in R8

2. **Transaction Construction**:
   ```
   Transaction inputs:  [Open Order Box]
   Transaction outputs: [Bond Box, Loan Box, Dev Fee Box, (UI Fee Box?)]
   Context extension:   getVar[SigmaProp](0) = optional UI fee address
   ```

3. **Validation Before Submission**:
   - Verify `bondBox