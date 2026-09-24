---
title: ThierryM1212/SigmaO — Sell_Token_Request.es
description: "ErgoScript contract analysis: contract/Sell_Token_Request.es"
tags: [thierrym1212, sigmao, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
contract_file: contract/Sell_Token_Request.es
project: thierrym1212-sigmao
---
# ErgoScript Contract Analysis: Sell_Token_Request

## Purpose

This contract implements an **open sell order** that allows a seller to list tokens for sale at a fixed price. The contract enables partial or complete token sales, automatically distributing proceeds to the seller, dApp UI fees, and miners while maintaining the sell order state through a replicated Box.

## Inputs / Outputs

### Inputs
- **SELF (Input Box 0):** The active sell order Box containing:
  - Token reserve (the tokens being sold)
  - Seller's public key (R4)
  - Pricing and fee parameters (R5)
  - dApp UI ErgoTree (R6)

### Outputs

**For `validCloseEmpty` (closing an empty reserve):**
- **Output 0:** Refund to seller's PK with remaining value
- **Output 1:** Miner fee Box

**For `validSellToken` (executing a sale):**
- **Output 0:** Replicated sell order Box (same contract, reduced tokens if partial sale)
- **Output 1:** Buyer's token delivery Box (contains `deliveredTokens`)
- **Output 2:** Seller payment Box (receives `≥ minPrice` nanoERG)
- **Output 3:** dApp UI fee Box (receives `≥ dAppUIFee` nanoERG)
- **Output 4:** Miner fee Box

## Key Logic

The contract validates two mutually exclusive execution paths:

### Path 1: Close Empty Reserve
- **Condition:** Input token reserve is zero (`inputTokenReserve._2 == 0L`)
- **Effect:** Anyone can trigger a refund; the seller recovers remaining Box value minus miner fee
- **Purpose:** Clean up completed or abandoned sell orders

### Path 2: Execute Token Sale
Validates the following invariants:

1. **Reserve Replication:** Output 0 must be a Box with the same contract ErgoTree as SELF
   
2. **Token Consistency:** 
   - Same token ID in both input and output reserves
   - Handles both **partial sales** (output reserve > 0) and **complete sales** (output reserve = 0)

3. **Delivered Tokens Calculation:**
   ```
   deliveredTokens = inputTokenReserve - outputReserveTokens
   ```
   Must be positive (> 0L)

4. **Price Computation:**
   - **minPrice** = `max(BoxMinValue, deliveredTokens × tokenPrice)`
   - Ensures seller receives at least the fixed price per unit
   - Respects Ergo's Minimum box value constraint

5. **dApp UI Fee:**
   - **dAppUIFee** = `max(BoxMinValue, dAppUIFeePerThousand × minPrice / 1000L)`
   - Permille-based (per thousand) fee structure
   - Dynamically scales with transaction value

6. **Output Distribution:**
   - Seller receives ≥ minPrice (Output 2)
   - dApp UI receives ≥ dAppUIFee (Output 3)
   - Miner receives exactly txFee (Output 4)
   - Reserve state preserved in Output 0

7. **Reserve Preservation:** Output 0 replicates all register data:
   - R4: Seller PK (unchanged)
   - R5: Pricing parameters (unchanged)
   - R6: dApp UI ErgoTree (unchanged)

### Guard Clause (Refund Path)
- Contract can always be closed by the seller via `userPKIn` signature
- Provides an escape hatch independent of normal execution paths

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Seller's public key; required for refund and payment routing |
| **R5** | `Coll[Long]` | Pricing vector: `[tokenPrice, dAppUIFeePerThousand, txFee]` |
| **R6** | `Coll[Byte]` | ErgoTree bytecode of dApp UI fee recipient; enables dynamic fee routing |

All three registers are **mandatory** for the contract to function; their absence will cause script failure.

## Tokens

- **Token ID:** Stored in `inputTokenReserve._1` (the Coll[Byte] identifier)
- **Token Amount:** Tracked in `inputTokenReserve._2` (the Long quantity)
- **Role:** The token being sold; must be preserved across Box replications
- **Authentication:** No token-based authentication; instead uses ErgoTree identity and Sigma protocol signatures

The contract assumes the buyer (Output 1) validates token ownership in a separate **Buy** contract; this contract only verifies token delivery quantities.

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities:

1. **Constructing a Sale Transaction:**
   - Assemble 5 output Boxes with correct value distribution
   - Verify `deliveredTokens > 0` and token consistency
   - Calculate fees: `minPrice = max(BoxMinValue, deliveredTokens × R5[0])`
   - Calculate UI fee: `dAppUIFee = max(BoxMinValue, R5[1] × minPrice / 1000)`

2. **Price Verification:**
   - Enforce fixed price from R5[0] (smallest unit of token → nanoERG)
   - Validate Output 2 receives at least `minPrice`

3. **State Machine Transitions:**
   - If partial sale: replicate order with reduced token quantity in Output 0
   - If complete sale: Output 0 has zero tokens (but remains valid for closure on next invocation)

4. **Fee Distribution:**
   - Route Output 3 to dApp UI ErgoTree (from R6)
   - Route Output 4 to miner (fixed txFee from R5[2])
   - Ensure Output 2 ≥ minPrice for seller

5. **Context Extension:**
   - No explicit Context extension variables required
   - All parameters are embedded in SELF registers

### Validation Sequence:
```
1. Verify seller signature (userPKIn) OR
2. Verify (validCloseEmpty OR validSellToken)
   ├─ validCloseEmpty: simple refund
   
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
