---
title: K-Singh/Sigma-Finance — OpenOrderOnCloseERG.ergo
description: "ErgoScript contract analysis: contracts/OpenOrderOnCloseERG.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/OpenOrderOnCloseERG.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: OpenOrderOnCloseERG

## Purpose

This contract manages **collateralized bond order creation** in the Sigma-Finance lending protocol. Borrowers lock ERG and/or tokens as collateral while specifying bond terms (principal, repayment amount, maturity). The contract either finalizes the bond when a lender accepts the order, or allows the borrower to reclaim collateral if the order expires unclosed.

---

## Inputs / Outputs

### Input
- **SELF (OpenOrderOnCloseERG box):**
  - Contains borrower's collateral (ERG value + native tokens)
  - Carries loan parameters in registers R4–R7
  - Acts as the order specification

### Outputs (on order closure)

| Index | Box | Purpose |
|-------|-----|---------|
| **0** | Bond Box | State machine advancement; tracks active bond with lender details |
| **1** | Loan Box | Sends principal amount to borrower's address |
| **2** | Dev Fee Output | Protocol fee (0.5% of principal) to `_devPK` |
| **3** | UI Fee Output | Optional frontend fee (0.4% of principal) if `optUIFee` defined |

### Output (on refund)
- Single box returning collateral to `borrowerPK`

---

## Key Logic

### Execution Paths

#### **Path A: Order Matched (Closure)**
Contract validates if `OUTPUTS(0)` contains the Bond contract ErgoTree:

1. **Bond Box Integrity:**
   - `R4` = SELF's box ID (links order to bond)
   - `R5` = borrower's public key (preserved)
   - `R6` = repayment amount (state invariant)
   - `R8` = must contain lender's signature (defined but not checked here)
   - All collateral tokens and ERG flow unchanged into bond box

2. **Maturity Validation:**
   - Maturity length ≥ 30 blocks (minimum bond duration)
   - Confirms maturity height in bond box ≈ `HEIGHT + maturityLength`
   - Tolerates 0–8 block variance for mempool confirmation delays
   - **Prevents** disappearing transactions by enforcing tight height constraints

3. **Loan Disbursement:**
   - `OUTPUTS(1)` sends exactly `principal` nanoERG to borrower
   - Uses borrower's public key for immediate access

4. **Fee Distribution:**
   - **Dev fee:** `(500 / 100000) × principal` (0.5%)
   - **UI fee (optional):** `(400 / 100000) × principal` (0.4%)
   - Uses `BigInt` arithmetic to prevent `Long` overflow on large principals
   - Skips fee outputs if calculated amount ≤ 0 (dust prevention)
   - Signature required: `sigmaProp(orderMade && feesPaid)`

#### **Path B: Refund (No Match)**
- Order not closed within validity window
- Collateral returned to `borrowerPK` without fees
- Signature requirement: borrower's Sigma protocol proof

---

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R4** | `SigmaProp` | Borrower's public key; controls refund & loan receipt | Read from SELF |
| **R5** | `Long` | Bond principal (nanoERG to disburse); fee calculation basis | Read from SELF |
| **R6** | `Long` | Total repayment required from lender before maturity | Read from SELF; copied to bond box |
| **R7** | `Int` | Bond maturity length in blocks (relative to closure height) | Read from SELF |
| **R8** (Bond Box) | `SigmaProp` | Lender's signature placeholder; must be defined post-closure | Checked existence in OUTPUTS(0) |

---

## Tokens

### Native Token Handling
- **Collateral tokens:** Entire `SELF.tokens` collection flows into bond box unchanged
- **No token-specific authentication:**
  - Tokens are value, not state markers
  - Any token composition acceptable as collateral
  - Could be XRP, portfolio assets, or protocol tokens

### Pseudo-Token State (Implicit)
- **Bond box itself acts as State NFT:** Linked via `SELF.id` in `R4`, creating singleton pattern
- **Lender identity encoded in `R8`:** Acts as proof of match (not validated by this contract)

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Order Creation:**
   - Construct SELF box with:
     - Borrower's public key in R4
     - Principal & repayment amounts in R5, R6
     - Maturity length in R7
     - Collateral assets as box value + tokens

2. **Order Matching (Lender Bot):**
   - Scan mempool for OpenOrderOnCloseERG boxes
   - Construct Bond box (OUTPUTS(0)) with:
     - ErgoTree matching `_bondContractHash` (verified via blake2b256)
     - SELF.id → R4
     - borrowerPK → R5
     - repayment → R6
     - lender's SigmaProp → R8
     - Maturity height = `HEIGHT + maturityLength`
   - Construct Loan box (OUTPUTS(1)) with principal ERG
   - Construct fee outputs (OUTPUTS(2) and optionally OUTPUTS(3))

3. **Context Extension:**
   - Optional: `getVar[SigmaProp](0)` to inject UI fee recipient
   - If undefined, only dev fee applies

4. **Height Constraint Awareness:**
   - Ensure transaction is signed and submitted within ±8 block window
   - Maturity length must be encoded at order creation time (immutable)

---

## Related Contracts

### **Bond Contract** (Referenced as `_bondContractHash`)
- Receives collateral & bond terms in OUTPUTS(0)
- Expected to:
  - Track repayment conditions
  - Enforce liquidation if repayment not received by maturity
  - Release