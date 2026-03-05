---
title: skyharbor-market/contracts — V1_ErgEditsAndOffersV1.md
description: "ErgoScript contract analysis: V1_ErgEditsAndOffersV1.md"
tags: [skyharbor-market, contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/skyharbor-market/contracts"
contract_file: V1_ErgEditsAndOffersV1.md
project: skyharbor-market-contracts
---
# ErgoScript Contract Analysis: Erg Edits V1 with Offers

## Purpose

This contract implements an NFT marketplace listing box that enforces payment distribution during sales while protecting against replay attacks. It allows NFT sellers to list items for sale with optional royalty payouts to the original issuer, or to refund the listing by proving ownership via signature.

## Inputs / Outputs

### Inputs
- **SELF (INPUTS(0))**: The listing box containing the NFT, sale price, seller address, royalty box reference, and seller's public key
- **Data Input (implicit)**: The royalty box (referenced via `SELF.R6`) is read to determine royalty percentage

### Outputs
- **OUTPUTS(0)**: Seller receive box — must contain seller's proceeds (after fees and royalties)
- **OUTPUTS(1)**: Service fee box — receives 2% of sale price (salePrice / 50)
- **OUTPUTS(2)** *(conditional)*: Royalty box — receives royalty payout if royalty percentage is defined and non-zero
- **OUTPUTS(3+)** *(conditional)*: Additional outputs are permitted if offers contract is not the spender

## Key Logic

The contract enforces two distinct execution paths:

### Purchase Path (Normal Sale)
**Triggered when:** `OUTPUTS.size > 3` AND `INPUTS(0)` is NOT signed by the offers contract

**Validations:**
1. **Sale Price Distribution** — Total funds must equal:
   - Service fee: `salePrice / 50` (2%)
   - Royalty payout *(if applicable)*: `(salePrice × royaltyPercentage) / 1000`
   - Seller proceeds: `salePrice - serviceFee - royaltyFee`

2. **Box Value Enforcement** — Each output box must have at least the minimum required value
3. **Seller Address Validation** — OUTPUTS(0) proposition must match `SELF.R5`
4. **Replay Attack Prevention** — OUTPUTS(0).R4 must equal `SELF.id` (box ID)
5. **Service Fee Address** — OUTPUTS(1) must send to hardcoded service address: `1sw5t6iJRxzSjNGvSRw8kcaTADxEG52wGMVgSjdXPLMbhvUM`
6. **Royalty Conditions**:
   - If `royaltyPercentage` is defined and `0 < royaltyPercentage < 900`: OUTPUTS(2) must receive at least `royaltyReceives` to the issuer box address
   - If undefined or out of range: royalty is waived (conditional passes)
   - Issuer box ID must match `SELF.tokens(0)._1` (the stored NFT/token ID)

### Refund Path (Seller Withdrawal)
**Triggered when:** `OUTPUTS.size ≤ 3` OR `INPUTS(0)` is signed by the offers contract

**Validation:**
- Proves ownership via Schnorr signature: `proveDlog(SELF.R7)`
- Seller must provide the signature corresponding to the public key stored in R7

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | Sale price in nanoErg (1 ERG = 10⁹ nanoErgs) |
| **R5** | `Coll[Byte]` | Seller's receive address (proposition bytes) |
| **R6** | `Box` | Royalty issuer box (used to read royalty percentage in R4 of that box) |
| **R7** | `GroupElement` | Seller's public key (for Schnorr signature verification on refund) |
| **OUTPUTS(0).R4** | `Coll[Byte]` | Sale identifier (must equal `SELF.id` to prevent replay) |

## Tokens

- **`SELF.tokens(0)._1`**: Token ID of the NFT being sold
  - Used as a Singleton / State NFT identifier
  - Its ID must match the royalty issuer box ID to enforce correct royalty routing
  - This acts as an **invariant** preventing token substitution attacks

## Integration Pattern

### Off-Chain Construction Requirements

1. **Listing Creation**:
   - Pack sale price into R4 as `Long`
   - Pack seller address into R5 as `Coll[Byte]` (via `.propositionBytes`)
   - Reference the royalty issuer box in R6
   - Include seller's public key in R7 (via `GroupElement`)
   - Attach the NFT as a native token with `SELF.tokens(0)`

2. **Purchase Transaction**:
   - Must have `OUTPUTS.size > 3` (or be from offers contract)
   - Construct three mandatory outputs:
     - **Output 0**: Seller box with value ≥ `sellerReceives`, proposition matching R5, R4 = `SELF.id`
     - **Output 1**: Service box with value ≥ `salePrice / 50`, proposition = hardcoded service address
     - **Output 2** *(if royalty applies)*: Royalty box with value ≥ `royaltyReceives`, proposition matching royalty issuer
   - Off-chain bot must:
     - Read `SELF.R4` to get sale price
     - Read `SELF.R6` to fetch royalty box and check `R4[Int]` for percentage
     - Calculate distribution amounts accounting for 2% service fee
     - Verify seller address from R5 before constructing output
     - Use `SELF.id` as the unique identifier in OUTPUTS(0).R4 to prevent same-price replay attacks

3. **Refund Transaction**:
   - Construct transaction with `OUTPUTS.size ≤ 3`
   - Provide Schnorr signature (`proveDlog`) matching the public key in R7
   - Off-chain must retrieve seller's private key (or obtain signature) to authorize

### Offers Contract Integration
- If `INPUTS(0)` is signed by the offers contract (checked via `blake2b256(INPUTS(0).propos