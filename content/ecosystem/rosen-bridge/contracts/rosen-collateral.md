---
title: rosen-bridge/contract — Collateral.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/Collateral.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/Collateral.es
project: rosen-bridge-contract
---
# Collateral Contract Analysis

## Purpose

This contract manages collateral lockup and redemption for the Rosen Bridge. It validates state transitions where collateral (RSN tokens) can be partially returned/extended, slashed (in fraud scenarios), or fully redeemed when the corresponding wrapped token (RWT) debt is repaid to the repository.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Repository box (holds RWT_REPO_NFT and tracks total RWT issued)
- **INPUTS(1)**: **SELF** — the Collateral box (state machine box)
- **INPUTS(2)** *(optional)*: Permit box (for extend/partial return scenarios)
- **INPUTS(3)** *(conditional)*: WID box (Wrapped token ID state box, required for complete return)
- **INPUTS(4)** *(optional)*: Fraud evidence or cleanup box (slash scenarios)

### Outputs
- **OUTPUTS(0)**: Updated Repository box
- **OUTPUTS(1)** *(partial/extend)*: Updated Collateral box (state carries forward)
- **OUTPUTS(3)** *(extend case)*: WID box (returned with permit tokens consumed)
- **OUTPUTS(1)** *(complete return)*: User change box (receives returned collateral + ERG)

## Key Logic

The contract enforces **three distinct transaction paths**, determined by `transferedRwt` (change in RWT token balance at the repository):

### Path 1: Partial Return or Extend (`transferedRwt < R5`)
- RWT repaid is **less than** locked collateral amount
- Validates:
  - Collateral box state carries forward (SELF.id in INPUTS(1))
  - Repository holds correct NFTs (RWT_REPO_NFT at token index 0; X-AWC NFT at index 3)
  - Output Collateral maintains ERG value and X-AWC NFT identity
  - If RSN collateral present (SELF.tokens.size > 1): must be preserved exactly
  - New locked amount: `outCollateral.R5 + transferedRwt == SELF.R5`
  - **If negative transfer** (extend): WID box at OUTPUTS(3) must hold ≥2 copies of owner WID token

### Path 2: Slash (Fraud)
- Implicit: transferedRwt is negative or scenario requires slashing
- Collateral state box must survive with updated R5 to reflect reduced lock
- Cleanup box validates fraud evidence (not detailed in this contract; external)

### Path 3: Complete Return (`transferedRwt >= R5`)
- RWT repaid **equals or exceeds** locked collateral
- Validates:
  - WID box (INPUTS(3)) holds ≥2 copies of owner WID token
  - Repository R5 decremented by 1 (tracking one fewer active collateral)
  - Collateral is **consumed** (not in outputs); user receives return in subsequent output

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Owner Wrapped ID (WID) — identifies the bridge participant who locked this collateral |
| **R5** | `Long` | Locked RSN amount — principal collateral balance; decremented on partial return, cleared on full return |

## Tokens

| Index | Token | Purpose |
|-------|-------|---------|
| **0** | X-AWC NFT | Collateral box singleton identifier; must be preserved across state transitions to ensure continuity |
| **1** *(optional)* | RSN token | Collateral value; quantity stored but not explicitly validated in logic (implicitly tied to R5) |

**Repository tokens:**
- **Token 0**: RWT_REPO_NFT (repository singleton)
- **Token 3**: X-AWC NFT (cross-reference to collateral, enables validation of repo↔collateral binding)

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Monitor Repository**:
   - Track RWT issuance (token 1 quantity in repo box)
   - Identify collateral box by X-AWC NFT ID (from repo token 3)

2. **Construct Partial Return Transaction**:
   - Gather: [Updated Repo, Collateral (updated R5), Permit box, WID box (for extend)]
   - Calculate: `transferedRwt = repoOut.tokens(1)._2 - repo.tokens(1)._2`
   - Compute new `R5`: `R5_new = R5_old - transferedRwt`
   - Increment or preserve Repository R5 counter

3. **Construct Complete Return Transaction**:
   - Gather: [Updated Repo, Permit, WID box with ≥2 WID tokens]
   - Verify: `transferedRwt >= SELF.R5[Long]`
   - Decrement repository R5 counter by 1
   - Send ERG + returned RSN to user change box

4. **Construct Slash Transaction** *(optional)*:
   - Provide fraud evidence box (external contract)
   - Update Collateral R5 to reduced amount
   - Redirect collateral to protocol or slashing pool

### Verification Checkpoints
- Atomic swap invariant: Collateral state box ID must remain in INPUTS(1)
- State machine invariant: New R5 satisfies: `outCollateral.R5 + transferedRwt == SELF.R5`
- Token authentication: All NFT IDs match constants and cross-references
- Register continuity: Owner WID copied from R4 to output R4

## Related Contracts

- **Repository (RWT_REPO_NFT holder)**: Tracks total RWT debt; decrements counter on complete collateral return
- **Permit Contract** *(inferred)*: Authorizes extend/partial return operations; consumed from INPUTS(2)
- **WID Box Contract** *(inferred)*: State machine for wrapped token ID ownership; holds ≥2 copies of WID token for authorization
- **Fraud/Cleanup Contract** *(inferred)*: Validates slash scenarios; consumes fraud evidence and produces cleanup proof

---