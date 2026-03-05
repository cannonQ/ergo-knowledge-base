---
title: LiliumErgo/scala-api — SingletonIssuance.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/SingletonIssuance.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/SingletonIssuance.es
project: liliumergo-scala-api
---
# SingletonIssuance.es Contract Analysis

## Purpose

This contract acts as a **proxy intermediary** for minting and transferring a Singleton State NFT to a newly created state box. Since the state box requires the singleton token ID as a compile-time constant, the singleton cannot be directly minted into it; instead, this contract holds the token temporarily and validates its transfer in the same transaction, ensuring atomic state box initialization with proper singleton binding.

---

## Inputs / Outputs

### Inputs
- **SELF (this box):**
  - Contains exactly 1 Singleton NFT token (`_singletonToken` with amount = 1 or 2)
  - Locked by the `SingletonIssuance` ErgoScript contract
  - Consumed in the transaction that creates the state box

### Outputs
- **OUTPUT(0) — State Box:**
  - Must be locked by the same `SingletonIssuance` contract bytes (via context extension variable 0)
  - Must receive the Singleton NFT token (1 unit)
  
- **OUTPUT(1) — Pool/Sale LP Box (conditional, if `_usePool = true`):**
  - Must be locked by the `SaleLPContract` (retrieved from context extension variable 1)
  - Must contain exactly `_totalFees` ergs
  - Must receive the Singleton NFT token (1 unit)
  - **Note:** This appears to handle a fee-pooling or liquidity pool initialization scenario

---

## Key Logic

The contract enforces two primary invariants via AND composition:

1. **ProperOutput Check:**
   - `OUTPUT(0).propositionBytes == singletonIssuanceContractBytes`
   - Ensures the first output is locked by the same contract (maintaining state box structure)

2. **ProperTokenTransfer Check (branching on `_usePool` flag):**

   **If `_usePool = true` (pool-based initialization):**
   - `OUTPUT(0).tokens(0) == (_singletonToken, 1L)` — State box receives singleton
   - `OUTPUT(1).propositionBytes == saleLPContractBytes` — Second output locked by pool contract
   - `OUTPUT(1).value == _totalFees` — Pool box holds accumulated fees
   - `OUTPUT(1).tokens(0) == (_singletonToken, 1L)` — Pool box also receives singleton
   - `SELF.tokens(0)._1 == _singletonToken` — Input carries the correct singleton token ID

   **If `_usePool = false` (direct state box transfer):**
   - `OUTPUT(0).tokens(0) == (_singletonToken, 1L)` — State box receives singleton
   - `SELF.tokens(0)._1 == _singletonToken` — Input carries the correct singleton token ID

3. **Authorization:**
   - Transaction must be signed by `_txOperatorPK` (off-chain operator)
   - Uses AND (`&&`) to require both contract logic AND operator signature (Sigma protocol composition)

---

## Registers Used

**None explicitly read from input/output boxes** (R4–R9 not accessed).

- **Context Extension Variables (getVar calls):**
  - **Index 0:** `singletonIssuanceContractBytes` — Serialized ErgoScript bytes of this contract, used for OUTPUT(0) validation
  - **Index 1 (conditional):** `saleLPContractBytes` — Serialized ErgoScript bytes of the pool contract, used when `_usePool = true`

---

## Tokens

### Native Token Used

| Token | Amount | Purpose | Role |
|-------|--------|---------|------|
| **Singleton NFT** (ID = `_singletonToken`) | 1 unit | **State machine identifier** | Uniquely identifies the protocol state box; enforces singleton constraint (only one valid state at a time). Acts as both NFT authentication and Unique Identity Marker |

**Token Quantity Quirk:**  
The input may carry 1 or 2 units (`(SingletonTokenId, 1 | 2)`) according to comments, though the output validation enforces exactly `1L` unit transfer. This suggests a minting or burn scenario where excess units are handled elsewhere.

---

## Integration Pattern

### Off-Chain Bot / dApp Responsibilities

1. **Contract Constant Segregation:**
   - Precompute `singletonIssuanceContractBytes` (ErgoTree serialization) for the `SingletonIssuance` contract
   - Precompute `saleLPContractBytes` (if applicable)
   - Resolve `_singletonToken` token ID (likely from a previous minting transaction)

2. **Transaction Construction:**
   ```
   Transaction {
     inputs: [ SingletonIssuance box with 1 singleton NFT ]
     outputs: [
       0: State Box {
         propositionBytes: singletonIssuanceContractBytes
         tokens: [ (_singletonToken, 1L), ... ]
       }
       1: (if _usePool) Sale LP Box {
         value: _totalFees
         propositionBytes: saleLPContractBytes
         tokens: [ (_singletonToken, 1L), ... ]
       }
     ]
     contextExtension: {
       0: singletonIssuanceContractBytes,
       1: saleLPContractBytes (if needed)
     }
   }
   ```

3. **Signing:**
   - Obtain signature from `_txOperatorPK` (off-chain signer, likely a headless dApp or multisig authority)

4. **Verification:**
   - Ensure no other singleton tokens are minted in parallel (external constraint via Token ID rule)
   - Confirm the state box ErgoTree is deterministically derived before transaction submission

---

## Related Contracts

Based on context and structure:

1. **SaleLPContract** (referenced by `saleLPContractBytes`)
   - Likely a liquidity pool or fee collection contract
   - Receives Singleton NFT and accumulated fees when `_usePool = true`
   - Part of a multi-stage contract composition for protocol initialization

2. **State Box Contract** (referenced by `singletonIssuanceContractBytes`)
   - The main protocol state machine contract that this proxy feeds
   - Locked by the same ErgoScript;