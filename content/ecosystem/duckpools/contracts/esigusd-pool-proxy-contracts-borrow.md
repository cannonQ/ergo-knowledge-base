---
title: duckpools/lend-protocol-contracts — borrow.md
description: "ErgoScript contract analysis: contracts/pools/eSIGUSD-POOL/proxy-contracts/borrow.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/eSIGUSD-POOL/proxy-contracts/borrow.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: eSIGUSD-POOL Borrow Proxy

## Purpose

This contract serves as a **proxy authorization layer** for borrowing operations in the eSIGUSD lending protocol. It validates that either a user-initiated refund occurs (if the borrow request expires) or a legitimate loan exchange executes with proper collateral setup, ensuring the borrower's public key authorizes all state transitions.

## Inputs / Outputs

### Inputs
- **SELF (INPUTS(0))**: Proxy box containing request metadata and user credentials
- **INPUTS(0)** (implicit in validation): Must contain pool NFT (checked via `validInterestIndex`)
- **Data Inputs**: None explicitly required

### Outputs

**Refund Path** (OUTPUTS.size < 3):
- **OUTPUTS(0)**: Refund box returning ERG to the user, with SELF.id stored in R4 (multi-box spend safety)

**Exchange Path** (OUTPUTS.size >= 3):
- **OUTPUTS(0)**: Pool box (updated state; validated by separate pool contract)
- **OUTPUTS(1)**: Collateral box (newly created; stores borrowed tokens and user data)
- **OUTPUTS(2)**: User box (newly created; receives loan tokens)

## Key Logic

### Core Validation Flow

The contract enforces an **atomic state machine** with two mutually exclusive paths:

#### **Path 1: Refund (Timeout Scenario)**
Executes when `HEIGHT >= publicRefund` (deadline passed) and `OUTPUTS.size < 3`:

1. **Refund Recipient Validation**: `refundBox.propositionBytes == user`
   - Ensures refund goes to the original requester
2. **Cost Accounting**: `deltaErg = SELF.value - refundBox.value ≤ minTxFee`
   - Validates transaction fees don't exceed 1 ERG (minimum transaction fee)
3. **Multi-Box Spend Safety**: `refundBox.R4 == SELF.id`
   - Prevents double-spending by requiring the refund box to reference this proxy's ID
4. **Deadline Check**: `HEIGHT >= publicRefund`
   - Ensures refund only possible after expiration window

#### **Path 2: Loan Exchange (Happy Path)**
Executes when `OUTPUTS.size >= 3`:

**Collateral Box Validation:**
- **Script Integrity**: `blake2b256(collateralBox.propositionBytes) == collateralBoxScript`
  - Ensures collateral is locked in the correct liquidation contract
- **ERG Collateral**: `collateral == SELF.value - minBoxValue - minTxFee`
  - All ERG except minimum box value (1 ERG) and fees is moved to collateral
- **Borrow Token Linkage**: 
  - `collateralBorrowTokens._1 == BorrowTokenId`
  - `collateralBorrowTokens._2 == loanAmount` (loan size)
- **User Metadata**: Collateral box stores borrower identity, threshold penalties, DEX NFT, and user's public key
- **Forced Liquidation Window**: `collateralForcedLiquidation ∈ (HEIGHT + 65480, HEIGHT + 65520]`
  - Enforces a ~14-day liquidation grace period (in 1024-block intervals; ~13 days)

**Loan Consistency:**
- `userBox.tokens(0)._1 == PoolNativeCurrency` (receives pool's native token)
- `userBox.tokens(0)._2 == requestAmount` (matches requested amount from R5)
- `loanAmount == userBox.tokens(0)._2` (collateral and user box agree on loan size)

**User Box Validation:**
- **Script**: `userBox.propositionBytes == user`
  - Loan goes to the borrower's address
- **Multi-Box Spend Safety**: `userBox.R4 == SELF.id`
  - Links user box to this proxy transaction

**Cross-Box Consistency:**
- `recordedBorrower == user` (collateral matches proxy's user)
- `userThresholdPenalty == thresholdPenalty` (penalty terms agreed upon)
- `userDexNft == dexNft` (DEX NFT consistency)
- `userPk == collateralUserPk` (user's Sigma public key matches)
- Pool NFT present in inputs (enforces pool contract participation)

### Authorization

Final condition: **`operation || proveDlog(userPk)`**

- If either refund or exchange validations pass, the transaction is authorized
- **OR** the transaction is signed by the user's private key (Sigma proof of discrete log)
- This provides a fallback for user-initiated transactions (e.g., emergency cancellations)

---

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** | `Coll[Byte]` | User's address (identity for refund/collateral recipient) | Read |
| **R5** | `Long` | Requested loan amount in PoolNativeCurrency tokens | Read |
| **R6** | `Int` | Deadline height for refund (`publicRefund`) | Read |
| **R7** | `(Long, Long)` | Liquidation threshold & penalty parameters (`userThresholdPenalty`) | Read |
| **R8** | `Coll[Byte]` | DEX NFT ID (for AMM integration in liquidation) | Read |
| **R9** | `GroupElement` | User's Sigma public key (for signature fallback authorization) | Read |

---

## Tokens

### Pool NFT (Singleton State Token)
- **Token ID**: `8A5R3bhY16TCJXPF8cCNL5bgdBg1vHZyM3f8W1PqAvdM`
- **Role**: State machine identifier; presence in inputs validates pool contract execution
- **Location**: INPUTS(0) (implied)

### Borrow Token (Loan Denomination)
- **Token ID**: `2z3Fmiezj1EzsaL