---
title: duckpools/lend-protocol-contracts — proposal.md
description: "ErgoScript contract analysis: contracts/treasury-system/voting/proposal.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/treasury-system/voting/proposal.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Proposal (Treasury Voting System)

## Purpose

This contract manages treasury proposal state transitions within a voting/governance system. It validates the progression of a proposal from an initial voting phase (token count = 1) to an executed phase (token count = 2), ensuring that proposal parameters (recipient, proportion) and script logic remain immutable throughout the lifecycle while enforcing proper counting box validation and eventual treasury interaction.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)** — *Counting Box*: A box holding a state token (same token ID as SELF) with quantity equal to `currentValidationHeight`. Validates that voting has reached the required block height.
- **INPUTS(1)** (conditional) — *Treasury Box*: Only required in the second branch; must carry the treasury NFT (`treasuryNft`). Used when finalizing/executing the proposal.
- **SELF** — *Proposal Box*: The box protected by this script, containing proposal state (recipient, proportion, validation height) and a state token with quantity 1 (initial) or 2 (executed).

### Outputs
- **OUTPUTS(1)** (normal path) — *Successor Proposal Box*: Updated proposal state with identical script, recipient, and proportion; token quantity must be incremented to 2L.
- **OUTPUTS(0..n)** (execution path) — *Distribution Boxes*: When proposal executes, all outputs must NOT contain the proposal's state token (token ID is removed from circulation).

---

## Key Logic

### Branch 1: Proposal State Advancement (Normal Case)
**Condition:** `OUTPUTS(1).tokens.size == 1`

Validates a proposal's progression from voting (phase 1) to execution-ready (phase 2):

1. **Counting Box Validation** — Ensures `INPUTS(0)` holds:
   - Same token ID as SELF's state token (`currentTokens._1`)
   - Token quantity equal to `currentValidationHeight` (voting deadline reached)

2. **Immutability Checks** — The successor box at `OUTPUTS(1)` must preserve:
   - **Script** — `propositionBytes` unchanged (contract logic frozen)
   - **Proportion** — `R4[Long]` unchanged (distribution ratio immutable)
   - **Recipient** — `R5[Coll[Byte]]` unchanged (beneficiary immutable)

3. **State Token Progression**:
   - Current state token quantity must be **1L** (`isFirstUpdate`)
   - Successor state token quantity must be **2L** (`isValidTokens`)
   - Token ID remains identical across transition

4. **Height Gate** — Transaction is only valid after block 124 (`HEIGHT > 124`), enforcing a genesis/initialization period.

### Branch 2: Proposal Execution (Terminal Case)
**Condition:** `OUTPUTS(1).tokens.size != 1` (or implicit failure of Branch 1)

Executes the proposal by burning/removing the state token:

1. **Treasury Presence** — `INPUTS(1)` must carry the treasury NFT for authorization.
2. **Token Removal Invariant** — ALL outputs must NOT contain the proposal's state token ID (`currentTokens._1`), ensuring the proposal cannot be reused.

---

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R4** | `Long` | **Proportion/Ratio** — Governs how treasury funds are distributed to the recipient (e.g., percentage or fixed amount). Immutable across state transitions. | Read in both branches |
| **R5** | `Coll[Byte]` | **Recipient Address** — The Ergo address (serialized public key or contract hash) that receives distributed funds. Immutable across state transitions. | Read in both branches |
| **R6** | `Long` | **Validation Height** — The block height threshold at which voting concludes; used to set the counting box's token quantity for synchronization. | Read in Branch 1 only |

---

## Tokens

### State Token (Singleton Pattern)
- **Token ID:** `currentTokens._1` (derived from first token in SELF)
- **Initial Quantity:** `1L` (voting/pending phase)
- **Final Quantity:** `2L` (execution-ready phase)
- **Purpose:** Acts as a **State NFT** / singleton token to uniquely identify and authenticate this proposal box. Prevents double-spending and tracks proposal lifecycle.
- **Burned in Execution:** Removed from all outputs when the proposal executes, preventing replay or reuse.

### Treasury NFT
- **Token ID:** `treasuryNft` (hardcoded: `Goj3WUfmRmWgF6AngvFowK6CwQbZTmapDY3H136f528K`)
- **Purpose:** Authentication for the treasury box in the execution branch. Only treasury-authorized inputs can finalize proposal execution.

---

## Integration Pattern

### Off-Chain Workflow

1. **Proposal Creation** (genesis):
   - Off-chain bot constructs a box with this script, embedding:
     - A newly minted state token with quantity `1L`
     - Recipient address in `R5`
     - Distribution proportion in `R4`
     - Voting deadline (block height) in `R6`

2. **Voting/Counting Phase**:
   - Off-chain bot monitors voting and constructs a "counting box" (INPUTS(0)) with:
     - The same state token ID
     - Token quantity set to `R6` value (deadline height)

3. **Proposal Advancement**:
   - Off-chain constructs a transaction with:
     - INPUTS(0) = counting box
     - INPUTS(1) = SELF (proposal box)
     - OUTPUTS(1) = successor box with identical script/R4/R5, incremented state token to `2L`
     - Submits after block 124

4. **Proposal Execution**:
   - Off-chain constructs a transaction with:
     - INPUTS(0) = SELF (now phase-2 proposal)
     - INPUTS(1) = treasury box (carries `treasuryNft`)
     - OUTPUTS(0..n) = distribution boxes for recipients
     - Verifies no