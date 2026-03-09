---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — digital_public_good.es
description: "ErgoScript contract analysis: contracts/digital_public_good.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/digital_public_good.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# StabilityNexus/Bountiful-BountyPlatform-Ergo: Digital Public Good Contract

## Purpose

This contract enforces an **immutable state machine** for a Digital Public Good (DPG) singleton, ensuring that core metadata, identity token, and contract logic remain permanently fixed while allowing accumulation of ERG value. It uses a **State NFT** pattern to guarantee single-instance state transitions across transactions.

## Inputs / Outputs

**Input:**
- **SELF Box**: The current DPG state box, identified by a unique native token (singleton) in `tokens(0)`. Contains immutable metadata in R4–R9 and current ERG balance.

**Output:**
- **Successor Box** (exactly one): Must carry the same State NFT token and satisfy all immutability invariants. The contract validates that exactly one output contains the original token ID.

## Key Logic

The contract enforces three critical invariants:

1. **Single Successor Requirement**
   - Filters all outputs for boxes containing the exact same token ID as SELF (the State NFT).
   - Fails if zero or more than one successor exists, ensuring linear state progression.

2. **Register Immutability** (R4–R9)
   - `R4`, `R5`, `R6`: Byte-encoded metadata fields (immutable)
   - `R7`: Boolean flag (immutable)
   - `R8`, `R9`: Additional byte-encoded state (immutable)
   - Successor registers must equal current registers exactly.

3. **Data & Token Immutability**
   - `propositionBytes`: The ErgoScript contract code itself cannot change.
   - `tokens(0)`: The State NFT itself is locked; no token mutation allowed.
   - Only ERG value can increase (`successor.value >= SELF.value`).

All three conditions must hold; failure in any triggers `sigmaProp(false)` and transaction rejection.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Immutable metadata field (e.g., DPG descriptor, hash, or encoded parameters) |
| **R5** | `Coll[Byte]` | Immutable metadata field (e.g., creator identifier or commitment) |
| **R6** | `Coll[Byte]` | Immutable metadata field (e.g., timestamp, version, or governance hash) |
| **R7** | `Boolean` | Immutable flag (e.g., active status or authorization state) |
| **R8** | `Coll[Byte]` | Immutable extended metadata (e.g., AVL tree root or merkle proof) |
| **R9** | `Coll[Byte]` | Immutable extended state (e.g., oracle reference or external commitment) |

## Tokens

**State NFT (Singleton Token)**
- Stored in `SELF.tokens(0)`
- Token ID acts as the unique identifier for this DPG instance.
- **Quantity**: Assumed to be 1 (standard singleton pattern; enforced by token ID rule).
- **Purpose**: Ensures only one valid successor exists per transaction, preventing double-spend and enforcing linear state machine progression.
- The successor must carry the identical token in `tokens(0)`.

## Integration Pattern

**Off-chain Bot / Headless dApp Responsibility:**

1. **Query Current State**
   - Locate the UTXO carrying the DPG State NFT from the blockchain.
   - Extract R4–R9, `propositionBytes`, and current ERG balance.

2. **Construct Successor Box**
   - Create an output box with:
     - The same State NFT token.
     - Identical R4–R9 register values (byte-for-byte copy from input).
     - Identical `propositionBytes` (same ErgoScript contract).
     - ERG value ≥ input ERG (can accumulate funds, e.g., from bounty contributions).
   
3. **Sign & Submit Transaction**
   - Construct a transaction consuming SELF and producing the successor.
   - Sign with the holder's private key (Sigma protocol authentication).
   - Submit to the Ergo network.

4. **Validation Happens On-Chain**
   - Ergo nodes execute this ErgoScript in the **ErgoScript context** to validate:
     - Successor token ID matches SELF token ID.
     - All registers and contract code are byte-identical.
     - ERG balance constraint satisfied.

## Related Contracts

**Likely Companion Contracts:**
- **Bounty Deposit / Funding Box** (not shown): Feeds ERG or tokens into the DPG successor via multi-output transactions. The DPG contract allows value accumulation.
- **Bounty Claim / Reward Distribution** (not shown): A separate contract that reads the DPG state (R4–R9) and distributes accumulated ERG to claimants based on immutable metadata rules.
- **Governance / Metadata Update Contract** (if any): Would need to handle off-chain signaling or multi-sig approval *before* state inception, since this contract forbids any metadata mutation post-deployment.

---

## Summary

This is a **read-only state oracle** contract using the **Singleton / State NFT pattern**. It guarantees that a Digital Public Good's identity and immutable metadata persist unchanged across all future transactions, while functioning as a persistent accumulator for ERG value. Any modification to R4–R9 or contract logic is cryptographically blocked, ensuring trustless, permanent commitment to the DPG's original terms and properties.