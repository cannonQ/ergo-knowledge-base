---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — bounty_v1_0.es
description: "ErgoScript contract analysis: contracts/bounty_v1_0.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/bounty_v1_0.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: Bountiful Bounty Platform v1.0.0

## Purpose

The **Bountiful Bounty Platform Contract** is a multi-stage state machine that manages decentralized bounty creation, contribution tracking, and reward distribution on Ergo. It enables contributors to stake ERG, receive APT (contribution tokens) proportional to their stake, and exchange these for PFT (reward tokens) once funding goals are met. The contract enforces deadline-based refunds and developer fee collection upon bounty claim.

---

## Inputs / Outputs

### Transaction 1: Contribute to Bounty
**Inputs:**
- **Bounty Contract Box (SELF)** – Contains APT singleton token, ERG value, and stateful registers (R4–R9)
- **Contributor Box** – User's box with ERG to stake

**Outputs:**
- **Updated Bounty Contract Box** – Replicated with incremented `selfContributedCounter` (R6[0])
- **Contributor Receipt Box** – Receives APT tokens calculated as `erg_contributed / selfExchangeRate`

### Transaction 2: Refund Contribution
**Inputs:**
- **Bounty Contract Box (SELF)** – Post-deadline state
- **Contributor Box** – Holds APT tokens to refund

**Outputs:**
- **Updated Bounty Contract Box** – Incremented `selfRefundCounter` (R6[1])
- **Refunded Contributor Box** – Returns ERG = `apt_amount * selfExchangeRate`

### Transaction 3: Claim Bounty Reward
**Inputs:**
- **Bounty Contract Box (SELF)** – Post-deadline, threshold met

**Outputs:**
- **Updated Bounty Contract Box** (if partial claim) – Reduces ERG value
- **Solution Provider Box** – Receives `ERG * (100 - dev_fee) / 100`
- **Developer Fee Box** – Receives `ERG * dev_fee / 100`

### Transaction 4: Withdraw Unused Reward Tokens
**Inputs:**
- **Bounty Contract Box (SELF)**

**Outputs:**
- **Updated Bounty Contract Box** – PFT amount reduced
- **Creator Box** – Receives unused PFT tokens

### Transaction 5: Add More Reward Tokens
**Inputs:**
- **Bounty Contract Box (SELF)**
- **Creator Box** – Contains additional PFT tokens

**Outputs:**
- **Updated Bounty Contract Box** – PFT amount incremented

### Transaction 6: Exchange Contribution Tokens for Reward Tokens
**Inputs:**
- **Bounty Contract Box (SELF)**
- **Contributor Box** – Holds APT tokens

**Outputs:**
- **Updated Bounty Contract Box** – Incremented `selfAuxiliarExchangeCounter` (R6[2])
- **Contributor Box** – Receives PFT tokens at 1:1 ratio

---

## Key Logic

### Core Validation Conditions

1. **Box Replication Invariant** (`isSelfReplication`):
   - Output[0] must replicate all immutable properties: bounty ID (APT token), block deadline (R4), minimum threshold (R5), exchange rate (R7), creator details (R8), metadata (R9), and script bytecode
   - Ensures state machine integrity across transactions
   - Validates that only APT and optionally PFT tokens exist (no additional native tokens)

2. **Contribution Accounting** (`temporaryContributionTokenAmountOnContract`):
   - Available APT for exchange = `PFT_on_contract - contributed + refunded + exchanged`
   - Prevents double-counting of contributed ERG
   - Accounts for three distinct counters in R6: contribution total, refund total, and APT→PFT exchanges

3. **Deadline Enforcement**:
   - Refunds only permitted if `current_height > R4`
   - Claims only permitted if `current_height > R4` AND `selfContributedCounter >= selfMinimumContribution`

4. **Exchange Rate Validation**:
   - APT minted = `erg_contributed / selfExchangeRate` (integer division)
   - APT refunded = `apt_amount * selfExchangeRate`
   - PFT distributed at 1:1 ratio with APT exchanged

5. **Developer Fee Calculation**:
   - Deducted from claimed bounty: `dev_fee` percentage of total ERG
   - Routed to separate contract verified by `$dev_fee_contract_bytes_hash`

6. **Proposition Bytes Comparison** (`isSigmaPropEqualToBoxProp`):
   - Handles two ErgoTree serialization formats:
     - **Format 0**: Direct byte equality
     - **Format non-0**: Skips 2–3 byte VLQ-encoded length header before comparing payload
   - Essential for verifying script identity in replicated outputs

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Int` | **Deadline block height** – After this height, bounty becomes claimable or refundable; enforces temporal constraints |
| **R5** | `Long` | **Minimum contribution threshold (ERG)** – Required to make bounty claimable; prevents claiming with insufficient funds |
| **R6** | `Coll[Long]` (3 elements) | **State counters**: [0] = total ERG contributed, [1] = total ERG refunded, [2] = total APT exchanged for PFT; tracks transaction history |
| **R7** | `Long` | **Exchange rate (ERG per APT)** – Immutable ratio for mint/burn calculations; enables proportional token issuance |
| **R8** | `Coll[Byte]` | **Creator metadata (Base58-encoded JSON)** – Stores bounty creator's details; immutable reference data |
| **R9** | `Coll[Byte]` | **Bounty metadata (Base58-encoded JSON)** – Contains title, description, requirements; immutable specification of bounty terms |

---

## Tokens

### 1. APT