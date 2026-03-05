---
title: K-Singh/Sigma-Finance — OpenOrderFixedHeightERG.ergo
description: "ErgoScript contract analysis: contracts/OpenOrderFixedHeightERG.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/OpenOrderFixedHeightERG.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: OpenOrderFixedHeightERG

## Purpose

This contract implements an **Open Order** mechanism for collateralized lending bonds (SigmaBonds) in the Sigma-Finance protocol. A borrower deposits ERG and/or tokens as collateral, specifying loan terms (principal, repayment amount, maturity height) via registers. The contract either closes the order when a lender accepts it and a Bond contract is created, or refunds the collateral to the borrower if the order expires or is cancelled.

---

## Inputs / Outputs

### Inputs
- **SELF (Open Order Box)**
  - Contains borrower's collateral (ERG + native tokens)
  - Stores loan terms in R4–R7
  - Must satisfy the contract's locking script

### Outputs

**If order is closed (matched by a lender):**
1. **OUTPUTS(0) – Bond Box**
   - Locks collateral under Bond contract
   - Tracks repayment obligation and maturity

2. **OUTPUTS(1) – Loan Box**
   - Sends principal (minus fees) to borrower
   - Locked to borrower's public key

3. **OUTPUTS(2) – Dev Fee Box** (if dev fee > 0)
   - Sends fee to `_devPK`
   - Amount: 0.5% of principal

4. **OUTPUTS(3) – UI Fee Box** (if UI fee defined and > 0)
   - Sends fee to optional UI intermediary
   - Amount: 0.4% of principal

**If order is refunded (not matched):**
- Collateral returned to `borrowerPK` (via refund path)

---

## Key Logic

### Order Closure Path (if `orderIsClosed == true`)

The contract validates the following atomic conditions:

1. **Bond Contract Verification**
   - `OUTPUTS(0)` must be locked under the Bond contract (hash match with `_bondContractHash`)
   - This prevents unauthorized substitution of the bond-tracking UTXO

2. **Bond Box Integrity**
   - `R4`: OpenOrder box ID (tracks collateral source)
   - `R5`: Borrower's public key (preserved for repayment verification)
   - `R6`: Repayment amount (borrower's obligation)
   - `R7`: Maturity height (liquidation deadline)
   - `R8`: Must be defined (lender's public key, set by Bond contract)
   - Collateral (tokens & ERG) passed through unchanged

3. **Principal Distribution**
   - Loan box receives `principal - totalFees` in ERG
   - Guarantees borrower receives net loan amount immediately

4. **Fee Extraction**
   - **Dev Fee**: `0.5% × principal` → `_devPK`
   - **UI Fee** (optional): `0.4% × principal` → `optUIFee` (from context variable 0)
   - Fees calculated using **BigInt** to prevent Long overflow on large principals
   - Fee outputs only validated if amount > 0 (graceful handling of dust values)

### Refund Path (if `orderIsClosed == false`)

- Returns collateral directly to `borrowerPK`
- No fees charged
- Allows borrower to cancel or withdraw unmatched orders

---

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R4** | `SigmaProp` | Borrower-provided | Borrower's public key (controls refund; verified by Bond) |
| **R5** | `Long` | Borrower-provided | Principal loan amount (nanoERG); fee basis |
| **R6** | `Long` | Borrower-provided | Total repayment obligation (nanoERG); copied to Bond box |
| **R7** | `Int` | Borrower-provided | Bond maturity height; liquidation deadline |
| **R8** | `SigmaProp` (Bond Box) | Set by Bond contract | Lender's public key; validates bond ownership |

---

## Tokens

### Token Handling
- **`SELF.tokens`** (Coll[TokenID → Amount])
  - Borrower can deposit any native tokens as additional collateral
  - Passed through unchanged to Bond box (`bondBox.tokens == totalAssets`)
  - No filtering or token-specific validation in this contract

### Fee Mechanism
- Fees are **ERG-only** (no token fees)
- Denominator: `100,000` (5 significant figures)
  - Dev fee: `500` → **0.5%**
  - UI fee: `400` → **0.4%**

### State/Authentication
- No State NFT or singleton token used in this contract
- Bond contract (downstream) likely uses State NFT to track collateral state

---

## Integration Pattern

### Off-Chain Requirements (for order closure)

The off-chain bot/dApp must:

1. **Construct Bond Box**
   - Compute Blake2b256 hash of Bond contract's ErgoTree
   - Verify hash matches `_bondContractHash` constant
   - Populate R4–R8 with correct values

2. **Calculate Fees**
   - Dev fee: `(500 × principal) / 100,000` (BigInt arithmetic)
   - UI fee (if applicable): `(400 × principal) / 100,000`
   - Total fees subtracted from principal

3. **Build Transaction Outputs in Correct Order**
   - OUTPUTS(0): Bond box
   - OUTPUTS(1): Loan box (principal - fees, to borrowerPK)
   - OUTPUTS(2): Dev fee box (if fee > 0)
   - OUTPUTS(3): UI fee box (if UI fee defined and > 0)

4. **Inject Context Variables**
   - **Context Variable 0** (optional): UI fee recipient's `SigmaProp`
   - If undefined, only dev fee extracted

5. **Transaction Signing**
   - Spend SELF (OpenOrder box)
   - Provide valid Sigma proof for all fee recipient addresses and borrower

### Invariants Maintained
- **Collateral Conservation**: `SELF.tokens + SELF.value == bondBox.tokens + bond