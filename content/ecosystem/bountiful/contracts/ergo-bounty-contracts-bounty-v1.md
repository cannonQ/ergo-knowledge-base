---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — bounty-v1.es
description: "ErgoScript contract analysis: contracts/ergo-bounty-contracts/bounty-v1.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/ergo-bounty-contracts/bounty-v1.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# Bountiful Bounty Platform Contract Analysis

## Purpose

This ErgoScript contract implements a decentralized bounty platform where creators can post bounties with reward pools, submitters can propose solutions, and creators can judge submissions. The contract manages the entire lifecycle of a bounty—from creation through submission, judgment, reward distribution, and optional refunds—using state machine semantics with a Singleton State NFT (the BBT token) to ensure only one active bounty box exists at any time.

---

## Inputs / Outputs

### Standard Transaction Pattern (Multi-stage Contract)

**Inputs:**
- **Primary Input (SELF)**: The current bounty box containing:
  - Native token (BBT) with amount = 1 (Singleton / State NFT pattern)
  - Value in nanoERGs (the reward pool)
  - Registers R4–R9 encoding bounty state
  
- **Creator-signed transactions**: May include additional boxes with funds or judgment data

**Data Inputs:**
- Optional boxes containing:
  - Judgment decisions (submission acceptance/rejection)
  - Winner address and dispute period verification

**Outputs:**

| Action | Output Structure |
|--------|------------------|
| **Submit Solution** | Updated bounty box (SELF replicated with incremented submission counter) |
| **Judge Submission** | Updated bounty box (submission stats mutated) |
| **Withdraw Reward** | Winner box (ERG reward) + Dev fee box; bounty box destroyed |
| **Refund Bounty** | Creator refund box (ERG); bounty box destroyed |
| **Add Funds** | Updated bounty box (value and R7 increased) |
| **Extend Deadline** | Updated bounty box (R4 deadline updated) |
| **Update Metadata** | Updated bounty box (R9 metadata root changed, version incremented) |

---

## Key Logic

### Core Validation Invariants

1. **Singleton Preservation**: The BBT token ID and amount (1) must remain constant across all state transitions. This enforces the eUTXO model's single-box-per-bounty constraint.

2. **Box Replication (`isBoxReplication`)**: For all mutations:
   - Token ID and amount unchanged
   - Immutable registers (R4, R5, R8) preserved
   - ErgoTree (propositionBytes) unchanged
   - Only mutable state (R6, R7, R9) allowed to change

3. **Deadline Enforcement**:
   - Submissions only before `HEIGHT <= R4` (deadline block height)
   - Refunds only after `HEIGHT > R4`
   - Metadata/deadline extension only before deadline

4. **Submission Lifecycle**:
   - Each submission increments `R6[0]` (total submissions) by exactly 1
   - Creator judgments increment either `R6[1]` (accepted) or `R6[2]` (rejected) by 1
   - Submission data tracked via Merkle root in `R9.slice(0,32)` (AVL tree or similar)

5. **Creator Authorization**: Judgment, funding, deadline extension, and metadata update all require:
   ```ergoscript
   creatorProp = proveDlog(R8[Coll[Byte]].toGroupElement)
   ```
   This enforces Sigma protocols (discrete log proof) for creator authenticity.

6. **Reward Withdrawal Constraints**:
   - Requires `R6[1] >= 1` (at least one accepted submission)
   - Requires `R6[0] >= R5` (total submissions meet minimum threshold)
   - Dispute period must have passed (off-chain verified via data input block height)

7. **Refund Eligibility**:
   - `HEIGHT > R4` (deadline passed) AND
   - (`R6[0] < R5` OR `R6[1] == 0`) — either insufficient submissions or no accepted solutions

### Action-Specific Logic

**Submit Solution:**
- Verifies `HEIGHT <= selfDeadline`
- Validates increment: `newTotal == oldTotal + 1`
- Accepts/rejected counters frozen
- Submissions root (first 32 bytes of R9) must change
- Judgments and metadata roots unchanged

**Judge Submission:**
- Validates creator signature via `proveDlog(creatorPubKey)`
- Reads decision from data input box `R4[Boolean]`
- Increments either accepted or rejected counter (mutually exclusive)
- Judgments root (bytes 32–64 of R9) must change
- Total submissions counter frozen

**Withdraw Reward:**
- Enforces minimum submissions: `R6[0] >= R5`
- Enforces at least one accepted: `R6[1] >= 1`
- Dispute period validation (e.g., 7 blocks from judgment height)
- Calculates fee: `devFee = R7 / 100` (1% of reward)
- Winner receives: `R7 - devFee`
- Bounty box destroyed (not replicated in outputs)

**Refund Bounty:**
- Only after deadline: `HEIGHT > R4`
- Eligibility check: insufficient submissions OR no accepted solutions
- Refund amount = `SELF.value` sent to creator address

**Add Funds & Extend Deadline:**
- Requires creator signature
- Only immutable state (R4–R5, R8) and structure preserved
- Deadline extension: `newDeadline > oldDeadline`

---

## Registers Used

| Register | Type | Purpose | Mutable? |
|----------|------|---------|----------|
| **R4** | `Int` | Block height deadline for submissions | ✗ (Extend only via new tx) |
| **R5** | `Long` | Minimum number of submissions required | ✗ |
| **R6** | `Coll[Long]` | `[totalSubmissions, acceptedSubmissions, rejectedSubmissions]` | ✓ (incremented per action) |
| **R7** | `Long` | Reward amount in nanoERGs | ✓ (increased by "Add Funds") |
| **R8** | `Coll[Byte]` | Creator's compressed public key (33 bytes, Secp256k1 standard)