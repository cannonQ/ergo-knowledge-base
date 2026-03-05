---
title: rosen-bridge/contract — Emission.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/Emission.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/Emission.es
project: rosen-bridge-contract
---
# ErgoScript Contract Analysis: Emission.es

## Purpose

This contract manages the emission of RSN tokens (the bridge's native token) in the Rosen Bridge protocol. It enforces two distinct transaction modes: (1) standard emission transactions that mint new RSN tokens while consuming an equivalent amount from a reserve, and (2) guarded update transactions that allow authorized signers to modify emission box parameters via a multi-signature scheme.

## Inputs / Outputs

### Inputs
- **SELF**: The Emission box itself, holding:
  - The EmissionNFT (Singleton / State NFT) to uniquely identify this box
  - RSN token reserve (token index 1)
  - Emitted RSN token counter (token index 2)
  - Minimum ERG value for storage rent

### Data Inputs (Guard Update Mode)
- **GuardBox** (CONTEXT.dataInputs(0)): A read-only data input box containing:
  - GuardNFT for verification
  - R4: Coll[Coll[Byte]] — serialized EC points (public keys)
  - R5: Coll[Int] — configuration array where index 1 is the required signature threshold

### Outputs

**Emission Mode:**
- **OUTPUTS(0)**: Updated Emission box with:
  - Same ErgoTree (propositionBytes) as SELF
  - ERG value ≥ SELF value (monotonic increase for storage rent)
  - All three tokens preserved (with EmittedRSN quantity increased)
  - New EmittedRSN amount equals the amount consumed from RSN reserve

**Guard Update Mode:**
- **OUTPUTS(0)**: Updated Emission box with:
  - Identical token IDs and quantities as SELF (state preserved)
  - Parameters in registers may be modified by off-chain code

## Key Logic

### Emission Transaction Path (No Data Inputs)
```
IF CONTEXT.dataInputs.size == 0 THEN validate:
  1. Output box must have identical ErgoTree (same contract address)
  2. Output ERG value must be ≥ input value (no ERG loss)
  3. Token array size must be exactly 3
  4. EmissionNFT (token 0) ID and quantity are immutable
  5. RSN reserve (token 1) ID is immutable
  6. EmittedRSN (token 2) ID is immutable
  7. EmittedRSN quantity strictly increases: output > input
  8. **Invariant**: RSN burned == EmittedRSN minted
     (SELF.RSN_qty - OUTPUT.RSN_qty == OUTPUT.EmittedRSN_qty - SELF.EmittedRSN_qty)
```

This implements a **State Machine** pattern where the Emission box maintains conservation of token supply: every RSN removed from the reserve must appear as newly minted EmittedRSN.

### Guard Update Transaction Path (Data Inputs Present)
```
IF CONTEXT.dataInputs.size > 0 THEN validate:
  1. First data input (GuardBox) contains GuardNFT
  2. Extract threshold: R5[Coll[Int]](1) — the required signature count
  3. Extract public keys: R4[Coll[Coll[Byte]]] — serialized EC points
  4. Decode all points and create proveDlog assertions for each
  5. Verify at least `threshold` signatures via atLeast(threshold, signedColl)
  6. Output token 0 (EmissionNFT) ID and quantity unchanged
  7. All validations combined with AND logic
```

This implements a **Multi-Signature** authorization pattern using Sigma protocols, where a m-of-n signature set (stored in GuardBox registers) can authorize modifications.

---

## Registers Used

| Register | Type | Mode | Purpose |
|----------|------|------|---------|
| **R4** | `Coll[Coll[Byte]]` | Guard Update | Array of serialized EC points (public keys for Sigma protocol verification) |
| **R5** | `Coll[Int]` | Guard Update | Configuration array; R5[1] = required signature threshold (m-of-n) |
| **R6–R9** | — | — | Unused in this contract |

---

## Tokens

### Token Positions in SELF.tokens Array
| Index | Token | Purpose | Rules |
|-------|-------|---------|-------|
| **0** | **EmissionNFT** | Singleton identifier for this state box | Quantity immutable; ID must not change across any transaction |
| **1** | **RSN** | Reserve of unminted tokens | ID immutable; quantity can only decrease (consumed on emission) |
| **2** | **EmittedRSN** | Cumulative emission counter | ID immutable; quantity strictly monotonic increasing; minted amount equals RSN burned |

### Token ID Rule
- All three token IDs must match between input (SELF) and output (OUTPUTS(0))
- EmissionNFT and RSN quantities are strictly immutable
- Only EmittedRSN quantity may change (and only upward)

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

#### Emission Transaction Construction
1. **Read** the Emission box from the blockchain
2. **Determine** how many RSN tokens to emit (application logic)
3. **Construct** OUTPUTS(0) such that:
   - Same ErgoTree (address) as SELF
   - ERG value covers transaction fee + storage rent (≥ SELF.value)
   - Token arrays:
     - `tokens(0)` = (EmissionNFT_id, SELF.tokens(0)._2) ✓ immutable
     - `tokens(1)` = (RSN_id, SELF.tokens(1)._2 - emitted_amount)
     - `tokens(2)` = (EmittedRSN_id, SELF.tokens(2)._2 + emitted_amount)
   - Verify invariant before signing
4. **Sign** the transaction with the appropriate key(s)
5. **Submit** to mempool

#### Guard Update Transaction Construction
1. **Read** the Emission box and Gu