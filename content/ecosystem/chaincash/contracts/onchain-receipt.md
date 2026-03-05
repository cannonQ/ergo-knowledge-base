---
title: BetterMoneyLabs/chaincash — receipt.es
description: "ErgoScript contract analysis: contracts/onchain/receipt.es"
tags: [bettermoneylabs, chaincash, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
contract_file: contracts/onchain/receipt.es
project: bettermoneylabs-chaincash
---
# ErgoScript Contract Analysis: `receipt.es`

## Purpose

This contract manages **receipt boxes** that track redeemed notes in a multi-stage financial protocol, protecting them from storage rent erosion while enabling either long-term token burn or re-redemption through paired reserve contract spending. Receipts serve as immutable proof of redemption history and can be spent only under strict conditions: either after a 3-year lockup with mandatory token burning, or immediately via atomic spending with a reserve contract box.

## Inputs / Outputs

### Inputs
- **SELF (Box #0)**: The receipt box being spent, containing:
  - Tokens to be managed (protected from storage rent)
  - R4: AVL tree of ownership history
  - R5: Redeemed position identifier
  - R6: Creation height
  - R7: Redeemer's public key
  - propositionBytes: Receipt contract ErgoTree

- **INPUTS(1)**: Reserve contract box (required at fixed position #1)
  - propositionBytes: Reserve contract ErgoTree (hashed for verification)

### Outputs
- **OUTPUTS(1)**: New receipt box (in re-redemption path)
  - propositionBytes: Must match SELF's ErgoTree (contract preserves itself)
  - Carries forward receipt state

- **All other outputs**: Must contain **zero native tokens** (in burn path)

## Key Logic

The contract enforces a **disjunctive validation** (`||`) with two mutually exclusive redemption paths:

### Path 1: Token Burn (After 3-Year Lockup)
```
burnDone = (HEIGHT > creationHeight + burnPeriod) && noTokensInOutputs
```
- Requires **788,400 blocks** (~3 years) to elapse since box creation (R6)
- All outputs must be token-free (`noTokensInOutputs`)
- Protects against **storage rent** by removing tokens before they accumulate fees
- No signature required (timelock-based)

### Path 2: Immediate Re-Redemption (Atomic Spend with Reserve)
```
reRedemption = proveDlog(SELF.R7[GroupElement].get) && sigmaProp(reserveSpent && receiptCreated)
```
- **Signature requirement**: Redeemer's private key (corresponding to R7 public key) must sign
- **Reserve contract validation**: 
  - INPUTS(1) must be a reserve contract (verified via blake2b256 hash of ErgoTree)
  - Version byte is stripped (`slice(1, size)`) for robust comparison
  - Hash must match `$reserveContractHash` (injected constant)
- **Receipt continuation**: OUTPUTS(1) must be a new receipt box with identical ErgoTree
- Enables **re-redemption** workflows without waiting for burn period

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | AVLTree | Immutable history of ownership changes for the redeemed note; enables audit trail |
| **R5** | Long | Identifier of the redeemed position; links receipt to original redemption event |
| **R6** | Int | Block height when receipt was created; used to calculate burn eligibility (current HEIGHT - R6) |
| **R7** | GroupElement | Redeemer's public key (Schnorr); enables re-redemption signature verification via `proveDlog` |

**Registers R8-R9**: Unused in this contract.

## Tokens

### Token Protection Mechanism
- **Purpose**: Prevent **storage rent** from eroding tokenized value
- **Burn Path**: All native tokens must be destroyed (removed from UTXO set) after 3-year lockup
- **Re-redemption Path**: Tokens may be transferred to new receipt outputs (state continuity)
- **No NFT used**: Unlike singleton patterns, receipts don't require a unique state NFT; the fixed position constraint (INPUTS(1)) and reserve contract pairing provide atomicity

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

**For Burn Path:**
1. Monitor receipt boxes for reaching `creationHeight + 788400`
2. Construct transaction:
   - Input: Receipt box
   - Outputs: **Zero-token boxes** (must satisfy `noTokensInOutputs`)
   - Adjust box values to maintain **minimum box value** and **minimum transaction fee**
3. Sign with network (no receipt holder signature needed)
4. Execute to eliminate storage rent liability

**For Re-Redemption Path:**
1. Construct atomic transaction with:
   - INPUTS(0): Receipt box (SELF)
   - INPUTS(1): Reserve contract box (exact position critical)
2. Obtain **Sigma protocol signature** from redeemer (R7 key)
3. Create OUTPUTS(1): New receipt box with:
   - Same propositionBytes as SELF
   - Updated state in R4/R5 (if applicable)
4. Verify reserve contract hash matches injected constant
5. Submit signed transaction

### Constant Segregation
- `$reserveContractHash`: Base58-encoded blake2b256 hash of reserve contract ErgoTree
  - Must be injected at contract compilation
  - Enables reserve contract upgrades via new receipt deployments

## Related Contracts

### Reserve Contract (`reserve.es`)
- **Counterpart**: Receipt's atomic spending partner
- **Interaction**: INPUTS(1) in re-redemption path
- **State Machine**: Together they form a multi-stage contract system
  - Reserve handles actual fund management
  - Receipt tracks redemption history + burn mechanism
- **Cross-validation**: Reserve contract likely validates receipt's R4 (AVL tree) and R5 (position) during re-redemption

### Implied Multi-Stage Protocol
- **Stage 1**: Redemption (creates receipt + reserve state)
- **Stage 2**: Re-redemption (receipt + reserve spend atomically, preserving receipt)
- **Stage 3**: Burn (receipt destroyed after 3 years, tokens removed)

## Security Properties

| Property | Mechanism |
|----------|-----------|
| **Burn Guarantee** | Timelock (788400 blocks) + mandatory zero-token output constraint |
| **Re-redemption Atomicity** | Fixed input position (INPUTS(1)) + reserve hash verification |
| **