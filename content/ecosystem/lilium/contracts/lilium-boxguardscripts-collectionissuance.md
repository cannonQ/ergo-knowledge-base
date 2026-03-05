---
title: LiliumErgo/scala-api — CollectionIssuance.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/CollectionIssuance.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/CollectionIssuance.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: Collection Issuance

## Purpose

This contract acts as a **temporary proxy box** that holds newly minted Collection tokens before they are transferred to a newly created State box. It ensures that Collection tokens (which serve as authentication for the state machine) are issued and routed correctly, since the State box requires the Collection Token ID as a compile-time constant that cannot be known until after token minting.

## Inputs / Outputs

**Inputs:**
- **SELF**: The Collection Issuance box, containing:
  - Native tokens: `(CollectionTokenID, CollectionSize)` – the newly minted collection tokens

**Data Inputs:**
- **CollectionIssuerBox** (via Context Extension): A box containing metadata in register R9 that specifies the expected collection size

**Outputs:**
- **OUTPUTS(0)**: The newly created State box, which must:
  - Have its `propositionBytes` equal to `StateBoxContractBytes` (the State contract's ErgoTree)
  - Receive the Collection tokens: `(CollectionTokenID, CollectionSize)`

## Key Logic

The contract validates two critical conditions:

1. **Correct State Box Creation** (`properOutput`):
   - The first output must be guarded by the State box contract (verified by comparing propositionBytes)
   - This ensures the State box is instantiated with the correct contract logic

2. **Token Transfer Validation** (`properTokenTransfer`):
   - The Collection token in SELF (from CollectionIssuerBox) must match the token being sent to OUTPUTS(0)
   - The token quantity in the output must equal the value stored in `CollectionIssuerBox.R9[Long]`
   - This ensures no token loss or substitution occurs during the transfer

Both conditions must be true **AND** the transaction must be signed by `_txOperatorPK` (the operator's Sigma proposition).

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R9** (CollectionIssuerBox) | `Long` | Stores the expected Collection token quantity | Read via `CollectionIssuerBox.R9[Long].get` |

The SELF box uses only standard token fields; no additional registers are required for this contract.

## Tokens

- **Collection Token**: 
  - **Type**: Native token (issued in the same transaction via the Ergo emission mechanism)
  - **Purpose**: Serves as a **Singleton / State NFT** equivalent for authenticating the State box; required as a compile-time constant in the State contract
  - **Quantity**: Must match the value in `CollectionIssuerBox.R9[Long]`
  - **Rule**: Only one Collection token ID is minted per collection issuance (enforces uniqueness across the state machine)

## Integration Pattern

**Off-chain bot / Headless dApp responsibility:**

1. **Construct the transaction**:
   - Call Ergo's token issuance endpoint to mint Collection tokens with a specified quantity
   - Include this CollectionIssuance box as an input
   - Create the State box as the first output with:
     - `propositionBytes` = compiled bytes of the State contract (StateBoxContractBytes)
     - Tokens = `(newly_minted_collection_token_id, quantity)`
   - Include CollectionIssuerBox as a data input (read-only reference)

2. **Provide Context Extension variables**:
   - **Variable 0** (`StateBoxContractBytes`): The ErgoTree bytes of the State contract
   - **Variable 1** (`CollectionIssuerBox`): The box containing the collection metadata

3. **Sign the transaction**:
   - Off-chain code must obtain a signature from `_txOperatorPK` (the contract operator's private key)
   - Include this signature to satisfy the final `sigmaProp(...) && _txOperatorPK` condition

4. **Verify invariants**:
   - Ensure the minted token ID matches the one expected by the State contract's constant
   - Confirm the quantity equals R9 before submission

## Related Contracts

- **State Box Contract** (`StateBoxContractBytes`):
  - The destination contract that guards the primary state box
  - Requires the Collection Token ID as a **compile-time constant**
  - This Collection Issuance contract exists specifically to bootstrap the State box with its required token before the State contract's constant is fixed

**Composition Pattern**: This is a **Multi-stage contract** where:
1. CollectionIssuance (Stage 1: bootstrap/proxy) → 
2. State Box (Stage 2: primary state machine)

This pattern is necessary because ErgoScript constants are immutable and must be known at compile-time, but token IDs are only generated at runtime.

---

## Notes

- **Storage rent**: Both SELF and the new State box are subject to Ergo's storage rent mechanism (~0.14 ERG per year per 4KB); the transaction must include sufficient ERG value
- **Minimum box value**: OUTPUTS(0) must hold ≥ 1,000,000 nanoERG (0.01 ERG) as per Ergo protocol rules
- **Atomicity**: The entire transaction is atomic; either both the token transfer and State box creation succeed, or the entire transaction fails—no partial execution