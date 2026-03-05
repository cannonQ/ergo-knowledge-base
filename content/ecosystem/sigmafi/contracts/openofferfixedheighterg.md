---
title: K-Singh/Sigma-Finance — OpenOfferFixedHeightERG.ergo
description: "ErgoScript contract analysis: contracts/OpenOfferFixedHeightERG.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/OpenOfferFixedHeightERG.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: OpenOfferFixedHeightERG

## Purpose

This contract implements an **open lending offer** that allows a lender to post terms for a collateralized loan bond. When a borrower accepts the offer, it validates the creation of a SigmaBond UTXO with matching terms and distributes protocol fees. If unmatched, the lender can reclaim their ERG.

---

## Inputs / Outputs

### Inputs
- **SELF (OpenOfferFixedHeightERG box)**: Contains the lender's principal amount (in nanoERG) and bond terms encoded in registers R4–R8.
- **Optional context variables**: UI fee recipient address (Context extension, variable 0).

### Outputs

**When order is matched** (`orderIsClosed == true`):
1. **OUTPUTS(0) - Bond Box**: The created SigmaBond UTXO, locked under the bond contract hash (`_bondContractHash`).
2. **OUTPUTS(1) - Loan Box**: Borrower's receiving box, locked under their spending condition (from `bondBox.R5`).
3. **OUTPUTS(2) - Dev Fee Box** *(if fee > 0)*: Protocol fee to `_devPK` (0.5% of principal).
4. **OUTPUTS(3) - UI Fee Box** *(if defined and fee > 0)*: Optional UI integrator fee (0.5% of principal).

**When order is unmatched** (refund path):
- All funds return to `lenderPK`.

---

## Key Logic

### Order Closure Detection
```
orderIsClosed = blake2b256(OUTPUTS(0).propositionBytes) == _bondContractHash
```
Validates that the first output box is locked under the correct bond contract (verified via **ErgoTree hash**).

### Order Matching Validation (`orderMade`)
When matched, the contract enforces:

1. **Bond Box Integrity**:
   - `R4`: Must reference SELF's box ID (prevents bond reuse).
   - `R5`: Contains borrower's spending condition (SigmaProp).
   - `R6`: Repayment amount matches `SELF.R7`.
   - `R8`: Lender's public key recorded in bond state.
   - **Value & Tokens**: Bond collateral equals `SELF.R5` (nanoERG) and `SELF.R6` (assets).

2. **Maturity Enforcement**:
   - `bondBox.R7` must equal `maturityHeight` from SELF.R8.

3. **Loan Box Creation**:
   - Locked under borrower's proposition (from bond box `R5`).
   - Receives exact `principal` amount (SELF.value).

### Fee Calculation & Payment
- **Fee Denominator**: 100,000 (basis points).
- **Dev Fee**: 0.5% (500 basis points) → calculated as `(devFee × principal) ÷ feeDenom`.
- **UI Fee**: 0.5% *(only if `optUIFee` defined)*.
- **BigInt Arithmetic**: Prevents Long overflow on large principal amounts.
- **Fee Validation**: Each fee output's value (cast to BigInt) must match calculated fee, and proposition bytes must match fee recipient's public key.
- **Graceful Degradation**: Zero-value fees skip output validation to prevent errors on dust-value bonds.

### Refund Path
If the order is not matched (`orderIsClosed == false`), the contract authenticates with `lenderPK`, allowing the lender to recover their funds.

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Lender's public key (owner of collateral, recipient in refund). |
| **R5** | `Long` | Bond collateral in nanoERG. |
| **R6** | `Coll[(Coll[Byte], Long)]` | Collateral assets (token ID → quantity pairs). |
| **R7** | `Long` | Total repayment amount (tokens lender expects by maturity). |
| **R8** | `Int` | Bond maturity height (deadline for repayment before liquidation). |

---

## Tokens

### Native Tokens
- **Collateral Assets** (`SELF.R6`): Array of native token IDs and quantities locked in the bond as collateral.
- **Loan Tokens**: The `principal` (in nanoERG) transferred to the borrower represents the loan; repayment terms are in tokens (potentially different from collateral).

### State Token / NFT Pattern
- **No singleton NFT** in this contract, but the **bond contract** (referenced by `_bondContractHash`) likely uses a State NFT to track the bond lifecycle.
- The open offer itself is stateless; closure is determined by transaction structure.

---

## Integration Pattern

### Off-Chain Bot / Dapp Responsibilities

1. **Monitoring Open Offers**:
   - Scan the blockchain for UTXOs with `OpenOfferFixedHeightERG` proposition.
   - Index the register data (lender PK, collateral, repayment, maturity height).

2. **Matching Orders**:
   - When a borrower accepts, construct a transaction with:
     - **Input**: The open offer UTXO (SELF).
     - **Output(0)**: Bond box, locked under `_bondContractHash`, with registers:
       - R4 = SELF.id (reference to open offer).
       - R5 = borrower's spending condition.
       - R6 = repayment amount.
       - R7 = maturity height.
       - R8 = lender PK.
       - Tokens = collateral assets; value = collateral (nanoERG).
     - **Output(1)**: Loan box (borrower's address), value = principal.
     - **Output(2+)**: Fee boxes (if applicable).

3. **Fee Calculation**:
   - Compute dev fee: `(principal × 500) ÷ 100,000`.
   - Compute UI fee: `(principal × 500) ÷ 100,000` 