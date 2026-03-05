---
title: duckpools/lend-protocol-contracts — borrow.md
description: "ErgoScript contract analysis: contracts/pools/RSN-POOL/proxy-contracts/borrow.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/RSN-POOL/proxy-contracts/borrow.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: RSN-POOL Borrow Proxy

## Purpose

This contract acts as a **proxy/intermediary** for borrowing operations in the RSN lending pool protocol. It validates either a **refund operation** (if the borrow request is cancelled) or an **exchange operation** (if the borrow is accepted), ensuring all parties receive correct amounts and the collateral box is properly initialized with loan terms.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Pool box (must contain the `poolNFT` singleton token to enforce interest index tracking)
- **SELF**: The proxy request box, containing borrower info, requested loan amount, and user credentials in registers

### Outputs

**Refund Path** (OUTPUTS.size < 3):
- **OUTPUTS(0)**: Refund box sent back to the user (contains excess ERG after fees)

**Exchange Path** (OUTPUTS.size ≥ 3):
- **OUTPUTS(0)**: Updated pool box
- **OUTPUTS(1)**: Collateral box (newly created, holds user's collateral + loan terms)
- **OUTPUTS(2)**: User box (receives loaned tokens)

## Key Logic

The contract enforces **two mutually exclusive operations**:

### Refund Path (Cancellation)
Triggered when `OUTPUTS.size < 3`:
1. **Valid recipient**: Refund box must be locked to the user's address (`user` from R4)
2. **Minimal fee extraction**: The ERG difference between SELF and refund box ≤ `minTxFee`
3. **Safety reference**: Refund box must reference SELF.id in R4 (prevents reuse/confusion)
4. **Timeout check**: Current height must exceed `publicRefund` (deadline set in R6)

### Exchange Path (Borrow Acceptance)
Triggered when `OUTPUTS.size ≥ 3`:

**Collateral Box Validation:**
- Script hash matches expected `collateralBoxScript` (enforces multi-contract composition)
- ERG value = SELF.value − minBoxValue − minTxFee (all user's collateral transferred)
- First token is the Borrow token with amount = loan amount
- All user credentials copied to collateral box (borrower, threshold/penalty, DEX NFT, public key)
- Forced liquidation height is within acceptable window: `HEIGHT + 65480 ≤ forcedLiquidation ≤ HEIGHT + 65520` (~45 days in Ergo blocks)

**Loan Validation:**
- Loan amount in collateral box matches user's requested amount (R5)
- Loan tokens are the pool's native currency (PoolNativeCurrency)
- Interest index enforced by pool contract (poolNFT present in INPUTS(0))

**User Box Validation:**
- Locked to user's address (propositionBytes = user from R4)
- Contains correct loan amount in tokens
- References SELF.id in R4 (multi-box safety)

**Cross-box consistency:**
- User's borrower identity matches collateral box
- Threshold/penalty terms match
- DEX NFT matches
- User public key matches

### Authorization

Either path succeeds if validated **OR** if the user provides a valid Schnorr signature proving knowledge of the private key corresponding to `userPk` (R9).

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User's address (borrower identity) |
| **R5** | `Long` | Requested loan amount |
| **R6** | `Int` | Public refund deadline (block height) |
| **R7** | `(Long, Long)` | User's threshold and penalty parameters |
| **R8** | `Coll[Byte]` | User's DEX NFT (for liquidation routing) |
| **R9** | `GroupElement` | User's public key (Schnorr verification) |

## Tokens

| Token ID | Purpose |
|----------|---------|
| **poolNFT** | Singleton NFT in pool box; enforces interest index tracking and pool state validity |
| **BorrowTokenId** | Issued by pool; represents the loan obligation; transferred to collateral box |
| **PoolNativeCurrency** | Pool's native stablecoin/token; loaned to user in OUTPUTS(2) |

## Integration Pattern

### Off-chain Bot / Headless dApp Responsibilities

1. **Monitoring**: Listen for borrow requests locked by this proxy contract
2. **Collateral Box Construction**: 
   - Derive the collateral box script from `collateralBoxScript` constant
   - Initialize with user's collateral amount, borrow tokens, and loan terms from R4–R8
   - Calculate forced liquidation height: `currentHeight + 65500` (middle of acceptable window)
3. **Pool State Update**: 
   - Retrieve current pool box (with poolNFT)
   - Adjust pool reserves and interest indexes
4. **Transaction Assembly**:
   - Input: SELF (proxy) + pool box
   - Outputs: updated pool box, collateral box, user box
   - Verify all register values match SELF's registers exactly
5. **Signing**: 
   - Construct tx to satisfy the `proveDlog(userPk)` fallback OR ensure all validation conditions pass
   - User signs via context extension (Sigma protocol)

### Refund Path Trigger
Off-chain bot monitors `HEIGHT >= publicRefund`; at deadline, constructs a simple 1-output refund tx returning ERG to user (minus fees).

## Related Contracts

1. **Collateral Box Contract** (`collateralBoxScript`):
   - Implements liquidation logic, interest accrual, and borrower withdrawal
   - Referenced by hash; its script must validate loan state and forced liquidation parameters
   - Initialized by this proxy with borrower credentials and liquidation deadline

2. **Pool Contract**:
   - Holds the `poolNFT` singleton
   - Maintains interest rate indexes and reserve balances
   - Updated alongside collateral/user boxes in the exchange transaction

3. **User Script** (implicit):
   - Simple threshold script locked to `user` address
   - May incorporate multi-sig