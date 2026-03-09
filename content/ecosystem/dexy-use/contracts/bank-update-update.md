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
project: dexy-use
---
# ErgoScript Contract Analysis: `update.es`

## Purpose

This contract implements a **decentralized governance mechanism** for updating core system contracts (bank, extract, intervention) in the Dexy protocol. It requires a minimum threshold of ballot votes to authorize and execute contract upgrades atomically, ensuring protocol changes cannot be made unilaterally.

---

## Inputs / Outputs

### Inputs
| Position | Box Type | Purpose |
|----------|----------|---------|
| **0** | Update Box (SELF) | The governance authorization box; must be first input |
| **1** | Contract-to-Update Box | Holds the contract NFT and current contract code; locked under old ErgoTree |
| **2+** | Ballot Boxes (filtered) | Each holds a ballot token; must satisfy `isValidBallot` predicate |

### Outputs
| Position | Box Type | Purpose |
|----------|----------|---------|
| **0** | Update Box (copy) | Recreated with same tokens, propositionBytes, and preserved value |
| **1** | Contract-to-Update Box (updated) | New ErgoTree (contract code), same NFT & value as input |

---

## Key Logic

### Core Validation Steps

1. **Update Box Position Check** (`validUpdateIn`)
   - Ensures this contract's box is the first input (prevents reordering attacks)

2. **Contract-to-Update NFT Verification** (`validContractToUpdateIn`)
   - Input box at position 1 must hold the `contractToUpdateNFT` singleton token
   - Confirms the correct contract box is being updated

3. **Value & Token Preservation** (`validContractToUpdateOut`)
   - NFT token ownership remains unchanged (cannot be burned or transferred)
   - Ergs value persists across the update

4. **Ballot Collection & Vote Counting**
   - Filter all inputs for boxes holding `ballotTokenId` and satisfying `isValidBallot`:
     - Each ballot stores its owner's **GroupElement** in R4
     - R5 contains the box ID of this update box (ties vote to this governance proposal)
     - R6 contains the **blake2b256 hash** of the proposed new contract's `propositionBytes`
   - Sum ballot token quantities (voting power = token amount)

5. **Threshold Check** (`validVotes`)
   - Total votes must reach minimum (`minVotes = 3` out of expected 5 ballot holders)

6. **Update Box Preservation** (`validUpdateOut`)
   - Update box must be recreated as first output
   - Same tokens and propositionBytes (contract logic immutable)
   - Value >= original (can only increase; protects against storage rent drainage)

7. **Contract Code Commitment** (`contractToUpdateBoxOutHash`)
   - Proposed new contract code's hash must match what ballot holders voted for (R6)
   - Prevents substitution attacks between voting and execution

---

## Registers Used

| Register | Input Box | Type | Purpose |
|----------|-----------|------|---------|
| **R4** | Ballot Box | `GroupElement` | Cryptographic identity of ballot token holder (owner/voter) |
| **R5** | Ballot Box | `Coll[Byte]` | Box ID of the update box; ensures vote is tied to this governance proposal |
| **R6** | Ballot Box | `Coll[Byte]` | blake2b256 hash of proposed contract's `propositionBytes`; commits voter to specific upgrade |

---

## Tokens

| Token | Location | Type | Purpose |
|-------|----------|------|---------|
| **contractToUpdateNFT** | Input[1], Output[1] | State NFT / Singleton | Identifies and authenticates the contract box being governed; prevents unauthorized upgrades |
| **ballotTokenId** | Input[2+] | Voting Token (variable quantity) | Represents voting power; quantity determines vote weight; immutable identity prevents double-voting |

---

## Integration Pattern

### Off-Chain Bot / dApp Responsibilities

1. **Governance Proposal Creation**
   - Monitor governance events (e.g., community signaling, DAO vote)
   - Compile new contract code (ErgoScript)
   - Compute `blake2b256(newContractPropositionBytes)`

2. **Ballot Collection**
   - Identify all 5 ballot token holders
   - For each holder willing to vote:
     - Create input ballot box containing:
       - `ballotTokenId` (NFT identifying this ballot holder)
       - R4: voter's `GroupElement` (public key or group commitment)
       - R5: `SELF.id` (this update box's ID)
       - R6: hash of proposed contract
   - Requires voter's Sigma protocol signature (from ballot box spending)

3. **Transaction Construction**
   - Input[0]: This update box (spends under its ErgoTree)
   - Input[1]: Contract-to-Update box (spends under old contract's ErgoTree)
   - Input[2..n]: Filtered ballot boxes (each spends under ballot box's ErgoTree; includes voter signature)
   - Output[0]: Update box (value ≥ SELF.value, same contract logic)
   - Output[1]: Contract-to-Update box (new ErgoTree, same NFT & value)

4. **Proof Requirements**
   - Valid Sigma protocol signatures from ≥ 3 ballot token holders
   - Each ballot's R5 must equal update box ID (cryptographic commitment)
   - Each ballot's R6 must equal computed hash (vote verification)

---

## Related Contracts

Based on code structure and comments, this contract integrates with:

| Contract | Role | Integration |
|----------|------|-------------|
| **Bank Contract** | System core | Governs via `bankNFT` singleton; update box may update its ErgoTree |
| **Extract Contract** | System core | Governs via `extractNFT` singleton; update box may update its ErgoTree |
| **Intervention Contract** | System core | Governs via `interventionNFT` singleton; update box may update its ErgoTree |
| **Ballot Contracts** | Voter authorization | Each ballot box holds voting token; must spend to authorize vote |

**Governance Composition**: This is a **multi-stage contract** pattern—the update