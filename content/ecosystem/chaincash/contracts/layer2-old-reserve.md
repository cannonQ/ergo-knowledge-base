---
title: BetterMoneyLabs/chaincash — reserve.es
description: "ErgoScript contract analysis: contracts/layer2-old/reserve.es"
tags: [bettermoneylabs, chaincash, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
contract_file: contracts/layer2-old/reserve.es
project: bettermoneylabs-chaincash
---
# ErgoScript Contract Analysis: `reserve.es`

## Purpose

This is a **Layer 2 Reserve contract** that manages a gold-backed stablecoin reserve in the ChainCash protocol. It handles redemption of notes against physical gold (via oracle price feeds), top-ups to the reserve, and a multi-stage refund mechanism with a contestation period for dispute resolution.

## Inputs / Outputs

### Inputs
- **SELF (Box 0)**: The reserve contract box itself, containing:
  - Native token #0: Singleton/State NFT for identification
  - ERG value: The reserve balance
  - R4: Owner's public key (GroupElement)
  - R5: Refund initiation height (Int.MaxValue if inactive)

- **INPUTS(1+)** (context-dependent):
  - **Redemption path (action 0)**: Redemption contract box with AVL tree of historical state
  - **Refund paths (actions 2-4)**: No additional inputs required

- **CONTEXT.dataInputs(0)** (action 0 only): Gold price oracle box
  - Token: Oracle identity NFT
  - R4: Gold price in nanoErg per kg (normalized to per mg)

### Outputs
- **OUTPUTS(0)**: Updated reserve box (must preserve):
  - Same singleton token
  - Same propositionBytes (contract code)
  - Same R4 (owner key)
  - Modified R5 (only for refund actions)
  - Adjusted ERG value (top-up or redemption)

---

## Key Logic

### Action 0: Redeem Note
**Core Flow**: Verify dual cryptographic signatures (reserve and note holder), validate AVL tree proofs, fetch oracle price, calculate redemption amount with 2% fee, and validate ERG deduction.

1. **Redemption Leaf Verification** (Reserve's signature on redemption record):
   - Construct message: `treeHash || reserveId || noteValue || holderId`
   - Verify Fiat-Shamir Sigma protocol proof: `g^z == A * pk^e`
   - Validate reserve identified by token ID

2. **Holder Leaf Verification** (Note holder's signature on same record):
   - Same Sigma protocol check with holder's public key
   - Ensures both parties agree on the redemption terms

3. **AVL Tree Inclusion Proofs**:
   - Both redemption leaf and last processed leaf must exist in history tree
   - Prevents double-redemption by tracking processed positions (TODO: noted as incomplete)

4. **Oracle Validation**:
   - Data input must be the gold oracle (token ID: `2DfY1K4rW9zPVaQgaDp2KXgnErjxKPbbKF5mq1851MJE`)
   - Extract normalized price: `oracleRate = R4 / 1000000`

5. **Redemption Amount Calculation**:
   - `nanoergsToRedeem = tokenCount * oracleRate * 98 / 100`
   - Apply 2% fee (2% retained by reserve)
   - Validate: `SELF.value - OUTPUTS(0).value ≤ nanoergsToRedeem`

6. **Reserve Preservation**: Verify singleton token and R4 unchanged

---

### Action 1: Top Up
Increase reserve balance to back additional notes.

- Must add minimum **1 ERG** (`1000000000` nanoErg)
- Preserve singleton token and R4
- No signature required (anyone can top up)

---

### Action 2: Init Refund
Owner initiates a refund contestation period (dispute window).

- Set **R5 to current height** (within ±5 blocks)
- Requires **owner signature** (`proveDlog(ownerKey)`)
- Marks reserve as "refunding" to prevent other state changes

---

### Action 3: Cancel Refund
Owner cancels an active refund before completion.

- **Clear R5** (remove/undefine refund height)
- Requires **owner signature**
- Returns reserve to normal operation

---

### Action 4: Complete Refund
Owner finalizes refund after contestation period expires.

- **Refund period**: 7200 blocks (~10 days) from initiation
- Requires: `SELF.R5 + 7200 ≥ HEIGHT`
- Requires **owner signature**
- TODO: Currently incomplete—notes that ERGs must remain for signature verification

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `GroupElement` | Owner's public key; used in all refund actions and note redemptions |
| **R5** | `Int` | Refund initiation height; `Int.MaxValue` when inactive, set to current block height during refund init |
| **R6** | `Long` (redemption input) | Position of redemption leaf in AVL tree |
| **R5** (redemption input) | `Long` | Position of last processed leaf in AVL tree |

---

## Tokens

### Singleton Token (Native Token #0)
- **Purpose**: Identifies this specific reserve box (State NFT / singleton pattern)
- **Location**: `SELF.tokens(0)` and verified in `OUTPUTS(0).tokens`
- **Invariant**: Must be preserved unchanged across all state transitions

### Oracle Identity Token
- **Token ID**: `2DfY1K4rW9zPVaQgaDp2KXgnErjxKPbbKF5mq1851MJE`
- **Purpose**: Authenticates the gold price oracle data input
- **Requirement**: Must be present in `CONTEXT.dataInputs(0)` during redemptions

### Redemption Contract Token
- **Purpose**: Identifies the redemption history contract (TODO: currently hardcoded with placeholder `fromBase58("...")`)
- **Usage**: Validated against first input's token #0

---

## Integration Pattern

### Off-Chain Interaction (Headless dApp / Off-chain Bot)

#### Redemption Flow (Action 0)
1. **Construct Context Extension Variables** (`getVar` calls):
   - `Var(0)`: Action type = `0