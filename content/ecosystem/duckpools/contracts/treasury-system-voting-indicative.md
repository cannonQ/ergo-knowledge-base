---
title: duckpools/lend-protocol-contracts — indicative.md
description: "ErgoScript contract analysis: contracts/treasury-system/voting/indicative.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/treasury-system/voting/indicative.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Indicative Voting

## Purpose

This contract implements an **indicative voting mechanism** for a governance system, allowing token holders to stake **Quacks** tokens (a native token) on proposals before a deadline. The contract enforces vote accumulation during the voting period and enforces vote redemption afterward, maintaining immutable proposal metadata and ensuring token conservation through atomic swaps.

## Inputs / Outputs

| Aspect | Details |
|--------|---------|
| **Input Box (SELF)** | A Box locked by this contract containing: proposal metadata (R4-R7), two token types (placeholder Quacks + real Quacks), and the current vote count. |
| **Output Box (OUTPUTS(0))** | The continuation Box, must retain the same ErgoTree script and proposal data, with modified token quantities reflecting vote changes and updated vote counts. |
| **Data Inputs** | None required. |

## Key Logic

The contract enforces a **state machine** with two phases:

### Phase 1: Voting Period (`HEIGHT < deadline`)
- **Vote Direction**: Only **increases** in real Quacks (`deltaQuacks > 0`) are permitted—tokens are being staked as votes.
- **Vote Accounting**: The output's vote count (`finalVotesFor`) must increase by exactly the amount of real Quacks received (`deltaQuacks`), OR decrease by that amount if voting against (dual-direction logic).
- **Token Exchange**: Placeholder Quacks **decrease** by the amount of real Quacks received, enforcing a 1:1 redemption: `placeHolderQuacks._2 - deltaQuacks == finalPlaceHolderQuacks._2`.
- **Immutability**: Proposal ID (R6), title (R7), deadline (R5), script, and token IDs must remain unchanged.

### Phase 2: Post-Deadline (`HEIGHT ≥ deadline`)
- **Only Withdrawal**: Real Quacks can only **decrease** (`deltaQuacks < 0`), enforcing vote redemption and token reclamation.
- **Vote Freezing**: Vote counts must remain static (`retainVotes`).
- **Token Restoration**: Placeholder Quacks increase as real Quacks decrease, reversing the staking relationship.

Both phases enforce **token ID verification** and **script continuity**, ensuring the singleton Box follows the same ErgoTree.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | **Vote count** (cumulative "yes" votes); must remain constant post-deadline, updated during voting. |
| **R5** | `Long` | **Deadline** (block height); immutable; determines phase transition. |
| **R6** | `Coll[Byte]` | **Proposal ID/Hash** (identifier); immutable; links voting to specific proposal. |
| **R7** | `Coll[Byte]` | **Proposal Title** (human-readable); immutable; metadata for off-chain indexing. |

## Tokens

| Token Slot | Role | Semantics |
|------------|------|-----------|
| **tokens(0)** – Placeholder Quacks | **Voting receipt / liquidity pool** | Represents an option to vote. Decreases 1:1 when staked as real Quacks during voting; increases when real Quacks are redeemed post-deadline. |
| **tokens(1)** – Real Quacks | **Governance voting power** | Native token representing locked voting stake. Increases during voting (tokens staked), decreases post-deadline (tokens redeemed). Quantity change (`deltaQuacks`) drives vote count updates. |

This is a **token swap pattern**: placeholder → real (voting) → placeholder (redemption).

## Integration Pattern

### Off-Chain Requirements

1. **Proposal Creation Bot**:
   - Mint an initial Box with both token types in correct quantities.
   - Set R4=0 (initial vote count), R5=deadline height, R6=proposal hash, R7=title.
   - Lock with this contract's ErgoTree.

2. **Vote Staking (During Voting Window)**:
   - Construct a transaction with:
     - Input: the singleton voting Box (SELF).
     - Output: a new Box with the same script, R4 updated to `votesFor + deltaQuacks`, token quantities adjusted.
     - Attach user signature or proof that they hold real Quacks to exchange.
   - Off-chain must verify `HEIGHT < deadline` and delta sign.

3. **Vote Redemption (Post-Deadline)**:
   - Construct a transaction with:
     - Input: the voting Box with frozen votes.
     - Output: a Box with R4 unchanged, placeholder Quacks restored, real Quacks redeemed.
   - Off-chain must verify `HEIGHT ≥ deadline`.

4. **Validation**: 
   - Off-chain must ensure correct token IDs before submission.
   - Verify the ErgoTree of OUTPUTS(0) matches SELF to enforce singleton continuity.

## Registers Used (Corrected & Expanded)

The contract reads and writes R4–R7 in both SELF and OUTPUTS(0):

- **Read from SELF**: R4, R5, R6, R7, token array indices.
- **Write to OUTPUTS(0)** (via off-chain construction): R4 (vote count), others remain unchanged.
- **R0–R3**: Not used (standard: R0=amount, R1=tokens implicit, R2=creationInfo, R3=registers map).

---

## Related Contracts

Based on file structure (`treasury-system/voting/`), this contract is part of a **governance subsystem** likely including:

- **Proposal Registry Contract**: Manages proposal creation, storage, and finality.
- **Voting Aggregator**: Collects votes from multiple indicative voting Boxes and transitions them to binding votes.
- **Treasury/DAO Contract**: Receives finalized vote results and executes approved actions (e.g., fund transfers, parameter updates).
- **Quacks Token Contract**: Defines minting/burning rules for placeholder and real Quacks (if applicable).

The **indicative** contract serves as a **stage in a multi-stage contract workflow**, gathering preference signals before committing to binding governance actions.

---

## Security Considerations

1. **