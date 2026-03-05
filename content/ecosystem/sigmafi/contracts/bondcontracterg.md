---
title: K-Singh/Sigma-Finance — BondContractERG.ergo
description: "ErgoScript contract analysis: contracts/BondContractERG.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/BondContractERG.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: BondContractERG

## Purpose

This contract manages collateralized bond agreements on Ergo, holding borrower collateral (ERG and native tokens) until either the loan is repaid before maturity or the lender liquidates the position post-maturity. It enforces a two-path state machine: early repayment returns collateral to the borrower, while maturity allows the lender to seize all collateral as compensation.

## Inputs / Outputs

### Inputs
- **SELF Box**: The bond contract Box containing:
  - ERG collateral (`value`)
  - Token collateral (`tokens`)
  - Bond metadata in R4–R8

### Outputs

**Path 1: Pre-Maturity Repayment** (HEIGHT < maturityHeight)
- **OUTPUT(0) - Repayment Box**: Pays `repayment` nanoERGs to lender, includes SELF.id reference in R4
- **OUTPUT(1) - Return Box**: Returns all collateral (ERG + tokens) to borrower

**Path 2: Post-Maturity Liquidation** (HEIGHT ≥ maturityHeight)
- **OUTPUT(0) - Liquidation Box**: Transfers entire collateral (ERG + tokens) to lender, includes SELF.id reference in R4

## Key Logic

### Validation Tree

```
IF HEIGHT >= maturityHeight THEN
  ✓ Lender can liquidate collateral
  Require:
    - OUTPUT(0) sends to lender (propositionBytes == lenderPK.propBytes)
    - OUTPUT(0) contains all collateral tokens (tokens == collateralAssets)
    - OUTPUT(0) contains all collateral ERG (value == collateralERG)
    - OUTPUT(0).R4 references this bond box (SELF.id)
    
ELSE (HEIGHT < maturityHeight)
  ✓ Only borrower can repay and reclaim collateral
  Require:
    - OUTPUT(0) sends repayment amount to lender (value == repayment)
    - OUTPUT(0).R4 references this bond box (SELF.id)
    - OUTPUT(1) returns collateral to borrower (propositionBytes == borrowerPK.propBytes)
    - OUTPUT(1) includes all tokens
    - OUTPUT(1) includes all ERG collateral
    - Transaction signed by borrower (borrowerPK)
```

**Critical Invariant**: Collateral can only exit via one of these two legitimate paths; no other spending is valid.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **Order ID**: Box ID of originating OpenOrder contract (enables loan traceability) |
| **R5** | `SigmaProp` | **Borrower Public Key**: Σ-protocol assertion enabling borrower signature verification for repayment |
| **R6** | `Long` | **Repayment Amount**: Total nanoERGs borrower must pay to reclaim collateral |
| **R7** | `Int` | **Maturity Height**: Block height at which lender can liquidate; compared against blockchain HEIGHT |
| **R8** | `SigmaProp` | **Lender Public Key**: Σ-protocol assertion for lender-only liquidation post-maturity |

**R0–R3**: Not used (implicitly available but unused in this contract).

## Tokens

### Native Token Handling

- **Collateral Tokens**: Arbitrary native tokens held in `SELF.tokens` collection
  - Must be preserved exactly in output Box (no partial transfers, no token swaps)
  - Enables multi-asset collateral (not just ERG)
  - **Token ID Rule**: No new tokens introduced; only original collateral tokens moved

### No NFT-based State Machine

Unlike singleton-based contracts, this uses **Height-based state transitions** rather than a State NFT. The bond's lifecycle is determined by blockchain HEIGHT, not token possession.

## Integration Pattern

### Off-Chain Bot / dApp Responsibilities

#### **Repayment Path** (before maturity)
```
1. Read bond Box from blockchain (filter by contract address)
2. Extract maturityHeight from R7, compare to current HEIGHT
3. Construct transaction:
   a. Input: Bond Box (SELF)
   b. Output(0): Send repayment nanoERGs to lender.propBytes, include R4 = SELF.id
   c. Output(1): Send collateral to borrower.propBytes
4. Sign with borrower's private key (satisfies borrowerPK Sigma protocol)
5. Submit and monitor inclusion
```

#### **Liquidation Path** (after maturity)
```
1. Monitor HEIGHT >= R7 (maturityHeight)
2. Construct transaction:
   a. Input: Bond Box (SELF)
   b. Output(0): Send all collateral to lender.propBytes, include R4 = SELF.id
3. Sign with lender's private key
4. Submit and monitor
```

### Context Extension Requirements

- **No Context Extensions** are explicitly used (no CONTEXT.dataInputs, no Merkle proof extensions)
- **HEIGHT check** is implicit in `HEIGHT >= maturityHeight` (system variable, always available)

### Data Inputs / Reference Inputs

- None explicitly declared or required
- Borrower identity validated via Sigma protocol signature, not external proof

## Related Contracts

### Likely Companion Contracts (from code comments)

1. **OpenOrder Contract** (referenced as `R4: Box id of originating order`)
   - Initiates bond creation
   - Likely holds loan terms before they move to BondContractERG
   - Composable via R4 cross-reference for order history

2. **Lender / Borrower Scripts** (implicit)
   - Scripts guarding lender's repayment/liquidation funds
   - Scripts guarding borrower's collateral reclamation

### Composition Pattern

```
OpenOrder Box 
    ↓ (creates)
BondContractERG Box (holds collateral, enforces terms)
    ↓ (split into two paths)
    ├─→ RepaymentBox (to Lender) + ReturnBox (to Borrower)  