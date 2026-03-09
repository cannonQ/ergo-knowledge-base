---
title: kushti/dexy-stable — ballot.es
description: "ErgoScript contract analysis: contracts/bank/update/ballot.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/update/ballot.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `ballot.es`

## Purpose

This contract manages **ballot boxes** in a decentralized governance or voting system (likely for protocol updates in the Dexy stable ecosystem). It allows ballot token holders to either **cast votes** by signing with their private key or **transition their ballot during an update action** without generating new votes, ensuring voting integrity during state transitions.

---

## Inputs / Outputs

### Inputs
- **SELF (index variable)**: The ballot box itself, containing:
  - The ballot token (authenticated by this contract's ErgoTree)
  - Owner's public key in R4
  - Update box ID in R5 (if already voted)
  - Vote value in R6 (if already voted)
  
- **INPUTS(0)**: The update box (data input or spending input), which must carry the `updateNFT` token to authorize state transitions during updates

### Outputs
- **OUTPUTS(index)**: The corresponding output ballot box at the same position, which must:
  - Preserve the owner's public key (R4)
  - Preserve the contract's proposition bytes (ErgoTree)
  - Preserve all native tokens (ballot token)
  - Maintain or increase the box value (≥ SELF.value)
  - Either preserve R5 (already voted) or leave R5 undefined (not yet voted)

---

## Key Logic

The contract validates transactions through a **Sigma proposition** with two allowed paths:

### Path 1: Basic Copy + Vote Cast (`isBasicCopy && castVote`)
- Output must be a "basic copy" of the ballot box (same pubkey, ErgoTree, tokens, sufficient value)
- Transaction must be signed by the ballot owner (`proveDlog(pubKey)`)
- **Result**: Owner actively casts or changes their vote

### Path 2: Update Action (`isBasicCopy && update`)
- Output must be a "basic copy" of the ballot box
- INPUTS(0) (the update box) must carry the `updateNFT` token
- Output must **not have R5 defined** (`notVoted == true`), meaning the ballot has not yet recorded a vote
- **Result**: During a protocol update, unvoted ballots transition to new state without enabling new vote generation

### Security Invariants
- **Circular reference prevention**: R5 (update box ID) cannot be set to SELF's output box ID because outputs cannot reference themselves; this makes update-induced vote injection cryptographically impossible
- **Double-security check**: The `notVoted` flag adds an explicit gate ensuring updates only progress ballots that haven't voted, preventing vote duplication across state transitions

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `GroupElement` | Owner's public key (Schnorr group element); used for `proveDlog` signature verification |
| **R5** | `Coll[Byte]` (optional) | Box ID of the update box that accepted this ballot's vote; undefined if ballot hasn't voted yet |
| **R6** | `Coll[Byte]` (optional) | The vote value itself (exact meaning depends on off-chain interpretation; could be a proposed parameter, hash, or choice ID) |

R4, R5, R6 are **immutable during execution**; only the output box's registers are checked via `.isDefined` or equality.

---

## Tokens

### updateNFT (Singleton Token)
- **Type**: Native token (NFT—single instance)
- **Constraint**: `fromBase64("$updateNFT")` (constant-segregated at compile time)
- **Role**: Authenticates the update box and authorizes state transitions
- **Enforcement**: Must be in `INPUTS(0).tokens(0)._1` (first token of first input)
- **State Machine Pattern**: Acts as a **State NFT** to enforce that only legitimate update transactions can transition ballots

### Ballot Token
- **Type**: Native token (likely an NFT or voting share token)
- **Constraint**: Preserved in output via `output.tokens == SELF.tokens`
- **Role**: Authenticates ballot box ownership; prevents forgery of new ballot boxes

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Vote Casting Transaction**:
   - Construct a transaction with the ballot box as input
   - Create an output at the same index with:
     - Same R4 (pubkey), ErgoTree, tokens
     - Value ≥ SELF.value
     - R5 and R6 set to encode the vote
   - Sign with the ballot owner's private key (matches R4)
   - Broadcast to network

2. **Update Action Transaction**:
   - Include the update box (carrying `updateNFT`) as INPUTS(0)
   - Include all unvoted ballot boxes as inputs
   - For each ballot, create an output:
     - At the same index
     - With R5 and R6 **not defined** (or cleared)
     - With same R4, ErgoTree, tokens
   - No signature required (update authority comes from `updateNFT`)
   - Ensure no output box re-establishes R5 (circular reference check)

3. **Constant Segregation**:
   - `updateNFT` is compile-time constant; dApp must generate contract with correct token ID baked in

4. **Multi-Stage Composition**:
   - This contract likely interacts with:
     - **Update box contract**: Maintains voting state, tallies, and triggers transitions
     - **Vote aggregation contract**: Collects and verifies ballot boxes to compute governance outcomes

---

## Related Contracts

Based on context from **kushti/dexy-stable** and governance patterns:

- **`update.es` (Update Box Contract)**: 
  - Holds the `updateNFT` singleton
  - Triggers state transitions by spending, authorizing the `update` path in ballot boxes
  - Likely stores vote tallies or update proposals in its own registers

- **`ballot_issue.es` (Ballot Issuance Contract)** (inferred):
  - Mints ballot boxes with unique tokens
  - Sets initial R4 with owner's pubkey
  - Ensures R5 starts undefined

- **Governance / Vote Aggregation Contract** (inferred):
  - Reads