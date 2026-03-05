---
title: LiliumErgo/scala-api — SingletonIssuer.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/SingletonIssuer.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/SingletonIssuer.es
project: liliumergo-scala-api
---
# SingletonIssuer.es – Contract Analysis

## Purpose

This contract acts as a **proxy/issuer contract** for creating singleton (one-of-a-kind) NFTs on Ergo. Although singleton tokens don't technically require an issuer contract, this contract enforces that all singleton issuance transactions flow through a single, operator-controlled gateway, ensuring atomic, coordinated state transitions and preventing race conditions in a multi-client environment.

## Inputs / Outputs

| Component | Details |
|-----------|---------|
| **Input** | A box locked by `SingletonIssuer.es` containing the source value (ergs) and initial state |
| | Context Extension Variable 0: serialized ErgoTree bytes of the downstream Singleton Issuance Contract |
| **Output 0** | Must be locked by the Singleton Issuance Contract (bytes match context extension) |
| | Contains the newly issued NFT token (1 or 2 units depending on `_usePool` flag) |
| | Must carry forward SELF value minus `_minerFee` |

## Key Logic

The contract validates three critical conditions before allowing the transaction:

1. **NFT Creation Rule (`nftBox`)**  
   - If `_usePool == true`: Output 0 must contain exactly **2 units** of a token with ID equal to `SELF.id`  
   - If `_usePool == false`: Output 0 must contain exactly **1 unit** of a token with ID equal to `SELF.id`  
   - This ensures the singleton (or dual-token pool state) is properly minted from the current box

2. **Contract Migration (`properOutput`)**  
   - Output 0's locking script (ErgoTree) must exactly match the `singletonIssuanceContractBytes` provided in context extension variable 0  
   - Prevents the NFT from being redirected to an unauthorized contract

3. **Value Conservation (`properValueTransfer`)**  
   - Output 0 value must equal `SELF.value - _minerFee`  
   - Ensures the miner fee is deducted and no additional ergs are siphoned away

**Final Guard:** Both conditions AND the operator's signature (`_txOperatorPK`) must be satisfied via conjunction (`&&`).

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| R4–R9 | Not explicitly used | Available for downstream Singleton Issuance Contract to store state (e.g., pool parameters, accounting data) |

The contract does not read/write registers itself; it focuses on guarding the box transition at the UTXO level.

## Tokens

| Token | Purpose | Quantity |
|-------|---------|----------|
| **Singleton Token (ID = `SELF.id`)** | Identifies the NFT being issued | 1 or 2 units (depending on `_usePool`) |
| **Operator Private Key (`_txOperatorPK`)** | Sigma protocol signature authorizing the issuance | Required in all valid transactions |

The **Token ID rule** ensures that when this box is spent, a new token with ID = `SELF.id` is created (Ergo's mechanism for native token issuance). The contract enforces that exactly the right quantity reaches the proper downstream contract.

## Integration Pattern

**Off-chain (Client/Bot) Responsibilities:**

1. **Construct the Transaction:**
   - Identify the current `SingletonIssuer` box (UTXO) on-chain
   - Prepare Output 0 locked by the Singleton Issuance Contract
   - Calculate required value: `singletonIssuerBoxValue - minerFee`
   - Set Output 0 tokens to `(SELF.id, 1)` or `(SELF.id, 2)` based on pool mode

2. **Provide Context Extension:**
   - Variable 0: Serialize the ErgoTree bytes of the next Singleton Issuance Contract and inject into transaction context

3. **Sign the Transaction:**
   - Use the operator's private key (corresponding to `_txOperatorPK`) to produce a Sigma protocol signature
   - Broadcast the signed transaction

4. **Verify On-Chain:**
   - Ergo nodes validate that all three conditions (`nftBox`, `properOutput`, `properValueTransfer`) pass
   - Verify the operator signature satisfies the Sigma proposition
   - Upon validation, the singleton NFT is atomically created and locked in the downstream contract

**Key Invariant:** Only one transaction per singleton issuance can succeed from this box, because once spent, `SELF.id` is consumed and cannot be reused.

## Related Contracts

- **Singleton Issuance Contract** (downstream, referenced by `singletonIssuanceContractBytes`)  
  The actual contract that receives the newly minted singleton NFT. This `SingletonIssuer` serves as a transactional gate to it, likely enforcing state machine transitions (e.g., state changes in an AMM, lending protocol, or governance structure).

- Possibly a **Pool Contract** (if `_usePool == true`)  
  The two-token issuance suggests this may integrate with a liquidity pool or multi-asset singleton system where both an NFT and a companion token are created.

---

## Summary Table

| Aspect | Value |
|--------|-------|
| **Contract Type** | Issuer / Proxy / Gate Contract |
| **State Machine Role** | Initialization / Gating Layer |
| **Token Mechanism** | Native Token Issuance (Ergo native feature) |
| **Signature Scheme** | Sigma protocol (operator-only) |
| **Min Box Value** | SELF.value - `_minerFee` |
| **Reentrancy Risk** | ✓ Mitigated (box consumed on spend) |
| **Auditability** | High (deterministic token creation, frozen downstream contract) |