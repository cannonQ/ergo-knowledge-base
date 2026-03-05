---
title: duckpools/lend-protocol-contracts — counting.md
description: "ErgoScript contract analysis: contracts/treasury-system/voting/counting.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/treasury-system/voting/counting.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Voting Counting System

## Purpose

This contract implements the **vote counting and validation logic** for a decentralized treasury governance system in the duckpools lending protocol. It manages multi-stage voting periods (initiation, counting, validation, and proposal execution), accumulates vote tallies from individual voter boxes, and validates that proposals meet quorum and support thresholds before execution.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: The counting box itself (SELF) — maintains voting state across periods
- **INPUTS(1+)**: Vote boxes (during counting period) — individual voter UTXOs containing vote tokens and preferences
  - During vote validation: proposal box containing the proposal state
- **Data Inputs (during initiation)**: Initiation box — references the nominated proposal parameters

### Outputs
- **OUTPUTS(0)**: Successor counting box — updated state with accumulated vote tallies or reset state
- **OUTPUTS(1)** (during validation): Proposal box — the validated/executed proposal box with updated state

---

## Key Logic

The contract enforces a **four-phase state machine** gated by block height (`HEIGHT`):

### Phase 1: Before Counting (`isBeforeCounting`)
- Allows initiation of a new vote with a nominated proposal
- Validates that the initiator provides sufficient `quacks` tokens (>100M nanoErgs) to meet the `initiationHurdle`
- Resets the counting box: clears vote tallies (`R7`, `R9`), stores the nominated proportion and recipient
- Ensures successor maintains same script, deadline, and value

### Phase 2: Counting Period (`isCountingPeriod`)
- Accepts individual voter boxes as inputs (INPUTS slice [1, size))
- **Accumulates votes**:
  - Sums token amounts (`tokens(1)._2`) from voters voting for the current proportion/recipient pair
  - Tallies total votes across all voters
  - Tracks validation votes (marked with `R9 == 1`)
- **Burns vote NFTs** (`validVoteId`) to prevent double-voting
- **Validates voter boxes**:
  - Must hold valid vote token (`validVoteId`)
  - Must hold `quacks` tokens for vote power
  - Submission deadline must precede `nextVoteDeadline`
- Updates successor: increments vote counts in `R7` and validation votes in `R9`

### Phase 3: Vote Validation Period (`isVoteValidationPeriod`)
- Loads the proposal box (INPUTS(1)) from pending state
- **Checks proposal approval** against thresholds:
  - Minimum final votes required: 300B quacks
  - If proposal proportion > 1M: requires 90% support (`elevatedSupport`)
  - Otherwise: requires 50% support (`minimumSupport`)
  - Support = (validation votes / total votes) × 1000
- If approved:
  - Transitions proposal box to executed state (NFT count: 1 → 2)
  - Preserves proportion and recipient parameters
  - Verifies proposal script matches `proposalTree` blueprint
- Updates counting box state for the next cycle

### Phase 4: New Proposal Period (`isNewProposalPeriod`)
- Allows new proposals to be initiated in the next voting round

---

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R4** | `Long` | Vote deadline (countdown timer for current voting period) | Read in all phases; maintained by successor |
| **R5** | `(Long, Long)` | Vote tally tuple: (nominated proportion, votes in favor of proportion) | Tracks proposal distribution ratio and accumulated support |
| **R6** | `Coll[Byte]` | Recipient ergotree hash (160-bit blake2b256 commitment) | Identifies the target treasury recipient |
| **R7** | `Long` | Total votes accumulated in counting period | Denominator for quorum and support calculations |
| **R8** | `Long` | Initiation amount (quacks tokens provided by initiator) | Anti-spam measure; validates proposal was properly initiated |
| **R9** | `Long` | Validation votes count (subset of total votes that validated) | Numerator for support percentage; tracks yes-votes in validation phase |

---

## Tokens

### Primary Tokens

1. **`quacksId`** (AA5H...Qkv)
   - The governance token; vote power is denominated in quacks
   - Required in voter boxes (`tokens(1)`) to prove voting stake
   - Required in initiation box to meet `initiationHurdle` (100M quacks)

2. **`validVoteId`** (8pAA...3Cqz)
   - **Vote NFT** — authenticates that a box is a valid voter vote
   - Present in voter inputs during counting phase
   - Must be **burnt** (removed from all outputs) to prevent double-voting
   - Acts as a singleton-like token per voter per voting round

3. **Result/Proposal Token** (referenced via `currentResultTokens._1`)
   - Tracks proposal state through NFT count in register R5:
     - Value `1` = pending proposal awaiting validation
     - Value `2` = executed/approved proposal
   - Tied to proposal validation height stored in voter box

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Proposal Initiation**
   - Construct initiation box with sufficient `quacks` tokens
   - Specify nominated proportion (in R4) and recipient ergotree (in R5)
   - Submit as data input when triggering `isBeforeCounting` phase

2. **Vote Collection**
   - Monitor the blockchain for the counting box and its deadline (R4)
   - Aggregate individual voter UTXOs from users who locked `validVoteId` + `quacks`
   - Include voter boxes as inputs (INPUTS[1..N]) during counting period
   - **Verify before submission**:
     - Each voter box has valid `validVoteId` and `quacks` tokens
     - Voter's submission deadline (`R8`) < `nextVoteDeadline`
     - Voter's registered proportion matches current proposal
     - No double-spending of vote NFTs

3