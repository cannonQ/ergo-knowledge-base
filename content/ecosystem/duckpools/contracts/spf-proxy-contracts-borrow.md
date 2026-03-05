---
title: duckpools/lend-protocol-contracts — borrow.md
description: "ErgoScript contract analysis: contracts/pools/spf/proxy-contracts/borrow.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/spf/proxy-contracts/borrow.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Borrow Proxy

## Purpose

This contract serves as a **proxy/intermediary box** in a lending protocol that facilitates borrowing operations. It validates either a **refund path** (if the borrow request is cancelled after a deadline) or an **exchange path** (if the borrow is accepted), ensuring collateral is properly locked and loan tokens are transferred to the user.

## Inputs / Outputs

### Inputs
- **SELF (Input 0):** This proxy box, containing user request metadata and value to be distributed
- **INPUTS(0):** Expected to hold the Pool NFT (verified via token check), providing the interest index for the lending pool

### Outputs

**Refund Path** (OUTPUTS.size < 3):
- **OUTPUTS(0):** Refund box returned to the user containing unspent ERG, with a reference to SELF.id in R4

**Exchange/Borrow Path** (OUTPUTS.size ≥ 3):
- **OUTPUTS(0):** Pool box (receives collateral contribution)
- **OUTPUTS(1):** Collateral box (newly created, locked by collateralBoxScript)
- **OUTPUTS(2):** User box (receives loan tokens, locked by user's script)

## Key Logic

### Refund Validation
The contract allows a **refund-only** operation if:
1. **Height threshold passed:** `HEIGHT >= publicRefund` (R6) – user-specified deadline has expired
2. **Minimal fee deducted:** The ERG delta between SELF and the refund output ≤ minTxFee
3. **Correct recipient:** Refund box script matches the user address from R4
4. **Safety reference:** Refund box R4 contains SELF.id (multi-box spend safety marker)

### Exchange/Borrow Validation
The contract validates a full borrow if **all** of these hold:

**Collateral Box Integrity:**
- Script hash matches expected `collateralBoxScript` (blake2b256)
- Value equals ERG remaining after loan fee: `SELF.value - minBoxValue - minTxFee`
- Records the borrower, indexes, threshold/penalty ratios, DEX NFT, user's public key, and forced liquidation height

**Loan Token Consistency:**
- Collateral box holds BorrowTokenId with amount = loanAmount
- User box receives PoolNativeCurrency with the same loanAmount
- User's requested amount matches the loan issued

**User Data Consistency:**
- Borrower address, threshold/penalty ratios, DEX NFT, and public key in collateral box match SELF's registers (R4–R9)
- User script in output matches user address
- User loan amount equals requestAmount from R5

**Forced Liquidation Window:**
- Liquidation height is strictly future: `> HEIGHT + 65480` and `≤ HEIGHT + 65520` (~9 days buffer, Ergo block time ~2 min)

**Pool Interaction:**
- INPUTS(0) carries the Pool NFT (enforced by pool contract logic)

**Multi-Box Safety:**
- User box R4 contains SELF.id (prevents orphaning/replay)

### Authorization
The transaction is valid if:
- **Either** the structured operation passes (refund OR exchange), **OR**
- **The user signs:** `proveDlog(userPk)` (allows user override with signature)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User/borrower address (script hash) |
| **R5** | `Long` | Requested loan amount |
| **R6** | `Int` | Block height after which refund becomes available |
| **R7** | `(Long, Long)` | Threshold and penalty ratios (stored in collateral box R6) |
| **R8** | `Coll[Byte]` | DEX NFT identifier (for liquidation routing) |
| **R9** | `GroupElement` | User's public key (Sigma protocol proof element) |

## Tokens

| Token | Role |
|-------|------|
| **poolNFT** | State singleton for the lending pool; presence in INPUTS(0) authorizes the borrow operation |
| **BorrowTokenId** | Debt/loan token issued by the pool; collateral box holds this to track borrowed amount |
| **PoolNativeCurrency** | Native asset representing loanable liquidity; transferred to user's output box |

## Integration Pattern

### Off-Chain Construction (Bot/dApp)

1. **Initiate Borrow Request:**
   - Create SELF (proxy box) with:
     - R4 = user script hash
     - R5 = desired loan amount
     - R6 = refund deadline (e.g., `currentHeight + 100` blocks)
     - R7 = `(threshold, penalty)` tuple from pool state
     - R8 = user's DEX NFT (or identifier for liquidation)
     - R9 = user's public key (for signature fallback)
     - Value = collateral ERG + minBoxValue + minTxFee overhead

2. **Pool Acceptance (Happy Path):**
   - Construct OUTPUTS(0) = pool box (collateral accumulated)
   - Construct OUTPUTS(1) = collateral box with:
     - Script = `collateralBoxScript` (evaluated from blake2b256 constant)
     - R4–R9 = copies of user data from SELF
     - Token = BorrowTokenId with loanAmount
     - Value = collateral ERG
   - Construct OUTPUTS(2) = user box with:
     - Script = user address
     - Token = PoolNativeCurrency with loanAmount
     - R4 = SELF.id (safety marker)
   - Include INPUTS(0) = pool box holding poolNFT
   - Sign with pool key (or be co-signed by pool oracle)

3. **Cancellation/Timeout (Refund Path):**
   - After `publicRefund` height, user can issue a transaction with:
     - INPUTS(0) = SELF (this proxy)
     - OUTPUTS(0) = refund box (user script, minimal