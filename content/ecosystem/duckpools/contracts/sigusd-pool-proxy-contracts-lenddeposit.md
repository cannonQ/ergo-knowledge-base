---
title: duckpools/lend-protocol-contracts — lendDeposit.md
description: "ErgoScript contract analysis: contracts/pools/drafts/SIGUSD-POOL/Proxy-Contracts/lendDeposit.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/drafts/SIGUSD-POOL/Proxy-Contracts/lendDeposit.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: lendDeposit

## Purpose

This contract serves as a **deposit/lending request proxy** in the DuckPools lending protocol. It validates either a **refund path** (when lending conditions aren't met) or an **exchange path** (when the user receives lend pool tokens in return for their deposit). The contract acts as a state machine controlling conditional fund release based on timing and token fulfillment.

---

## Inputs / Outputs

### Expected Inputs
- **SELF (spending box):** The deposit request box itself, containing user information and request parameters in registers.

### Expected Outputs

#### Refund Path (OUTPUTS.size < 3):
- **OUTPUTS(0):** Refund box sent back to the user
  - Must have propositionBytes matching the original user's public key
  - Can optionally carry a reference to SELF via R4 for multi-box refund tracking

#### Exchange Path (OUTPUTS.size ≥ 3):
- **OUTPUTS(0) & OUTPUTS(1):** Intermediate outputs (validation doesn't constrain these directly)
- **OUTPUTS(2):** Successor box (the funded result)
  - Must be locked to the user's script
  - Must contain the lend pool tokens (at least requestAmount quantity)
  - Can reference SELF via R7 for multi-box spend safety

---

## Key Logic

### Branch 1: Refund Condition (OUTPUTS.size < 3)
The contract validates a **refund-to-user** path when fewer than 3 outputs are present:

1. **validRefundScript:** Refund box must be locked to the original user's public key (proposition bytes match)
2. **validDeltaErg:** The ERG difference between input and refund output must not exceed `minTxFee` (1,000,000 nanoERG), ensuring minimal slippage
3. **validHeight:** Current block HEIGHT must be ≥ `publicRefund` (stored in R6), enforcing a timeout unlock after which refunds become available
4. **multiBoxRefund:** If the refund box has an R4 register, it must point back to SELF.id, providing traceability for multi-box refund scenarios
5. **Result:** All four conditions must be true (AND logic)

### Branch 2: Exchange Condition (OUTPUTS.size ≥ 3)
The contract validates a **token exchange** path when 3+ outputs are present:

1. **validSuccessorScript:** The successor box (OUTPUTS(2)) must be locked to the user's public key
2. **validTokens:** 
   - The successor box must carry tokens
   - The **first token** (index 0) must have ID matching `lendPoolToken` (from R7)
   - The quantity of that token must be **≥ requestAmount** (from R5)
3. **multiBoxSpendSafety:** If the successor box has an R7 register, it must contain SELF.id for spend safety tracking
4. **Result:** All three conditions must be true (AND logic)

### Overall Control Flow
```
if (OUTPUTS.size < 3) → validate refund
else                 → validate exchange
```
**Only one path succeeds per transaction.** The contract rejects transactions that satisfy neither condition.

---

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R4** | `Coll[Byte]` | SELF | User's public key / script (recipient address) |
| **R5** | `Long` | SELF | Requested amount of lend pool tokens to receive |
| **R6** | `Long` | SELF | Block height at which refund becomes available (timeout) |
| **R7** | `Coll[Byte]` | SELF | Lend pool token ID (identifies which SigmaUSD or other token is being lent) |
| **R4** | `Coll[Byte]` | OUTPUTS(0) in refund path | Optional: SELF.id reference for multi-box refund tracking |
| **R7** | `Coll[Byte]` | OUTPUTS(2) in exchange path | Optional: SELF.id reference for multi-box spend safety |

---

## Tokens

### Lend Pool Token
- **Stored in:** R7 (as `Coll[Byte]` token ID)
- **Purpose:** Identifies the native token (likely SigmaUSD or similar) that the protocol will lend to the user
- **Validation:** In the exchange path, the first token in OUTPUTS(2) must match this ID and have quantity ≥ requestAmount
- **Token ID Rule:** The token ID is a unique 32-byte identifier derived from the UTXO that created the token

### No other tokens are directly validated, but the contract assumes:
- The successor box may contain multiple tokens (only the first is checked)
- ERG balances are tracked via `.value` properties

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

#### Constructing a Refund Transaction
1. **Monitor:** Watch for deposit boxes reaching their timeout height (R6 ≤ current HEIGHT)
2. **Construct:** Create a transaction with:
   - **Input:** The deposit box (SELF)
   - **Output(s):** Exactly 1–2 outputs (OUTPUTS.size < 3):
     - Output 0: Refund box with:
       - `value` ≤ SELF.value − minTxFee
       - `propositionBytes` = user's public key (from R4)
       - Optional R4 = SELF.id (for multi-box tracking)
   - **Fee:** At least minTxFee (1,000,000 nanoERG)
3. **Submit:** Send transaction; script validates via the refund branch

#### Constructing an Exchange Transaction
1. **Trigger:** When lending terms are met (collateral posted, pool has capital)
2. **Construct:** Create a transaction with:
   - **Input:** The deposit box (SELF)
   - **Outputs:** At least 3 outputs:
     - Output 0 & 1: Service/fee boxes or other protocol outputs (unconstrained by this script)
     - Output 2 (successor