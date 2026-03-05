---
title: duckpools/lend-protocol-contracts — proxyBorrow.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/proxy-contracts/proxyBorrow.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/proxy-contracts/proxyBorrow.md
project: duckpools-lend-protocol-contracts
---
# ProxyBorrow Contract Analysis

## Purpose

This contract acts as a **proxy intermediary** for borrowing operations in the ERG-POOL lending protocol. It validates either a **refund path** (if the borrow request is cancelled) or an **exchange path** (if the borrow is executed), ensuring collateral is locked, loan tokens are transferred to the user, and all protocol invariants are maintained.

---

## Inputs / Outputs

### Inputs
- **SELF** (this Box): The proxy borrow request box containing user parameters and request metadata
- **INPUTS(0)**: Expected to be the pool box (validated via poolNFT token presence)
- Additional inputs as needed for transaction construction

### Outputs

**Refund Path** (OUTPUTS.size < 3):
- **OUTPUTS(0)**: Refund box returning ERG to the user, with SELF.id stored in R4 for multi-box spend safety

**Exchange Path** (OUTPUTS.size ≥ 3):
- **OUTPUTS(0)**: Pool box (state updated with new interest indexes)
- **OUTPUTS(1)**: Collateral box locked under `collateralBoxScript`, holding collateral tokens and borrow tokens (NFT + amount)
- **OUTPUTS(2)**: User box with borrowed ERG amount, locked to user's public key

---

## Key Logic

### Refund Operation (OUTPUTS.size < 3)

The contract validates a **cancellation/timeout refund**:

1. **Recipient Validation**: `refundBox.propositionBytes == user` — funds return to the originating user
2. **Delta ERG Check**: `deltaErg <= minTxFee` — only transaction fees are consumed (≤1 ERG)
3. **Multi-box Safety**: `refundBox.R4 == SELF.id` — prevents output re-use in multi-box scenarios
4. **Height Lock**: `HEIGHT >= publicRefund` — refund is only possible after a deadline block height
5. **Token Preservation**: Collateral tokens are returned intact to the refund box

### Exchange Operation (OUTPUTS.size ≥ 3)

The contract validates a **successful borrow execution**:

1. **Collateral Box Integrity**:
   - Script hash matches expected `collateralBoxScript`
   - Collateral token matches request (SELF.tokens(0))
   - Borrow token ID is correct
   - Loan amount in collateral box matches user's output value

2. **Borrower & User Consistency**:
   - Collateral box borrower address matches SELF.R4 (user)
   - User threshold/penalty parameters match across boxes
   - DEX NFT and user public key align with collateral box

3. **Forced Liquidation Window**:
   - `collateralForcedLiquidation > HEIGHT + 65480 && collateralForcedLiquidation <= HEIGHT + 65520`
   - Ensures liquidation can only occur within a ~9-day window (at ~2 min blocks)

4. **User Box Creation**:
   - Locked to user's address
   - Contains exactly `requestAmount` ERG
   - R4 contains SELF.id for multi-box spend safety

5. **Pool Interaction**:
   - `INPUTS(0).tokens(0)._1 == poolNFT` — enforces pool contract validates the interest index update

### Signature Fallback

```ergoscript
operation || proveDlog(userPk)
```
If either refund or exchange fails, the transaction succeeds only if the user proves knowledge of their private key (`userPk`).

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User/borrower address (used to lock refund or identify borrower in collateral box) |
| **R5** | `Long` | `requestAmount` — ERG amount the user requests to borrow |
| **R6** | `Int` | `publicRefund` — block height after which refund becomes available |
| **R7** | `(Long, Long)` | `userThresholdPenalty` — liquidation threshold ratio and penalty parameters |
| **R8** | `Coll[Byte]` | `userDexNft` — DEX oracle NFT for price feeds (used in collateral valuation) |
| **R9** | `GroupElement` | `userPk` — user's public key (Sigma protocol commitment for signature fallback) |

---

## Tokens

1. **Collateral Token** (SELF.tokens(0)):
   - Native Ergo token or custom token ID
   - Locked in collateral box during borrow
   - Returned on refund

2. **Borrow Token** (`BorrowTokenId`):
   - Token ID: `FcHBx6x4ir4cvXQsiuwLiyBbqRctzASX7biFViG1YXtC`
   - Paired with loan amount in collateral box
   - Tracks borrowed amount and enables protocol accounting

3. **Pool NFT** (`poolNFT`):
   - Token ID: `Ahk13GiqmS1txRpk9TdJmbs1Qr6wGya8MstvhMVfNDbq`
   - Singleton identifying the pool box
   - Validates pool contract has updated interest indexes

4. **DEX Oracle NFT** (userDexNft):
   - Identifies price oracle box for collateral valuation
   - Stored in collateral box (R7) for liquidation logic

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Borrow Request Construction** (Refund Path):
   - Create proxy borrow box with borrower address (R4), requested amount (R5), and refund height (R6)
   - Sign with user's private key

2. **Borrow Execution** (Exchange Path):
   - **Fetch pool box**: Read current interest indexes via poolNFT
   - **Create collateral box**: 
     - Lock under `collateralBoxScript`
     - Populate R4–R9 with borrower details, threshold, penalty, and forced liquidation height
     