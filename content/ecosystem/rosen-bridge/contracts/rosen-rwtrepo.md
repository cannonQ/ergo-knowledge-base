---
title: rosen-bridge/contract — RwtRepo.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/RwtRepo.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/RwtRepo.es
project: rosen-bridge-contract
---
# RwtRepo.es Contract Analysis

## Purpose

This contract manages a **Watcher Repository (Repo)** that orchestrates the lifecycle of watcher permits in the Rosen Bridge. It facilitates watcher registration (initial permit issuance), permit extension (restaking), and permit revocation while maintaining invariants over collateral, RWT tokens, and watcher identity state.

## Inputs / Outputs

### Inputs
- **SELF (Primary Input)**: The RwtRepo box, holding:
  - The Repo State NFT (token 0)
  - X-RWT token pool (token 1)
  - RSN token pool (token 2)
  - X-AWC NFT pool (token 3, used as collateral tracker)
  - R4: Chain ID (Coll[Byte])
  - R5: Total active watchers (Long)

- **INPUTS(1)** (conditional): Watcher Collateral box (during permit extension/revocation)
- **INPUTS(2)** (conditional): Watcher Permit box (during permit revocation/return)
- **Data Input(0)** (conditional): RepoConfig box (during initial permit issuance only)

### Outputs
- **OUTPUTS(0)**: Replicated RwtRepo box (state continuation)
- **OUTPUTS(1)** (conditional): Updated Collateral box or User change output
- **OUTPUTS(2)** (conditional): New Watcher Permit box (during issuance/extension)
- **OUTPUTS(3)** (conditional): Watcher ID (WID) box with identity token (during initial permit)

---

## Key Logic

### Transaction Classification & Validation

The contract follows a **state machine** pattern with three core paths:

#### **Path 1: Repo Update Transaction**
```
Condition: OUTPUTS(0).tokens(0) == REPO_CONFIG_NFT
Action: Accept unconditionally (sigmaProp(true))
Purpose: Allow administrative updates via config box replacement
```

#### **Path 2: Initial Permit Issuance** (Watcher Registration)
```
Condition: 
  - repo.tokens(3)._2 == repoOut.tokens(3)._2 - 1  (one AWC NFT consumed)
  - RWT outflow detected: repo.tokens(1)._2 > repoOut.tokens(1)._2

Validations:
  1. RepoReplication invariant holds (see below)
  2. RWT decrease equals RSN increase: RWTOut == repoOut.tokens(2)._2 - repo.tokens(2)._2
  3. Permit token count matches RWT bonded: permit.tokens(0)._2 == RWTOut
  4. Permit script matches expected hash
  5. RepoConfig (data input) is present and holds configuration array
  6. Collateral box created with:
     - Script hash matching watcherCollateralScriptHash
     - R4 = repo.id (Watcher ID reference)
     - Value >= repoConfig.get(4) (minimum collateral ERG)
     - R5[Long] = RWTOut (bonded amount)
     - Token(0) = one X-AWC NFT from repo
     - Token(1) (optional) = RSN, amount >= repoConfig.get(5) if required
  7. WID box created with identity token (from repo.id) quantity >= 3
  8. Watcher count incremented: repoOut.R5[Long] == repo.R5[Long] + 1
```

#### **Path 3: Permit Extension** (Restaking)
```
Condition:
  - RWT outflow detected
  - repo.tokens(3)._2 == repoOut.tokens(3)._2  (no AWC NFT consumed, watcher already exists)

Validations:
  1. RepoReplication invariant holds
  2. Collateral box exists at INPUTS(1)
  3. New permit created with same validation as Path 2
  4. Collateral R5 accumulates: collateral.R5[Long] + RWTOut == outCollateral.R5[Long]
  5. Watcher count unchanged: repoOut.R5[Long] == repo.R5[Long]
  6. AWC NFT count unchanged
```

#### **Path 4: Permit Revocation / Return** (Watcher Exit)
```
Condition:
  - RWT inflow detected: repo.tokens(1)._2 < repoOut.tokens(1)._2

Sub-Path 4a: Partial Permit Return / Slash
  Condition: collateral.R5[Long] > RWTIn
  Validations:
    - Collateral reduced: collateral.R5[Long] - RWTIn == outCollateral.R5[Long]
    - AWC NFT count, watcher count unchanged
    - RSN returned to repo: RWTIn == repo.tokens(2)._2 - repoOut.tokens(2)._2

Sub-Path 4b: Full Permit Return (Watcher Exit)
  Condition: collateral.R5[Long] == RWTIn
  Validations:
    - One AWC NFT released: repoOut.tokens(3)._2 == repo.tokens(3)._2 + 1
    - Watcher count decremented: repoOut.R5[Long] == repo.R5[Long] - 1
    - Collateral box returned to user
```

### RepoReplication Invariant
Applied to **all non-update paths**:
```
✓ Output propositionBytes == Input propositionBytes (script locked)
✓ Output value >= Input value (minimum box value maintained)
✓ Token(0) (Repo NFT) ID and quantity preserved
✓ Token(1) (X-RWT) ID preserved
✓ Token(2) (RSN) ID preserved
✓ Token(3) (X-AWC NFT) ID preserved
✓ R4 (Chain ID) unchanged
```

This ensures the repo cannot be "destroyed" or mutated into an unrecognized state.

---

## Registers Used

| Register | Type | Purpose