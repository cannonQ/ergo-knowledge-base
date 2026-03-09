---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — bounty_contract.es
description: "ErgoScript contract analysis: bounty_contract.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: bounty_contract.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: Bountiful Bounty Platform

## Purpose

The Bountiful Bounty Platform Contract implements a decentralized bounty management system on Ergo, enabling creators to post bounties with deadlines and reward pools, accepting solution submissions from participants, and distributing rewards based on creator judgment. It manages the complete bounty lifecycle: creation, submission tracking, judgment, reward distribution, refunds, and metadata updates.

---

## Inputs / Outputs

### Submit a Solution Transaction
**Inputs:**
- **Primary Input (SELF):** Bountiful Bounty Contract Box
  - Contains: BBT token (State NFT), submission statistics (R6), bounty metadata (R9)
  - Value: ERG reward pool
- **Secondary Input:** Submitter box with submission data

**Outputs:**
- **Updated Bountiful Bounty Contract Box**
  - Submission counter (R6) incremented by 1
  - Submissions root hash updated in R9 (JSON metadata)
  - All other registers preserved

**Constraints:**
- `HEIGHT <= selfDeadline` (submission window open)
- `selfSubmissionStats(0)` incremented exactly by 1
- BBT token retained as State NFT in output
- Contract script replicated identically

---

### Judge a Submission Transaction
**Inputs:**
- **Primary Input (SELF):** Bountiful Bounty Contract Box
- **Data Input:** Box containing judgment decision and submission ID

**Outputs:**
- **Updated Bountiful Bounty Contract Box**
  - Either `selfSubmissionStats(1)` (accepted) or `selfSubmissionStats(2)` (rejected) incremented by 1
  - Judgments root hash updated in R9
  - Value and deadline preserved

**Validation:**
- Must be signed by creator (SigmaProp from R8)
- Judgment counter logic: exactly one counter increments
- Contract script replication enforced

---

### Withdraw Reward Transaction
**Inputs:**
- **Primary Input (SELF):** Bountiful Bounty Contract Box

**Data Inputs:**
- Box containing: `winner_address`, `judgment_height`

**Outputs:**
- **Winner Reward Box:** 
  - Value: `selfRewardAmount - development_fee`
  - Locked to `winner_address`
- **Development Fee Box:**
  - Value: calculated fee portion
  - Locked to `$dev_wallet_address` (Constant)

**Validation:**
- `selfAcceptedSubmissions >= 1` (minimum one accepted)
- `selfTotalSubmissions >= selfMinSubmissions` (minimum threshold met)
- `HEIGHT >= judgment_height + dispute_period` (dispute period elapsed)
- Fee calculation verified before distribution

---

### Refund Bounty Transaction
**Inputs:**
- **Primary Input (SELF):** Bountiful Bounty Contract Box

**Outputs:**
- **Refund Box:**
  - Value: `selfValue` (full ERG amount minus tx fee)
  - Locked to creator (derived from R8 public key)

**Validation:**
- `HEIGHT > selfDeadline` (deadline passed)
- Either `selfTotalSubmissions < selfMinSubmissions` OR `selfAcceptedSubmissions == 0`
- Refund destination must be creator's address

---

### Add More Funds Transaction
**Inputs:**
- **Primary Input (SELF):** Bountiful Bounty Contract Box
- **Creator-signed transaction with additional ERG**

**Outputs:**
- **Updated Bountiful Bounty Contract Box:**
  - Value: `selfValue + additional_funds`
  - R7 (reward): updated to new total
  - All other registers unchanged

**Validation:**
- Transaction signed by creator (R8 SigmaProp)
- Only value and R7 reward amount change
- Script replication enforced

---

### Extend Deadline Transaction
**Inputs:**
- **Primary Input (SELF):** Bountiful Bounty Contract Box
- **Creator-signed transaction**

**Outputs:**
- **Updated Bountiful Bounty Contract Box:**
  - R4: new deadline (block height)
  - All other registers unchanged

**Validation:**
- Signed by creator
- `HEIGHT < selfDeadline` (before current deadline)
- `new_deadline > selfDeadline` (extended in future)
- Script replication enforced

---

### Update Metadata Transaction
**Inputs:**
- **Primary Input (SELF):** Bountiful Bounty Contract Box
- **Creator-signed transaction**

**Outputs:**
- **Updated Bountiful Bounty Contract Box:**
  - R9: updated JSON metadata
  - Version field in R9 incremented
  - Value, deadline, reward unchanged

**Validation:**
- Signed by creator
- `HEIGHT < selfDeadline` (metadata locked after deadline)
- Version increment verified
- Script replication enforced

---

## Key Logic

### Core Validation Invariants

1. **State NFT (BBT Token) Singleton Rule:**
   - Exactly one BBT token of `selfId` exists in output
   - Amount always equals 1 (ensures single bounty instance)
   - Implements **Singleton / State NFT** pattern for multi-stage contract state machine

2. **Creator Authentication:**
   - Helper function `isSigmaPropEqualToBoxProp(prop, box)` compares:
     - SigmaProp from R8 (creator public key)
     - Transaction signature (Sigma protocol proof)
   - P2PK comparison: extracts public key from both `sigmaPropBytes` (0xcd prefix, 34 bytes) and box proposition
   - Complex script handling: direct ErgoTree bytes comparison for non-P2PK propositions

3. **Submission Window Enforcement:**
   - All submission transactions validate: `HEIGHT <= selfDeadline`
   - Prevents submissions after bounty deadline (block height context variable)

4. **Counter Increment Atomicity:**
   - Submission action: `selfTotalSubmissions` incremented by exactly 1
   - Judgment action: exactly one of (accepted, rejected) counters incremented by 1
   - Prevents double-counting or skipped increments

5. **Minimum