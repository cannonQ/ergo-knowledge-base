---
title: StabilityNexus/BenefactionPlatform-Ergo — contract_v1_1.es
description: "ErgoScript contract analysis: contracts/bene_contract/contract_v1_1.es"
tags: [stabilitynexus, benefactionplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
contract_file: contracts/bene_contract/contract_v1_1.es
project: stabilitynexus-benefactionplatform-ergo
---
# ErgoScript Contract Analysis: Bene Fundraising Platform Contract

## Purpose

The **Bene Fundraising Platform Contract** (v1.1) enables projects to conduct token sales by accepting ERG contributions in exchange for **Participation Tokens (PFT)** and **Access Proof Tokens (APT)**. It manages fundraising state across multiple transaction types—purchases, refunds, withdrawals, and token exchanges—while enforcing temporal constraints, exchange rate validation, and developer fee distribution.

---

## Inputs / Outputs

### Transaction Type 1: Buy APT Tokens
| Aspect | Details |
|--------|---------|
| **Inputs** | 1. Project Bene Contract Box (SELF) 2. User Box (ERG funding source) |
| **Data Inputs** | None |
| **Outputs** | 1. Updated Project Bene Contract Box (replicated) 2. User Box (containing APT tokens) |

### Transaction Type 2: Refund APT Tokens
| Aspect | Details |
|--------|---------|
| **Inputs** | 1. Project Bene Contract Box (SELF) 2. User Box (containing APT to refund) |
| **Data Inputs** | None |
| **Outputs** | 1. Updated Project Bene Contract Box 2. User Box (containing refunded ERG) |

### Transaction Type 3: Withdraw Funds
| Aspect | Details |
|--------|---------|
| **Inputs** | 1. Project Bene Contract Box (SELF) |
| **Data Inputs** | None |
| **Outputs** | 1. Updated Project Bene Contract Box (optional; if partial withdrawal) 2. Project Address Box (90%-95% of ERG) 3. Developer Address Box (5%-10% dev fee) |

### Transaction Type 4: Withdraw Unsold Tokens
| Aspect | Details |
|--------|---------|
| **Inputs** | 1. Project Bene Contract Box (SELF) |
| **Data Inputs** | None |
| **Outputs** | 1. Updated Project Bene Contract Box 2. Project Address Box (unsold PFT) |

### Transaction Type 5: Add Tokens
| Aspect | Details |
|--------|---------|
| **Inputs** | 1. Project Bene Contract Box (SELF) 2. Project Address Box (token source) |
| **Data Inputs** | None |
| **Outputs** | 1. Updated Project Bene Contract Box (with increased token supply) |

### Transaction Type 6: Exchange Funding Tokens
| Aspect | Details |
|--------|---------|
| **Inputs** | TBD (not yet implemented) |
| **Data Inputs** | TBD |
| **Outputs** | TBD |

---

## Key Logic

### Core Validation Conditions

#### 1. **Box Replication Invariant** (`isSelfReplication`)
The contract enforces that OUTPUTS(0) is a valid state replica by verifying:
- **NFT ID Preservation**: `selfId == OUTPUTS(0).tokens(0)._1`
  - The singleton State NFT (Proof of Funding Token ID) must remain constant across state transitions.
- **Register Immutability**:
  - R4 (block height limit): `selfBlockLimit == OUTPUTS(0).R4[Int].get`
  - R5 (minimum tokens sold threshold): `selfMinimumTokensSold == OUTPUTS(0).R5[Long].get`
  - R7 (ERG-to-token exchange rate): `selfExchangeRate == OUTPUTS(0).R7[Long].get`
  - R8 (owner details): `selfOwnerDetails == OUTPUTS(0).R8[Coll[Byte]].get`
  - R9 (project metadata): `selfProjectMetadata == OUTPUTS(0).R9[Coll[Byte]].get`
- **Script Hash Preservation**: `selfScript == OUTPUTS(0).propositionBytes`
  - The ErgoTree bytecode must remain identical.
- **Token Slot Constraint**: `OUTPUTS(0).tokens.size ∈ {1, 2}`
  - Only APT (Access Proof Token) or APT + PFT (Proof of Funding Token) allowed; no additional tokens.

#### 2. **Temporal Lock Enforcement**
```
refund allowed iff currentBlockHeight > R4[Int]
withdrawal allowed iff R6[0] (sold counter) >= R5[Long]
```
- **R4** acts as a block-height deadline before which refunds/certain withdrawals are locked.
- Prevents premature capital extraction.

#### 3. **Token Accounting via Counter Registers** (R6)
R6 stores a `Coll[Long]` with three counters:
- **R6[0]**: `sold` – cumulative APT→PFT exchanges
- **R6[1]**: `refunded` – cumulative refund amount
- **R6[2]**: `exchanged` – auxiliary counter to prevent double-counting when APT→PFT conversion occurs

**Available Funding Token Function**:
```ergoscript
def temporaryFundingTokenAmountOnContract(contract: Box): Long = {
  val proof_funding_token_amount = if (contract.tokens.size == 1) 0L else contract.tokens(1)._2
  val sold = contract.R6[Coll[Long]].get(0)
  val refunded = contract.R6[Coll[Long]].get(1)
  val exchanged = contract.R6[Coll[Long]].get(2)
  
  proof_funding_token_amount - sold + refunded + exchanged
}
```
This ensures no tokens are double-counted during complex multi-step transactions.

#### 4. **Sigma Protocol Proposition Matching** (`isSigmaPropEqualToBoxProp`)
```ergoscript
def isSigmaPropEqualToBoxProp(propAndBox: (SigmaProp, Box)): Boolean = {
  val propBytes: Coll[Byte] = prop.propBytes
  val treeBytes: Coll[