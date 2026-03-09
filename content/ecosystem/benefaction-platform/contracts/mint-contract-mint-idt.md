---
title: StabilityNexus/BenefactionPlatform-Ergo — mint_idt.es
description: "ErgoScript contract analysis: contracts/mint_contract/mint_idt.es"
tags: [stabilitynexus, benefactionplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
contract_file: contracts/mint_contract/mint_idt.es
project: stabilitynexus-benefactionplatform-ergo
---
# ErgoScript Contract Analysis: `mint_idt.es`

## Purpose

This contract enforces that minted Identity Tokens (IDT) can only be spent by transferring them to a specific authorized contract identified by its Blake2b-256 hash. It acts as a gatekeeper for IDT distribution, ensuring all minted tokens flow exclusively to the designated contract without loss or diversion.

## Inputs / Outputs

| Aspect | Details |
|--------|---------|
| **Input Box (SELF)** | Contains the IDT native token with quantity to be spent. Must satisfy this contract's conditions to be consumed. |
| **Output Box (OUTPUTS(0))** | The first output box in the transaction, which must receive the IDT tokens. Must be locked by the authorized contract identified in `contract_bytes_hash`. |
| **Additional Outputs** | Not validated by this contract; secondary outputs are permitted but not constrained. |

## Key Logic

The contract enforces two mandatory conditions via `sigmaProp(allOf(...))`:

1. **`correctSpend`**: Validates token integrity and completeness
   - Checks that the token ID (first element of the token tuple) in the input box matches the token ID in the first output box
   - Verifies that the full token amount from the input is transferred to the output (no partial spends allowed)
   - Both conditions must be true to proceed

2. **`correctContract`**: Validates destination authorization
   - Computes the Blake2b-256 hash of the output box's `propositionBytes` (its ErgoTree bytecode)
   - Compares it against a hardcoded constant `contract_bytes_hash` (injected at compile time via string interpolation)
   - Only permits spending if the output box is guarded by the exact authorized contract

**Both conditions must hold for the transaction to be valid.**

## Registers Used

| Register | Type | Purpose | Usage |
|----------|------|---------|-------|
| None (R4–R9) | — | This contract does not read or write auxiliary registers. | State and metadata are embedded in the token ID and output contract identity only. |

## Tokens

| Token Type | Role | Details |
|------------|------|---------|
| **IDT (Native Token)** | State & Value | The minted Identity Token itself serves as both the unit of value and proof of issuance. Its token ID is validated to match between input and output. Quantity must be fully preserved. |
| **No Authentication Token** | — | This contract relies on cryptographic hash verification rather than a separate NFT for authorization. |

## Integration Pattern

**Off-chain Bot / Headless dApp Responsibility:**

1. **Token Preparation**: Obtain or mint the IDT token with the desired quantity.

2. **Contract Compilation**: Compile the target contract and compute its Blake2b-256 hash using Ergo's hashing functions.

3. **Template Substitution**: Inject the computed hash into the `contract_bytes_hash` constant during ErgoScript compilation (via string interpolation: `` `+contract_bytes_hash+` ``).

4. **Transaction Construction**:
   - Create an input box containing the IDT tokens, locked by this `mint_idt.es` contract.
   - Create output box at index 0 with the same IDT tokens and the destination contract's ErgoTree.
   - Ensure no token loss or partial transfers.

5. **Validation**: Before submission, verify off-chain that:
   - `blake2b256(targetContract.propositionBytes) == contractBytes Hash`
   - Token IDs match
   - Token quantities are preserved
   - Output box value meets minimum box value requirement

**Sigma Protocol**: The contract uses `sigmaProp()` to create a provable predicate; spending requires a valid Sigma proof that both conditions hold.

## Related Contracts

- **Benefaction Main Contract** (referenced as `contract_bytes_hash`): The authorized recipient contract that must receive all IDT tokens. Its identity is cryptographically bound via Blake2b-256 hashing.

- **Other Mint Contracts** (inferred): StabilityNexus/BenefactionPlatform likely includes multiple mint contracts for different token types (PFT, IDT, etc.). This contract specializes in IDT distribution control.

## Notable Limitations & Design Decisions

| Aspect | Detail |
|--------|--------|
| **No Emission Validation** | The contract does not verify that the IDT quantity matches the authorized issuance amount; off-chain logic must enforce emission schedules. |
| **No Metadata Verification** | Token name, description, and decimal places are not validated; trust is placed in the minting process. |
| **Atomic Single-Output Spend** | All tokens must exit in a single atomic spend to `OUTPUTS(0)`; no batch or multi-step distribution is supported by this contract. |
| **Hash Immutability** | The target contract hash is constant and cannot be updated without redeploying this contract; upgradeability requires a new contract version. |

---

**Ergo Pattern**: This is a **constraint contract** implementing **output-driven validation**, common in token distribution and multi-stage contracts on Ergo. It pairs naturally with a State machine where the receiving contract manages downstream logic (e.g., beneficiary distribution, governance, or fund management).