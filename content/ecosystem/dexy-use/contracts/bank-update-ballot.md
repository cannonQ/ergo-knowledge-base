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
project: dexy-use
---
# ErgoScript Contract Analysis: `ballot.es`

## Purpose

This contract implements a **ballot box** in a multi-signature voting system where token holders can cast votes on protocol updates. The ballot box enforces that votes are only cast or updated by the legitimate owner (via Sigma protocol proof) and prevents vote manipulation during active update transactions.

## Inputs / Outputs

### Inputs
- **SELF (Ballot Box)**: The ballot box itself, containing the voter's public key in R4, an optional update box ID in R5, and optionally a voted value in R6
- **INPUTS(0)**: The **update box** (must carry the updateNFT token) in the case of an update action

### Outputs
- **OUTPUTS(index)**: A new ballot box at the same position as SELF in the input array, preserving state or recording a vote

## Key Logic

The contract enforces a **state machine** with two valid actions:

1. **Cast Vote** (`castVote`):
   - The owner proves ownership via `proveDlog(pubKey)` (Sigma protocol proof of discrete log)
   - A new ballot box is output at the same index with unchanged proposition, tokens, and public key
   - The new box must preserve or increase the box value (covering Minimum transaction fee and Storage rent)

2. **Update Action** (`update`):
   - Triggered when INPUTS(0) carries the updateNFT token
   - ONLY valid if the ballot has not yet voted (`notVoted = output.R5.isDefined == false`)
   - This prevents a ballot from casting a new vote during an active update transaction

### Invariants

- **isBasicCopy**: Ensures the output ballot maintains the same owner (pubKey in R4), contract logic (propositionBytes), and token allocation (no token theft)
- **Mutual exclusivity prevention**: The `notVoted` check ensures that if an update is in progress, no fresh vote can be generated in the same transaction

## Registers Used

| Register | Type | Purpose | Used In |
|----------|------|---------|---------|
| **R4** | `GroupElement` | The owner's public key (voter identity) | Vote authentication and ballot preservation |
| **R5** | `Coll[Byte]` (optional) | Box ID of the update box associated with this vote | Prevents replay/re-voting; checked for emptiness to gate updates |
| **R6** | `Coll[Byte]` (optional) | The value voted for (e.g., parameter hash or proposal ID) | Not directly used in this contract; assumed set off-chain |

## Tokens

- **updateNFT** (injected as `$updateNFT` constant):
  - A **Singleton / State NFT** carried by the update box
  - Used to authenticate update transactions and trigger the `update` action
  - Prevents unauthorized protocol updates by requiring presence of a specific token in INPUTS(0)

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Vote Casting**:
   - Construct a transaction spending the current ballot box
   - Output a new ballot box with R4 (pubKey) preserved, optionally populating R5 and R6 with the update box ID and vote value
   - Sign the transaction with the voter's private key (satisfies `proveDlog(pubKey)`)

2. **Update Action**:
   - Construct a transaction with the updateNFT box as INPUTS(0)
   - Include the ballot box to be updated
   - Ensure the output ballot has R5 undefined (empty) to satisfy `notVoted`
   - Off-chain code must verify that INPUTS(0).tokens(0)._1 == updateNFT before submission

3. **Constant Segregation**:
   - The `updateNFT` value is injected at contract compilation time via `$updateNFT` placeholder
   - This allows the same contract code to work with different update NFTs per deployment

## Related Contracts

- **Update Box Contract** (`update.es` or similar):
  - Holds the updateNFT token and orchestrates protocol updates
  - Must reference this ballot contract to enforce voting during updates
  - Likely contains logic to tally votes from multiple ballot boxes

- **Bank / Treasury Contracts**:
  - The `bank/` directory suggests this is part of a larger system managing reserves or protocol parameters
  - Likely composed in multi-stage contracts where ballots feed into parameter update mechanisms (e.g., SigmaUSD, Dexy rate oracles)

---

## Security Notes

- **Voter Privacy**: Votes are on-chain; privacy depends on external mixing or accumulator techniques
- **Vote Locking**: Once R5 is set (vote cast), the `update` action cannot proceed, preventing vote manipulation mid-update
- **Minimal Trust**: Relies only on Sigma protocol (ECDSA) for authentication; no trusted signers needed
- **Storage Rent**: Output boxes must maintain minimum value to cover network storage costs