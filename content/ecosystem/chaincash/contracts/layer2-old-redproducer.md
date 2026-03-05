---
title: BetterMoneyLabs/chaincash — redproducer.es
description: "ErgoScript contract analysis: contracts/layer2-old/redproducer.es"
tags: [bettermoneylabs, chaincash, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/BetterMoneyLabs/chaincash"
contract_file: contracts/layer2-old/redproducer.es
project: bettermoneylabs-chaincash
---
# ErgoScript Contract Analysis: `redproducer.es`

## Purpose

This contract manages the issuance of redemption request boxes by releasing redemption request tokens one at a time. It acts as a factory or producer contract that validates the creation of properly-formed redemption request boxes, ensuring they meet collateral, deadline, and script requirements before releasing tokens into circulation.

## Inputs / Outputs

**Inputs:**
- **SELF (Input 0):** The producer contract box itself, holding:
  - Token #0: Contract NFT (identifies this producer)
  - Token #1: Redemption request tokens (supply being depleted)
  - ERG value (minimum box value)

**Outputs:**
- **Output 0 (SELF):** Updated producer box with:
  - Same contract NFT
  - One fewer redemption request token (supply decremented)
  - At least the same ERG value as input
- **Output 1:** New redemption request box with:
  - Exactly one redemption request token (released from producer)
  - Specific ERG collateral amount
  - Deadline, position, and state registers populated
  - Script matching the validated redemption contract hash

## Key Logic

The contract enforces a state machine transition where:

1. **Token Conservation:** The producer must output itself with all tokens intact except one redemption request token, which is transferred to a new redemption request box.

2. **Collateral Enforcement:** The redemption request box must hold exactly **2,000,000,000 nanoERG** (2 ERG), establishing minimum collateral requirements.

3. **Deadline Validation:** The redemption request box must set a deadline at least **720 blocks** (≈1 day) in the future, allowing a contestation period.

4. **Position Constraints:** The redemption position (R6) must not exceed the total amount (R5), enforcing `position ≤ amount`.

5. **Initial State:** Register R7 must be initialized as `(-1, false)`, establishing a clean initial state for the redemption lifecycle.

6. **Script Authenticity:** The redemption request box's ErgoTree must hash to a pre-configured value (`redeemScriptHash`), preventing token issuance to unauthorized scripts via constant segregation.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R5** | `Long` | Total redemption amount |
| **R6** | `(Long, Coll[Byte])` | Current redemption position and metadata (pair of position and byte data) |
| **R7** | `(Long, Boolean)` | State tuple; initialized to `(-1, false)` to mark unused/initial state |
| **R8** | `Int` | Deadline height for contestation window |

## Tokens

| Token Index | Type | Purpose |
|-------------|------|---------|
| **#0** | **NFT (Singleton)** | Contract identifier; proves this is the authorized producer |
| **#1** | **Redemption Request Tokens** | Semi-fungible tokens representing redemption requests; supply decreases by 1 per transaction |

## Integration Pattern

**Off-chain Bot / Headless dApp Responsibilities:**

1. **Box Selection:** Locate the producer box (identified by its contract NFT).
2. **Token Count:** Query current redemption request token supply in the producer.
3. **Transaction Construction:** Build a transaction that:
   - Consumes the producer box as input
   - Creates a new producer output with token supply decremented by 1
   - Creates a new redemption request box with:
     - Exactly 1 redemption request token
     - 2 ERG collateral
     - R5 = total amount to redeem
     - R6 = (current position, metadata bytes)
     - R7 = (-1, false)
     - R8 = current height + 720
     - Script bytes hashing to the validated redemption contract
4. **Verification:** Ensure blake2b256 of the redemption contract ErgoTree matches `redeemScriptHash`.
5. **Submission:** Sign with sufficient signatures to satisfy the producer's spending condition.

## Related Contracts

- **Redemption Contract** (referenced by `redeemScriptHash`): The downstream contract that receives the produced redemption request box; validates claims, contestation, and payout logic.
- **Implicit composability:** This producer is part of a multi-stage contract system where redemption requests flow through a state machine (initial → contested → resolved → redeemed).

---

### Key Observations

- **State NFT Pattern:** Token #0 acts as a Singleton / State NFT enforcing uniqueness.
- **Emission Control:** Token #1 supply is strictly controlled; one token released per valid transaction.
- **Constant Segregation:** The `redeemScriptHash` must be pre-computed off-chain and hardcoded, preventing dynamic script substitution attacks.
- **Invariant:** `redemptionRequestTokensInSelf - 1` ensures monotonic token depletion.
- **Time-Lock:** The 720-block deadline implements a soft contestation window, protecting against invalid redemptions.