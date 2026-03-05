---
title: LiliumErgo/scala-api — ProxyContract.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/ProxyContracts/ProxyContract.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/ProxyContracts/ProxyContract.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: NFT Buyer Proxy Contract

## Purpose

This contract acts as an intermediary holding funds and tokens for NFT purchases, enforcing atomic execution of either a successful NFT sale transaction or a complete refund to the buyer. It ensures that buyer funds cannot be misappropriated—they must either purchase an NFT through a valid State Box transaction or return fully to the buyer with correct miner fees.

## Inputs / Outputs

**Inputs:**
- **SELF (spending input):** The Proxy Contract box, holding buyer funds and any required payment/whitelist tokens
- **INPUTS(0):** Must be the State Box singleton (validated by checking for token ID match in R5), representing the active NFT sale state machine
- **Buyer signature:** Required for refund path validation

**Outputs:**

*Success Path (valid NFT sale):*
- **OUTPUTS(0):** The Issuer Box, receiving buyer funds and storing buyer's SigmaProp in R9 as proof of purchase

*Refund Path (invalid sale state):*
- **OUTPUTS(n):** Buyer's refund box, receiving all SELF value and tokens
- **OUTPUTS(m):** Miner fee box, receiving exactly `_minerFee` ergs

## Key Logic

The contract implements a **state-dependent branching mechanism**:

1. **Valid State Box Check:**  
   Verifies that INPUTS(0) holds the singleton token matching `stateBoxSingleton` (R5). This ensures the transaction references the authoritative NFT sale state machine.

2. **Success Path (if validStateBox):**  
   - Validates that OUTPUTS(0) (Issuer Box) stores the buyer's SigmaProp in R9
   - This confirms the buyer received the NFT and created proof of ownership
   - No additional signatures required beyond ErgoTree evaluation

3. **Refund Path (if !validStateBox):**  
   - **Value validation:** Sums all outputs matching `buyerPK` propositionBytes; total must be ≥ SELF.value (no value loss)
   - **Token validation:** If SELF contains tokens, they must be transferred atomically in a single output to the buyer
   - **Miner fee validation:** Exactly one output with blake2b256 hash matching the miner fee address must contain exactly `_minerFee` ergs
   - **Buyer signature:** Buyer must co-sign the transaction (`buyerPK` SigmaProp required)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Buyer's public key / Sigma protocol commitment; used to validate refund outputs and verify transaction signature |
| **R5** | `Coll[Byte]` | State Box Singleton token ID; identifies the authoritative NFT sale state machine box to enforce atomicity |
| **R9** (output) | `(SigmaProp, Long)` | Issuer Box only; stores buyer SigmaProp and secondary data (timestamp/price); serves as proof of purchase |

## Tokens

- **Optional Payment/Whitelist/PreMint Token in SELF:**  
  - **Payment Token:** Custom currency required by the NFT issuer for payment
  - **PreMint Token:** Grants early access rights to the buyer
  - **Whitelist Token:** Proves buyer eligibility for the sale
  - **Refund requirement:** If present, must be atomically transferred back to buyer in a single output during refund

- **State Box Singleton (R5):**  
  - Token ID used to identify and validate the state machine box (INPUTS(0))
  - Does not move with this transaction; serves as a reference/data input validation mechanism

## Integration Pattern

**Off-chain Bot / dApp Interaction:**

1. **Purchase Scenario:**
   - Bot constructs transaction spending Proxy Contract box
   - Bot ensures INPUTS(0) references valid State Box (singleton present)
   - Bot creates OUTPUTS(0) as Issuer Box with buyer SigmaProp in R9
   - Bot submits transaction; ErgoTree evaluation passes because `validStateBox == true`

2. **Refund Scenario:**
   - Bot detects failed sale or timeout condition
   - Bot constructs transaction spending Proxy Contract box without valid State Box
   - Bot creates output returning SELF.value + tokens to buyer
   - Bot creates separate miner fee output with exactly `_minerFee`
   - Bot requests buyer signature via wallet/signing service
   - Buyer signs; `buyerPK` SigmaProp requirement satisfied
   - All three validation conditions (`validValueTransfer`, `validTokenTransfer`, `validMinerFee`) must pass

3. **Constant Segregation:**
   - `_minerFee`: Compile-time constant, embedded in contract bytecode; allows gas cost flexibility without re-deployment

## Related Contracts

**State Machine Dependency:**
- **State Box (referenced in INPUTS(0)):** The singleton-authenticated NFT sale state machine; must hold the token ID specified in R5
  - Likely tracks sale status, issuer information, and NFT availability
  - Acts as the **gatekeeper** for the success path

**Issuer Box (OUTPUTS(0) in success case):**
- Produced by this contract; receives buyer funds and stores ownership proof
- Likely consumed by a subsequent issuer-controlled contract to deliver the NFT

**Implied Atomic Swap Pattern:**
- Part of a **multi-stage contract** pipeline: Buyer Proxy → State Box → Issuer Box → NFT Delivery Contract
- Uses **eUTXO model** and **Singleton NFTs** to enforce state machine transitions

---

**Security Model:** This contract relies on **Sigma protocol verification** (buyer signature requirement in refund path) and **deterministic ErgoTree evaluation** to prevent:
- Fund theft by unauthorized parties
- Partial refunds or token loss
- Incorrect miner fee routing
- Atomic swap failures in multi-contract workflows