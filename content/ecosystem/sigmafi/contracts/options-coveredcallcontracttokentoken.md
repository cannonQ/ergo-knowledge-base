---
title: K-Singh/Sigma-Finance — CoveredCallContractTokenToken.ergo
description: "ErgoScript contract analysis: contracts/options/CoveredCallContractTokenToken.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/options/CoveredCallContractTokenToken.ergo
project: k-singh-sigma-finance
---
# ErgoScript Contract Analysis: Covered Call (Token-Token)
**Source:** `contracts/options/CoveredCallContractTokenToken.ergo`

---

## Purpose

This contract implements a **covered call option** where the underlying asset is a native token and the strike price is denominated in another native token. The seller deposits tokens as collateral; upon expiry, the seller reclaims them, or the buyer exercises the option by paying the strike price in the payment token to acquire the underlying tokens.

---

## Inputs / Outputs

### Inputs
- **SELF (Option Contract Box):**
  - Contains the underlying token(s) as native tokens in `SELF.tokens`
  - Holds contract terms in registers R5–R8
  - Must have minimum box value (1 ERG implied by 1000000L nanoERG checks)

### Outputs

**On Expiry (Expired Path):**
- **Output 0 (Payment Box → Seller):**
  - Receives `underlyingAssets` (original tokens from SELF)
  - Locked to `sellerPK`
  - Contains reference to SELF via `R4[Coll[Byte]] = SELF.id`
  - Value: 1,000,000 nanoERG (≈ 0.001 ERG)

**On Exercise (Executed Path):**
- **Output 0 (Payment Box → Seller):**
  - Receives strike price amount of `_tokenId` tokens
  - Locked to `sellerPK`
  - Contains reference to SELF via `R4[Coll[Byte]] = SELF.id`
  - Value: 1,000,000 nanoERG
  
- **Output 1 (Return Box → Buyer):**
  - Receives `underlyingAssets` (the underlying tokens)
  - Locked to `buyerPK`
  - Value: 1,000,000 nanoERG

---

## Key Logic

The contract enforces **mutually exclusive execution paths** via OR logic:

### Path 1: Expiration (Seller Reclamation)
```
IF (HEIGHT >= expiryHeight) THEN
  - Verify Output(0) goes to sellerPK
  - Verify Output(0) contains original underlyingAssets
  - Verify Output(0) has minimum box value (1,000,000 nanoERG)
  - Verify Output(0).R4 references this contract (SELF.id)
```
**Purpose:** Allows seller to reclaim collateral if buyer does not exercise before expiry height.

### Path 2: Exercise (Buyer Acquires Underlying)
```
IF (HEIGHT < expiryHeight) THEN
  - Verify Output(0) (payment) goes to sellerPK
  - Verify Output(0) contains exactly strikePrice amount of _tokenId
  - Verify Output(0) has exactly 1 token (the payment token)
  - Verify Output(0).R4 references this contract
  - Verify Output(1) (return) goes to buyerPK
  - Verify Output(1) contains original underlyingAssets
  - Verify Output(1) has minimum box value
```
**Purpose:** Buyer pays strike price to acquire underlying tokens; seller receives payment immediately.

### Invariants
- **One-to-one binding:** Only two outcomes possible; contract consumes atomically.
- **Height enforcement:** Expiry creates a hard temporal boundary; no early/late execution mixing.
- **Asset identity:** Underlying tokens must move unchanged; payment token strictly validated by ID.
- **Box value:** Both paths enforce minimum 1 ERG per box (storage rent compliance).

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R5** | `SigmaProp` | **Seller's Public Key** – locks seller's payment/collateral outputs |
| **R6** | `Long` | **Strike Price** – amount of `_tokenId` buyer must pay to exercise |
| **R7** | `Int` | **Expiry Height** – block height after which option expires; seller can reclaim |
| **R8** | `SigmaProp` | **Buyer's Public Key** – locks buyer's output on exercise path |

**R4 (Implicit):**  
Output boxes use `R4[Coll[Byte]]` to store `SELF.id` for audit/reference traceability.

---

## Tokens

### Underlying Asset
- **Token ID:** Implicit in `SELF.tokens` (passed via transaction inputs)
- **Role:** The asset the buyer wants to acquire
- **Quantity:** Held in SELF; transferred intact to buyer (or back to seller on expiry)
- **Type:** Native token (ERC-20 equivalent on Ergo)

### Payment Token
- **Token ID:** `_tokenId` (external constant, must be supplied off-chain)
- **Role:** Currency for strike price payment
- **Quantity:** Must equal `strikePrice` in Output(0) on exercise
- **Type:** Native token; buyer sources this from their own wallet

### Authentication Tokens
- None explicit; contract uses **Sigma protocol signatures** (`SigmaProp`) on sellerPK and buyerPK for authentication.

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Initialization (Creation of Option Contract Box):**
   - Construct SELF box with:
     - `R5` ← seller's public key (as `SigmaProp`)
     - `R6` ← strike price (Long)
     - `R7` ← expiry height (Int)
     - `R8` ← buyer's public key (as `SigmaProp`)
     - `tokens` ← underlying asset(s) with quantities
     - `value` ← ≥ 1,000,000 nanoERG
   - Sign with seller's private key
   - Submit to blockchain

2. **Exercise Transaction (Buyer Path):**
   - **Verify preconditions:**
     - `HEIGHT < R7` (option not expired)
     - Buyer has `strikePrice` amount of `_tokenId` in wallet
   - **Construct outputs:**