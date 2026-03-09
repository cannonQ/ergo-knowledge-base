---
title: StabilityNexus/BenefactionPlatform-Ergo — dev_fee.es
description: "ErgoScript contract analysis: contracts/dev_fee_contract/dev_fee.es"
tags: [stabilitynexus, benefactionplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
contract_file: contracts/dev_fee_contract/dev_fee.es
project: stabilitynexus-benefactionplatform-ergo
---
# ErgoScript Contract Analysis: BeneFactionPlatform Dev Fee Contract

## Purpose

This contract guards a fee collection box for the Bene Fundraising Platform and enforces deterministic distribution of accumulated fees (ERG or tokens) to four pre-configured recipients. It validates that collected fees are split according to fixed proportions (32% Bruno, 32% Lgd, 32% Jossemi, 4% The Stable Order) in a single atomic transaction.

## Inputs / Outputs

### Inputs
- **Self Box (SELF)**: The fee box containing:
  - ERG value (minimum 5,000,000 nanoERG for box preservation)
  - Optional tokens to distribute
  - Register R4: Token ID (if distributing non-ERG assets; empty/absent for ERG distribution)

### Outputs
Exactly 4 output boxes in fixed order:
1. **OUTPUTS(0)**: Bruno's recipient box (receiving 32% of devAmount)
2. **OUTPUTS(1)**: Lgd's recipient box (receiving 32% of devAmount)
3. **OUTPUTS(2)**: Jossemi's recipient box (receiving 32% of devAmount)
4. **OUTPUTS(3)**: The Stable Order recipient box (receiving 4% of devAmount)

Each output must:
- Hold the correct proportional amount (ERG or specified token)
- Match the recipient's hardcoded address (via `propositionBytes` comparison)

## Key Logic

### Validation Flow

1. **Token Type Detection**
   - Reads R4 for optional token ID
   - If R4 contains data: token distribution mode
   - If R4 empty/absent: ERG distribution mode

2. **Amount Extraction** (`getDistributionAmount`)
   - Token mode: filters recipient's tokens for matching token ID, returns amount
   - ERG mode: returns box's ERG value (`box.value`)

3. **Proportional Splitting**
   - Calculates total devAmount from all four outputs
   - Applies fee shares: `(numerator × devAmount) / 100`
     - Bruno: 32/100
     - Lgd: 32/100
     - Jossemi: 32/100
     - Order: 4/100

4. **Constraints Enforced**
   - **Minimum total value**: All outputs combined ≥ 5,000,000 nanoERG (storage rent requirement)
   - **Recipient validation**: Each output's `propositionBytes` must match hardcoded addresses
   - **Amount precision**: Each recipient receives *exact* proportional amount (no rounding tolerance)

5. **Context Requirements**
   - No data inputs required
   - No context variables (`_`) used
   - No miner fee paid from this box (externally funded)

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** | `Coll[Byte]` | Optional token ID for non-ERG distributions. Empty byte collection for ERG mode. | Read-only |

**Register Semantics**:
- Absent or empty R4 → distribute native ERG (`box.value`)
- Non-empty R4 → token ID identifying which token to distribute across recipients

## Tokens

### Native Token Handling
- **Optional token distribution**: Box may contain a secondary token specified by R4
- **Token ID rule**: Only one token type supported (R4 stores single ID)
- **Distribution logic**: `box.tokens.filter` extracts matching token by ID, uses tuple `(Coll[Byte], Long)` format

### Authentication
- No NFT/singleton pattern used
- Recipient validation via hardcoded Sigma propositions (`PK` addresses) embedded as compile-time constants

## Integration Pattern

### Off-Chain Requirements

An off-chain bot or fee aggregation service must:

1. **Monitor fee accumulation**
   - Track this box's ERG/token balance over time

2. **Trigger fee distribution transaction**
   - Construct transaction with:
     - Input: current fee box (SELF)
     - Outputs: 4 recipient boxes in exact order
     - Each output funded to correct proportional amount
   - No additional outputs (strict output count)

3. **Verify box construction**
   - Ensure total output ≥ 5,000,000 nanoERG
   - Set each output's `ergoTree` to recipient's address (PK proposition)
   - If token distribution: include matching token in each recipient's tokens list
   - If ERG distribution: fund recipient boxes entirely via `.value` field

4. **Transaction signing**
   - Input box guarded by this ErgoScript must satisfy `sigmaProp(validFeeDistributionTx)`
   - Wallet provides Sigma proof of fee distribution validity

### Constant Segregation
Compile-time constants (`$bruno`, `$lgd`, `$jm`, `$order`) injected during contract compilation; enables address updates without bytecode changes.

## Related Contracts

**Identifiable Dependencies** (from comments):

1. **Phoenix HodlERG Fee Contract** (ancestor/inspiration)
   - Referenced as original design basis
   - Similar multi-recipient fee distribution pattern

2. **Bene Fundraising Platform** (parent system)
   - This contract is a component; likely composed with:
     - **Campaign box contracts**: accumulate funds and forward to this fee box
     - **Benefactor reward contracts**: may trigger fee distributions
     - **Treasury/order management**: The Stable Order recipient may manage overall platform treasury

### Contract Composition Pattern
```
Fundraising Inputs
    ↓
Campaign/Collection Boxes
    ↓
Dev Fee Box (this contract)
    ↓ (Fee Distribution Tx)
Recipient Boxes (Bruno, Lgd, Jm, Order)
```

---

## Technical Notes

### Storage Rent Compliance
- Minimum box value (5M nanoERG) ensures output boxes survive storage rent decay
- Ergo's storage rent mechanism requires periodic activity; outputs must maintain minimum balance

### Invariants Maintained
- **Fee ratio invariant**: `bruno + lgd + jm + order = 100%` (32+32+32+4)
- **All-or-nothing**: Either all 4 recipients receive exact amounts, or entire transaction fails (atomic execution)