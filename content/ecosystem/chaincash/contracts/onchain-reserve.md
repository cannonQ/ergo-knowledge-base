---
title: BetterMoneyLabs/chaincash — reserve.es
description: "ErgoScript contract analysis: contracts/onchain/reserve.es"
tags: [bettermoneylabs, chaincash, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
contract_file: contracts/onchain/reserve.es
project: bettermoneylabs-chaincash
---
# ErgoScript Contract Analysis: Reserve (chaincash)

## Purpose

This contract manages a reserve of ERG that backs issued note tokens in a gold-backed stablecoin system (chaincash). It handles three core operations: redeeming notes for ERG at oracle-determined prices, topping up the reserve with additional ERG, and minting new note tokens. The contract enforces that all redemptions are backed by sufficient ERG reserves and validates cryptographic proofs of issued notes.

---

## Inputs / Outputs

### Inputs
- **SELF (Input #0)**: The reserve box itself
  - Token #0: Singleton NFT identifying this specific reserve
  - Value: ERG backing all issued notes
  - R4: Owner's `GroupElement` (public key)
  - R5: AVL tree of all issued note tokens (TODO: preservation not yet implemented)

- **Action-specific inputs**:
  - **Action 0 (Redeem)**: 
    - Input #index: Note box being redeemed (or receipt for re-redemption)
      - Token #0: Note NFT with quantity in mg of gold
      - R4: AVL tree with signed mint proofs
    - Data input #0: Oracle box providing gold price in nanoErg/kg
    - Input #2 (conditional): Buyback contract box (if ERG is redeemed)

### Outputs
- **Output #index**: Reserve box itself (state preservation)
- **Action-specific outputs**:
  - **Action 0 (Redeem)**:
    - Output #1: Receipt box (proof of redemption)
    - Output #2: Buyback contract box (receives 0.2% of redeemed value)
  - **Action 1 (Top-up)**: Only the reserve box is updated
  - **Action 2 (Mint)**: Only the reserve box is updated

---

## Key Logic

### Universal Validations (All Actions)
```
- Reserve box must be preserved with identical:
  * propositionBytes (contract code)
  * tokens (singleton NFT)
  * R4 (owner key)
```

### Action 0: Note Redemption
1. **Oracle Verification**: Data input must be the authorized gold price oracle (hardcoded NFT ID from mainnet: `3c45f29a5165b030fdb5eaf5d81f8108f9d8f507b31487dd51f4ae08fe07cf4a`)
2. **Redemption Fee Calculation**:
   - Max redeemable = note_value_mg × oracle_rate_nanoErg/mg × 0.98 (2% fee)
   - Actual redeemed = SELF.value - output_value
   - Must satisfy: `redeemed ≤ maxToRedeem`
3. **Buyback Contribution**: 0.2% of redeemed ERG routed to buyback contract (supports oracle network)
4. **Cryptographic Proof Validation**:
   - Note holder provides Schnorr signature proof via AVL tree lookup
   - Position and max value extracted from context variables
   - Fiat-Shamir challenge: `e = blake2b256(a || position || maxValueBytes || noteTokenId || ownerKey)`
   - Signature validity: `g^z = a × ownerKey^e` (discrete log proof)
5. **Receipt Formation**: Output receipt must contain:
   - Same note token
   - Original AVL tree history
   - Position reference
   - Height validation (≤20 blocks old)
   - Owner key reference
6. **Mode-Specific Logic**:
   - If `receiptMode = true`: Re-redemption against existing receipt; position must be < receipt's max position
   - If `receiptMode = false`: First-time note redemption

### Action 1: Top-up
- Reserve must receive ≥ 1 ERG minimum (threshold: 1,000,000,000 nanoErg)
- TODO: AVL tree preservation not yet enforced

### Action 2: Mint Note
- Reserve box state must be preserved
- Note creation logic handled off-chain or in companion contract
- TODO: AVL tree preservation not yet enforced

---

## Registers Used

| Register | Type | Purpose | Mutable |
|----------|------|---------|---------|
| **R4** | `GroupElement` | Reserve owner's public key; used in Schnorr signature verification for note redemptions | No (preserved) |
| **R5** | `AvlTree` | AVL tree storing all issued note tokens with their mint proofs; maps `position || reserveId` → `a_point || z_bigint` | TODO: Should be preserved but not enforced |
| **R6** | `Int` (receipt only) | Block height for receipt validity window | N/A |
| **R7** | `GroupElement` (receipt only) | Owner key reference in receipt | N/A |

### Context Variables (via Context Extension)
| Variable | Index | Type | Purpose |
|----------|-------|------|---------|
| **action** | 0 | `Byte` | Action selector (0=redeem, 1=topup, 2=mint); derived as `v / 10` |
| **index** | 0 | `Byte` | Output index for reserve box; derived as `v % 10` |
| **proof** | 1 | `Coll[Byte]` | AVL tree proof for Schnorr signature verification |
| **maxValueBytes** | 2 | `Coll[Byte]` | Maximum redeemable value (long encoded); protects against replay attacks |
| **position** | 3 | `Long` | Position in AVL tree for note lookup |
| **receiptMode** | 4 | `Boolean` | If true, redeeming against receipt; if false, redeeming note directly |
| **receiptOutIndex** | 5 | `Int` | Output index of receipt (if redeemed == 0) |

---

## Tokens

### Singleton NFTs
- **Reserve NFT (Token #0 of SELF)**: Identifies this specific reserve instance
  - Used to ensure state machine continuity
  - Hardcoded check: `selfOut.tokens == SELF.tokens`

- **Note NF