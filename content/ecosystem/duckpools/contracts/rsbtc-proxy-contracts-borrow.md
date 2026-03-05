---
title: duckpools/lend-protocol-contracts — borrow.md
description: "ErgoScript contract analysis: contracts/pools/rsbtc/proxy-contracts/borrow.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsbtc/proxy-contracts/borrow.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Borrow Proxy (rsbtc/borrow)

## Purpose

This contract serves as a **proxy intermediary** for borrowing operations in the duckpools lending protocol. It validates two distinct operations: (1) a **refund path** that allows the user to reclaim collateral after a timeout, or (2) an **exchange path** that facilitates the atomic creation of a collateralized loan by validifying the correct construction of collateral and user boxes with proper loan terms.

## Inputs / Outputs

### Inputs
- **SELF** (spending box): The proxy contract box itself, containing loan request parameters in registers R4–R9
- **INPUTS(0)** (data input, implicit): A pool box authenticated by the `poolNFT` token (enforces interest index validity)

### Outputs

**Refund Path (OUTPUTS.size < 3):**
- **OUTPUTS(0)**: Refund box sent back to the user with reduced ERG value (delta ≤ minTxFee)

**Exchange Path (OUTPUTS.size ≥ 3):**
- **OUTPUTS(0)**: Pool box (state updated by pool contract)
- **OUTPUTS(1)**: Collateral box (locks the user's collateral with loan parameters)
- **OUTPUTS(2)**: User box (delivers loan tokens to borrower)

## Key Logic

### Refund Branch (Timeout Path)
The contract permits refund **if and only if** all conditions hold:
1. **Recipient validity**: Refund box recipient equals the original `user` (R4)
2. **Self-reference**: Refund box R4 contains `SELF.id` (prevents orphaned refunds)
3. **Fee bounded**: ERG delta between SELF and refund ≤ `minTxFee` (1 ERG)
4. **Timeout expired**: Current `HEIGHT ≥ publicRefund` (R6, absolute block height)

### Exchange Branch (Loan Execution)
The contract permits the borrow operation **if and only if** all conditions hold:

**Collateral Box Validation:**
- Script hash matches expected `collateralBoxScript` (blake2b256)
- ERG value = `SELF.value - minBoxValue - minTxFee` (no value loss)
- First token is `BorrowTokenId` with amount = loan amount
- Stored borrower address = `user`
- Threshold/penalty tuple matches user's declared values
- DEX NFT identifier matches
- User's public key matches stored key
- Forced liquidation block window: `HEIGHT + 65480 < collateralForcedLiquidation ≤ HEIGHT + 65520` (~454 day window)

**Loan Amount Validation:**
- Collateral box borrow token amount = user box native currency token amount
- User box token ID = `PoolNativeCurrency`
- User box token amount = requested `requestAmount` (R5)

**User Box Validation:**
- Script equals `user` (borrower controls output)
- Loan tokens received = `requestAmount`
- R4 contains `SELF.id` (multi-box spend safety)

**Pool Integrity:**
- INPUTS(0) carries `poolNFT` (prevents pool state manipulation)

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R4** | `Coll[Byte]` | SELF | Borrower's address (script bytes) |
| **R5** | `Long` | SELF | Requested loan amount (tokens) |
| **R6** | `Int` | SELF | Public refund deadline (absolute HEIGHT) |
| **R7** | `(Long, Long)` | SELF | Liquidation threshold & penalty pair |
| **R8** | `Coll[Byte]` | SELF | DEX NFT identifier (for liquidation routing) |
| **R9** | `GroupElement` | SELF | Borrower's public key (Sigma protocol) |

**Output Collateral Box Registers:**
- **R4**: Borrower address (echoed from SELF.R4)
- **R5**: `(Int, Int)` — index pair (likely interest/update indices)
- **R6**: `(Long, Long)` — threshold & penalty (echoed from SELF.R7)
- **R7**: DEX NFT (echoed from SELF.R8)
- **R8**: Borrower's public key (echoed from SELF.R9)
- **R9**: `(Long, Long)` — forced liquidation parameters, first element = block height

**Output User Box Registers:**
- **R4**: `SELF.id` (multi-box spend reference)

## Tokens

### Authentication Tokens
- **`poolNFT`** (ID: `6wu6NgonXKFYQ32mvLbwj9XGzURVB7Z4r1QEhdUmHRcD`)
  - Singleton NFT identifying the pool state box
  - Checked in INPUTS(0) to ensure pool contract validates the operation

### Loan & Collateral Tokens
- **`BorrowTokenId`** (ID: `A7MbiXQLNJvhAU2K9EbwD3Z3KdXkhv2Ltf9AfvnESsmM`)
  - Token ID minted by the pool representing borrowed amount
  - Locked in collateral box as debt record

- **`PoolNativeCurrency`** (ID: `9EUtfvw33g6Zdasq31vJY8XmPkcr2NSx9fjjm6jdEwi7`)
  - Loan asset delivered to user box
  - Amount must equal `requestAmount`

### DEX NFT
- **`userDexNft`** (R8, arbitrary bytes)
  - Identifier for liquidation routing (likely points to a specific Dex pair or liquidation contract)
  - Ensures collateral is liquidated through the correct DEX

## Integration Pattern

### Off-Chain Bot / Headless dApp Construction

1. **Borrow Request Phase:**
   - User creates proxy box with registers R4–R9 populated
   - Off-