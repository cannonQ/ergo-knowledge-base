---
title: K-Singh/Sigma-Finance — OpenOrderFixedHeightToken.ergo
description: "ErgoScript contract analysis: contracts/OpenOrderFixedHeightToken.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/OpenOrderFixedHeightToken.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: OpenOrderFixedHeightToken

## Purpose

This contract implements an **Open Order box** in a lending protocol (SigmaFinance/K-Singh), where borrowers collateralize ERG and/or tokens to request a bond issuance. When a lender accepts the order, the contract validates the creation of a corresponding bond box, loan disbursement box, and fee distribution boxes, then atomically executes the matched order or allows the borrower to refund their collateral.

## Inputs / Outputs

### Inputs
- **SELF (OpenOrderFixedHeightToken box)**
  - Contains borrower's collateral (ERG value + native tokens)
  - R4: Borrower's SigmaProp (public key)
  - R5: Bond principal amount (raw SIGUSD tokens, no decimals)
  - R6: Total repayment amount (raw SIGUSD tokens)
  - R7: Bond maturity height (Int)

### Outputs

**Matched Order Path:**
- **Output(0) – Bond Box**: Singleton state NFT tracking the active bond
  - R4: SELF.id (reference to this open order)
  - R5: Borrower's SigmaProp
  - R6: Repayment amount
  - R7: Maturity height
  - R8: Lender's SigmaProp (must be defined)
  - Tokens & ERG: Pass-through from SELF

- **Output(1) – Loan Box**: Disbursement to borrower
  - Value: 1000000 nanoERG (minimum box value)
  - Tokens: Exactly `principal` amount of `_tokenId`
  - Recipient: Borrower's PK

- **Output(2) – Dev Fee Box** (if dev fee > 0):
  - Value: 1000000 nanoERG
  - Tokens: Dev fee amount (0.5% of principal)
  - Recipient: `_devPK`

- **Output(3) – UI Fee Box** (if optUIFee defined and > 0):
  - Value: 1000000 nanoERG
  - Tokens: UI fee amount (0.4% of principal)
  - Recipient: UI fee address from context variable

**Refund Path:**
- Entire SELF box returned to borrower (controlled by borrowerPK signature)

## Key Logic

### Order Matching Validation (Primary Path)

1. **Bond Box Verification**: Output(0) must be a valid bond contract
   - Validates ErgoTree hash equals `_bondContractHash`
   - Bond box references this open order via R4 (SELF.id)
   - Bond box preserves borrower identity (R5), repayment terms (R6), and maturity (R7)
   - Bond box R8 must contain lender's SigmaProp (proof lender committed)
   - All collateral tokens and ERG pass through unchanged

2. **Loan Disbursement**: Output(1) distributes principal tokens to borrower
   - Exactly `principal` amount of bond token (`_tokenId`)
   - Minimum box value (1000000 nanoERG) to borrower's address
   - No extraneous tokens

3. **Fee Distribution**: Calculates and validates percentage-based fees
   - **Dev fee**: 0.5% of principal (500 / 100000)
   - **UI fee** (conditional): Additional 0.4% if UI fee address provided via context variable (0)
   - Fees calculated as `(feePercentage * principal) / 100000` using BigInt to prevent overflow
   - Each fee output receives exactly its calculated amount + minimum box value
   - Dev output at Output(2), UI output at Output(3)

4. **Safe Fee Handling**: Prevents script failure on low-value bonds
   - Fees that round to ≤ 0 are skipped (no validation required)
   - If UI fee undefined, UI fee check passes vacuously

### Refund Path (Secondary Path)

- No matching order detected (Output(0) is not a bond contract box)
- Requires only borrower's signature → returns all collateral unchanged
- Allows non-matched orders to be cancelled without loss

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R4** | `SigmaProp` | SELF | Borrower's public key; controls refund path |
| **R5** | `Long` | SELF | Bond principal (raw token amount, no decimals); basis for fee calculation |
| **R6** | `Long` | SELF | Total repayment obligation; passed to bond box |
| **R7** | `Int` | SELF | Bond maturity height (block height); passed to bond box |
| **R4** | `Coll[Byte]` | Output(0) (Bond Box) | Reference to SELF.id (open order ID) |
| **R5** | `SigmaProp` | Output(0) (Bond Box) | Borrower identity (must match SELF.R4) |
| **R6** | `Long` | Output(0) (Bond Box) | Repayment amount (must match SELF.R6) |
| **R7** | `Int` | Output(0) (Bond Box) | Maturity height (must match SELF.R7) |
| **R8** | `SigmaProp` | Output(0) (Bond Box) | Lender's public key (must exist for matched order) |

## Tokens

### State Machine / Singleton Pattern
- **Open Order Box**: Not explicitly a singleton NFT in this contract, but the ID (`SELF.id`) is unique per transaction and acts as a reference token (State NFT analogue)
- The ID is embedded in the bond box (Output(0) R4) to link the lifecycle

### Bond Currency Token
- **`_tokenId`** (constant): Native token ID representing the bond currency (e.g., SigmaUSD)
  - Tracked in SELF collateral and passed to bond box
  - Disbursed to borrower in Output(1)
  - Distributed as fees in Output(2) and Output(3)

### Principal & Fee Tracking
-