---
title: K-Singh/Sigma-Finance — OpenOfferFixedHeightToken.ergo
description: "ErgoScript contract analysis: contracts/OpenOfferFixedHeightToken.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/OpenOfferFixedHeightToken.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: OpenOfferFixedHeightToken

## Purpose

This contract implements an **Open Offer box** in a lending protocol (SigmaBond), allowing a lender to deposit tokens and specify collateral requirements, repayment terms, and maturity conditions. When a borrower accepts the offer, the contract validates the creation of a Bond box and distributes fees; otherwise, it allows the lender to reclaim their tokens via a refund path.

---

## Inputs / Outputs

### Inputs
- **SELF** (Open Offer Box):
  - **Value**: 1,000,000 nanoERG (minimum box value)
  - **Tokens**: Single token of type `_tokenId` representing the loan principal
  - **Registers**:
    - R4: Lender's public key (SigmaProp)
    - R5: Required collateral in nanoERG (Long)
    - R6: Collateral assets list (Coll[(Coll[Byte], Long)])
    - R7: Total repayment amount in tokens (Long)
    - R8: Maturity height (Int)

### Outputs (Order Matched Path)

| Index | Name | Purpose |
|-------|------|---------|
| 0 | **Bond Box** | Locks collateral and terms; must match `_bondContractHash` |
| 1 | **Loan Box** | Sends principal tokens to borrower; locked by borrower's PK (from Bond R5) |
| 2 | **Dev Fee Output** | (Conditional) Sends dev fee to `_devPK` if fee > 0 |
| 3 | **UI Fee Output** | (Conditional) Sends UI fee if `optUIFee` is defined and fee > 0 |

### Outputs (Refund Path)
- Single output returning tokens to `lenderPK`

---

## Key Logic

### Validation Flow

The contract enforces two mutually exclusive paths:

#### **Path 1: Order Matched (Loan Origination)**
Executed when `OUTPUTS(0)` box's script hash equals `_bondContractHash`:

1. **Bond Box Validation** (OUTPUTS(0)):
   - Must reference this offer via R4 = SELF.id
   - Must have borrower's PK defined in R5
   - Must encode total repayment in R6
   - Must lock lender's PK in R8
   - Must contain exact collateral assets and ERG value
   - Must encode maturity height in R7

2. **Loan Box Validation** (OUTPUTS(1)):
   - Script must match borrower's PK (from Bond R5)
   - Value = 1,000,000 nanoERG (minimum box value)
   - Token = `_tokenId` with amount = principal - totalFees
   - Must contain exactly 1 token type

3. **Fee Calculation & Distribution**:
   - Base dev fee: 0.5% of principal
   - Optional UI fee: 0.5% of principal (if `optUIFee` context variable defined)
   - Fees computed using BigInt to prevent overflow on large principals
   - Dev fee output (OUTPUTS(2)): 1M nanoERG + dev fee tokens → `_devPK`
   - UI fee output (OUTPUTS(3)): 1M nanoERG + UI fee tokens → UI fee address
   - Both fee outputs conditional; skipped if fee amount ≤ 0

4. **Input Constraints**:
   - SELF.tokens must contain exactly 1 token type (the principal)
   - SELF.value must equal 1,000,000 nanoERG

#### **Path 2: Refund (Cancellation)**
If OUTPUTS(0) does not match `_bondContractHash`:
- Transaction must be signed by `lenderPK`
- Allows lender to reclaim tokens without creating a bond

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Lender's public key; required to sign refund path |
| **R5** | `Long` | Required collateral in nanoERG (immutable loan term) |
| **R6** | `Coll[(Coll[Byte], Long)]` | List of (token ID, amount) tuples for collateral assets |
| **R7** | `Long` | Total repayment obligation in principal tokens |
| **R8** | `Int` | Block height at which borrower becomes subject to liquidation |

---

## Tokens

### Token Usage
- **`_tokenId`** (Contract Constant):
  - Represents the loan currency (e.g., SigmaUSD or another stablecoin)
  - Held in SELF with amount = principal (the loan size)
  - Distributed to borrower in Loan Box after fee deductions
  - Fee outputs also denominated in this token

### State Tracking
- **No State NFT**: This contract does not use a Singleton pattern; each open offer is independent
- **Collateral Assets**: Arbitrary native tokens held in Bond box, referenced by token ID byte array in R6

---

## Integration Pattern

### Off-Chain Components (Expected Interaction)

1. **Lender Bot / UI**:
   - Constructs SELF box with:
     - Principal tokens (amount = loan size)
     - Registers R4–R8 with offer terms
   - Funds with 1M nanoERG minimum
   - Submits to blockchain

2. **Borrower Bot / Matcher**:
   - Monitors open offers
   - Constructs Bond Box transaction:
     - OUTPUTS(0): New box locked by `_bondContractHash` with borrower PK in R5
     - OUTPUTS(1): Loan box sending principal tokens to borrower
     - OUTPUTS(2)–(3): Fee outputs (if applicable)
   - Reads `optUIFee` from context extension (Context variable 0)
   - Verifies fee calculations using BigInt arithmetic
   - Signs with borrower's key

3. **Verification Requirements**:
   - Off-chain code must compute expected fees before broadcasting
   - Must construct Bond box matching exact script hash (determin