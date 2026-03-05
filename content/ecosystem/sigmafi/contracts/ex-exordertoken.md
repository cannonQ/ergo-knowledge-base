---
title: K-Singh/Sigma-Finance — ExOrderToken.ergo
description: "ErgoScript contract analysis: contracts/ex/ExOrderToken.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/ex/ExOrderToken.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: ExOrderToken.ergo

## Purpose

This contract implements an **Open Exchange Order** for peer-to-peer token swaps, enabling sellers to post assets (ERG and native tokens) for sale at a fixed price denominated in SigmaUSD or another bond currency. When a buyer matches the order, the contract validates the atomic swap, distributes the sale proceeds to the seller, and collects configurable dev and UI fees.

---

## Inputs / Outputs

### Inputs
- **SELF (Input Box under ExOrderToken contract)**
  - Contains seller's assets: ERG (`SELF.value`) and native tokens (`SELF.tokens`)
  - Stores seller's public key (`R4`) and sale price in raw tokens (`R5`)

### Outputs

| Index | Purpose | Validation |
|-------|---------|-----------|
| **0** | Exchange Box | Must contain original seller assets; acts as order fulfillment receipt |
| **1** | Seller Payment Box | Receives payment in `_tokenId` at `salePrice` amount; minimum 1 ERG |
| **2** | Dev Fee Box *(conditional)* | Receives dev fee (0.5% of principal) if fee > 0 |
| **3** | UI Fee Box *(conditional)* | Receives UI fee (0.4% of principal) if `optUIFee` is defined and fee > 0 |

---

## Key Logic

### Two Execution Paths:

#### **Path 1: Order Closed (Order Matched)**
Triggered when `exBox.propositionBytes != sellerPK.propBytes` (output box is NOT locked to seller).

**Validations:**
1. **Exchange Box Integrity** – Output(0) must preserve:
   - Original box ID in R4 (creates audit trail)
   - All tokens (`totalAssets`)
   - All ERG value (`totalERG`)

2. **Seller Receives Payment** – Output(1) enforces:
   - Locked to seller's PK
   - Exactly `salePrice` tokens of `_tokenId`
   - Minimum 1 ERG (satisfies storage rent + transaction fee)
   - No additional tokens

3. **Fee Distribution** – Calculates and validates:
   - **Dev Fee**: 0.5% of principal (500/100000)
   - **UI Fee** *(optional)*: 0.4% of principal if `optUIFee` context variable provided
   - Each fee output gets 1 ERG minimum + calculated token amount
   - Graceful handling: zero fees bypass validation (prevents dust errors)

#### **Path 2: Refund (Order Not Matched)**
When `exBox.propositionBytes == sellerPK.propBytes` (output box IS locked to seller).

**Validation:** Returns `sellerPK` Sigma proposition – seller can spend refund box with their signature only.

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Seller's public key; used to lock refund path and validate seller payment box |
| **R5** | `Long` | Sale price in raw `_tokenId` tokens; amount buyer must send to seller |

---

## Tokens

### Primary Token: `_tokenId` (Bond Currency)
- **Role**: Medium of exchange / settlement currency
- **Usage**:
  - Seller receives `salePrice` amount in `_tokenId`
  - Dev and UI fees denominated in `_tokenId`
  - Likely SigmaUSD or Dexy stablecoin in practice

### Secondary Assets: `SELF.tokens`
- **Role**: Seller's offerings (arbitrary native tokens or NFTs)
- **Validation**: Preserved as-is through exchange box; exact amounts verified

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities:

1. **Order Posting**
   - Construct SELF box with seller assets and metadata:
     ```
     R4 = seller.sigmaProp
     R5 = salePrice (raw tokens, e.g., 1000000L for 1M SigmaUSD microunits)
     tokens = [seller's assets]
     value = [ERG amount]
     ```

2. **Order Matching**
   - Listen for SELF boxes under this contract (off-chain indexing)
   - When buyer agrees, construct transaction with:
     - INPUTS: SELF box
     - OUTPUT(0): Exchange box (preserves SELF.id in R4, assets in tokens/value)
     - OUTPUT(1): Seller payment (seller's PK, `salePrice` of `_tokenId`, 1+ ERG)
     - OUTPUT(2-3): Fee boxes (if fees > 0 and optUIFee defined)
     - Buyer provides `_tokenId` tokens via separate input

3. **Context Extension**
   - Optional: Pass `optUIFee` via context variable index 0 if UI fee applies
   - Format: `Coll(0 -> SigmaProp.encode(uiFeeAddress))`

4. **Fee Calculation (Off-Chain)**
   - Compute dev fee: `(salePrice * 500) / 100000`
   - Compute UI fee: `(salePrice * 400) / 100000` *(if applicable)*
   - Ensure output boxes have >= 1 ERG minimum value

5. **Refund Path**
   - If order expires/unmatches, spend SELF with seller's signature alone
   - Returns all assets to seller without fee deduction

---

## Related Contracts

### Likely Composition:
- **Bond/Stablecoin Contract** (`_tokenId` issuer)
  - Validates SigmaUSD or Dexy stablecoin transactions
  - Fee outputs likely verified downstream

- **Liquidity Pool / Swapper Contract**
  - May use ExOrderToken as a limit-order mechanism feeding into AMM
  - Atomic swap with LP to aggregate liquidity

- **Fee Collector Contract**
  - Dev and UI fee outputs may lock to secondary contract for withdrawal/governance

### Design Pattern: **State Machine with Atomic Swaps**
- ExOrderToken acts as **order state box** (singleton-like role)