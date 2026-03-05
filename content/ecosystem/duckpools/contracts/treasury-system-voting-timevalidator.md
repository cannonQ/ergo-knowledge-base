---
title: duckpools/lend-protocol-contracts — timeValidator.md
description: "ErgoScript contract analysis: contracts/treasury-system/voting/timeValidator.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/treasury-system/voting/timeValidator.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: `timeValidator.md`

## Purpose

This contract validates and processes voting transactions in a governance system where users vote with QUACKS tokens. It ensures that vote creation boxes are properly constructed, that voting tokens are correctly distributed, and that voting power meets minimum thresholds before advancing to the next state in a voting state machine.

## Inputs / Outputs

### Input
- **SELF** (implicit): The current timeValidator box containing:
  - A state NFT (identified by token ID in `currentTokens._1`)
  - Token quantity that decrements with each valid vote

### Outputs
- **OUTPUTS(0)** (successor): The next timeValidator box maintaining the state machine
  - Same proposition bytes as SELF
  - Same state NFT with quantity decremented by 1
- **OUTPUTS(1)** (userVote): A newly created user vote box
  - Locked by `userVoteContract` ErgoTree
  - Contains a singleton vote token (quantity = 1)
  - Contains user's QUACKS tokens (must be ≥ 50,000)
  - Stores vote creation height in R8

## Key Logic

The contract validates six critical invariants:

1. **Vote Contract Verification**: The blake2b256 hash of the user vote box's proposition bytes must match the hardcoded `userVoteContract` address, ensuring votes are locked by the correct contract.

2. **Vote Token Integrity**: The user vote box receives exactly one unit of the state NFT from SELF, creating a singleton token for atomic vote tracking.

3. **Vote Height Validation**: The R8 register (userVoteHeight) must be strictly greater than the current blockchain HEIGHT, establishing a future timestamp for vote maturity/activation.

4. **State Machine Continuity**: The successor box must have identical proposition bytes as SELF, maintaining contract continuity in the state chain.

5. **Token Decrement**: The successor's state NFT quantity must equal the current quantity minus 1, enforcing linear consumption of voting capacity.

6. **Voting Power Threshold**: Users must hold at least 50,000 QUACKS tokens (MinimumVoteAmount) to participate, enforcing minimum stake requirements.

All seven conditions (via `&&` operators) must evaluate to `true` for transaction validity.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R8** (userVote) | `Long` | Stores the blockchain height at which the vote becomes valid/active; must exceed current `HEIGHT` to ensure future-proofing |

## Tokens

| Token | Purpose | Constraints |
|-------|---------|-------------|
| **State NFT** (ID: `currentTokens._1`) | Singleton state tracking for the voting contract; decrements with each processed vote | Quantity decreases 1→0 across state chain |
| **QUACKS** (ID: `quacksId = "aa5Hq5V5ssGxbReLMzpJ55nVrb73CWJ1oRiKD2X5Qkv"`) | Governance token representing voting power/stake | Minimum 50,000 units required per vote |
| **Vote Token** (ID: `userVoteTokens._1`, same as state NFT) | Singleton NFT locked in user vote box for atomic vote representation | Exactly 1 unit |

## Integration Pattern

Off-chain systems (voting dApp / off-chain bot) must:

1. **Construct the userVote box** with:
   - Proposition bytes corresponding to `userVoteContract` (verified via blake2b256)
   - Exactly 1 unit of the state NFT
   - User's QUACKS balance (≥50,000)
   - A future blockchain height in R8 (> current HEIGHT)

2. **Construct the successor box** with:
   - Identical ErgoTree to SELF
   - Same state NFT ID with quantity decremented by 1
   - Sufficient ERG for storage rent

3. **Verify constants** before transaction construction:
   - Confirm `userVoteContract` address hasn't changed
   - Confirm `quacksId` matches governance token
   - Confirm `MinimumVoteAmount` (50,000) aligns with governance parameters

4. **Atomically commit** the transaction, ensuring all seven validation conditions pass at block inclusion.

## Related Contracts

- **`userVoteContract`** (hash: `9bjVXo29fWDenQ1xvubpNinB5ZoP5PdLhEUGWZr8Qudx`): The contract that locks individual user vote boxes; receives vote tokens and QUACKS as inputs for downstream vote aggregation/counting logic.

- **Implicit parent state machine**: This contract is part of a multi-stage voting state machine where:
  - timeValidator acts as a gatekeeper/validator
  - Successive calls decrement the state NFT supply
  - Final state (when state NFT quantity = 0) likely triggers vote finalization or result tallying

---

**Note**: The constant segregation of `userVoteContract`, `quacksId`, and `MinimumVoteAmount` ensures that governance parameters can only be updated via contract redeploy, preventing mid-election manipulation. The state NFT singleton pattern combined with decremental validation enforces strict ordering and prevents vote duplication attacks.