---
title: skyharbor-market/contracts — SigUSDV1.txt
description: "ErgoScript contract analysis: SigUSDV1.txt"
tags: [skyharbor-market, contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/skyharbor-market/contracts"
contract_file: SigUSDV1.txt
project: skyharbor-market-contracts
---
# SigUSD V1 Contract Analysis

## Purpose

This contract implements a **List NFT Guard Script** for an NFT marketplace, mediating the sale of NFTs with optional royalty payments to the original issuer. It enforces that when an NFT is purchased (outputs > 2), the sale price is correctly distributed among the seller, marketplace service fee, and royalty recipient; alternatively, the seller can refund the listing by providing a signature (outputs == 2).

## Inputs / Outputs

### Inputs
- **SELF**: The List NFT Guard Box, containing:
  - Native token: NFT being sold (token ID checked against issuer box)
  - Registers: price, seller address, issuer box reference, seller public key
  - Value: Minimum box value in nanoErg

### Outputs (Purchase Path: size > 2)
1. **OUTPUTS(0)**: Seller Payment Box
   - Receives seller's share of sale price (in currency tokens)
   - Locked to seller's address (SELF.R5)
   - Must include sale identifier in R4 (SELF.id) to prevent replay

2. **OUTPUTS(1)**: Service Fee Box
   - Receives marketplace fee (2% = SELF.R4 / 50, minimum 1 nanoErg)
   - Locked to hardcoded service address

3. **OUTPUTS(2)**: Royalty Box (conditional)
   - Only required if royalty percentage is non-zero
   - Receives royalty amount (sale price × royalty% / 1000)
   - Locked to original issuer's address (royaltyBox.propositionBytes)

### Outputs (Refund Path: size == 2)
- **OUTPUTS(0)** and **OUTPUTS(1)**: Seller-controlled refund (requires seller signature)

## Key Logic

### Purchase Conditions (OUTPUTS.size > 2)

1. **Fee Calculation**:
   - Service fee = max(sale price / 50, 1 nanoErg)
   - Royalty fee = max(sale price × R4[Int] / 1000, 0) if issuer defined royalty
   - Seller receives = sale price − service fee − royalty fee

2. **Royalty-Aware Path** (if royaltyBox.R4[Int] is defined):
   - All three outputs required
   - OUTPUTS(0): seller gets at least their share in currency tokens
   - OUTPUTS(1): service gets exact fee amount
   - OUTPUTS(2): royalty recipient gets exact royalty (or skipped if royalty == 0)
   - Currency token ID verified across all outputs
   - Seller address, service address, and issuer address constraints

3. **Non-Royalty Path** (if royaltyBox.R4[Int] undefined):
   - Only two outputs required
   - OUTPUTS(0): seller receives sale price − service fee
   - OUTPUTS(1): service receives fee
   - Royalty box reference still validated as NFT issuer

4. **Replay Protection**:
   - OUTPUTS(0).R4 must equal SELF.id (unique listing identifier)
   - Prevents same-price attack by tying output to specific listing box

5. **Issuer Validation**:
   - royaltyBox.id == SELF.tokens(0)._1
   - Forces royalty payments to the NFT issuer identified in this box's state

### Refund Conditions (OUTPUTS.size == 2)

- Seller can reclaim listing by providing Schnorr signature via proveDlog(SELF.R7[GroupElement])
- SELF.R7 must contain seller's public key
- No fee or royalty deductions applied

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | Sale price in nanoErg (denominated in currency token) |
| **R5** | `Coll[Byte]` | Seller's receive address (propositionBytes) |
| **R6** | `Box` | Issuer box reference (contains royalty % in its R4[Int]) |
| **R7** | `GroupElement` | Seller's public key for refund signature (Schnorr proof) |
| **OUTPUTS(0).R4** | `Coll[Byte]` | Sale identifier (must equal SELF.id to prevent replay) |

---

## Tokens

### Primary Token (Native)
- **Token ID**: `SELF.tokens(0)._1` (the NFT being listed)
- **Validation**: Linked to issuer box via royalty rules
- **Quantity**: Typically 1 (NFT assumption, though contract allows any quantity)

### Currency Token
- **Token ID**: `GYATox71P9XAERmzoDdTGELa62f5ALyjxJLRSfJfKsh` (hardcoded)
- **Purpose**: Payment settlement in all three output paths
- **Validation**: Must match across OUTPUTS(0), OUTPUTS(1), OUTPUTS(2)

### State Machine
- **State NFT**: SELF.tokens(0) (the listed NFT) acts as singleton during listing
- **Lifecycle**: Listing created → Purchase consumes this box and distributes currency → Refund reclaims for seller

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Listing Creation**:
   - Construct box with SELF.R4 = sale price
   - Set SELF.R5 = seller address (serialized propositionBytes)
   - Fetch issuer box, set SELF.R6 = issuer box
   - Set SELF.R7 = seller's public key (for future refund)
   - Mint with NFT token as SELF.tokens(0)
   - Sign with seller's key to create listing

2. **Purchase Transaction Construction**:
   - Verify `OUTPUTS.size > 2`
   - Check royalty percentage from issuer box's R4[Int]
   - Calculate fees:
     - serviceGets = max(price / 50, 1)
     - royaltyGets = max(price × royalty / 1000, 0) if royalty != 0
     - seller