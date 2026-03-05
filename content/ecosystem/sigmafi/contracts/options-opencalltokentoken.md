---
title: K-Singh/Sigma-Finance — OpenCallTokenToken.ergo
description: "ErgoScript contract analysis: contracts/options/OpenCallTokenToken.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/options/OpenCallTokenToken.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: OpenCallTokenToken

## Purpose

This contract manages **open call option orders** in a decentralized options protocol. It enables a seller to list a call option at a strike price with automatic matching when a buyer accepts, or allows the seller to reclaim their collateral if the order expires or remains unmatched. The contract enforces fee collection (dev + optional UI fees) during order closure.

---

## Inputs / Outputs

### Inputs
- **SELF (Input Box 0):** The order box itself, containing:
  - Seller's public key (R4)
  - Strike price in nanoErgs (R5)
  - Credit amount (collateral posted by seller, R6)
  - Expiry height (R7)
  - No native tokens (flexibility for various option types)

### Outputs (Order Matched Path)
- **OUTPUTS(0):** Option contract box (validated against constant `_optContractHash`)
  - Must contain the order's UTXO ID in R4
  - Seller PK, strike price, expiry height preserved in R4–R7
  - Buyer info in R8
  - Exactly 1 native token (the underlying asset or NFT)
  - Value: 1,000,000 nanoErgs (minimum box value)

- **OUTPUTS(1):** Credit box
  - Recipient: Seller (sellerPK)
  - Value: 1,000,000 nanoErgs
  - Token: `_tokenId` (payment currency) with amount = `credit`

- **OUTPUTS(2):** Dev fee box (conditional)
  - Recipient: `_devPK`
  - Value: 1,000,000 nanoErgs
  - Token: `_tokenId` with calculated fee amount
  - Only created if dev fee > 0

- **OUTPUTS(3):** UI fee box (conditional, only if UI fee defined)
  - Recipient: UI fee address from context variable
  - Value: 1,000,000 nanoErgs
  - Token: `_tokenId` with calculated fee amount
  - Only created if UI fee > 0

### Outputs (Refund Path)
- Any box signed by **sellerPK** (seller can reclaim funds)

---

## Key Logic

### Order Matching Validation (`orderIsClosed == true`)

The contract enforces **atomic settlement** of the order through these checks:

1. **Option Contract Box Validation:**
   - Output box 0 must be a valid option contract (blake2b256 hash matches `_optContractHash`)
   - Must preserve order state: order ID (R4), seller PK (R5), strike price (R6), expiry (R7)
   - Must have buyer info in R8 (indicates accepted order)
   - Must contain exactly 1 token (underlying asset—flexible for NFTs or different assets)
   - Minimum value: 1,000,000 nanoErgs (storage rent requirement)

2. **Credit Distribution:**
   - Seller receives their credit (collateral) back in the payment currency (`_tokenId`)
   - Amount must equal original `credit` from R6

3. **Fee Calculation & Payment:**
   - **Dev fee:** 0.45% of principal, calculated as `(450 * principal) / 100,000`
   - **UI fee:** Additional 0.45% (only if context variable 0 is defined)
   - Fees use **BigInt arithmetic** to prevent Long overflow on large positions
   - Each fee recipient receives exactly their calculated share in `_tokenId`
   - Conditional outputs prevent errors on low-value orders (fees < 1 nanounit ignored)

### Refund Path (`orderIsClosed == false`)

- Seller can unilaterally close the order and reclaim all funds
- Requires only seller's signature (SigmaProp from R4)
- Typically triggered after expiry height is reached

---

## Registers Used

| Register | Type | Purpose | R/W |
|----------|------|---------|-----|
| **R4** | `SigmaProp` | Seller's public key; used for signature validation & credit recipient | R |
| **R5** | `Long` | Strike price (nanoErgs per unit of underlying) | R |
| **R6** | `Long` | Credit amount (collateral posted by seller in payment currency) | R |
| **R7** | `Int` | Expiry height; determines when seller can refund | R |
| — | — | *No R8–R9 used in this contract* | — |

### Context Variables
- **Context Var 0:** `SigmaProp` (optional UI fee recipient address)

---

## Tokens

### Native Tokens Used

1. **`_tokenId` (Constant)**
   - **Type:** Payment currency token ID (ERG equivalent, likely a stablecoin in Sigma-Finance)
   - **Purpose:** Medium for option credit/collateral and fee payments
   - **Amount in SELF:** Not held; transferred in matching transaction
   - **Validation:** Token ID verified in all fee and credit outputs

2. **Option Underlying Asset (Token in OUTPUTS(0))**
   - **Type:** Any native token or NFT
   - **Purpose:** The asset being optioned (flexibility allows options on any Ergo token)
   - **Amount:** Flexible (not enforced by this contract)
   - **Reason:** Allows the protocol to support options on non-homogeneous assets (including NFTs with supply = 1)

### Token ID Rule Implication
- The contract references `_tokenId` as a constant segregated value, ensuring consistency across all instances of this contract type
- Underlying asset token ID is **not enforced**, allowing protocol flexibility

---

## Integration Pattern

### Off-Chain Bot / Dapp Responsibilities

1. **Order Creation:**
   - Construct SELF box with:
     - Seller's PK in R4
     - Strike price in R5
     - Credit amount (collateral) in R6
     - Expiry height in R7
   - Initial value: 1,000,000 nanoErgs (minimum)

2. **Order Matching (Closed Path):**
   - Off-chain matches buyer with seller order
   - Constructs **4 output boxes** in exact