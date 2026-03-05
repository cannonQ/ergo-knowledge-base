---
title: BetterMoneyLabs/chaincash — note.es
description: "ErgoScript contract analysis: contracts/layer2-old/note.es"
tags: [bettermoneylabs, chaincash, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
contract_file: contracts/layer2-old/note.es
project: bettermoneylabs-chaincash
---
# ErgoScript Contract Analysis: `note.es`

## Purpose

This contract implements a **transferable note** with an immutable ownership history recorded in an AVL+ tree. Notes can be spent (transferred with optional change output) or redeemed through a multi-signature protocol. The history tree tracks sequential ownership changes, keyed by position + reserve ID, with Schnorr-like signatures as values.

## Inputs / Outputs

### Inputs
- **SELF**: The note box containing:
  - R4: AVL+ tree of ownership history
  - R5: Current holder's public key (GroupElement)
  - R6: Current chain position (Long)
  - R7: Note value (Long)
  - Tokens: Native token representing the note itself

- **Data Input (CONTEXT.dataInputs(0))**: Reserve box providing:
  - tokens(0)._1: Reserve ID (used as AVL tree key)
  - R4: Reserve's public key (GroupElement) for holder validation

### Outputs
- **Spending Path**: 
  - OUTPUTS(action): Updated note box with incremented position, modified AVL tree digest, and new holder
  - Optional OUTPUTS(changeIdx): Change note box (if splitting)
  
- **Redemption Path**:
  - OUTPUTS(0): Redemption box containing the historical AVL tree and redemption deadline

## Key Logic

### Spending Path (action ≥ 0)
1. **Signature Verification** (Schnorr-like protocol):
   - Message = position || noteValue || noteId
   - Challenge `e` = BLAKE2b-256(message) as BigInt (weak Fiat-Shamir)
   - Validates proof-of-knowledge: `g^z = a * holder^e`
   - Confirms holder matches reserve's designated public key (R4)

2. **AVL Tree Insertion**:
   - Inserts (keyBytes, valueBytes) into history tree where:
     - keyBytes = position || reserveId
     - valueBytes = a || z (signature components)
   - Proof must be valid; insertion failure triggers contract rejection

3. **Output Validation**:
   - **nextNoteCorrect()** checks each note output:
     - R4 digest matches new AVL tree (post-insertion)
     - Script remains unchanged (same propositionBytes)
     - R5 (new holder) is defined
     - Minimum box value preserved
     - R6 position incremented by exactly 1
   - **Change handling** (optional):
     - If changeIdx provided: both selfOutput and changeOutput must be valid notes
     - Sum of output positions ≤ input position (burn allowed)
     - Both outputs have position > 0

### Redemption Path (action < 0)
1. Validates OUTPUTS(0) contains redemption token (placeholder: fromBase58(""))
2. Confirms AVL history is copied unchanged to redemption box
3. Enforces redemption deadline in R5 ≥ HEIGHT + 1440 blocks (~10 days)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | AvlTree | Immutable ownership history indexed by (position, reserveId); values are (a, z) signature tuples |
| **R5** | GroupElement (spending); Int (redemption) | Current holder's public key (spending path); Redemption deadline block height (redemption path) |
| **R6** | Long | Sequential chain position, incremented on each transfer; used to prevent replay and order history |
| **R7** | Long | Note's value in nanoErg or arbitrary units; preserved or burnt during transfers |

## Tokens

- **Note Token**: The native token in SELF.tokens represents the note's identity; copied to output boxes to maintain continuity
- **Reserve Token**: Reserve box uses tokens(0)._1 as a unique reserve identifier, embedded as AVL tree key
- **Redemption Token** (TODO): Placeholder redemption credential; contract references fromBase58("") but actual token ID is unimplemented

## Integration Pattern

### Off-Chain Components Must Construct:
1. **Context Variables** (getVar calls):
   - `Byte(0)`: action (≥0 for spend, <0 for redeem)
   - `GroupElement(1)`: Schnorr signature component `a` (g^r for random r)
   - `Coll[Byte](2)`: Schnorr signature component `z` as bytes (r + e·sk mod order)
   - `Coll[Byte](3)`: AVL tree insertion proof
   - `Byte(4)` (optional): change output index

2. **Off-Chain Logic**:
   - Compute Schnorr challenge: `e = blake2b256(position || noteValue || noteId)` 
   - Generate signature (a, z) proving knowledge of current holder's private key
   - Fetch current AVL tree digest from R4
   - Generate valid AVL insertion proof for (position || reserveId) → (a || z)
   - Construct output note(s) with incremented position and new holder public key
   - Ensure minimum box value (Storage Rent) is met for all outputs

3. **Data Input**:
   - Provide reserve box as data input for holder validation (non-spending input)

### Spending Flow
```
Note(holder=H, pos=n, tree=T) + Reserve(pk=H) 
  → Signature proof (a, z, e)
  → AVL insert (n || reserveId) → (a || z)
  → Note(holder=H', pos=n+1, tree=T')
```

## Related Contracts

- **Reserve Contract** (referenced but not shown): Must expose public key in R4 and token ID; acts as holder registry
- **Redemption Contract** (referenced but incomplete): Would accept OUTPUTS(0) from redemption path; expected to validate redemption token and deadline
- **Multi-stage State Machine** (implied): Note lifecycle spans spending → redemption stages; suggests parent contracts orchestrate redemption logic

---

## Notes & Issues

⚠️ **TODO Items in Code**:
- **Weak Fiat-Shamir**: Challenge uses single BLAKE2b hash; consider strong FS with additional entropy
- **