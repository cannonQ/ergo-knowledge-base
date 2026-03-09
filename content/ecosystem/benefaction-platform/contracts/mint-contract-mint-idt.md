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

This contract enforces token spend restrictions by ensuring that minted tokens (IDTs—Identity/Issuance Designation Tokens) can only be transferred to a specific downstream contract identified by a Blake2b-256 hash digest. It acts as a gating mechanism in a multi-stage contract pipeline, preventing unauthorized token routing while delegating comprehensive token validation (amount, metadata) to the receiving contract.

## Inputs / Outputs

| Component | Details |
|-----------|---------|
| **Input Box (SELF)** | Contains the IDT token in its first position (`SELF.tokens(0)`). This box must satisfy the contract to be spent. |
| **Output Box (OUTPUTS(0))** | The destination box that must receive the IDT. Its `propositionBytes` (ErgoTree) must hash to the constant `contract_bytes_hash`. |
| **Token Movement** | The entire token amount (`SELF.tokens(0)._2`) must be transferred to `OUTPUTS(0)` in full; partial transfers are rejected. |

## Key Logic

The contract enforces two critical invariants via a conjunction (`allOf`) of conditions:

1. **Token Identity & Quantity Check (`correctSpend`)**
   - Verifies the token ID (first element of token tuple) in SELF matches the token ID in OUTPUTS(0)
   - Ensures the full token amount from SELF is spent into OUTPUTS(0) (no partial burns or diversions)
   - Rejects transactions that attempt to split, burn, or redirect the token

2. **Contract Destination Verification (`correctContract`)**
   - Computes the Blake2b-256 hash of the receiving box's `propositionBytes` (the ErgoTree bytecode)
   - Compares this hash against a hardcoded constant (`contract_bytes_hash`) embedded at contract deployment
   - Only allows the output box if it executes the exact contract specified; prevents redirect to unauthorized contracts

Both conditions must evaluate to `true`; failure of either blocks the transaction.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4–R9** | Not used | This contract uses only native box properties: `tokens` (state) and `propositionBytes` (code reference). No custom data registers are read or written. |

**Note:** The contract is stateless regarding user-defined registers; all state is implicit in token carriage.

## Tokens

| Aspect | Details |
|--------|---------|
| **IDT (Issuance Designation Token)** | A native Ergo token (NFT or fungible) used as the primary state object. Its Token ID must remain invariant across the transaction. |
| **Token Amount** | Must be fully preserved; the contract enforces the **Token ID rule**: the same token cannot be minted or burned mid-transfer, only moved. |
| **Use Case** | Acts as a credential or proof-of-authorization: possession of the IDT is necessary to execute spend logic; the token itself is the gating mechanism. |
| **Assumption** | The contract assumes the IDT was legitimately minted upstream (likely in a main contract). This contract does **not** validate issuance amounts, names, decimals, or metadata. |

## Integration Pattern

### Off-Chain Construction Requirements

1. **Identify the Downstream Contract**
   - Deploy or reference the target contract (e.g., the main benefaction contract).
   - Compute its ErgoTree bytecode hash using Blake2b-256.
   - Embed this hash in the constant `contract_bytes_hash` during compilation.

2. **Build the Transaction**
   - **Input:** Select a box holding the IDT (output from a prior mint/issuance transaction).
   - **Output:** Create OUTPUTS(0) with:
     - `propositionBytes` = the exact ErgoTree of the downstream contract
     - `tokens(0)` = the same IDT and full amount from the input
     - Other fields (value, registers, additional tokens) as required by downstream contract

3. **Verification (Off-Chain Bot / Wallet)**
   - Before signing, verify:
     - `blake2b256(OUTPUTS(0).propositionBytes) == fromBase16(contract_bytes_hash)`
     - `OUTPUTS(0).tokens(0) == SELF.tokens(0)` (same token ID and amount)
   - If both checks pass, the transaction will satisfy the contract guard.

### Headless dApp Integration

- **State Machine Role:** This contract is a **transit node** in a multi-stage state machine. The IDT is the singleton/state NFT that flows through successive contract stages.
- **Composability:** The contract does not itself issue or validate the IDT; it assumes a prior issuance contract (likely in the same project) created and initialized it.
- **Bot Responsibility:** An off-chain bot must watch for UTXOs locked under this contract, verify the downstream contract hash is correct, and construct forward transactions.

## Related Contracts

| Contract | Relationship |
|----------|--------------|
| **Main Issuance/Mint Contract** | Upstream: Issues the IDT. This contract enforces that the issued token flows only to designated downstream contract(s). |
| **Downstream Benefaction/Stability Contract** | Downstream: Receives the IDT and executes the core business logic (token distribution, stability guarantees, etc.). The hash `contract_bytes_hash` points to this contract's ErgoTree. |
| **Multi-Stage Pipeline** | This contract is one checkpoint in a larger chain; typical patterns include: `Issuance → Transit (this contract) → Distribution → Settlement`. |

---

## Contract Limitations & Disclaimers

⚠️ **Explicit Out-of-Scope:**
- Token amount must match PFT (Platform Facilitation Token) issuance in the main contract—**this contract does not verify it**.
- Token name, description, and decimals are **not validated**; metadata governance is delegated upstream.
- No rate-limiting, time-locks, or epoch-based controls.

⚠️ **Security Implications:**
- The contract hash is immutable post-deployment; if the downstream contract requires an upgrade, a new IDT and new transit contract are required.
- The contract does not prevent the downstream contract from mis-using the IDT; trust is placed entirely on the downstream contract's validation logic.

---

## Summary Table

| Aspect