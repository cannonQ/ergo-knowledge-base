---
title: kushti/dexy-stable — ballot.es
description: "ErgoScript contract analysis: contracts/bank/update/ballot.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/update/ballot.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `ballot.es`

## Purpose

This contract implements a **Ballot Box** in a decentralized voting/governance system, allowing token holders to cast votes on protocol updates or to have their ballot boxes consumed (reset) during an active update phase. The ballot tracks the owner's voting identity and prevents double-voting by recording which update proposal has been voted on.

## Inputs / Outputs

### Inputs
- **SELF (Ballot Box)**: The box being validated, containing:
  - The voter's public key in R4
  - Reference to an update proposal (box ID) in R5
  - The voted value in R6
- **INPUTS(0) (Update Box)**: When an update is triggered, this box must hold the Update NFT token to authorize ballot consumption

### Outputs
- **OUTPUTS(index) (Ballot Box Copy)**: A new ballot box at the same input index with:
  - Preserved voter public key (R4)
  - Preserved proposition (contract code)
  - Preserved native tokens
  - Equal or greater value (respecting minimum box value)

## Key Logic

The contract enforces two mutually exclusive paths via a **Sigma proposition**:

1. **Cast Vote Path** (`castVote`):
   - Requires the voter to sign with their private key (provable via `proveDlog` against the public key in R4)
   - Output ballot box must be a valid copy with preserved owner pubkey and contract
   - Allows vote state transitions (R5/R6 modifications are implicit in application layer)

2. **Update Path** (`update`):
   - Triggered when INPUTS(0) holds the Update NFT singleton token
   - Only valid if the ballot box has NOT YET VOTED (`notVoted`: R5 undefined)
   - Prevents creation of new valid votes during an active update
   - Consumes the ballot without requiring voter signature

**Invariant**: `isBasicCopy` ensures ballot box structural integrity—pubkey, code, and tokens cannot change, preventing impersonation or contract mutation.

**Security Note**: The `notVoted` check is **redundant but intentional**. R5's value (update box ID) cannot equal the current transaction's output box IDs by construction, so a voted ballot inherently cannot be updated. This is explicit defense-in-depth.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `GroupElement` | Voter's public key; used for signature verification and ballot ownership |
| **R5** | `Coll[Byte]` (Option) | Box ID of the update proposal being voted on; undefined until vote cast |
| **R6** | `Coll[Byte]` | The actual value voted for (e.g., parameter hash or proposal ID) |

Standard registers R0–R3 hold box metadata (ID, creation height, tokens, value).

## Tokens

- **Ballot Token** (`SELF.tokens`): A Native token (likely an NFT per voter) that must be preserved in the output. Acts as a **Singleton / State NFT** proving this is the canonical ballot box for the owner.
- **Update NFT** (injected via `$updateNFT`): A constant-segregated singleton token held in INPUTS(0). Used to authenticate and trigger the update/reset action.

## Integration Pattern

### Off-Chain Bot / Headless dApp Must:

1. **For Vote Casting**:
   - Fetch the ballot UTXO (identified by the voter's ballot NFT)
   - Construct a transaction consuming the ballot box
   - Build an output ballot box with:
     - Same R4 (pubkey), R5 (update box ID), R6 (vote value)
     - Same tokens and contract code
     - Updated value if needed for transaction fees or storage rent
   - Attach a Sigma proof (signature from the voter's private key) to satisfy `proveDlog(pubKey)`

2. **For Update/Reset**:
   - Ensure the Update NFT box is in INPUTS(0)
   - Consume ballot boxes whose R5 is undefined (not yet voted)
   - No signature required; the Update NFT presence authorizes consumption
   - Emit fresh/reset ballot boxes or discard them

### Context Extension
- Voter's signature is provided as part of the **Sigma protocol proof** attached to the input
- Update NFT authenticity is verified via **Token ID rule** (the specific token ID matches the injected constant)

## Related Contracts

- **Update Box Contract** (`contracts/bank/update/update.es` — inferred): Holds the Update NFT; orchestrates the voting/update state machine
- **Bank / Governance Framework**: This ballot is part of a larger Multi-stage contract where parameter updates are proposed and voted on (similar to SigmaUSD governance patterns)

The ballot interacts as part of a **State machine** where:
- **Voting Phase**: Ballots collect votes (R5 undefined → defined with vote)
- **Update Phase**: Update NFT present; unvoted ballots are consumed; voted ballots are finalized

---

## Summary Table

| Aspect | Detail |
|--------|--------|
| **Type** | State NFT / Ballot Singleton |
| **Auth Mechanism** | Sigma proof (voter signature) OR Update NFT presence |
| **State Transitions** | Unvoted → Voted (via castVote); Any → Consumed (via update) |
| **Immutables** | Owner pubkey, contract code, ballot NFT |
| **Mutables** | R5 (update ref), R6 (vote value), box value |
| **Composability** | Part of decentralized update governance (SigmaUSD-like architecture) |