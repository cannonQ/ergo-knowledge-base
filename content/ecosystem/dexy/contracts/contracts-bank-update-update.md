---
title: kushti/dexy-stable — update.es
description: "ErgoScript contract analysis: contracts/bank/update/update.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/update/update.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `contracts/bank/update/update.es`

## Purpose

This contract implements a **multi-signature governance mechanism** for upgrading core Dexy protocol contracts (bank, extract, or intervention contracts). It validates that a proposed contract update has received sufficient weighted votes from ballot token holders before permitting the upgrade to proceed, following a pattern adapted from SigmaUSD's governance framework.

---

## Inputs / Outputs

### Inputs
1. **INPUTS(0)** – The Update Box itself (this contract); must be the first input
2. **INPUTS(1)** – The Contract-to-Update Box (bank, extract, or intervention contract); holds the State NFT (`contractToUpdateNFT`)
3. **INPUTS(2..n)** – Ballot Boxes (filtered dynamically); each holds a ballot token and encodes a governance vote

### Outputs
1. **OUTPUTS(0)** – Update Box (copy of input update box; must preserve tokens, propositionBytes, and value)
2. **OUTPUTS(1)** – Updated Contract Box (copy of input contract box with same tokens and value, but potentially modified `propositionBytes`)

---

## Key Logic

### Core Validation Flow

The contract enforces five independent invariants that must all pass:

1. **`validUpdateIn`** – Ensures this update box is the first input (prevents reordering attacks)

2. **`validContractToUpdateIn`** – Verifies the second input holds the target contract's State NFT (`contractToUpdateNFT`), confirming it is the genuine contract being upgraded

3. **`validContractToUpdateOut`** – Enforces that the output contract box preserves:
   - All native tokens (the State NFT cannot be burned or minted)
   - The ERG value (prevents fund extraction)
   - Only the `propositionBytes` (ErgoTree) may change

4. **`validUpdateOut`** – Ensures the update box itself is preserved as-is in output:
   - Tokens unchanged
   - ErgoScript contract (`propositionBytes`) unchanged
   - Value maintained or increased (allows additional deposits for fees)

5. **`validVotes`** – Aggregates ballot token quantities across all valid ballot boxes and verifies the total vote count ≥ `minVotes` (default: 3 out of 5)

### Vote Validation (`isValidBallot`)

A ballot box is considered valid only if:
- It holds at least one token
- Its first token is the `ballotTokenId`
- **R5** stores `SELF.id` (the update box ID), binding the vote to this specific proposal
- **R6** stores `blake2b256(contractToUpdateBoxOut.propositionBytes)`, the hash of the new contract code being voted on

This design prevents vote reuse across different proposals and ensures voters commit to the exact bytecode being deployed.

---

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R5** | `Coll[Byte]` | Ballot Box | Stores the ID of the update box this ballot votes on; ensures votes bind to a specific proposal |
| **R6** | `Coll[Byte]` | Ballot Box | Stores the blake2b256 hash of the proposed contract code; ensures voters approve the exact bytecode |

**Note:** The update box itself has empty registers; all state is externally managed via the contract boxes being updated.

---

## Tokens

### Native Tokens Used

1. **`contractToUpdateNFT`** – State NFT singleton token
   - Held in the Contract-to-Update Box (INPUTS(1))
   - Identifies which Dexy contract (bank, extract, or intervention) is being upgraded
   - Token ID is injected as a Base64-encoded constant
   - Prevents unauthorized contract substitution

2. **`ballotTokenId`** – Governance / Voting Token
   - Held by each ballot box
   - Token quantity determines vote weight (votes are summed across all ballot boxes)
   - Allows weighted voting (e.g., a ballot box holding 2 tokens = 2 votes)
   - Token ID is injected as a Base64-encoded constant

### Token Invariants

- No tokens can be minted or burned by this contract
- The State NFT (`contractToUpdateNFT`) must flow unchanged from input to output
- Ballot tokens are consumed (spent) as part of vote validation but their value is aggregated, not preserved in outputs

---

## Integration Pattern

### Off-Chain Bot / DAO Coordinator Responsibilities

1. **Prepare the Proposal**
   - Compile new ErgoScript contract code for the target contract
   - Compute `blake2b256(propositionBytes)` of the new code
   - Create the update box with empty registers

2. **Collect Votes**
   - Wait for ballot token holders to create ballot boxes
   - Each ballot box must set:
     - **R5** = update box ID (SELF.id)
     - **R6** = hash of proposed contract bytecode
   - Track ballot boxes until vote threshold is reached

3. **Construct Transaction**
   - **Input 0:** Update box (this contract)
   - **Input 1:** Current contract-to-update box (holding State NFT)
   - **Inputs 2..n:** All ballot boxes with valid votes
   - **Output 0:** Copy of update box (same value, tokens, code)
   - **Output 1:** New contract box with:
     - Same State NFT and value as input
     - New `propositionBytes` (upgraded ErgoTree)
   - Include sufficient ERG for transaction fee

4. **Verification Steps**
   - Verify `votesCount` aggregates correctly across ballot boxes
   - Verify `contractToUpdateBoxOutHash` matches the blake2b256 hash from all R6 registers
   - Ensure no token minting or burning occurs
   - Validate box ordering (update box first, contract box second)

### Context Extension

Context constants must be set at signing:
```
{
  contractToUpdateNFT: <TokenId_Base64>,
  ballotTokenId: <TokenId_Base64>
}
```

These distinguish which Dexy contract is being upgraded and which token represents voting power.

---

## Related Contracts

### Composition Within Dexy Governance

Based on the