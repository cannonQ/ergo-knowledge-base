---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — reputation-v0.es
description: "ErgoScript contract analysis: contracts/ergo-bounty-contracts/in_development/reputation-v0.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/ergo-bounty-contracts/in_development/reputation-v0.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: Bountiful Reputation System

## Purpose

The **Bountiful Reputation System Contract** is an on-chain reputation tracking mechanism for judges within the bounty platform. It manages reputation events (feedback, judgments, profile creation) using Reputation Badge Tokens (RBTs) as singleton identifiers, enabling transparent, auditable judge performance tracking while preventing Sybil attacks through minimal ERG fees and cryptographic verification.

---

## Inputs / Outputs

### Inputs
- **Primary Input (SELF)**: A Box containing:
  - Exactly one RBT (Reputation Badge Token) with amount = 1L
  - 6 registers (R4–R9) encoding reputation event metadata
  - Minimum value ≥ 1,000,000 nanoERG (0.001 ERG) for Sybil attack prevention
  
- **Data Inputs (CONTEXT.dataInputs)**: Zero or more read-only boxes providing context:
  - Judge profile boxes with R4 containing `SigmaProp` (judge's public key)
  - Bounty reference boxes with token IDs
  - Signer credentials for authentication

### Outputs
- **Output Box (OUTPUTS(0))**: A new Box with:
  - Same RBT token issued (tokenId = INPUTS(0).id, amount = 1L)
  - Updated/validated registers R4–R9 containing event data
  - Minimum box value maintained (storage rent)

---

## Key Logic

### 1. **Token Issuance & Validation (`contractIsTokenIssuer`)**
   - Verifies the RBT token is **newly created** from the first input's box ID
   - Ensures exactly one token with amount = 1L exists in output
   - Acts as a **Singleton / State NFT** for immutable reputation event tracking

### 2. **Register Structure Validation (`hasValidRegisters`)**
   - **R4 (Event Type)**: Must be one of: `judge-profile`, `judge-feedback`, `judgment`, `spam-alert`, `reputation-query`, `reputation-calc`, `external-verification`
   - **R5 (Reference Type)**: Non-empty Coll[Byte] (what entity type is referenced)
   - **R6 (Target ID)**: Non-empty Coll[Byte] (judge address being evaluated)
   - **R7 (Author Address)**: Non-empty Coll[Byte] (who created the event)
   - **R8 (Sentiment)**: Boolean flag (true = positive, false = negative)
   - **R9 (Metadata)**: Non-empty Coll[Byte] (JSON-encoded comment, timestamp, etc.)

### 3. **Signer Authentication (`signerIsAuthor` & similar)**
   - Extracts `SigmaProp` from data input R4
   - Compares signer's `propBytes` (Sigma protocol proof) against stored author address (R7)
   - Ensures cryptographic binding of reputation event to creator identity
   - **Sigma protocol verification**: Off-chain signature must be valid for transaction acceptance

### 4. **Judge Profile Creation (`isCreateJudgeProfile`)**
   - Event type must be `judge-profile`
   - Creator (`SigmaProp` from data input) must equal target (R6)
   - Self-verification prevents impersonation
   - Enforces minimum 0.001 ERG fee to prevent spam/Sybil attacks

### 5. **Feedback Addition (`isAddJudgeFeedback`)**
   - Event type = `judge-feedback`
   - Reference type (R5) must be `judge-profile`
   - Target judge must exist (simplified check; real implementation queries on-chain)

### 6. **Reputation Query (`isQueryJudgeReputation`)**
   - Data input provides judge's public key (R4)
   - Output creates a `reputation-query` event referencing the judge
   - Enables off-chain reputation aggregation without state mutations

### 7. **Judgment Recording (`isRecordJudgment`)**
   - Event type = `judgment`
   - Reference (R5) must contain bounty ID from data input token
   - Judge's `SigmaProp` must match signer (judge performs judgment)
   - Cryptographically links judgment to specific bounty & judge

### 8. **Proposition Bytes Comparison (`isSigmaPropEqualToBoxProp`)**
   - Compares two serialized ErgoTree representations:
     - `prop.propBytes`: Direct Sigma protocol proof
     - `box.propositionBytes`: ErgoTree with potential size encoding prefix
   - Handles variable-length quantity (VLQ) encoding offset (byte 0 prefix)
   - Critical for matching signer identity across contexts

---

## Registers Used

| Register | Type | Purpose | Event Types |
|----------|------|---------|-------------|
| **R4** | `Coll[Byte]` | **Event Type** – categorical classification of reputation event | All paths |
| **R5** | `Coll[Byte]` | **Reference Type** – entity class being referenced (e.g., "judge-profile", bounty ID) | Feedback, Judgment |
| **R6** | `Coll[Byte]` | **Target ID** – address/key of judge under evaluation | Profile, Feedback, Judgment |
| **R7** | `Coll[Byte]` | **Author Address** – creator's address; must match signer for CREATE events | All paths |
| **R8** | `Boolean` | **Sentiment** – reputation polarity (true = positive, false = negative) | Feedback, Judgment |
| **R9** | `Coll[Byte]` | **Metadata** – JSON-encoded comment, timestamp, proof hash, external verification data | All paths |

**Data Input Registers:**
- **Data Input R4**: `SigmaProp` – signer's public key/Sigma protocol proof for authentication

---

## Tokens

### Reputation Badge Token (RBT)
- **Token ID**: Generated as `INPUTS(0).id` (box ID of input that creates it)
- **Amount**: Always 1L (singleton constraint)
- **Purpose**: 
  - Serves