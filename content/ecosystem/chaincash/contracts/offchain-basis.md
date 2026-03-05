---
title: BetterMoneyLabs/chaincash — basis.es
description: "ErgoScript contract analysis: contracts/offchain/basis.es"
tags: [bettermoneylabs, chaincash, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
contract_file: contracts/offchain/basis.es
project: bettermoneylabs-chaincash
---
# ErgoScript Contract Analysis: `basis.es`

## Purpose

This contract implements **Basis**, an on-chain reserve backing off-chain credit-based payment systems. It enables debt redemption with cryptographic guarantees, preventing double-spending and unauthorized fund access while allowing minimally-trusted trackers to manage off-chain debt state. The contract is designed for micropayments, mesh network payments, and agent-to-agent transfers where immediate on-chain settlement is impractical.

---

## Inputs / Outputs

### Inputs
- **Reserve Box** (primary input): Contains the contract, holds ERG collateral backing off-chain debt, and stores cumulative redeemed amounts in an AVL tree (R5).
- **Data Input** (optional): Tracker's committed state as an AVL tree proof, providing authoritative debt records off-chain.

### Outputs
- **Updated Reserve Box**: Same contract script, reduced ERG (after redemption payout), updated R5 AVL tree reflecting newly redeemed amounts.
- **Payment Box**: Recipient receives redeemed ERG value.

### Key Box Properties
- **Reserve Owner Box**: Signed by reserve owner (issuer of original IOU).
- **Tracker State Box** (via data input): Merkle proof of cumulative debt(A → B) in tracker's AVL tree.

---

## Key Logic

### Redemption Action (Core Validation)

The contract enforces:

1. **Dual Signature Requirement**
   - Signature from **reserve owner** (issuer of original IOU, verifies authorization to redeem)
   - Signature from **tracker** (verifies off-chain debt state is consistent, prevents replay)
   - Both signatures on message: `hash(ownerPubKey || receiverPubKey) || totalDebt`

2. **AVL Tree Proofs Verify Debt Commitment**
   - **Context var #8** (required): Merkle proof in tracker's committed AVL tree that `hash(A || B) → totalDebt` exists.
   - Proves the claimed debt amount was committed by the tracker off-chain.

3. **Cumulative Redeemed Amount Tracking**
   - **R5 AVL tree** in reserve box stores: `hash(A || B) → alreadyRedeemed`
   - **Context var #7** (optional): Merkle proof of prior redemptions for this (owner, receiver) pair.
   - Constraint: `newRedemption ≤ totalDebt - alreadyRedeemed`
   - Prevents double-redemption of the same debt.

4. **Redemption Amount Constraint**
   - Output box value: `inputReserveValue - redemptionAmount ≥ minBoxValue`
   - ERG output to receiver: `redemptionAmount`

5. **Storage Rent Compliance**
   - Updated reserve box must satisfy Ergo's minimum box value rules.
   - AVL tree serialization fits within register limits.

### Debt Transfer (Novation) Action

For off-chain debt reassignment (A → B → C becomes A → C):

1. **Debtor Consent** (A's signature)
   - Message: `hash(A || B) || hash(A || C) || transferAmount`
   - Proves A authorizes debt obligation shift.

2. **Tracker Verification & Atomic Update**
   - Tracker verifies: `debt(A → B) ≥ transferAmount`
   - Atomically decrements `debt(A → B)` and increments `debt(A → C)` in off-chain ledger.
   - Posts updated AVL tree root on-chain (via state box).

3. **On-Chain Enforcement** (if redemption follows transfer)
   - Both new debt obligations must be committable in tracker's AVL tree.
   - Redemption contract validates against updated tree state.

### Security Invariants

| Threat | Mitigation |
|--------|-----------|
| A pays B, then pays self and redeems (double-spend) | Tracker maintains cumulative ledger; contract enforces AVL tree consistency |
| Tracker steals reserve funds | Both owner **and** tracker signatures required; tracker alone cannot unlock ERG |
| Unauthorized debt transfer | Debtor (A) must sign transfer; tracker cannot forge |
| Redemption double-counting | Contract's AVL tree (R5) tracks `alreadyRedeemed`, ensuring `totalDebt - alreadyRedeemed ≥ 0` |
| Tracker censorship / re-ordering | Tracker can re-order but cannot reverse prior redemptions (immutable on-chain AVL state) |

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` (implied) | Reserve owner's public key for signature verification |
| **R5** | `AvlTree` | Cumulative redeemed amounts: `hash(ownerPubKey \|\| receiverPubKey) → redeemed(nanoERG)`. Maintained as state machine across redemption transactions. |
| **R6** | (reserved) | Tracker federated pubkey(s) or threshold signature parameters (if multi-sig). |
| **R7** | (optional) | Receiver's public key or acceptance predicate digest. |
| **R8** | (optional) | Metadata: timestamp, tracker ID, version number. |
| **R9** | (reserved) | Future use. |

**Context Extension Registers** (provided by off-chain code):
- **Context var #7**: Merkle proof for prior redemption lookup in R5 AVL tree (optional for first redemption).
- **Context var #8**: Merkle proof for debt lookup in tracker's committed AVL tree (required for all redemptions).

---

## Tokens

### Native Tokens (if any)

1. **State NFT (optional singleton)**: If implemented, a unique token identifies the canonical reserve box across transactions.
   - Token ID: `stateNFT`
   - Ensures only one authoritative reserve exists.
   - Passed through outputs to maintain state machine continuity.

2. **Tracker Commitment Token** (optional): Tracker could issue a token alongside AVL tree commitments to prove timeliness or authority.

### No Authentication Tokens in Core Logic

- Signatures provide authentication (Sigma