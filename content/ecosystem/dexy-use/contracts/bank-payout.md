---
title: kushti/dexy-stable — payout.es
description: "ErgoScript contract analysis: contracts/bank/payout.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/payout.es
project: dexy-use
---
# ErgoScript Contract Analysis: `payout.es`

## Purpose

The **Payout contract** enforces the distribution of protocol rewards (payouts) from the Bank box to a Buyback box at regular intervals. It validates that withdrawals do not exceed 0.1% of bank reserves and only occur when the system maintains sufficient collateralization (≥1200%) and appropriate time delays (≈1 week) have elapsed.

---

## Inputs / Outputs

### Inputs
| Index | Box | Role |
|-------|-----|------|
| 0 | **Payout (SELF)** | State box holding the last payout timestamp; contains Payout NFT in tokens(0) |
| 1 | **Bank** | Reserve box holding DEXY tokens and ERG collateral |
| 2 | **Buyback** | Reward accumulation box; receives ERG payouts from Bank |

### Data Inputs
| Index | Box | Role |
|-------|-----|------|
| 0 | **Oracle Pool** | Provides current nanoErg/USD exchange rate via R4[Long] |
| 1 | **LP (reserved)** | Currently unused; available for future extensions |

### Outputs
| Index | Box | Role |
|-------|-----|------|
| 0 | **Payout (successor)** | Updated state box; R4 set to current HEIGHT |
| 1 | **Bank (updated)** | Bank with reduced ERG value; tokens preserved |
| 2 | **Buyback (updated)** | Buyback with increased ERG value (payment amount) |

---

## Key Logic

### Core Validation Flow

The contract enforces four independent constraint bundles:

#### 1. **Oracle Validity** (`validOracle`)
```
✓ Data input at index 0 contains Oracle NFT (identifies canonical oracle pool)
```
Ensures the exchange rate is from the trusted oracle pool, preventing price manipulation.

#### 2. **Collateralization Check** (`collateralized`)
```
✓ collateralization ratio = (oracleRate × dexyInCirculation × 12) < bank.value
```
- `oracleRate = oracleBox.R4[Long] / 1000` (nanoErg per USE, accounting for 3 decimals)
- `dexyInCirculation = initialDexyTokens - bankDexy` (DEXY not held in reserve)
- **Requirement**: At least **1200% collateralization** (12x buffer)

Prevents payouts that would compromise protocol solvency.

#### 3. **Payment Constraint** (`properPayment`)
```
✓ 0 < paymentAmount ≤ maxPaymentAmount
✓ maxPaymentAmount = bank.value / 1000  (0.1% of reserves)
✓ buybackOut.value - buybackIn.value == paymentAmount  (atomic transfer)
```
Limits each payout to 0.1% of bank reserves to prevent reserve depletion.

#### 4. **Time-Lock Enforcement** (`properHeight`)
```
✓ lastPayment + delayInPayments ≤ HEIGHT
✓ delayInPayments = 5040 blocks  (~1 week at 2 min/block)
```
Enforces minimum 5040-block spacing between consecutive payouts.

#### 5. **Successor State Integrity** (`validSuccessor`)
```
✓ propositionBytes preserved (script immutability)
✓ tokens preserved (Payout NFT stays in box)
✓ value ≥ SELF.value  (ERG amount non-decreasing)
✓ R4[Int] = HEIGHT ± buffer  (timestamp update within 5-block margin)
```
Ensures the Payout box remains a valid singleton and its state is atomically updated.

#### 6. **Bank Token Preservation** (`validBank`)
```
✓ bankOut.tokens == bankIn.tokens  (no token supply changes)
```
Prevents unauthorized token minting/burning during payout.

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|-----------|
| **R4** | `Int` | **Last payout height** — block height when the previous payout occurred; initialized to 0 | ✓ Updated each transaction |
| **R5–R9** | — | Unused | — |

**State Machine**: R4 forms a monotonically advancing timestamp that gates the next payout eligibility.

---

## Tokens

### Token IDs (Constants, injected via Context)

| Token | Position | Role | Box Presence |
|-------|----------|------|---|
| **oracleNFT** | — | Oracle pool singleton identifier | Data input box tokens(0) |
| **lpNFT** | — | LP box identifier (reserved for future use) | — |
| **Payout NFT** | tokens(0) | Singleton authenticator for this Payout box | SELF, successor |
| **buybackNFT** | tokens(0) | Singleton authenticator for Buyback box | BuybackBoxIn |

### Token Rules
- **Payout NFT**: Must be present and preserved in successor box (enforces single authorized payout contract per system)
- **Bank DEXY**: tokens(1) of Bank box; used to calculate DEXY in circulation
- **No minting/burning**: All token counts are validated for preservation

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

The off-chain payout bot must:

1. **Monitor Eligibility**
   - Track current HEIGHT vs. `lastPayment + 5040`
   - Query oracle pool via data input to fetch current exchange rate

2. **Construct Transaction**
   ```
   Transaction {
     inputs: [
       Box(Payout, R4=lastHeight, value≥minBoxValue),
       Box(Bank, tokens=[bankNFT, dexyToken(amount)], value=currentReserves),
       Box(Buyback, tokens=[buybackNFT], value=currentAccumulation)
     ],
     dataInputs: [
       Box(Oracle, tokens=[oracleNFT], R4=nanoErg
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
