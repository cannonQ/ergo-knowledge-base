---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — bounty-v0.es
description: "ErgoScript contract analysis: contracts/ergo-bounty-contracts/in_development/bounty-v0.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/ergo-bounty-contracts/in_development/bounty-v0.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# Bountiful Bounty Platform Contract Analysis

## Purpose

The **Bountiful Bounty Platform Contract** is a state machine contract that manages the complete lifecycle of bounties on Ergo, including bounty creation, submission tracking, and judge-based reward distribution. It enables trustless bounty execution by combining token-based authentication (APT and PFT tokens), Merkle proof verification for submissions/judgments, and external reputation integration via oracles.

---

## Inputs / Outputs

### Inputs
- **SELF (Primary Input Box)**
  - Holds the bounty state as a **Singleton / State NFT** (APT token with ID in tokens(0))
  - Contains all bounty metadata in registers R4–R9
  - Locked by this contract's ErgoTree
  - Must be spent in state transitions (bounty updates, submissions, judgments)

- **Data Inputs (Oracle Boxes)**
  - Optional boxes referenced via `CONTEXT.dataInputs()` for external reputation verification (GitHub, POAP, Gitcoin Passport, Discord)
  - Read-only; not consumed in the transaction

### Outputs
- **OUTPUTS(0) (Updated Bounty Box)**
  - New state box replicating the bounty with potentially updated registers
  - Must preserve the APT token (same ID and amount = 1)
  - Must preserve deadline, minimum submissions, reward amount, and creator/judge data
  - Must preserve the contract script (`propositionBytes`)
  - Submission stats (R6) and bounty data (R9) may be updated

- **Optional Submission Proof Boxes**
  - Additional outputs may hold PFT tokens representing accepted submissions (for reward distribution downstream)

---

## Key Logic

### Core Validation Conditions

1. **Box Replication Invariant** (`isBoxReplication`)
   - The output bounty box must preserve:
     - Same bounty token ID and amount (Singleton constraint)
     - Same deadline (R4)
     - Same minimum submissions threshold (R5)
     - Same reward amount (R7)
     - Same creator/judge metadata (R8)
     - Same contract script
   - **Purpose**: Ensures state continuity and prevents unauthorized modifications to immutable bounty parameters

2. **Merkle Proof Verification** (`verifyMerkleProof`)
   - Validates submission and judgment data using **Merkle trees**
   - Walks through proof elements, hashing leaf data with proof siblings using **blake2b256**
   - Compares final computed root against stored roots in R9
   - **Purpose**: Enables compact, trustless verification of large submission/judgment sets without storing all data on-chain

3. **Register Validation** (`hasValidRegisters`)
   - Ensures all output registers are properly defined and non-empty
   - Validates byte array sizes (≤1000 bytes for most registers, ≤4000 for R9 bounty data)
   - **Purpose**: Prevents malformed state boxes

4. **JSON Field Extraction** (`extractJsonField`)
   - Parses encoded JSON in R8/R9 to extract creator public keys, trust status, judge info, and submission/judgment metadata
   - Handles string escaping and quote tracking
   - **Purpose**: Enables flexible metadata storage while maintaining backward compatibility

5. **Creator/Judge Authorization**
   - Extracts creator public key from first 33 bytes of R8
   - Reads trust status flag (byte 33 of R8: 1 = trusted, 0 = untrusted)
   - Validates judge identity from remaining bytes of R8
   - **Purpose**: Implements role-based access control for bounty actions

6. **External Reputation Integration** (partial, `isLinkExternalReputation`)
   - Verifies reputation link events via oracle data inputs
   - Supports multiple sources: GitHub, POAP, Gitcoin Passport, Discord
   - Validates oracle proof against source type
   - **Purpose**: Integrates off-chain identity/reputation systems to qualify judges and submitters

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Int` | Block height deadline for bounty completion and submission cutoff |
| **R5** | `Long` | Minimum number of submissions required to validate/execute the bounty |
| **R6** | `Coll[Long]` | Submission statistics: `[Total Submissions, Total Accepted, Total Rejected]` |
| **R7** | `Long` | Total reward amount in **nanoERG** (smallest Ergo unit) to be distributed |
| **R8** | `Coll[Byte]` | Encoded JSON: creator public key (33 bytes) + trust status flag (1 byte) + judge metadata (remaining bytes) |
| **R9** | `Coll[Byte]` | Encoded JSON containing: submissions Merkle root (32 bytes) + judgments Merkle root (32 bytes) + metadata root (32 bytes) + submission/judgment details |

**Register Preservation Invariant**: R4, R5, R7, R8 must remain unchanged across state transitions to enforce immutable bounty parameters.

---

## Tokens

### APT (Bountiful Proof Token) – **Singleton / State NFT**
- **Purpose**: Uniquely identifies and authenticates the bounty box
- **Location**: `SELF.tokens(0)`
- **Properties**:
  - Token ID: Unique per bounty (extracted as `selfId = SELF.tokens(0)._1`)
  - Amount: Always 1 (enforces **Singleton** pattern)
  - **Invariant**: Must be preserved in output box (same ID and amount)
- **Role**: Acts as the **State NFT** in the state machine; only one valid bounty box can exist per APT token ID

### PFT (Proof of Bounty Token) – Submission Proof
- **Purpose**: Represents and tracks individual submissions
- **Properties**:
  - Token ID: Unique per submission
  - Amount: Number of submission tokens (typically 1 per submission)
- **Role**: Used to verify submissions via Merkle proofs embedded in R9; may appear in output boxes to track accepted submissions for downstream reward distribution

---

## Integration Pattern

### Off-Chain Responsibilities

1. **Bounty Creation**