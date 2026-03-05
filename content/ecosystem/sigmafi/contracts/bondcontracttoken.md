---
title: K-Singh/Sigma-Finance — BondContractToken.ergo
description: "ErgoScript contract analysis: contracts/BondContractToken.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/BondContractToken.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: BondContractToken

## Purpose

This contract implements a **collateralized debt instrument (bond)** in the SigmaUSD/K-Singh ecosystem, where a borrower locks collateral (ERG + native tokens) to borrow SIGUSD. The contract enforces two mutually-exclusive spending paths: early repayment by the borrower before maturity, or liquidation by the lender after maturity.

## Inputs / Outputs

### Input Box (SELF)
- **Proposition**: This contract's ErgoTree
- **Value**: Collateral in ERG (nanoERGs)
- **Tokens**: Native token collateral assets
- **Registers**:
  - `R4`: Original order box ID (Coll[Byte])
  - `R5`: Borrower's public key (SigmaProp)
  - `R6`: Total repayment amount in SIGUSD tokens (Long, raw/undecimaled)
  - `R7`: Bond maturity height (Int)
  - `R8`: Lender's public key (SigmaProp)

### Output Boxes

#### Path 1: Early Repayment (`HEIGHT < maturityHeight`)
- **OUTPUTS(0)** – RepaymentBox:
  - Locked to lender's address
  - Contains exactly 1 SIGUSD token with amount = `repayment`
  - Minimum value: 1 million nanoERGs (dust limit)
  - `R4` contains SELF's box ID (audit trail)
  
- **OUTPUTS(1)** – ReturnBox:
  - Locked to borrower's address
  - Returns all collateral (ERG + tokens) to borrower
  - `R4` contains SELF's box ID

#### Path 2: Liquidation (`HEIGHT >= maturityHeight`)
- **OUTPUTS(0)** – LiquidationBox:
  - Locked to lender's address
  - Contains all original collateral (ERG + tokens)
  - `R4` contains SELF's box ID

## Key Logic

The contract implements a **time-gated state machine** with two branches:

### **Before Maturity** (`HEIGHT < maturityHeight`)
The borrower may spend this box to repay the loan. Validation requires:
1. **RepaymentBox (OUTPUTS(0))** must:
   - Be locked to the lender (`lenderPK`)
   - Contain exactly the repayment amount in SIGUSD (`_tokenId` token)
   - Have minimum value of 1M nanoERGs
   - Reference SELF in R4

2. **ReturnBox (OUTPUTS(1))** must:
   - Be locked to the borrower (`borrowerPK`)
   - Contain all original collateral (ERG + tokens) intact
   - Reference SELF in R4

3. **Spending Authority**: Requires both `borrowerPK` signature AND satisfaction of the above conditions (`sigmaProp(repaid) && borrowerPK`)

### **At or After Maturity** (`HEIGHT >= maturityHeight`)
The lender may liquidate the collateral. Validation requires:
1. **LiquidationBox (OUTPUTS(0))** must:
   - Be locked to the lender (`lenderPK`)
   - Contain all original collateral (ERG + tokens) unchanged
   - Reference SELF in R4

2. **Spending Authority**: Requires only lender signature (implicit via `sigmaProp(liquidated)`)

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** | `Coll[Byte]` | Original order box ID (audit/linking) | Read |
| **R5** | `SigmaProp` | Borrower's public key for re-locking | Read |
| **R6** | `Long` | Repayment amount (raw SIGUSD tokens) | Read |
| **R7** | `Int` | Maturity block height (state trigger) | Read |
| **R8** | `SigmaProp` | Lender's public key for liquidation | Read |

All registers are **read-only** in this contract; the contract validates output register assignments but does not mutate them.

## Tokens

### **Collateral Tokens**
- `SELF.tokens`: Arbitrary native tokens locked as collateral
- Stored in `collateralAssets` variable
- Must be returned intact to borrower (early repayment) or transferred to lender (liquidation)

### **Repayment Token** (Early Repayment Path Only)
- **Token ID**: `_tokenId` (external constant, likely SigmaUSD/SIGUSD)
- **Amount**: `repayment` (stored in R6)
- **Purpose**: Borrower must pay this token amount to the lender to recover collateral
- **Verification**: `repaymentBox.tokens(0)._1 == _tokenId && repaymentBox.tokens(0)._2 == repayment`

### **Collateral ERG**
- `collateralERG = SELF.value`: Primary collateral in ERG
- Locked until maturity or repayment

## Integration Pattern

### Off-Chain Responsibilities

**1. Order Creation (Off-chain Bot)**
- Construct a transaction that:
  - Locks collateral (ERG + tokens) into this contract
  - Initializes R4 with order box ID (self-referential or linked order)
  - Sets R5, R6, R7, R8 with correct borrower/lender/amount/maturity data
  - Ensures minimum box value ≥ 1M nanoERGs + storage rent

**2. Early Repayment (Borrower)**
- Monitor blockchain until `HEIGHT < maturityHeight`
- Construct repayment transaction:
  - Spend the bond box (sign with borrower key)
  - Provide SIGUSD tokens (amount = R6) to output 0
  - Return collateral to output 1
  - Verify lender receives exactly repayment amount
  - Verify output script addresses are correct

**3. Liquidation (Lender)**
- Monitor blockchain until `HEIGHT >= maturityHeight`
- Construct liquidation transaction: