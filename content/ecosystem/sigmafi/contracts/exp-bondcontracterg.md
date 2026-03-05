---
title: K-Singh/Sigma-Finance — EXP_BondContractERG.ergo
description: "ErgoScript contract analysis: contracts/EXP_BondContractERG.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/EXP_BondContractERG.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: EXP_BondContractERG

## Purpose

This experimental contract implements a collateralized bond/loan mechanism on Ergo where a borrower posts collateral (ERG and/or tokens) to secure a loan from a lender. The bond enforces repayment by the maturity height or enables liquidation of collateral, with support for customizable liquidation logic via hashed script validation.

## Inputs / Outputs

### Inputs
- **SELF**: The active bond Box containing:
  - Collateral in native ERG (`SELF.value`)
  - Collateral tokens (`SELF.tokens`)
  - Borrower and lender public keys (SigmaProps)
  - Repayment amount and maturity height
  - Hash of optional liquidation script

### Outputs
- **OUTPUTS(0) - Repayment/Liquidation Box**: Receives collateral; must be locked to lender
  - In repayment path: receives `repayment` nanoERGs + returns collateral tokens
  - In liquidation path: receives full collateral (ERG + all tokens)
  
- **OUTPUTS(1) - Return Box** (repayment only): Collateral returned to borrower after successful repayment
  - Locked to borrower (`borrowerPK`)
  - Contains original collateral tokens and ERG

## Key Logic

The contract validates two mutually exclusive paths:

### **Liquidation Path**
Triggered when bond maturity is reached or liquidation conditions are met:
```
(sigmaProp(liquidated) && liquidationConditions)
```

**Conditions:**
1. **Liquidated state** must be satisfied:
   - OUTPUTS(0) must be locked to lender (`lenderPK.propBytes`)
   - OUTPUTS(0) receives ALL collateral (tokens + ERG)
   - OUTPUTS(0).R4 contains SELF.id (bond reference)

2. **Liquidation gate** (either/or):
   - **Option A (default)**: `HEIGHT >= maturityHeight` (time-based liquidation)
   - **Option B (custom)**: If Context extension variable 0 provides a SigmaProp:
     - Its `propBytes` must hash to `hashedLiqScript`
     - The SigmaProp itself must validate (can embed arbitrary Sigma protocol logic)

### **Repayment Path**
Triggered before maturity when borrower repays:
```
(sigmaProp(repaid) && borrowerPK)
```

**Conditions:**
1. Current height < maturity height
2. **Repayment Box (OUTPUTS(0))**:
   - Locked to lender
   - Contains exactly `repayment` nanoERGs
   - R4 = SELF.id (bond reference)
3. **Return Box (OUTPUTS(1))**:
   - Locked to borrower
   - Contains all original collateral tokens + ERG
4. Must be signed by borrower (`borrowerPK`)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Order box ID from originating order contract (used as cross-reference) |
| **R5** | `SigmaProp` | Borrower's public key; controls collateral in repayment, signs repayment tx |
| **R6** | `Long` | Repayment amount in nanoERGs (must be < total collateral for profit margin) |
| **R7** | `Int` | Bond maturity height; determines time-based liquidation eligibility |
| **R8** | `SigmaProp` | Lender's public key; receives collateral/repayment |
| **R9** | `Coll[Byte]` | `blake2b256` hash of custom liquidation script propBytes; enables pluggable liquidation logic without storing full script on-chain |

## Tokens

### Authentication & State
- **Collateral tokens**: Arbitrary native tokens held in `SELF.tokens`; transferred to lender on liquidation or returned to borrower on repayment
- **No state NFT**: Contract uses `SELF.id` (box ID) as singleton identifier to prevent reuse across transactions

### Value
- **Collateral ERG**: `SELF.value` (must exceed Ergo's minimum box value ~0.001 ERG)
- **Repayment amount**: Stored in R6; can be less than collateral (interest accrues to lender via collateral surplus)

## Integration Pattern

### Off-Chain Construction Requirements

1. **Loan Initiation**:
   - Off-chain code calls OpenOrder contract to create bond parameters
   - Creates Bond Box with R4-R9 populated, locking collateral
   - Sets R9 = `blake2b256(liquidationScriptPropBytes)` if custom liquidation enabled

2. **Repayment Transaction**:
   - Off-chain bot/dApp constructs Tx with:
     - INPUTS: Bond Box (SELF)
     - OUTPUTS(0): Repayment Box (lender locked, `repayment` ERGs, R4=bond ID)
     - OUTPUTS(1): Return Box (borrower locked, collateral)
     - Borrower signature (to satisfy `borrowerPK`)
   - Verifies `HEIGHT < maturityHeight`

3. **Liquidation Transaction**:
   - **Default path**: Once `HEIGHT >= maturityHeight`, anyone can liquidate
     - No signatures required (time-locked)
     - Construct outputs as `liquidated` specifies
   
   - **Custom path**: If using custom liquidation:
     - Include Context extension variable 0: liquidation SigmaProp
     - Off-chain code verifies: `blake2b256(liquidationSigmaProp.propBytes) == R9`
     - Liquidation script may enforce conditions (e.g., price oracle checks, governance votes)

### Verification Steps
- **Collateral integrity**: Ensure OUTPUTS preserve all tokens and ERG from SELF
- **Box reference**: Verify R4 in outputs matches SELF.id
- **Height checks**: Client verifies HEIGHT in context
- **Signature validation**: Ergo node verifies SigmaProof for `