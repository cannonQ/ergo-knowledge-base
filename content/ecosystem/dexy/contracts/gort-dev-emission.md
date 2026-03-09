---
title: kushti/dexy-stable — emission.es
description: "ErgoScript contract analysis: contracts/gort-dev/emission.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/gort-dev/emission.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: GORT Developer Emission

## Purpose

This contract manages the release of GORT tokens to developers (Gold cooperative) at a controlled rate of 1 ERG per block. It implements a state machine supporting two actions: **top-up** (replenishing the GORT reserve) and **withdrawal** (claiming accrued rewards up to the emission schedule).

## Inputs / Outputs

### Inputs
- **SELF** (current box): The singleton state box holding:
  - GORT token reserve (token #1)
  - State NFT for identification (token #0)
  - Last payout height (R4)
  - Authorization SigmaProp (R5)
  - ERG value backing the box

### Outputs
- **OUTPUTS(selfOutIndex)**: The successor state box, produced by the transaction at the index specified in context variable #0.
  - Must preserve the NFT and script
  - Must maintain or increase ERG backing
  - Must update GORT balance and/or payout height depending on action

## Key Logic

### Common Preservation Rules
All actions must satisfy:
1. **NFT Continuity**: State NFT (token #0) preserved in output
2. **Token ID Preservation**: GORT token ID (token #1) unchanged
3. **Script Immutability**: ErgoTree (minus header byte) identical in successor box
4. **Value Protection**: ERG backing maintained or increased

### Action 0: Top-Up
- **Condition**: Context variable #1 == 0
- **Requirements**:
  - GORT balance increases (`selfOut.tokens(1)._2 > SELF.tokens(1)._2`)
  - Last payout height (R4) unchanged
  - Authorization SigmaProp (R5) unchanged
- **Purpose**: Replenish the GORT reserve without triggering withdrawals
- **Signature**: Implicit (guarded by `sigmaProp`)

### Action 1: Withdrawal
- **Condition**: Context variable #1 == 1
- **Requirements**:
  - GORT balance decreases (`SELF.tokens(1)._2 > selfOut.tokens(1)._2`)
  - **Emission Rate Enforcement**: `SELF.tokens(1)._2 - selfOut.tokens(1)._2 <= newHeight - lastHeight`
    - Maximum 1 GORT released per block elapsed
  - Payout height advances: `newHeight > lastHeight`
  - Payout height does not exceed current blockchain height: `newHeight <= HEIGHT`
  - **Authorization Required**: Must produce valid Sigma protocol proof from the SigmaProp stored in R5
  - R5 may be updated (not validated in withdrawal, allowing auth rotation)

## Registers Used

| Register | Type | Purpose | Mutation |
|----------|------|---------|----------|
| **R4** | `Int` | Last payment/payout height (block number) | Updated on withdrawal to `newHeight` |
| **R5** | `SigmaProp` | Authorization proposition (Sigma protocol condition) | Preserved in top-up; may change in withdrawal |

## Tokens

| Index | Type | Purpose |
|-------|------|---------|
| **#0** | Native token (singleton) | **State NFT**: Identifies this singleton box; enforces exactly one active emission contract per deployment |
| **#1** | Native token (GORT) | **Emission token**: The reward token being distributed; balance tracked to enforce emission schedule |

Both tokens use the **Token ID rule**: token ID derives from the box ID that first issued the token, ensuring uniqueness.

## Integration Pattern

### Off-Chain Bot / Headless dApp
An off-chain agent (e.g., withdrawal bot) must:

1. **Monitor SELF box**: Track the current emission state box by State NFT
2. **Read R4**: Obtain `lastHeight` to calculate available rewards
3. **Construct Withdrawal Transaction**:
   - Spend SELF as input
   - Produce new state box (OUTPUTS at `selfOutIndex`) with:
     - Updated R4 = current `HEIGHT` (or intermediate height)
     - Updated GORT balance = `SELF.tokens(1)._2 - amountToWithdraw`
     - Preserved R5 (or updated if auth rotation needed)
   - Send withdrawn GORT to recipient address(es)
4. **Prove Authorization**: Include Sigma protocol proof satisfying R5 in the transaction (sign with private key matching R5)
5. **Set Context Variables**:
   - Context var #0 = output index of successor state box
   - Context var #1 = 1 (withdrawal action)
6. **Satisfy Minimum Transaction Fee**: Include ERG for network fee
7. **Respect Minimum Box Value**: Ensure successor box has ≥ 1 ERG (or network parameter minimum)

### On-Chain Validation
The contract validates:
- Emission rate (1 GORT per block max)
- State continuity (NFT, script, token IDs)
- Blockchain height consistency (no future claims)
- Authorization (R5 Sigma proof required)

## Related Contracts

Based on the project context (**kushti/dexy-stable**, GORT emission):

- **SigmaUSD / Dexy Reserve Contract**: Likely a parallel state machine managing stablecoin reserves; may interact with GORT for governance or fee mechanisms
- **GORT Governance / DAO Contract**: Probable consumer of emitted GORT tokens; may validate withdrawal recipients
- **Collateral / Oracle Contracts**: Dexy architecture typically relies on oracle-fed price feeds to stabilize assets; GORT emission may be tied to collateral ratio adjustments

The emission contract itself is a **singleton state machine** (eUTXO pattern) with no explicit composability visible in this code, but the context extension mechanism suggests coordination with off-chain bot logic typical of **multi-stage contracts** in Ergo dApps.

---

## Notes

- **Constant Segregation**: The contract hardcodes the emission rate (1 GORT/block) in logic; for parameterized rates, this would move to R6+.
- **Storage Rent Consideration**: Successor box must maintain `value >= SELF.value` to account for Ergo's storage rent (0.14 ER