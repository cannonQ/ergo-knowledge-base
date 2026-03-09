---
title: kushti/dexy-stable — update.es
description: "ErgoScript contract analysis: contracts/bank/update/update.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/update/update.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `update.es`

## Purpose

This contract implements a **decentralized governance mechanism** for updating critical system contracts in the Dexy stable protocol. It enables a multi-signature voting scheme where ballot-holding stakeholders must collectively approve contract changes before they take effect, preventing unauthorized modifications to core banking, extraction, or intervention contracts.

---

## Inputs / Outputs

### Inputs
| Position | Box Type | Purpose |
|----------|----------|---------|
| `INPUTS(0)` | **Update Box** (SELF) | The singleton governance box holding this contract; contains no data registers |
| `INPUTS(1)` | **Contract-to-Update Box** | The live contract box being modified (identified by `contractToUpdateNFT`); holds the current implementation |
| `INPUTS(2+)` | **Ballot Boxes** | Any number of boxes holding `ballotTokenId` tokens; filtered by `isValidBallot()` predicate |

### Outputs
| Position | Box Type | Purpose |
|----------|----------|---------|
| `OUTPUTS(0)` | **Updated Update Box** | Copy of the governance box; unchanged state |
| `OUTPUTS(1)` | **Updated Contract Box** | The contract box with new `propositionBytes` (ErgoTree); same tokens and value as input |

---

## Key Logic

The contract enforces these **invariant conditions** for a valid transaction:

1. **Input Position Validation** (`validUpdateIn`)
   - The update box must be the first input (`SELF.id == INPUTS(0).id`)
   - Ensures deterministic ordering and prevents replay attacks

2. **Contract Target Validation** (`validContractToUpdateIn`)
   - The second input must hold the target NFT (`contractToUpdateNFT`)
   - Verifies we're updating the intended contract (not an imposter box)

3. **Immutable Contract State** (`validContractToUpdateOut`)
   - Token composition is preserved: `contractToUpdateBoxIn.tokens == contractToUpdateBoxOut.tokens`
   - ERG value is preserved: `contractToUpdateBoxIn.value == contractToUpdateBoxOut.value`
   - Only the `propositionBytes` (ErgoTree bytecode) may change

4. **Update Box Preservation** (`validUpdateOut`)
   - The governance box's tokens and script remain identical
   - Its value cannot decrease (maintains minimum box value)

5. **Ballot Aggregation & Quorum** (`validVotes`)
   - **Vote Collection**: Filters all inputs matching `isValidBallot()` predicate
   - **Vote Counting**: Sums token quantities across valid ballot boxes (`votesCount`)
   - **Quorum Requirement**: `votesCount >= minVotes` (threshold = 3 out of 5 voters)

6. **Ballot Validation** (`isValidBallot()`)
   - Ballot box holds the correct token ID (`ballotTokenId`)
   - **Register R5** stores `SELF.id` (the update box ID) — prevents vote reuse across different governance proposals
   - **Register R6** stores `blake2b256(contractToUpdateBoxOut.propositionBytes)` — the cryptographic commitment to the new contract code being voted for
   - Ensures ballots are **bound to this specific update proposal and contract change**

---

## Registers Used

| Register | Type | Read/Write | Purpose |
|----------|------|-----------|---------|
| **R4** | `GroupElement` | Read (ballot boxes) | Public key of the ballot token owner; used for multi-sig validation in associated Sigma protocol signatures |
| **R5** | `Coll[Byte]` | Read (ballot boxes) | Box ID of the update box this vote applies to; prevents ballot reuse across different governance votes |
| **R6** | `Coll[Byte]` | Read (ballot boxes) | Blake2b256 hash of the proposed contract's `propositionBytes`; commits voters to the exact code being approved |
| **R7–R9** | — | Unused | Reserved for future governance state (e.g., timestamps, vote types) |

---

## Tokens

| Token Type | Quantity | Purpose | Location |
|-----------|----------|---------|----------|
| **contractToUpdateNFT** | 1 (singleton) | **State NFT** identifying the contract box to be updated; prevents unauthorized contract targeting; exists as `INPUTS(1).tokens(0)._1` |
| **ballotTokenId** | 1+ per ballot box | **Voting weight tokens**; quantity in each ballot box determines vote power; multiple ballot boxes aggregate votes for quorum calculation |
| **updateNFT** (implicit) | 1 (singleton) | Implicitly held by the update box itself (preserved via `validUpdateOut`); marks this as the authoritative governance singleton |

---

## Integration Pattern

### Off-Chain Bot / Governance Coordinator Responsibilities

1. **Proposal Stage**
   - Construct the new contract's ErgoTree (`newPropositionBytes`)
   - Hash it: `proposalHash = blake2b256(newPropositionBytes)`
   - Broadcast proposal off-chain to all ballot holders

2. **Voting Stage**
   - Each ballot holder creates/signs a transaction that **spends their ballot box** with:
     - R5 set to `updateBoxId` (the governance box ID)
     - R6 set to `proposalHash`
   - Ballot boxes remain unspent until the final governance transaction

3. **Execution Stage (this contract)**
   - Coordinator gathers ≥ 3 signed ballot inputs
   - Constructs the governance transaction:
     ```
     Inputs:  [updateBox, contractToUpdateBox, ballot1, ballot2, ballot3, ...]
     Outputs: [updateBox', contractToUpdateBox']
     ```
   - `contractToUpdateBox'` contains:
     - Same NFT and ERG value as input
     - New `propositionBytes` matching the voted proposal hash
   - Submits transaction to Ergo blockchain

4. **Contract Execution (this script)**
   - Validates all 6 invariants above
   - Rejects if fewer than 3 valid ballots present
   - Rejects if any ballot's R5 ≠ update box ID or R6 ≠ output hash