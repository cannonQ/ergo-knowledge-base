---
title: rosen-bridge/contract — GuardSign.es
description: "ErgoScript contract analysis: src/main/scala/rosen/bridge/scripts/GuardSign.es"
tags: [rosen-bridge, contract, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/rosen-bridge/contract"
contract_file: src/main/scala/rosen/bridge/scripts/GuardSign.es
project: rosen-bridge-contract
---
# ErgoScript Contract Analysis: GuardSign

## Purpose

GuardSign is a **State Machine** contract that validates multi-signature authorization for guard pool state transitions. It ensures that at least a threshold number of authorized guard signatories cryptographically sign off on updates to the guard box before allowing state progression.

## Inputs / Outputs

### Inputs
- **SELF (GuardSign box):** Contains the Guard NFT (Singleton token) in token slot 0, guard public keys in R4, and signature thresholds in R5.
- **guardBoxes (filtered):** All input boxes that hold the same Guard NFT token ID (filter ensures only boxes belonging to this guard pool are counted).
- **Additional inputs:** May include data inputs or payment UTXOs required for the transaction.

### Outputs
- **OUTPUTS(0) (GuardSign box):** The successor guard state box, must contain:
  - The same Guard NFT (same token ID)
  - The same Guard NFT quantity (no minting/burning)
  - Updated R4/R5 registers (off-chain constructed)

## Key Logic

The contract enforces four invariants via `allOf`:

1. **Singleton Integrity:** `guardBoxes.size == 1`
   - Exactly one input box holds the Guard NFT, preventing double-spend attacks and ensuring a single authoritative state.

2. **Token ID Preservation:** `OUTPUTS(0).tokens(0)._1 == SELF.tokens(0)._1`
   - Output must carry the identical Guard NFT token ID (no token substitution).

3. **Token Quantity Preservation:** `OUTPUTS(0).tokens(0)._2 == SELF.tokens(0)._2`
   - NFT quantity remains unchanged (guarantees 1-to-1 Singleton token rule compliance).

4. **Multi-Signature Threshold:** `updateSignLeast`
   - At least `updateSignCount` (from R5[1]) distinct signatures from the guard public key set (R4) must be present in the transaction's Sigma protocol proof.
   - Uses **Threshold Sigma Protocol** (`atLeast`) to validate M-of-N signatures.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Coll[Byte]]` | **GUARD_PKS** — Collection of encoded public keys (compressed Points) representing authorized guard signatories. |
| **R5** | `Coll[Int]` | Signature thresholds: `[paymentRequiredSigns, updateRequiredSigns]`. Index 1 (`updateRequiredSigns`) is the M-of-N threshold for state transitions. |

Standard registers R0–R3 implicitly contain box properties (value, tokens, propositionBytes, etc.).

## Tokens

| Slot | Type | Purpose |
|------|------|---------|
| **0** | **Guard NFT** (Native token, qty=1) | **Singleton / State NFT** that uniquely identifies this guard pool instance. Acts as a state machine linearizer—only one box with this token ID can exist per transaction output. Used for filtering legitimate guard boxes and preventing state forking. |

## Integration Pattern

### Off-Chain Bot / Dapp Workflow

1. **Read Current State:**
   - Fetch the UTXO carrying the Guard NFT from the blockchain.
   - Deserialize R4 (guard public keys) and R5 (thresholds).

2. **Construct Transaction:**
   - Gather `updateRequiredSigns` guard signatures on the transaction (via Context extension or external signing protocol).
   - Build OUTPUTS(0) with:
     - Same Guard NFT token
     - Updated R4/R5 (if guard set or thresholds change)
     - Any new contract state or payment logic
   - Ensure exactly one guard box input.

3. **Sign & Submit:**
   - The off-chain bot orchestrates M-of-N Sigma protocol signatures from guard signers.
   - Submits transaction; Ergo node validates:
     - `guardBoxes.size == 1` ✓
     - Guard NFT propagation ✓
     - `atLeast(updateSignCount, signedColl)` proof verification ✓

4. **Verification:**
   - The contract decodes R4 points, constructs Sigma propositions (`proveDlog` for each public key), and checks that the transaction's Sigma proof satisfies the threshold.

## Related Contracts

Based on Rosen Bridge architecture:

- **PaymentBox / PaymentProcessor:** Likely consumes payment UTXOs alongside GuardSign transactions to execute cross-chain payments.
- **GuardPool / GuardState (implied):** GuardSign may be the state box for a larger guard pool contract that manages member additions/removals.
- **Commitment / Observation Contracts:** Guard signatures may unlock commitment boxes that aggregate off-chain observations (block headers, NiPoPoW proofs, or token swap events).
- **Atomic Swap Contracts (bridge side):** GuardSign authorization may gate the final redemption phase of cross-chain swaps.

---

## Notes

- **Constant Segregation:** R4 and R5 are typically constant (rarely modified) across state transitions, enabling efficient off-chain filtering.
- **Invariant:** The Guard NFT acts as a **linearizer** in the eUTXO model, preventing concurrent state forks.
- **Soft Fork Compatibility:** Uses standard Sigma protocols (no exotic cryptography), ensuring upgradability.