---
title: rosen-bridge/contract — Fraud.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/Fraud.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/Fraud.es
project: rosen-bridge-contract
---
# Fraud Contract Analysis

## Purpose
This contract validates fraud slashing transactions in the Rosen Bridge, ensuring that RWT tokens are correctly transferred from a collateral pool to a fraud box when a malicious validator is detected. It acts as a **state machine guardian** that enforces the atomic swap of collateral during slash events.

## Inputs / Outputs

### Expected Inputs
| Index | Role | Key Requirement |
|-------|------|-----------------|
| 0 | RWT Repo Box | Must hold `RWTRepoNFT` singleton; contains source RWT tokens |
| 1 | (Implicit) | Collateral box (referenced contextually) |
| 2 | Self (Fraud Box) | Must match `SELF.id`; validates this contract's own constraints |
| 3 | Cleanup Box | Must hold `cleanupNFT` singleton |

### Expected Outputs
| Index | Role | Key Requirement |
|-------|------|-----------------|
| 0 | Updated RWT Repo | Receives reduced RWT token amount (post-slash) |
| 3+ | Slashed/Cleanup Outputs | Receives confiscated RWT via atomic composition |

## Key Logic

The contract enforces a **4-box atomic transaction pattern** via the following invariants:

1. **RWT Token Conservation**  
   ```
   SELF.tokens(0)._2 == (INPUTS(0).tokens(1)._2 - OUTPUTS(0).tokens(1)._2)
   ```
   The RWT tokens in the Fraud box (token index 0) **must equal** the RWT deficit between the Repo input and output. This ensures no RWT is created/destroyed—only transferred.

2. **Self-Reference Validation**  
   ```
   SELF.id == INPUTS(2).id
   ```
   This box must be the **third input** (`INPUTS(2)`), preventing replay or mismatched box references.

3. **Repo Authentication**  
   ```
   INPUTS(0).tokens(0)._1 == RWTRepoNFT
   ```
   The first input is verified to hold the **RWT Repository Singleton NFT**, ensuring only the official repo box can be drained.

4. **Cleanup Authority**  
   ```
   INPUTS(3).tokens(0)._1 == cleanupNFT
   ```
   The fourth input must hold the **Cleanup Singleton NFT**, granting cleanup-stage permissions and preventing unauthorized slash finalization.

**Satisfaction**: All four conditions must be true (logical AND via `allOf`).

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **WID** (likely Witness ID or Validator ID); identifies the fraudulent party being slashed |

No other registers (R5-R9) are referenced; this contract relies on **token-based state** rather than complex register logic.

## Tokens

| Index | Token | Purpose | Role |
|-------|-------|---------|------|
| **0** | X-RWT (Native Token) | **Fraud collateral payload** | Holds RWT tokens being slashed from the repo; amount must match the deficit in the repo output |
| **(Repo only)** | RWT (via `tokens(1)`) | **Primary repo reserve** | Tracked in `INPUTS(0).tokens(1)._2` vs. `OUTPUTS(0).tokens(1)._2` to calculate the slash amount |

**NFT Singletons** (for box identity):
- `RWTRepoNFT` → Authenticates the RWT Repository box
- `cleanupNFT` → Authenticates the Cleanup/Settlement stage box

## Integration Pattern

### Off-Chain Requirements (Bot/Headless dApp)

1. **Fraud Detection**  
   Off-chain oracle or validator monitor detects fraud and signals slash initiation.

2. **Transaction Construction**  
   The off-chain coordinator must assemble exactly **4 inputs** in order:
   - `INPUTS(0)`: Current RWT Repo box (holding `RWTRepoNFT`)
   - `INPUTS(1)`: Collateral box (context-dependent, not validated by this script)
   - `INPUTS(2)`: This Fraud box (with R4 = WID, `tokens(0)` = calculated RWT amount)
   - `INPUTS(3)`: Cleanup/Settlement box (holding `cleanupNFT`)

3. **Amount Calculation**  
   Calculate `transferedRwt = INPUTS(0).tokens(1)._2 - OUTPUTS(0).tokens(1)._2`  
   Assign this exact amount to `SELF.tokens(0)._2` in the Fraud box.

4. **Output Construction**  
   - `OUTPUTS(0)`: Updated Repo box with reduced RWT and preserved `RWTRepoNFT`
   - Downstream outputs handle slashed RWT distribution (Cleanup → Validator/DAO)

5. **Proof of Work**  
   Sign with the **owner of INPUTS(2)** (Fraud box); uses `sigmaProp(...)` for standard ECDSA validation.

### Verification Steps (on-chain)
- Token ID matching for NFT singletons
- Arithmetic proof of RWT conservation
- Box ordering constraints (SELF must be index 2)

## Related Contracts

This contract is part of a **multi-stage state machine** pipeline:

1. **RWT Repo Contract** (`INPUTS(0)`)  
   Manages the primary RWT reserve; must validate that its RWT decrease is authorized by a paired Fraud contract.

2. **Cleanup/Settlement Contract** (`INPUTS(3)`)  
   Likely responsible for distributing slashed RWT or marking the validator as punished; must validate Fraud box authorization.

3. **Collateral Contract** (`INPUTS(1)`)  
   Implicit; likely collects the forfeited stake or validates the slashed validator's identity.

4. **Bridge Validator/Guard Contracts** (upstream)  
   These likely generate fraud signals or create the Fraud box with properly initialized R4 (WID).

---

## Security Model

**Atomic Swap Pattern**: The contract ensures that