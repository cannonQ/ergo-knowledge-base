---
title: duckpools/lend-protocol-contracts — proxyPartialRepay.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/proxy-contracts/proxyPartialRepay.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/proxy-contracts/proxyPartialRepay.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: proxyPartialRepay

## Purpose

This contract manages partial loan repayment and timeout-based refunds in a lending protocol. It validates that either (1) a borrower repays part of their loan by reducing borrow tokens while maintaining collateral integrity, or (2) a refund is issued if the repayment window expires without action.

## Inputs / Outputs

### Inputs
- **SELF (Proxy Box)**: Contains repayment metadata in registers (collateral box ID, final borrow amount, user script, refund deadline)
- **INPUTS(1) (Collateral Box)**: The active loan position with collateral tokens, borrow tokens, and borrower metadata
- **Data Input (Optional)**: Referenced but not mutated; likely a price oracle or pool state box

### Outputs

**Refund Path** (OUTPUTS.size ≤ 2):
- **OUTPUTS(0)**: Refund box sent to original borrower (`userScript`), value ≥ `partialRepayment - MinTxFee`

**Repayment Path** (OUTPUTS.size > 2):
- **OUTPUTS(0)**: Successor collateral box with reduced borrow tokens, all other state preserved
- Additional outputs for protocol fees or pool updates (not validated in this contract)

## Key Logic

### Refund Branch (Timeout Path)
```
IF transaction outputs ≤ 2:
  - Verify output box script matches stored user script (borrower identity)
  - Verify refund value covers minimum (partialRepayment - 1M nanoERG fee)
  - Verify current block height ≥ refund deadline
  → ACCEPT (refund unlocks after deadline expires)
```

### Repayment Branch (Normal Path)
```
IF transaction outputs > 2:
  - Validate current collateral box ID matches SELF.R4 (anti-replay)
  - Validate successor box:
    * Same script (locked to same contract)
    * Value unchanged (no ERG theft)
    * Collateral tokens unchanged (no collateral swap)
    * Borrow token ID unchanged (same loan)
    * Borrow token amount = SELF.R5 (state transition enforced off-chain)
    * All metadata registers (R4-R9) identical
  → ACCEPT (partial repayment validated, state maintained)
```

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R4** | `Coll[Byte]` | SELF | Collateral box ID (prevents reuse of same proxy) |
| **R5** | `Long` | SELF | Final borrow token amount after repayment |
| **R6** | `Coll[Byte]` | SELF | User's script (borrower identity for refunds) |
| **R7** | `Long` | SELF | Refund deadline block height |
| **R4** | `Coll[Byte]` | Collateral | Borrower script (stored for verification) |
| **R5** | `(Int, Int)` | Collateral | Pool indexes (lending pool metadata) |
| **R6** | `(Long, Long)` | Collateral | Threshold & penalty ratio (liquidation parameters) |
| **R7** | `Coll[Byte]` | Collateral | DEX NFT ID (oracle reference) |
| **R8** | `GroupElement` | Collateral | User public key (Sigma protocol commitment) |
| **R9** | `(Long, Long)` | Collateral | Forced liquidation parameters (emergency flag) |

## Tokens

### Token Handling

**Collateral Token** (Index 0 in Collateral Box):
- Native asset held as collateral
- Must be retained identically in successor box
- Prevents collateral swaps during partial repayment

**Borrow Token** (Index 1 in Collateral Box):
- Tuple: `(tokenId: Coll[Byte], amount: Long)`
- Token ID immutable (same loan)
- Amount variable: `current` → `final` (reduction = repayment amount)
- Used to track outstanding loan balance

**No singleton NFT**: Unlike many state-machine contracts, this proxy does *not* require a singleton token; instead, it uses the **collateral box ID** (R4) as the anti-replay mechanism.

## Integration Pattern

### Off-Chain Interaction

**For Partial Repayment:**
1. Off-chain bot observes `proxyPartialRepay` box with `HEIGHT < R7` (not yet expired)
2. Retrieves current collateral box (ID from R4)
3. Calculates: `newBorrowAmount = currentBorrowAmount - repaymentAmount`
4. Constructs transaction:
   - Spends SELF (proxy box)
   - Spends collateral box (INPUTS(1))
   - Creates successor collateral box (OUTPUTS(0)) with:
     - **Borrow tokens**: new amount = SELF.R5
     - **All other fields**: copied from current
   - Sends repayment tokens to pool/treasury
5. **Constraint**: Bot must calculate and set `SELF.R5` *before* transaction submission; contract validates but does not compute

**For Refund (After Deadline):**
1. Off-chain watches for `HEIGHT >= R7`
2. Constructs refund transaction:
   - Spends SELF (proxy box)
   - Creates output to `SELF.R6` with value ≥ `SELF.value - 1M`
3. No collateral box input needed

**Context Extensions:** None explicitly required; all data in registers.

## Related Contracts

### Inferred Composition

- **Collateral Box Contract**: The state machine holding the loan (references R4-R9). This proxy validates state transitions from current → successor collateral state.
- **Pool / Treasury Contract**: Receives repayment tokens (implied by `OUTPUTS.size > 2`); not validated here.
- **Oracle / DEX Contract**: Referenced via `R7[Coll[Byte]]` in collateral box; used for price verification (off-chain).

### Design Pattern

This is a **multi-stage proxy contract