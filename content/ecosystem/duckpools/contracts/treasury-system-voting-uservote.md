---
title: duckpools/lend-protocol-contracts — userVote.md
description: "ErgoScript contract analysis: contracts/treasury-system/voting/userVote.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/treasury-system/voting/userVote.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: userVote

## Purpose

This contract manages user voting in a treasury system by validating two distinct voting flows: **vote cancellation** (with a cooldown period and counter box deadline) and **vote submission** (with token return validation). It enforces that votes are authenticated via Sigma protocols (Schnorr signatures) and that voting tokens are either burnt or returned to the user's address.

## Inputs / Outputs

### Inputs
- **SELF**: The user vote box containing:
  - **Tokens**: Vote NFT/token at index 0 (to be burnt or returned)
  - **Tokens[1]**: Secondary token (returned on vote submission)
  - **R6**: User's public key (`GroupElement`)
  - **R7**: User's address/proposition bytes (`Coll[Byte]`)
  - **R8**: Recorded submission height (`Long`)

### Data Inputs (Cancellation Path)
- **CONTEXT.dataInputs(0)**: Counter box containing:
  - **Tokens[0]**: Counter token with ID matching `counterToken` constant
  - **R4**: Voting deadline (`Long`)

### Inputs (Submission Path)
- **INPUTS(0)**: Counter box with valid counter token (same as data input path)

### Outputs
- **Cancellation Path**: Any boxes, but vote token must be burnt (not present in outputs)
- **Submission Path**: 
  - **OUTPUTS[0]**: Unrestricted (likely change/fee box)
  - **OUTPUTS[1...]**: At least one box must contain:
    - `propositionBytes == userTree` (user's address)
    - `tokens(0) == SELF.tokens(1)` (original vote token returned)
    - `R4 == SELF.id` (reference to this vote box)

## Key Logic

The contract implements a **state machine with two branches**:

### Branch 1: Vote Cancellation (with Data Input)
**Conditions (all must hold via AND logic):**

1. **Schnorr Signature**: `proveDlog(userPk)` — User must sign with their private key
2. **Voting Window Open**: `HEIGHT < counterBox.R4[Long].get` — Current block height must precede the counter box deadline
3. **Cooldown Enforced**: `HEIGHT > recordedSubmission + cancellationCooldown` — At least 20 blocks must pass since vote submission to prevent spam
4. **Valid Counter Box**: Counter box must hold the designated counter token with quantity > 100,000,000
5. **Token Burnt**: The vote token (at SELF.tokens[0]) must NOT appear in any output box, confirming destruction

### Branch 2: Vote Submission (without Data Input)
**Conditions (all must hold via AND logic):**

1. **Valid Counter Box**: First input must be a counter box with the correct token ID and sufficient token quantity
2. **Token Return**: At least one output box must:
   - Be controlled by the user (`propositionBytes == userTree`)
   - Contain the original vote token (`tokens(0) == SELF.tokens(1)`)
   - Reference this vote box (`R4[Coll[Byte]] == SELF.id`)

## Registers Used

| Register | Type | Purpose | Path |
|----------|------|---------|------|
| **R4** (Counter Box) | `Long` | Voting deadline (block height) | Both |
| **R6** | `GroupElement` | User's public key for Schnorr signature | Both |
| **R7** | `Coll[Byte]` | User's ErgoTree/proposition bytes (address) | Submission only |
| **R8** | `Long` | Recorded vote submission height | Cancellation only |
| **R4** (Output Box) | `Coll[Byte]` | Reference to SELF.id (vote box ID) | Submission only |

## Tokens

### Counter Token
- **Token ID**: `EHjj44TwNZKy5BA4y8fzpxSuh6B5evxZGzNto9dF4rsY` (singleton/state token)
- **Quantity Requirement**: Must exceed 100,000,000 units
- **Purpose**: Authenticates the counter/proposal box and gates voting operations
- **Usage**: Prevents spam via state validation; held by governance authority

### Vote Token
- **Position**: `SELF.tokens(0)` and `SELF.tokens(1)`
- **Cancellation Path**: Token at index 0 must be **burnt** (removed from circulation)
- **Submission Path**: Token at index 1 must be **returned** to user's output box with reference
- **Purpose**: Represents voting power/ticket; prevents double-voting through consumption

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities:

#### For Vote Cancellation:
1. **Construct transaction** with:
   - Input: User's vote box (SELF)
   - Data input: Counter box (read-only reference to R4 deadline)
   - Output: Arbitrary boxes, but excluding vote token (burnt)
2. **Sign with user's private key** (corresponding to R6 public key)
3. **Verify conditions** before submission:
   - `HEIGHT < counterBox.R4` (voting still open)
   - `HEIGHT > recordedSubmissionHeight + 20` (cooldown elapsed)
   - Counter box holds correct token ID with sufficient quantity

#### For Vote Submission:
1. **Construct transaction** with:
   - Input: Vote box + Counter box (full input)
   - Output[0]: Change/fees
   - Output[1+]: Return box containing vote token, user's address, and SELF.id reference
2. **No signature required** (vote box consumed, not user-signed)
3. **Verify**:
   - Counter box validity (token + quantity)
   - Return box structure matches requirements

### Context Extension
- No explicit context extension variables used; relies on `HEIGHT` (blockchain height) from Sigma context

## Related Contracts

Based on the contract structure, inferred related contracts in the **duckpools/lend-protocol-contracts** treasury-system:

1. **Counter / Proposal Box Contract** — Referenced by R4 deadline; likely manages voting windows and proposal state
2.