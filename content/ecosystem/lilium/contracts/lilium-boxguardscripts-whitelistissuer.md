---
title: LiliumErgo/scala-api — WhitelistIssuer.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/WhitelistIssuer.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/WhitelistIssuer.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: WhitelistIssuer

## Purpose

This contract guards the **issuer box** for minting whitelist tokens in the Lilium protocol. It validates that when whitelist tokens are created, they are issued in the correct quantity to the intended recipient, ensuring controlled and authorized whitelist token generation.

---

## Inputs / Outputs

| Aspect | Description |
|--------|-------------|
| **Input (SELF)** | The issuer box containing: whitelist amount in R4, recipient public key in R5, and the whitelist token ID (implicit in the transaction). |
| **Output (OUTPUTS(0))** | The newly minted whitelist box that must contain: the exact whitelist tokens minted (quantity from R4), and be locked to the public key specified in R5. |
| **Token Emission Rule** | The contract enforces the **Token ID rule**: the first token in OUTPUTS(0) must originate from SELF.id (this box) and match the specified amount exactly. |

---

## Key Logic

The contract validates a whitelist token minting transaction through **two nested conditions**:

1. **Valid Token Issuance:**
   - Extract the whitelist amount from `SELF.R4` (Long type)
   - Verify that `OUTPUTS(0)` receives exactly one token with:
     - **Token ID** = `SELF.id` (the current box's ID)
     - **Quantity** = the whitelist amount from R4
   - This ensures no duplicate/phantom tokens are created

2. **Valid Recipient:**
   - Extract the recipient's public key from `SELF.R5` (SigmaProp type)
   - Verify that `OUTPUTS(0)` is locked to this exact public key (via `propositionBytes` comparison)
   - This ensures tokens cannot be diverted to an unauthorized address

3. **Operator Authorization:**
   - The transaction must also be signed by `_txOperatorPK` (compile-time constant)
   - This adds a second layer of signing authority (multi-signature requirement)

**Logical structure:** `(validTokens AND validUser) AND operatorSignature`

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | Stores the **WhitelistAmount** — the quantity of whitelist tokens to mint in this transaction. |
| **R5** | `SigmaProp` | Stores the **recipient's public key** — the entity authorized to receive the newly minted whitelist tokens. |
| **R6-R9** | — | Not used in this contract. |

---

## Tokens

| Token | Role | Mechanism |
|-------|------|-----------|
| **Whitelist Token** | Primary minted asset | Created via the **Token ID rule**: derived from `SELF.id`. The contract ensures exactly `R4` tokens are issued per transaction. This token serves as a cryptographic proof of whitelist eligibility in the Lilium protocol. |
| **No auxiliary tokens** | — | This contract does not consume or validate multi-token workflows. |

---

## Integration Pattern

### Off-Chain Construction Requirements

The off-chain bot or dApp must:

1. **Read the issuer box state:**
   - Fetch the box containing this script (identified by its contract hash or singleton marker)
   - Extract `R4` (amount to mint) and `R5` (recipient public key)

2. **Construct the output box:**
   - Create `OUTPUTS(0)` with:
     - **Proposition:** the SigmaProp from R5 (recipient's public key)
     - **Tokens:** `[(SELF.id, R4_value)]` as the first token
     - **Value:** sufficient ERG to meet the **minimum box value** requirement (~0.1 ERG)

3. **Sign the transaction:**
   - Obtain **two signatures**:
     - One from the recipient (implicit via their public key in R5, if they authorize)
     - One from `_txOperatorPK` (the operator's private key)
   - Both signatures must be valid for the transaction to pass

4. **Submit transaction:**
   - The Ergo node validates that SELF (issuer box) → OUTPUTS(0) (recipient box) satisfies all conditions

---

## Related Contracts

| Contract | Relationship |
|----------|--------------|
| **Whitelist Guard** (inferred) | Likely validates spending of the whitelist tokens once issued by this contract. Guards boxes locked to whitelist holders. |
| **Lilium Protocol Contracts** | This is a component of a larger multi-stage contract system. Other boxes in the Lilium dApp likely consume or verify whitelist tokens as prerequisites for participation. |
| **Operator Authority Contract** (implicit) | The `_txOperatorPK` constant suggests a separate authority mechanism, possibly a singleton contract managing operator credentials. |

---

## Security Observations

✅ **Strengths:**
- **Dual authorization** (operator + recipient verification) prevents unauthorized minting
- **Exact token amount validation** prevents inflation/deflation
- **Recipient lock** prevents token theft via output redirection

⚠️ **Design Notes:**
- R5 is assumed to contain a valid `SigmaProp`; no type-safety fallback if R5 is missing (would throw exception)
- No state machine advancement; issuer box is not consumed/regenerated, allowing unlimited minting if operator key is compromised
- Consider adding a **nonce** or **state NFT** in future versions to prevent replay attacks across multiple minting cycles