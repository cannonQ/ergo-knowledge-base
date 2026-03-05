---
title: duckpools/lend-protocol-contracts — collateralContract.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/collateralContract.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/collateralContract.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Collateral Contract (DuckPools Lend Protocol)

## Purpose

This contract manages collateralized loans in the DuckPools lending protocol. It validates loan maintenance (collateral adjustments), repayment transactions, and liquidation events by verifying interest calculations against a multi-tiered interest rate oracle structure and ensuring sufficient collateral backing for outstanding debt.

## Inputs / Outputs

### Inputs
- **INPUTS(0)** (Collateral Adjustment): The SELF box itself, enabling the borrower to adjust collateral levels while maintaining loan integrity
- **INPUTS(1)** (Repayment/Liquidation): The SELF box, triggering either full repayment or liquidation pathways

### Outputs

**Collateral Adjustment Branch (INPUTS(0) == SELF):**
- **OUTPUTS(0)**: Successor collateral box (same script, adjusted collateral/value, retained state)

**Repayment Branch (INPUTS(1) == SELF):**
- **OUTPUTS(0)**: Borrower's box receiving collateral (script = `currentBorrower`)
- **OUTPUTS(1)**: Repayment box (script = `RepaymentContractScript`, contains borrow tokens + accrued interest in ERG)
- **OUTPUTS(2)** (optional, partial repay): Successor collateral box with reduced borrow tokens

**Liquidation Branch:**
- **OUTPUTS(0)**: DEX swap box (sells collateral to cover debt)
- **OUTPUTS(1)**: Repayment box
- **OUTPUTS(2)** (optional): Liquidator reward box

### Data Inputs
- **CONTEXT.dataInputs(0)**: Base child interest rate box (ChildInterestNft)
- **CONTEXT.dataInputs(1)**: Parent interest rate box (ParentInterestNft)
- **CONTEXT.dataInputs(2)**: Head child interest rate box (ChildInterestNft, most recent)
- **CONTEXT.dataInputs(3)**: DEX pool box (for collateral valuation via Spectrum DEX)

## Key Logic

### 1. **Interest Calculation (Multi-Tier Compound Interest)**
The contract reconstructs accrued interest by:
- Starting from the borrower's **childIndex** position in base child rates
- Folding (compounding) all intermediate interest rates from base child → head child → parent rates
- Formula: `totalOwed = loanAmount × ∏(rates) / InterestRateDenom`

Three cases:
- **Case 1**: Parent hasn't advanced → use only base child rates
- **Case 2**: Parent advanced by 1 → chain base child → head child rates
- **Case 3**: Parent advanced >1 → chain all three: base child → head child → parent rates

### 2. **Collateral Adjustment Validation** (INPUTS(0) == SELF)
Enforces:
- Successor box retains identical script (ErgoTree), borrow tokens, and register values
- Successor **value ≥ current value** (no ERG extraction)
- **Collateral value > totalOwed × liquidationThreshold / 1000** (LTV check)
- Collateral value computed via Spectrum DEX formula with 2% slippage buffer
- Signed by **currentUserPk** (borrower authorization via Sigma protocol `proveDlog`)

### 3. **Repayment Validation** (INPUTS(1) == SELF, full or partial)
Full repayment requires:
- **Borrower box**: script equals `currentBorrower`, receives original collateral token
- **Repayment box**: script = `RepaymentContractScript`, contains exact borrow tokens, ERG value ≥ **totalOwed + minimum fees**
- Interest rate boxes remain valid (no stale data)

Partial repayment (if OUTPUTS(0) has ≥2 tokens and INPUTS(0) has <3 tokens):
- Creates successor collateral box with reduced borrow token amount
- Validates successor state preservation (same pattern as collateral adjustment)

### 4. **Liquidation Validation**
Triggered if:
- **collateralValue < totalOwed × liquidationThreshold** (under-collateralized)
- OUTPUTS(0) is DEX swap box (sells collateral for ERG)
- OUTPUTS(1) is repayment box (covers debt)
- **liquidationReward = (totalOwed - collateralReceived) × (1000 + liquidationPenalty) / 1000**
- Liquidator receives reward from DEX proceeds

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Borrower's public key script hash (recipient of collateral on repayment) |
| **R5** | `(Int, Int)` | `(parentIndex, childIndex)` – indices into parent/child interest rate histories |
| **R6** | `(Long, Long)` | `(liquidationThreshold, liquidationPenalty)` – in basis points (denom = 1000) |
| **R7** | `Coll[Byte]` | DEX pool NFT ID (for collateral-to-ERG pricing) |
| **R8** | `GroupElement` | User's public key (Sigma protocol verification for collateral adjustments) |
| **R9** | `(Long, Long)` | `(forcedLiquidationFlag, liquidationBuffer)` – liquidation trigger and safety margin |

## Tokens

### SELF Box Tokens
- **Token(0)**: Collateral token (e.g., SPF, USDT) – `(tokenId, amount)` tracked across transitions
- **Token(1)**: Borrow token (identifying the loan) – `(borrowTokenId, loanAmount)` immutable except in partial repay

### Oracle/State NFTs
- **ChildInterestNft**: Singleton NFT in base and head child interest boxes (prevents forking)
- **ParentInterestNft**: Singleton NFT in parent interest rate box
- **DexNft** (R7): Spectrum DEX pool NFT for collateral valuation (validates price feed)

### Token ID Rule