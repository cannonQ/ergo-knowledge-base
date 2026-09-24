---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — proposal_v1_0.es
description: "ErgoScript contract analysis: contracts/proposal_v1_0.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/proposal_v1_0.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: Bountiful Proposal Contract

## Purpose

This contract manages the lifecycle of bounty proposals submitted by proposers to bounty creators. It enforces state transitions (Pending → Approved/Disputed/Rejected) and ensures only the bounty creator can approve proposals or transition them to disputed status. The contract serves as a **State Machine** within the Bountiful bounty platform, maintaining proposal metadata and authorization constraints across state changes.

---

## Inputs / Outputs

### Inputs
- **SELF (Proposal Box)**: The current proposal eUTXO containing:
  - Proposer's public key (R4)
  - Bounty ID (R5)
  - Metadata JSON (R6)
  - Bounty creator's SigmaProp (R7)
  - Status code (R8)
  - ERG value (preserved across transitions)

### Outputs
- **Output Box 0 (Updated Proposal Box)**: The new proposal eUTXO reflecting state change:
  - Same registers as input (except R8 status code, which is updated)
  - Identical proposition bytes (contract address unchanged)
  - Same ERG value (no funds transferred in this contract)
  - New status code (1, 2, or 3 depending on action)

---

## Key Logic

### State Definitions
The contract tracks four mutually-exclusive proposal states via R8 (Int register):
- **Pending (0)**: Initial state after proposal creation
- **Approved (1)**: Bounty creator accepted the proposal
- **Rejected (2)**: Bounty creator declined the proposal
- **Disputed (3)**: Proposal flagged for resolution/arbitration

### Validation Rules

#### 1. **Valid Setup** (always required)
```
bountyId.size > 0 AND metadataJson.size > 0
```
Ensures proposal metadata is non-empty.

#### 2. **Dispute Action** (`isDisputeAction`)
- **Precondition**: Current status is Pending, Approved, or Rejected
- **Effect**: Transition to Disputed (3)
- **Constraints**:
  - All registers (R4–R7) copied unchanged
  - Box value preserved
  - Proposition bytes unchanged
  - Requires bounty creator's signature (implicit via SigmaProp in R7)

#### 3. **Maintenance Action** (`isMaintenanceAction`)
- **Precondition**: Current status is Pending only
- **Effect**: Remain in Pending (0) — allows metadata updates without state change
- **Constraints**:
  - R4 (proposer), R5 (bountyId), R7 (creator SigmaProp) unchanged
  - R6 (metadata) *may be updated* (not checked)
  - Box value preserved
  - Proposition bytes unchanged

#### 4. **Approval Action** (`isApprovalAction`)
- **Precondition**: Current status is Pending or Rejected
- **Effect**: Transition to Approved (1)
- **Constraints**:
  - All registers copied unchanged
  - Box value preserved
  - Proposition bytes unchanged
  - **Requires bounty creator signature**: `bountyCreatorProp` (final condition enforces Sigma protocol)

### Authorization Pattern

The contract uses **SigmaProp-based authorization**. The approval and dispute actions require the `bountyCreatorProp` SigmaProp to evaluate to `true`, meaning the bounty creator must sign the transaction with their private key corresponding to the public key embedded in R7.

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|-----------|
| **R4** | `GroupElement` | Proposer's public key (identity) | Immutable across all actions |
| **R5** | `Coll[Byte]` | Bounty ID (links proposal to parent bounty) | Immutable across all actions |
| **R6** | `Coll[Byte]` | Proposal metadata (JSON-encoded details) | Updatable only in Maintenance action |
| **R7** | `SigmaProp` | Bounty creator's Sigma proposition (authorization) | Immutable across all actions |
| **R8** | `Int` | Proposal status code (0/1/2/3) | Updated via state transitions |

---

## Tokens

### NFT / State Tracking
This contract does **not explicitly manage Native tokens or NFTs**. However:
- The **Proposal Box itself acts as a Singleton / State NFT** — the immutable combination of `proposerId` (R4) + `bountyId` (R5) ensures uniqueness within a bounty.
- A companion **Token ID rule** could be enforced off-chain to create a unique NFT that travels with this box for stronger singleton guarantees (not implemented in this version).

### Value Transfer
- **ERG Value**: Preserved (`SELF.value == OUTPUTS(0).value`) across all actions — no rewards distributed by this contract.
- Reward distribution likely handled by a separate **companion contract** (e.g., `reward_distribution.es`).

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Reading Proposal State**:
   - Scan the blockchain for proposal boxes (matching this ErgoTree)
   - Extract R4–R8 to determine status and metadata
   - Index by `bountyId` (R5) to associate with parent bounties

2. **Constructing Approval Transaction**:
   ```
   - Input: Current proposal eUTXO (SELF)
   - Output: New box with R8 = 1 (Approved)
   - Signature: Bounty creator's private key (to satisfy bountyCreatorProp)
   - Validation: bountyCreatorProp must evaluate to true
   ```

3. **Constructing Dispute Transaction**:
   ```
   - Input: Current proposal eUTXO (SELF)
   - Output: New box with R8 = 3 (Disputed)
   - Signature: Bounty creator's private key
   - Validation: bountyCreatorProp must evaluate to true
   ```

4. **Constructing Maintenance Transaction** (proposer):
   ```
   - Input:
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
