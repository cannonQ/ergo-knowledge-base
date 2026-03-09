---
title: kushti/dexy-stable — payout.es
description: "ErgoScript contract analysis: contracts/bank/payout.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/payout.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `contracts/bank/payout.es`

## Purpose

This contract enforces periodic payout (reward distribution) logic for the Dexy stablecoin protocol. It validates that rewards can only be extracted from the Bank box when the system maintains minimum collateralization (800%), respects payment frequency constraints (≈1 week delays), and limits individual payouts to 0.5% of reserves.

## Inputs / Outputs

### Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Payout Box** (SELF) | State machine controlling payout logic; holds Payout NFT; tracks last payment height in R4 |
| 1 | **Bank Box** | Holds protocol reserves (Ergs) and Dexy token inventory; source of payout funds |
| 2 | **Buyback Box** | Receives payout amount; typically used for reward distribution or buy-back mechanics |

### Data Inputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Oracle Box** | Provides current gold price (Ergs per kg) via R4; authenticated by oracleNFT |
| 1 | **LP Box** | (Reference only; not actively used in validation logic) |

### Outputs
| Index | Box Type | Purpose |
|-------|----------|---------|
| 0 | **Payout Box (Successor)** | Updated state: same script, NFT, value ≥ input; R4 reset to current HEIGHT |
| 1 | **Bank Box (Successor)** | Same tokens and script; Erg value reduced by `paymentAmount` |
| 2 | **Buyback Box (Successor)** | Erg value increased by `paymentAmount` (receives payout) |

## Key Logic

### 1. **Collateralization Check** (`collateralized`)
```
oracleRate × dexyInCirculation × 8 < bankBoxIn.value
```
- Ensures Bank maintains >800% collateral ratio (8x over-collateralization)
- `oracleRate` = nanoErgs per Dexy (derived by dividing oracle's nanoErgs/kg by 1,000,000)
- `dexyInCirculation` = `initialDexyTokens - bankDexy` (total issued Dexy minus Bank's held reserve)
- **No payout allowed if under-collateralized**

### 2. **Payment Amount Validation** (`properPayment`)
- `maxPaymentAmount = bankBoxIn.value / 200` → maximum 0.5% of reserves per payout
- `paymentAmount = bankBoxIn.value - bankBoxOut.value` → actual Ergs extracted
- Validates:
  - Positive payment (`paymentAmount > 0`)
  - Within limit (`paymentAmount ≤ maxPaymentAmount`)
  - Buyback receives exactly the payout amount (atomic transfer)

### 3. **Temporal Constraint** (`properHeight`)
- `lastPayment + delayInPayments ≤ HEIGHT`
- Enforces ≈5,040 block delay (≈1 week) between consecutive payouts
- Prevents reward extraction frequency abuse

### 4. **State Continuity** (`properNewR4`)
- Successor's R4 must be ≥ `HEIGHT - 5` (within 5-block error margin)
- Ensures current height is recorded for next payout delay calculation

### 5. **Box Preservation**
- **Bank**: Tokens unchanged (Dexy inventory preserved)
- **Payout (Successor)**:
  - Proposition bytes identical (script locked)
  - Payout NFT preserved (Singleton authentication)
  - Value ≥ input (no Erg extraction from payout box itself)

### 6. **Oracle Validation** (`validOracle`)
- Data input's first token must be `oracleNFT`
- Ensures price feed authenticity

## Registers Used

| Register | Type | Purpose | Status |
|----------|------|---------|--------|
| **R4** (Payout Box) | `Int` | Height of last successful payout | Read (input), Write (output successor) |
| **R4** (Oracle Box) | `Long` | Nanoergs per 1 kg of gold (data input) | Read-only |

- **Non-nullable R4 in Payout**: Set to 0 initially; incremented to `HEIGHT` on each payout
- **Oracle R4 scaling**: Divided by 1,000,000 to convert kg-basis to Dexy (1 mg gold) basis

## Tokens

| Token ID | Box | Purpose | Role |
|----------|-----|---------|------|
| **oracleNFT** | Oracle (data input, tokens(0)) | Authenticates oracle pool box | Singleton marker |
| **lpNFT** | LP box (referenced but unused) | Liquidity provider state token | Not validated |
| **buybackNft** | Buyback input (tokens(0)) | Authenticates buyback/reward distribution box | Singleton marker |
| **Payout NFT** | Payout (SELF, tokens(0)) | Authenticates this payout controller | Singleton marker |
| **Dexy Token** | Bank (tokens(1)) | Protocol stablecoin; quantity tracked for collateral calculation | State variable |

- **Token ID Rule**: NFTs enforce unique box identity; contract verifies presence to confirm correct box type

## Integration Pattern

### Off-Chain Bot / Dapp Responsibilities

1. **Monitor payout eligibility**:
   - Query current HEIGHT, last payout (R4 from Payout box)
   - Check `HEIGHT ≥ lastPayment + 5040`
   - Fetch oracle rate from Oracle box (R4)
   - Calculate `dexyInCirculation` and verify collateral ratio

2. **Construct transaction**:
   - Select Payout, Bank, and Buyback boxes as inputs
   - Fetch Oracle box as data input
   - Calculate `paymentAmount ≤ min(maxPaymentAmount, bankValue / 200)`
   - Create Payout successor: same script, increment R4 to `HEIGHT`