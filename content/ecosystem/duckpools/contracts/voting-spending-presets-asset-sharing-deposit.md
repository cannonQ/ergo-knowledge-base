---
title: duckpools/lend-protocol-contracts — asset_sharing_deposit.md
description: "ErgoScript contract analysis: contracts/treasury-system/voting/spending_presets/asset_sharing_deposit.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/treasury-system/voting/spending_presets/asset_sharing_deposit.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Asset Sharing Deposit

## Purpose

This contract manages conditional asset deposits in a lending protocol's treasury system, enabling users to either **refund their ERG** if a time window expires or **exchange deposited ERG for desired tokens** if conditions are met. It acts as an atomic swap escrow with dual-path resolution: timeout-based refund or token fulfillment.

---

## Inputs / Outputs

### Inputs
- **SELF**: A deposit box containing:
  - ERG value (amount being locked)
  - User's identity and desired token specification (in registers)

### Outputs

**Path 1: Refund (OUTPUTS.size < 3)**
- **OUTPUTS(0)**: Refund box
  - Destination: User's address (from `user` register)
  - Value: Original ERG minus transaction fee
  - Optional R4: Reference to SELF.id (for multi-box tracking)

**Path 2: Exchange (OUTPUTS.size ≥ 3)**
- **OUTPUTS(1)**: Successor/exchange box
  - Destination: User's address
  - Tokens: Desired token with quantity ≥ requestAmount
  - Optional R7: Reference to SELF.id (for multi-box tracking)

---

## Key Logic

The contract enforces a **two-branch state machine** validated by transaction structure:

### Branch 1: Refund Path (timeout scenario)
```
IF OUTPUTS.size < 3 THEN
  ✓ OUTPUTS(0) script == user's public key
  ✓ ERG delta ≤ minTxFee (only fees consumed)
  ✓ HEIGHT ≥ publicRefund (refund window opened)
  ✓ Refund box's R4 == SELF.id (optional multi-box safety)
  THEN allow spending
ELSE deny
```

**Semantics**: User can reclaim their deposit if the deadline (`publicRefund` height) has passed, with minimal slippage.

### Branch 2: Exchange Path (fulfillment scenario)
```
IF OUTPUTS.size ≥ 3 THEN
  ✓ OUTPUTS(1) script == user's public key
  ✓ First token in OUTPUTS(1) == desiredToken (by token ID)
  ✓ First token quantity ≥ requestAmount
  ✓ Successor box's R7 == SELF.id (optional multi-box safety)
  THEN allow spending
ELSE deny
```

**Semantics**: The deposit is consumed and replaced with a box containing the promised token, ensuring atomic substitution.

### Critical Invariants
- **Mutual exclusivity**: Either refund OR exchange, never both in same tx
- **No value leakage**: Refund path ensures ERG output ≥ (input - fee)
- **Token precision**: Exact token ID matching; quantity checked as ≥ (not ==) to allow overfulfillment
- **Temporal gating**: Refund only valid after `publicRefund` height

---

## Registers Used

| Register | Type | Purpose | Used In |
|----------|------|---------|---------|
| **R4** | `Coll[Byte]` | User's public key / address (serialized) | Both paths; validates output recipient |
| **R5** | `Long` | Requested token quantity | Exchange path; minimum amount check |
| **R6** | `Long` | Refund deadline (block height) | Refund path; temporal lock |
| **R7** | `Coll[Byte]` | Desired token's token ID (32-byte hash) | Exchange path; token identity |
| **R4 (output)** | `Coll[Byte]` (optional) | Multi-box tracking reference | Refund path only; stores SELF.id |
| **R7 (output)** | `Coll[Byte]` (optional) | Multi-box tracking reference | Exchange path only; stores SELF.id |

---

## Tokens

### Primary Token
- **desiredToken** (R7): The token ID (token hash) the user requests in exchange for their ERG deposit
  - **Role**: Payment obligation identifier
  - **Validation**: OUTPUTS(1).tokens(0)._1 must match exactly

### Secondary Mechanisms
- **No NFT singleton pattern**: This contract does NOT use a State NFT for governance
- **Native token quantity check**: Validates `tokens(0)._2 >= requestAmount` (first token in OUTPUTS(1))

---

## Integration Pattern

### Off-Chain Bot / Fulfillment Service
1. **Monitor** deposit boxes locking to this ErgoTree
2. **For exchange path**:
   - Construct a transaction with ≥3 outputs
   - Place fulfillment box at OUTPUTS(1) with:
     - User's address as script
     - desiredToken tokens with quantity ≥ requestAmount
     - R7 = SELF.id (optional safety check)
   - Additional outputs at OUTPUTS(2+) for fees/change
3. **For refund path** (fallback):
   - Wait until HEIGHT ≥ publicRefund
   - Construct tx with <3 outputs
   - Place refund box at OUTPUTS(0) with user's address
   - Optionally set R4 = SELF.id for audit trail

### Context Extension Requirements
- None (contract is deterministic; no context variables required)

### Constant Segregation
- `minTxFee` and `minBoxValue` hardcoded (future: consider parameterization via registers)

---

## Related Contracts

**Likely composition within duckpools/lend-protocol-contracts**:

1. **Treasury System Governance**
   - This contract likely integrates with a **multi-sig or DAO voting contract** that authorizes token distributions
   - OUTPUTS(2+) may route fees to governance treasury

2. **Loan Collateral / Deposit Contract**
   - Parent state machine that creates asset_sharing_deposit boxes
   - May validate initial R4-R7 register contents

3. **Token Minting / Reserve Contract**
   - Responsible for creating/holding the desiredToken inventory to fulfill exchanges

4. **Refund Distributor**
   - Post-deadline