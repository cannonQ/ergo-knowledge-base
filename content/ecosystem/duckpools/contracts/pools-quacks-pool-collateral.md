---
title: duckpools/lend-protocol-contracts — collateral.md
description: "ErgoScript contract analysis: contracts/pools/QUACKS-POOL/collateral.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/QUACKS-POOL/collateral.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: QUACKS-POOL Collateral

## Purpose

This contract manages collateral boxes in a lending protocol, enabling borrowers to maintain loans by tracking interest accrual across a hierarchical interest rate index structure. It validates two primary operations: collateral adjustments (via DEX swaps to maintain health) and loan repayment/liquidation, ensuring the collateral value remains above a liquidation threshold while accruing compound interest.

## Inputs / Outputs

### Inputs
- **INPUTS(0) == SELF**: Collateral adjustment path
  - Reads: Current collateral box (self-reference)
  - Data inputs: Base child interest box, parent interest box, head child interest box, DEX LP box
  
- **INPUTS(1) == SELF**: Repayment/liquidation/partial repay path
  - Reads: Current collateral box at position 1
  - Data inputs: Base child interest box, parent interest box, head child interest box
  - Additional inputs (INPUTS(0)): Borrower box (during partial repay/liquidation)

### Outputs

**Collateral Adjustment Branch (INPUTS(0) == SELF):**
- **OUTPUTS(0)**: Successor collateral box (same script/tokens/registers, adjusted ERG value)

**Repayment Branch (INPUTS(1) == SELF):**
- **OUTPUTS(0)**: Borrower's box (receives remaining collateral or DEX output)
- **OUTPUTS(1)**: Repayment box (locked under `RepaymentContractScript`, carries repaid tokens)
- **OUTPUTS(2)** (partial repay only): Successor collateral box

---

## Key Logic

### Interest Calculation (Multi-Level Index Traversal)

The contract maintains a **hierarchical interest index structure**:
- **Child interest boxes** store rate history in R4 (Coll[Long])
- **Parent interest box** aggregates rates; R4 contains cumulative rates
- Child boxes track their position via R6[Int]

**Compound Interest Logic:**
```
compoundedInterest = fold over rate history:
  accumulator = InterestRateDenom (10^8, representing 1.0)
  For each rate: accumulator = (accumulator * rate) / InterestRateDenom
```

Three cases determine which rates to scan:
1. If `parentIndex == liveParentIndex`: Only scan base child rates
2. If `parentIndex + 1 == liveParentIndex`: Scan base child → head child rates
3. Otherwise: Scan base child → head child → parent rates

**Total Owed:**
```
totalOwed = 1 + (loanAmount * compoundedInterest) / InterestRateDenom
```
(The "+1" ensures rounding up via BigInt arithmetic)

### Collateral Adjustment Validation (INPUTS(0) == SELF)

**DEX Swap Calculation:**
- Converts ERG collateral to loan currency via constant-product DEX formula
- Applies slippage tolerance (2%) and DEX fee from LP box
- Derived `collateralValue` must exceed liquidation threshold:
  ```
  collateralValue > totalOwed * liquidationThreshold / 1000
  ```
- Successor box must retain minimum value: `3 * 1,000,000 + 1,000,000 ERG`

**State Preservation:**
- Successor must use identical script and borrow tokens
- All registers (R4–R9) must remain unchanged
- Borrower retains control via `proveDlog(currentUserPk)`

### Repayment/Liquidation Validation (INPUTS(1) == SELF)

**Repayment Path:**
- Borrower receives collateral back: `borrowerValue >= currentValue - MinimumTransactionFee`
- Repayment box receives loan tokens: `repaymentLoanTokens._2 >= totalOwed`
- Repayment box script must match `RepaymentContractScript` (blake2b256 hash)
- Borrow token NFT is transferred to repayment box (audit trail)

**Liquidation / Partial Repay:**
- If DEX output in OUTPUTS(0) and INPUTS(0) has <3 tokens: **partial repay path**
  - Successor collateral box created with remaining debt
  - Checks: sufficient collateral, correct successor state, borrow token retention
- Otherwise: **full liquidation**
  - No successor; all collateral claimed by borrower

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|-----------|
| **R4** | `Coll[Byte]` | Borrower's script (Blake2b256 hash) | Immutable in adj./repay |
| **R5** | `(Int, Int)` | Interest index pointers `(parentIndex, childIndex)` | Immutable |
| **R6** | `(Long, Long)` | `(liquidationThreshold, liquidationPenalty)` in basis points | Immutable |
| **R7** | `Coll[Byte]` | DEX NFT ID (identifies LP pool) | Immutable |
| **R8** | `GroupElement` | Borrower's public key (for `proveDlog`) | Immutable |
| **R9** | `(Long, Long)` | `(forcedLiquidationFlag, liquidationBuffer)` | Immutable |

**Interest Rate Boxes (Data Inputs):**
- **Child/Parent R4:** `Coll[Long]` — rate history (compound multipliers)
- **Child/Parent R6:** `Int` — index position

---

## Tokens

### Token Structure in Collateral Box

- **tokens(0):** `(ChildInterestNft, loanAmount: Long)`
  - **Token ID:** Derived from contract constants (`ChildInterestNft`)
  - **Purpose:** Singleton NFT tracking this loan + borrow amount
  - **Flow:** Transferred to repayment box on repayment (audit trail)

### Validation Tokens

- **ChildInterestNft** (R7 in child interest boxes)
  - Identifies base and head child interest boxes
  
-