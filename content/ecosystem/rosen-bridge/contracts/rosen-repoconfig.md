---
title: rosen-bridge/contract — RepoConfig.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/RepoConfig.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/RepoConfig.es
project: rosen-bridge-contract
---
# ErgoScript Contract Analysis: RepoConfig

## Purpose

The **RepoConfig** contract is a configuration state machine that stores and manages bridge governance parameters (watcher quorum, approval thresholds, and collateral requirements) protected by a multi-signature guard mechanism. It acts as a singleton state box authenticated by a unique **Config NFT**, ensuring only authorized guardian signatures can modify critical bridge settings.

---

## Inputs / Outputs

### Inputs
- **SELF**: The current RepoConfig box (state box holding the Config NFT and governance parameters in R4)
- **Data Input (CONTEXT.dataInputs(0))**: A **Guard box** containing:
  - The Guard NFT (for authentication)
  - R4: Collection of guardian public keys (encoded as Points)
  - R5: Collection containing the required signature threshold at index [1]

### Outputs
- **OUTPUTS(0)**: The updated RepoConfig box, must:
  - Carry the same Config NFT (token ID and amount)
  - Preserve state continuity (same singleton)
  - Contain new R4 values (updated governance parameters)

---

## Key Logic

The contract enforces a **guarded state update** pattern:

1. **Guard Verification**: Confirms the data input holds the correct Guard NFT
   ```
   verifyGuard = GuardBox.tokens contains GuardNFT
   ```

2. **Multi-Signature Threshold**: Validates that at least `updateSignCount` signatures from the guardian public keys are present in the transaction context
   ```
   atLeast(updateSignCount, signedColl)
   ```
   - Reconstructs guardian public keys via `proveDlog(decodePoint(row))`
   - Relies on Sigma protocol signatures in the tx context

3. **Token Preservation**: Ensures the Config NFT (both ID and quantity) flows unchanged to the output
   ```
   OUTPUTS(0).tokens(0)._1 == SELF.tokens(0)._1  // ID match
   OUTPUTS(0).tokens(0)._2 == SELF.tokens(0)._2  // Amount match (1)
   ```
   - Guarantees singleton property: only one valid RepoConfig box can exist at a time

4. **All conditions must pass** (conjunction via `allOf`)

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** (Self) | `Coll[Long]` | Governance parameters: `[Commitment RWT count, Watcher quorum %, Approval offset, Max approval needed, Collateral Erg, Collateral RSN]` |
| **R4** (Guard box) | `Coll[Coll[Byte]]` | Guardian public keys (Schnorr points, encoded as byte arrays) |
| **R5** (Guard box) | `Coll[Int]` | Metadata; index [1] contains required signature threshold for config updates |

---

## Tokens

| Token | Quantity | Purpose |
|-------|----------|---------|
| **Config NFT** (SELF.tokens(0)) | 1 | State authentication & singleton enforcement. Uniquely identifies this RepoConfig box. Immutable across state transitions. |
| **Guard NFT** (GuardBox.tokens) | (implicit) | Authentication of the guardian set. Ensures only boxes carrying this NFT can authorize updates. |

---

## Integration Pattern

### Off-Chain Bot / Update Sequence

1. **Read State**:
   - Fetch the RepoConfig box (identified by Config NFT)
   - Fetch the Guard box (identified by Guard NFT)

2. **Construct Transaction**:
   - **Input**: Current RepoConfig box
   - **Data Input**: Current Guard box (read-only; not spent)
   - **Output**: New RepoConfig box with:
     - Updated R4 (new governance parameters)
     - Same Config NFT preserved
     - Maintained minimum box value & storage rent

3. **Sign & Submit**:
   - Off-chain code must gather ≥ `updateSignCount` signatures from guardians
   - Inject signatures into **Sigma protocol context** (via transaction proof/witness)
   - The contract verifies signatures via `proveDlog` checks in the context
   - Submit to mempool

### Validation Sequence
```
tx.inputs[0] = RepoConfig box (SELF)
tx.dataInputs[0] = Guard box (read-only reference)
tx.outputs[0] = New RepoConfig box
  → Contract checks:
    1. Guard NFT is in data input
    2. Collected signatures ≥ threshold
    3. Config NFT ID & qty preserved
  → If all pass: tx valid
```

---

## Related Contracts

Based on the code context and Rosen Bridge architecture:

- **Guard Contract** (`GuardBox`): Maintains the set of authorized guardians and signature thresholds. This RepoConfig treats it as a data input for authorization.
  
- **Commitment/Watcher Contracts**: The R4 parameters (watcher quorum %, approval offset) are consumed by commitment validation logic elsewhere in the bridge, likely in contracts that handle event proposals and multi-sig consensus.

- **Collateral Contracts**: The collateral amounts in R4 are referenced by contracts managing watcher stake/slashing (Collateral Erg and RSN amounts).

---

## Design Patterns & Remarks

| Pattern | Implementation |
|---------|-----------------|
| **Singleton State Machine** | Config NFT ensures only one valid RepoConfig exists |
| **Multi-Sig Guard** | Threshold signatures + guardian public keys via Sigma protocols |
| **Data Input Reference** | Guard box is read-only; state is not spent, only referenced |
| **Immutable Authentication** | Token ID check prevents swapping the NFT; preserves box identity |
| **Constant Segregation** | Guard NFT & signature logic hardcoded; R4 parameters are mutable governance data |