---
title: duckpools/lend-protocol-contracts — repay.md
description: "ErgoScript contract analysis: contracts/v2-generics/repay.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/v2-generics/repay.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: `repay.md`

## Purpose

This contract enforces the repayment logic for a lending protocol, allowing borrowers to reclaim collateral by returning borrowed funds or triggering an emergency refund after a deadline. It validates that either repayment conditions are met (with correct token amounts returned) or that the refund deadline has passed.

## Inputs / Outputs

### Inputs
- **SELF**: A loan box containing:
  - Collateral in ERG (value field)
  - State tokens indexed in R8, R9
  - Borrower script hash in R5
  - Loan parameters in R4, R6

### Outputs

**Case 1: Repayment (OUTPUTS.size ≥ 3)**
- **OUTPUTS(0)**: Borrower box receiving collateral back
  - Must match borrower's script (R5)
  - Must contain ERG ≥ `neededAmount` (R4)
  - Must contain all original tokens in correct amounts (R8, R9)
  - Must reference SELF via R4 (multi-box spend safety)

**Case 2: Refund (OUTPUTS.size < 3)**
- **OUTPUTS(0)**: Refund box sent to borrower
  - Must match borrower's script (R5)
  - Must contain ERG ≥ SELF.value − minTxFee (1,000,000 nanoERG)
  - Must contain all original tokens (SELF.tokens)

## Key Logic

### Repayment Path (≥3 outputs)
1. **Script Validation**: Verify OUTPUTS(0) uses the borrower's proposition (ErgoTree)
2. **Collateral Return**: Ensure returned ERG meets or exceeds `neededAmount`
3. **Token Matching**: Confirm all tokens in R9 (IDs) match R8 (amounts) and are sent to borrower
4. **Multi-box Safety**: Require OUTPUTS(0).R4 to store SELF.id, preventing accidental reuse across transactions

### Refund Path (<3 outputs)
1. **Deadline Check**: Validate HEIGHT ≥ R6 (deadline block height)
2. **Script Validation**: Verify refund goes to borrower's address
3. **Value Preservation**: Ensure refund covers original value minus minimum transaction fee (1,000,000 nanoERG)
4. **Token Preservation**: Confirm all native tokens return intact

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | `neededAmount` – ERG required for repayment; also used in OUTPUTS(0) as safety reference |
| **R5** | `Coll[Byte]` | Borrower's proposition bytes (script hash) for validation |
| **R6** | `Int` | Refund deadline (block height) – if HEIGHT ≥ R6, borrower can force refund |
| **R8** | `Coll[Long]` | Token amounts array (paired with R9 token IDs) |
| **R9** | `Coll[Coll[Byte]]` | Token IDs array (paired with R8 amounts) |

## Tokens

- **R8 / R9 Token Pairs**: Native tokens representing loan collateral or state markers
  - In repayment path: tokens must be returned to borrower in exact amounts
  - In refund path: all tokens (SELF.tokens) returned without modification
  - Uses Ergo's native token standard (token ID = output box ID where first minted)

## Integration Pattern

### Off-Chain Requirements

1. **Repayment Construction**:
   - Construct OUTPUTS(0) with borrower's script and min. `neededAmount` ERG
   - Attach all tokens from R8/R9 pairs to OUTPUTS(0)
   - Store SELF.id in OUTPUTS(0).R4 (multi-box safety)
   - Ensure transaction has ≥3 outputs total

2. **Refund Construction**:
   - Monitor HEIGHT against SELF.R6 deadline
   - After deadline, construct OUTPUTS(0) for borrower with:
     - Original SELF.value − 1,000,000 nanoERG (minimum transaction fee)
     - All tokens from SELF.tokens
   - Keep transaction to <3 outputs

3. **Validation Steps**:
   - Verify borrower script matches R5 in both paths
   - Check box value arithmetic (ERG conservation with fee allowance)
   - Confirm token IDs and amounts via zip operation (R8 ↔ R9)
   - Validate deadline in refund scenario

### Context Extension
- No context extension variables (Sigma protocol challenges) needed
- All data available in box registers and UTXO set

## Related Contracts

Based on the file path `v2-generics/repay.md` and multi-box pattern:

- **Loan/Borrow Contract**: Likely a separate contract that locks collateral and issues loan terms; this repay contract consumes that output
- **Pool/Lender Contract**: Probable counterparty contract receiving repayment amounts
- **Liquidation Contract**: Sibling contract handling default scenarios (triggered if HEIGHT > R6 without repayment)
- **State Management Contract**: May interact with a State NFT to track loan lifecycle

---

## Security Observations

⚠️ **Multi-box Safety**: The R4 reference pattern (OUTPUTS(0).R4 == SELF.id) prevents double-spending across multiple loan boxes in a single transaction—critical for atomic loan operations.

⚠️ **Deadline Enforcement**: Refund path relies on Ergo's immutable HEIGHT; no time-based oracle dependency.

⚠️ **Fee Handling**: Refund path reserves exactly 1,000,000 nanoERG; off-chain must account for variable network fees.