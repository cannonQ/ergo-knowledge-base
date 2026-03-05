---
title: duckpools/lend-protocol-contracts — borrow.md
description: "ErgoScript contract analysis: contracts/pools/SIGRSV-POOL/proxy-contracts/borrow.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/SIGRSV-POOL/proxy-contracts/borrow.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Borrow Proxy (SIGRSV-POOL)

## Purpose

This contract acts as a **proxy intermediary** for borrowing operations in the SIGRSV lending protocol. It validates that a user can either:
1. **Refund** their loan request (if conditions expire), or
2. **Execute** a valid loan origination by atomically exchanging collateral for borrowed tokens while enforcing liquidation thresholds and penalty parameters.

## Inputs / Outputs

### Inputs
- **SELF (Input 0)**: The borrow proxy box itself, containing:
  - User address (R4)
  - Requested loan amount (R5)
  - Refund deadline height (R6)
  - Liquidation threshold & penalty (R7)
  - DEX NFT identifier (R8)
  - User public key (R9)

- **INPUTS(0)**: Must contain the **pool NFT** (State NFT) as first token—enforced by pool contract validation

### Outputs (Two Execution Paths)

**Path 1: Refund (OUTPUTS.size < 3)**
- **OUTPUTS(0)**: Refund box back to user with remaining ERG (after fee)
  - Must reference SELF.id in R4 (multi-box spend safety)

**Path 2: Loan Exchange (OUTPUTS.size ≥ 3)**
- **OUTPUTS(0)**: Pool box (updated state)
- **OUTPUTS(1)**: Collateral box (delegated to collateral contract)
  - Contains collateral in ERG + BorrowTokenId tokens
  - Holds user data: borrower ID, threshold/penalty, DEX NFT, user PK, forced liquidation window
- **OUTPUTS(2)**: User box
  - Receives PoolNativeCurrency tokens (the actual loan)
  - References SELF.id in R4 (multi-box spend safety)

## Key Logic

### Refund Path Validation
```
IF transaction outputs < 3 THEN:
  ✓ Refund recipient = original user address (R4)
  ✓ Refund box references this SELF.id (prevents double-spend)
  ✓ Fee delta ≤ minTxFee (1 ERG)
  ✓ Current HEIGHT ≥ publicRefund deadline (R6)
```

### Loan Exchange Path Validation

**Collateral Box Integrity:**
- Script hash matches expected collateralBoxScript (Blake2b256)
- Collateral amount = SELF.value - minBoxValue - minTxFee (accounting for box value + fee)
- User data fields propagate correctly (borrower, threshold, DEX NFT, user PK)

**Loan Token Validation:**
- Borrowed tokens (BorrowTokenId) in collateral box match amount in user box
- User receives PoolNativeCurrency tokens in exact requested amount (R5)

**Safety & Liquidation:**
- Borrower identity matches across all boxes (R4)
- Threshold/penalty parameters consistent (R6)
- DEX NFT identifier matches (R7)
- User public key matches (R8)
- **Forced liquidation window**: collateralForcedLiquidation ∈ [HEIGHT + 65480, HEIGHT + 65520]
  - ~18 days from now (assuming Ergo 2-min blocks)
  - Ensures collateral can be liquidated within predictable timeframe

**Multi-Box Spend Safety:**
- Both refund and user output boxes reference SELF.id to prevent reuse in concurrent transactions

**Pool State Validation:**
- INPUTS(0) must carry the pool NFT (enforced externally by pool contract)

### Final Authorization
```
operation OR proveDlog(userPk)
```
Either the atomic operation succeeds, **or** the user can unilaterally sign with their private key (R9) to abort/recover.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User address (script bytes) |
| **R5** | `Long` | Requested borrow amount (in PoolNativeCurrency) |
| **R6** | `Int` | Refund deadline height (public refund timelock) |
| **R7** | `(Long, Long)` | **(threshold, penalty)** tuple for liquidation logic |
| **R8** | `Coll[Byte]` | DEX NFT identifier (likely for price oracle or DEX interaction) |
| **R9** | `GroupElement` | User's public key (Sigma protocol commitment for unilateral recovery) |

## Tokens

| Token | Usage |
|-------|-------|
| **poolNFT** (`8txwdGRnbi...`) | State NFT in pool box input; ensures pool contract controls state machine |
| **BorrowTokenId** (`3zJxxr49st...`) | Debt instrument minted/held in collateral box; represents borrowed amount |
| **PoolNativeCurrency** (`1uuSELXj5m...`) | Native token distributed to user in loan box; the actual borrowed value |

## Integration Pattern

### Off-Chain Bot / Headless dApp Requirements

1. **Monitor Pool State**: Watch for new borrow request boxes at this proxy address
2. **Construct Atomic Transaction**:
   - Spend SELF (borrow proxy box)
   - Spend pool input containing poolNFT
   - Create collateral output with:
     - ERG value = SELF.value - minBoxValue - minTxFee
     - BorrowTokenId tokens (quantity = requestAmount)
     - User data propagated to R4–R9
     - Script: collateralBoxScript
   - Create user output with:
     - PoolNativeCurrency tokens (quantity = requestAmount from R5)
     - Script: user address (R4)
     - R4 = SELF.id (multi-box safety)
   - Optionally update pool box (OUTPUTS(0))

3. **Validate Before Submission**:
   - Collateral sufficiency (via threshold logic: R7)
   - Liquidation window valid (65480–65520