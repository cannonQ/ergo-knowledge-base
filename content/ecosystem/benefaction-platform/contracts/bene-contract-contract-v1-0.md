---
title: StabilityNexus/BenefactionPlatform-Ergo — contract_v1_0.es
description: "ErgoScript contract analysis: contracts/bene_contract/contract_v1_0.es"
tags: [stabilitynexus, benefactionplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
contract_file: contracts/bene_contract/contract_v1_0.es
project: stabilitynexus-benefactionplatform-ergo
---
# ErgoScript Contract Analysis: Bene Fundraising Platform Contract v1.0.0

## Purpose

The **Bene Fundraising Platform Contract** is a multi-stage eUTXO-based fundraising mechanism that enables projects to receive ERG funding in exchange for participation tokens (APT – Authentication/Project Tokens, and PFT – Proof of Funding Tokens). The contract manages the complete lifecycle of a fundraising campaign, including token purchases, refunds, fund withdrawals, and token exchanges, with built-in developer fee mechanisms and block-height-based time locks.

---

## Inputs / Outputs

### **Transaction 1: Buy APT Tokens**
| Aspect | Details |
|--------|---------|
| **Inputs** | • Project Bene Contract Box (SELF) containing APT NFT and PFT<br>• User Box containing ERG for purchase |
| **Outputs** | • Updated Project Bene Contract Box (SELF replica with updated counters)<br>• User Box containing newly minted APT tokens |
| **Data Inputs** | None |

### **Transaction 2: Refund APT Tokens**
| Aspect | Details |
|--------|---------|
| **Inputs** | • Project Bene Contract Box (SELF)<br>• User Box containing APT tokens to refund |
| **Outputs** | • Updated Project Bene Contract Box (with refund counter incremented)<br>• User Box containing refunded ERG |
| **Data Inputs** | None |

### **Transaction 3: Withdraw Funds**
| Aspect | Details |
|--------|---------|
| **Inputs** | • Project Bene Contract Box (SELF) |
| **Outputs** | • Updated/Depleted Project Bene Contract Box (optional, if partial withdrawal)<br>• Project Address Box (100% - dev_fee in ERG)<br>• Developer Address Box (dev_fee % in ERG) |
| **Data Inputs** | None |

### **Transaction 4: Withdraw Unsold Tokens**
| Aspect | Details |
|--------|---------|
| **Inputs** | • Project Bene Contract Box (SELF) |
| **Outputs** | • Updated Project Bene Contract Box<br>• Project Address Box (unsold PFT tokens) |
| **Data Inputs** | None |

### **Transaction 5: Add Tokens**
| Aspect | Details |
|--------|---------|
| **Inputs** | • Project Bene Contract Box (SELF)<br>• Project Address Box (containing additional tokens) |
| **Outputs** | • Updated Project Bene Contract Box (with additional PFT added) |
| **Data Inputs** | None |

### **Transaction 6: Exchange Funding Tokens**
| Aspect | Details |
|--------|---------|
| **Inputs** | • Project Bene Contract Box (SELF) |
| **Outputs** | • Updated Project Bene Contract Box |
| **Data Inputs** | None |
| **Note** | *Specification incomplete in source* |

---

## Key Logic

### **Core Invariants & Validation Conditions**

#### **Self-Replication (Box Propagation)**
The contract enforces strict preservation of contract state across all transactions via the `isSelfReplication` boolean:

- **NFT ID Immutability**: The Singleton token (`SELF.tokens(0)._1`) must remain identical in the output box (`OUTPUTS(0).tokens(0)._1`). This ensures the contract box is uniquely identified via the **Token ID rule** (native token used as state machine identifier).
- **Register Preservation**:
  - R4 (Block Limit): Fundraising period deadline must remain constant
  - R5 (Minimum Tokens Sold): Funding threshold unchanged
  - R7 (Exchange Rate): ERG-to-token conversion ratio locked
  - R8, R9 (Owner Details, Project Metadata): Immutable Base58-encoded JSON strings
- **Script Integrity**: `selfScript == OUTPUTS(0).propositionBytes` ensures the ErgoTree is replicated without modification
- **PFT Handling**: Proof of Funding Token amount must remain constant unless explicitly modified in designated transactions
- **Token Slot Constraint**: Output box must contain exactly 1 or 2 tokens (APT + optional PFT)

#### **Temporal Constraints (Block Height Lock)**
```
Block Height >= R4 ⇒ Refunds & Withdrawals Permitted
Block Height < R4 ⇒ Only Token Purchases Allowed
```
This implements a **soft time lock** via blockchain height, preventing premature fund withdrawal.

#### **Funding Threshold Logic**
```
IF tokens_sold >= R5 (minimum_tokens_sold):
  ⇒ Withdrawal & unsold token recovery enabled
ELSE:
  ⇒ Only refunds permitted (if block height >= R4)
```

#### **Counter-Based State Tracking (R6: Coll[Long])**
The contract maintains three counters in R6 to track cumulative state:
- **R6[0]**: `sold_counter` – Total APT/PFT sold
- **R6[1]**: `refunded_counter` – Total APT refunded
- **R6[2]**: `exchanged_counter` – Total APT exchanged to PFT

**Auxiliary Exchange Counter Rationale**: The `exchanged_counter` prevents double-counting when APT → PFT swaps occur, ensuring accurate available liquidity:

```ergoscript
temporaryFundingTokenAmountOnContract = PFT_amount - sold + refunded + exchanged
```

This formula ensures the contract always knows how many PFT are available for future purchases.

#### **ERG Exchange Validation**
Each token purchase/refund transaction must preserve the exchange rate:
```
ERG_transferred = APT_amount × R7 (exchange_rate_erg_per_token)
```

#### **Developer Fee Calculation**
On fund withdrawal, ERG is split:
```
Project_ERG = Total_ERG × (100 - $dev_fee) / 100
Developer_ERG = Total_ERG × $dev_fee / 100
```

The developer address is identified by matching the **Blake2b-256