---
title: duckpools/lend-protocol-contracts — proxyRepay.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/proxy-contracts/proxyRepay.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/proxy-contracts/proxyRepay.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: `proxyRepay.md`

## Purpose

This contract acts as a **repayment proxy** in the DuckPools lending protocol, validating that borrowed tokens are returned to the correct borrower address with the correct amount. It enforces either successful repayment (tokens returned to borrower) or timeout-based refund (after a deadline) back to the borrower's original address.

## Inputs / Outputs

### Inputs
- **SELF**: The proxy Box containing:
  - Value: ERG held as transaction fee reserve
  - R4: Required repayment amount (`Long`)
  - R5: Borrower's script bytes (`Coll[Byte]` — serialized PK or contract)
  - R6: Repayment deadline height (`Int`)
  - R8: Expected token ID to be repaid (`Coll[Byte]`)

### Outputs

**Success Path** (OUTPUTS.size ≥ 3):
- **OUTPUTS(0)** — Borrower Box: must receive the repaid tokens and be locked under borrower's script

**Timeout Path** (OUTPUTS.size < 3):
- **OUTPUTS(0)** — Refund Box: must return ERG to borrower after deadline

## Key Logic

The contract implements a **two-branch state machine**:

### Branch 1: Successful Repayment (≥3 outputs)
1. **Token validation**: OUTPUTS(0) must contain the `wantedTokenId` with amount ≥ `neededAmount`
2. **Script lock**: OUTPUTS(0)'s `propositionBytes` must equal the stored `borrower` script
3. **Multi-box safety**: OUTPUTS(0).R4 must reference this Box's ID (`SELF.id`), preventing the same proxy Box from validating multiple concurrent repayments

### Branch 2: Refund After Timeout (<3 outputs)
1. **Height check**: Current blockchain height must be ≥ deadline in R6
2. **Script lock**: Refund Box's `propositionBytes` must equal `borrower` script
3. **Value preservation**: Refund Box receives at least `SELF.value - minTxFee` (1 ERG fee deducted)

Both paths use `sigmaProp()` to enforce conditions via **Sigma protocol proofs**.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | Repayment amount (tokens) required |
| **R5** | `Coll[Byte]` | Borrower's serialized script/PK (authentication identity) |
| **R6** | `Int` | Absolute deadline height for timeout refund |
| **R8** | `Coll[Byte]` | Token ID being repaid (identifies the asset class) |

## Tokens

- **Native Token ID** (R8): The specific token asset being repaid
  - Tracked via `tokens(0)._1` (token ID) and `tokens(0)._2` (amount)
  - Used to ensure correct asset type and minimum quantity reach borrower
  - Follows Ergo's **Token ID rule**: first token in any Box is primary asset

## Integration Pattern

### Off-Chain Bot / Dapp Workflow

1. **Successful Repayment Transaction**:
   - Off-chain code must construct OUTPUTS with ≥3 boxes
   - Box 0 must lock repaid tokens under borrower's script
   - Box 0.R4 must be set to `SELF.id` (proxy Box's ID)
   - Bot signs the transaction

2. **Timeout Refund Transaction**:
   - Triggered after R6 height is reached
   - Off-chain code constructs OUTPUTS with <3 boxes
   - Box 0 refunds ERG to borrower, deducting `minTxFee`
   - Bot monitors blockchain height and executes

3. **Validation**:
   - Ergo node verifies `sigmaProp()` constraints
   - Script erasure ensures borrower cannot double-spend proxy Box
   - Multi-box safety (R4 reference) prevents race conditions

## Related Contracts

- **Borrower Contract** (implicit): The script stored in R5; must be able to spend the repayment Box
- **Loan Creation Contract**: Likely creates the initial proxy Box with R4–R8 values
- **Liquidation / Default Handler**: May interact if repayment fails (uses timeout path)
- **Pool Manager**: Orchestrates multi-box transactions with ≥3 outputs for atomic repayment

---

### Notes

- **Unused flags** (`true && true && true`): Placeholder for additional validation logic (gas optimization artifact)
- **Single token assumption**: `tokens(0)` implies only one native token expected; multi-token repayment would require loop
- **Storage rent**: Refund path deducts `minTxFee` but not full storage rent; assumes proxy Box is small
- **No spending height lock**: Success path allows immediate claim; timeout enforced only on refund