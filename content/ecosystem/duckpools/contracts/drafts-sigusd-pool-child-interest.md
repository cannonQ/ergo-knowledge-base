---
title: duckpools/lend-protocol-contracts — child-interest.md
description: "ErgoScript contract analysis: contracts/pools/drafts/SIGUSD-POOL/child-interest.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/drafts/SIGUSD-POOL/child-interest.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Child Interest Box

## Purpose

This contract manages a **child interest tracking box** that records historical interest rate calculations for a lending pool. It maintains an append-only history of computed interest rates based on utilization metrics, updating approximately every 20 blocks (~12 hours) with new rate snapshots computed from a polynomial formula using coefficients stored in a parameter box.

## Inputs / Outputs

### Inputs
- **SELF (Spending Input):** The child interest box itself, containing interest history and state
- **Data Input 0 (pool):** A pool box (identified by PoolNft) providing current borrowed token amounts and asset quantities
- **Data Input 1 (parameterBox):** A parameter box (identified by InterestParameterBoxNft) storing polynomial coefficients for interest rate calculation

### Outputs
- **OUTPUTS(0) (successor):** The updated child interest box with appended interest rate entry, same script and tokens, preserving ERG (minus execution fee)

## Key Logic

1. **Update Frequency Gating:** Transaction is only valid if at least `updateFrequency` (20) blocks have passed since the last recorded height (`HEIGHT - recordedHeight >= 20`)

2. **Utilization Calculation:**
   - Computes borrowed tokens: `MaximumBorrowTokens - pool.tokens(2)._2`
   - Calculates utilization ratio: `borrowed / (poolAssets + borrowed)`

3. **Interest Rate Computation via 5th-Degree Polynomial:**
   - Applies formula: `M + a + (b·x)/D + (c·x²)/D·M + (d·x³)/D·M² + (e·x⁴)/D·M³ + (f·x⁵)/D·M⁴`
   - Where `x` = utilization, `M` = 100,000,000 (InterestDenomination), `D` = 100,000,000 (CoefficientDenomination)
   - Coefficients (a–f) are retrieved from parameterBox.R4

4. **History Validation:**
   - Verifies that existing history entries remain unchanged
   - Validates that the new final entry equals the computed currentRate
   - Confirms history size incremented by exactly 1

5. **State Machine Invariants:**
   - Successor must have identical script bytes (same contract enforces successor)
   - Child index (R6) must remain constant
   - History size cannot exceed MaximumHistoryHeight (100 entries)
   - Final height delta must be valid (0–15 blocks into future)
   - ERG retained ≥ SELF.value minus MaximumExecutionFee (2,000,000 nanoERG)
   - Tokens (NFTs) must be preserved identically

6. **Box Authentication:**
   - Pool box confirmed via PoolNft in tokens(0)
   - Parameter box confirmed via InterestParameterBoxNft in tokens(0)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Interest history array; appended with new rate each update |
| **R5** | `Long` | Recorded block height of last update; used to gate update frequency |
| **R6** | `Int` | Child index identifier; immutable across state transitions |

## Tokens

- **PoolNft** (`UiocPX2UskC22zEyjduKAtm7XLWrfhDXn2KZrgAGbga`): Singleton token identifying the authoritative pool box; prevents spoofing pool state
- **InterestParameterBoxNft** (`5L4zTScZwqU5UUfibyPKgCXdSLEELKm87CEqqi217yhs`): Singleton token identifying the authoritative parameter box; prevents unauthorized coefficient changes
- **SELF.tokens:** Must be preserved in successor (typically includes the child interest box's own NFT for state continuity)

## Integration Pattern

### Off-Chain Bot / Dapp Responsibilities

1. **Monitoring:** Watch for blocks where `HEIGHT - recordedHeight >= updateFrequency`
2. **Data Fetch:** Retrieve current pool box state and parameter box (with coefficients)
3. **Calculation:** Compute utilization and apply polynomial formula locally
4. **Construction:** Build transaction with:
   - SELF as spending input
   - pool and parameterBox as data inputs
   - successor output with:
     - R4: interestHistory with new rate appended
     - R5: current HEIGHT
     - R6: unchanged childIndex
     - Value: SELF.value - fee (respecting MaximumExecutionFee)
     - Tokens: identical to SELF
     - Script: identical to SELF

5. **Validation:** Verify off-chain that all constraints will satisfy the contract before submission

### Transaction Structure
```
Inputs:  [ChildInterestBox]
DataInputs: [PoolBox, ParameterBox]
Outputs: [UpdatedChildInterestBox]
```

## Related Contracts

- **Pool Contract** (referenced via PoolNft): Maintains borrowed token state and pool assets; child interest box reads from it as authoritative source for utilization calculation
- **Parameter Contract** (referenced via InterestParameterBoxNft): Stores and manages polynomial coefficients; child interest box reads coefficients from its R4 register
- **Parent/Multi-Child Pattern:** The `childIndex` register suggests this is one of multiple sibling interest tracking boxes, likely managed by a parent contract that coordinates updates across children

---

## Security Observations

- **History Immutability:** Old history entries cannot be rewritten (checked via slice comparison)—provides cryptographic audit trail
- **Coefficient Mutability:** Coefficients can change (different parameter box state), affecting future rate calculations but not retroactively
- **Height Bounds:** `validDeltaFinalHeight` prevents successor from claiming far-future heights (anti-consensus manipulation)
- **Storage Rent:** Repeated appends to R4 increase box size; MaximumHistoryHeight (100) caps growth to prevent unbounded storage costs