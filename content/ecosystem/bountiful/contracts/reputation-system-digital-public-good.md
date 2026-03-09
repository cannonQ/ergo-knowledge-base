---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — digital_public_good.es
description: "ErgoScript contract analysis: contracts/reputation_system/digital_public_good.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/reputation_system/digital_public_good.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: Digital Public Good

## Purpose

This contract protects a box containing a Type NFT and its immutable metadata, ensuring the information serves as a permanent and tamper-proof standard for the ecosystem. It enforces that whenever the box is spent, all metadata and the NFT token itself are preserved identically, while allowing ERG value top-ups to cover storage rent.

## Inputs / Outputs

**Input:**
- A single box (SELF) containing:
  - One NFT token in the first token slot
  - Metadata in registers R4–R9

**Outputs:**
- Exactly one successor box that:
  - Contains the same NFT token (by token ID and amount)
  - Preserves all registers R4–R9 byte-for-byte
  - Has identical propositionBytes (ErgoTree)
  - Has ERG value ≥ input ERG value (allows top-ups)

If the transaction does not produce exactly one successor with these properties, it fails validation.

## Key Logic

1. **Successor Discovery:**  
   Filters OUTPUTS to find boxes containing the same NFT (matched by token ID in position `tokens(0)._1`).

2. **Successor Count Validation:**  
   Rejects the transaction if exactly one successor is not found. This prevents NFT destruction or duplication.

3. **Register Immutability:**  
   All registers R4–R9 in the successor must match the input identically:
   - **R4** (Coll[Byte]): Type name (e.g., "Web URL")
   - **R5** (Coll[Byte]): Description
   - **R6** (Coll[Byte]): Schema URI
   - **R7** (Boolean): Reputation proof flag
   - **R8** (Coll[Byte]): Reserved for future use
   - **R9** (Coll[Byte]): Reserved for future use

4. **Data Immutability:**  
   Validates that:
   - `propositionBytes` (ErgoTree lock) is unchanged
   - The NFT token (both ID and quantity) is preserved
   - All register contents are identical

5. **Value (ERG) Non-Decreasing:**  
   The successor's value must be ≥ input value, allowing only ERG additions (for storage rent payments) and never withdrawals.

6. **Atomic Validation:**  
   All conditions must be satisfied simultaneously; failure in any condition invalidates the transaction.

## Registers Used

| Register | Type | Purpose | Mutable? |
|----------|------|---------|----------|
| **R4** | `Coll[Byte]` | Type name (human-readable identifier) | ❌ No |
| **R5** | `Coll[Byte]` | Type description and use case | ❌ No |
| **R6** | `Coll[Byte]` | Schema URI (JSON Schema, IPFS reference) | ❌ No |
| **R7** | `Boolean` | Reputation proof flag (`true` if used for reputation proofs) | ❌ No |
| **R8** | `Coll[Byte]` | Reserved for future extensions | ❌ No |
| **R9** | `Coll[Byte]` | Reserved for future extensions | ❌ No |

**Note:** R0–R3 are implicit in all boxes and not explicitly checked here (R0 = value, R1 = propositionBytes, R2 = tokens, R3 = creationInfo).

## Tokens

**Single NFT:**
- Located in `SELF.tokens(0)` (first token slot)
- Must be preserved identically in the successor (same token ID and quantity)
- Serves as the non-fungible identifier and authenticity proof for the type metadata
- Acts as a Singleton / State NFT ensuring only one authoritative instance of this type exists

**No additional tokens required.**

## Integration Pattern

### Off-Chain Bot / Headless dApp Workflow

1. **Query:** Retrieve the box containing the Type NFT by token ID.

2. **Construct Transaction:**
   - Set SELF as an input (spends the current Type NFT box)
   - Build a successor output with:
     - Same NFT token (token ID and amount)
     - Identical R4–R9 register values
     - Same propositionBytes (lock script)
     - Optional: increased ERG value to cover storage rent
   - Attach required signatures or context extensions (none required by this contract)

3. **Validation:**
   - The contract automatically validates immutability constraints
   - No Sigma protocol signatures or ring signatures required
   - The spending is unconditional once structural validation passes

4. **Fee Handling:**
   - Caller must account for minimum transaction fee and minimum box value constraints
   - Top-up logic: if ERG accumulates (e.g., from donations), successor can hold more ERG

### Example Off-Chain Operation

```
Input Box (Type NFT):
  - tokens: [(NFT_ID, 1)]
  - R4: "Web URL"
  - R5: "A web-based reputation proof"
  - R6: "ipfs://QmSchema..."
  - R7: true
  - value: 1 ERG

Output Box (Successor):
  - tokens: [(NFT_ID, 1)]          # ✓ Identical
  - R4: "Web URL"                   # ✓ Identical
  - R5: "A web-based reputation proof"  # ✓ Identical
  - R6: "ipfs://QmSchema..."        # ✓ Identical
  - R7: true                        # ✓ Identical
  - value: 2 ERG                    # ✓ Value increased (top-up)
  - propositionBytes: [same]        # ✓ Lock unchanged
```

## Related Contracts

Based on the file path and context, this contract integrates with:

1. **Reputation Proof Contracts** (sibling modules):
   - Contracts that reference `R7` (the Boolean flag) to determine if this type is valid for reputation proofs
   - Must read this Type NFT box as a data input to validate proof structure

2. **Proof