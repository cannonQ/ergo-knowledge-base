---
title: BetterMoneyLabs/chaincash — note.es
description: "ErgoScript contract analysis: contracts/onchain/note.es"
tags: [bettermoneylabs, chaincash, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
contract_file: contracts/onchain/note.es
project: bettermoneylabs-chaincash
---
# ErgoScript Contract Analysis: `note.es`

## Purpose

The **Note contract** implements a digital currency unit (denominated in milligrams of gold) with a **cryptographic ownership chain** secured by Schnorr signatures. Each note tracks its holder and spending history via an **AVL+ tree**, enabling either standard spending (with signature validation and history append) or redemption against a reserve contract to create receipts for further transactions.

---

## Inputs / Outputs

### Inputs
- **SELF** (Note Box):
  - Contains the note token (#0) with amount equal to the note value
  - Locked by this contract
  - Carries R4 (AVL tree), R5 (holder public key), R6 (position counter)

- **Reserve Box** (Data Input, spending path only):
  - Referenced via `CONTEXT.dataInputs(0)` during spending
  - Must contain reserve ID token and holder's public key in R4
  - Used to validate holder authority without consuming the reserve

- **Reserve Box** (Regular Input, redemption path only):
  - Consumed at input index specified by negative action value
  - Must match embedded `$reserveContractHash`

### Outputs
- **Note Output(s)**:
  - Same ErgoTree script as SELF
  - Updated R4 (AVL tree with new signature appended)
  - Updated R5 (next holder's public key)
  - Updated R6 (position incremented)
  - Token amount preserved (or split if change exists)
  - Minimum box value ≥ SELF.value

- **Receipt Output** (redemption path only):
  - Created at same index as consumed reserve
  - Must match embedded `$receiptContractHash`
  - Locks the note token for receipt-based redemption

- **Change Output** (optional, spending path):
  - At index specified by context variable (4)
  - Receives remaining note tokens if splitting the note

---

## Key Logic

### **Spending Path** (`action >= 0`)

1. **Signature Validation** (Schnorr):
   - Retrieve signature components `a` (GroupElement) and `z` (BigInt) from context variables
   - Compute Fiat-Shamir challenge: `e = blake2b256(a_encoded || message || holder_encoded)`
   - Verify: `g^z == a * holder^e` (standard Schnorr equation)
   - Message = `position || noteValue || tokenId` (prevents replay across positions/tokens)

2. **Reserve Verification**:
   - Read reserve box from data inputs
   - Confirm holder's public key matches reserve's R4 (proves holder authorized the reserve)
   - Extract reserveId token from reserve for AVL tree key composition

3. **AVL Tree Update**:
   - Insert leaf `(positionBytes || reserveId) → (a_encoded || z_encoded)` into R4 tree
   - Verify insertion proof provided in context variable (3)
   - Digest must update deterministically; enabled operations must remain unchanged

4. **Output Validation**:
   - Next note output(s) must:
     - Have incremented position (`R6 = position + 1`)
     - Preserve AVL tree digest and operations
     - Maintain same ErgoTree script
     - Define new holder in R5
     - Preserve or increase ERG value
   - Token amounts: if change output exists, sum must equal input; otherwise, exact token match
   - **Dual signature check**: `proveDlog(holder)` prevents mempool-level note manipulation

### **Redemption Path** (`action < 0`)

1. **Reserve Contract Verification**:
   - Compute hash: `blake2b256(reserveErgoTree.slice(1, size))`
   - Must match `$reserveContractHash` (skips version byte)

2. **Receipt Contract Verification**:
   - Output at same index must have ErgoTree hashing to `$receiptContractHash`
   - Reserve contract handles token locking in receipt; note contract only validates contract presence

3. **Holder Signature**:
   - Require `proveDlog(holder)` to authorize redemption

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `AvlTree` | AVL+ tree digest tracking spending history: keys are `(position \|\| reserveId)`, values are `(a_encoded \|\| z_encoded)` from Schnorr signatures. Enables membership/non-membership proofs for audit trails. |
| **R5** | `GroupElement` | Current holder's public key (elliptic curve point). Used in signature verification and to authorize spending/redemption. |
| **R6** | `Long` | Position counter (spending chain length). Incremented on each spend; prevents signature replay. |

---

## Tokens

| Slot | Type | Purpose |
|------|------|---------|
| **#0** | Native Token | **Note Token**: amount = note value in milligrams of gold (unit of account). Token ID must remain consistent across all note boxes in the chain. New token created at note issuance with all supply locked in initial box; spent/transferred alongside note. Burned or split when note is divided or redeemed. |

**Token ID Rule**: The same token ID (#0) must appear in all note outputs and receipts to enforce accounting invariants.

---

## Integration Pattern

### Off-Chain Responsibilities

1. **For Spending (`action >= 0`)**:
   - **Construct Schnorr signature** over message = `position || noteValue || tokenId`:
     - Randomly sample `r`, compute `a = g^r`
     - Compute challenge `e = blake2b256(a_encoded || message || holder_encoded)`
     - Compute `z = r + e * private_key`
     - Pass `a` (var 1) and `z` (var 2) via Context Extension
   - **Obtain AVL tree proof**: fetch current tree digest, compute insertion proof for new leaf, pass via var (3)
   - **Identify note output**: set var (0) = output index of next note box
   - **Optional change**: if splitting note, provide change output index via var (4)
   - **Provide reserve data input**: place reserve box (not consumed) at input