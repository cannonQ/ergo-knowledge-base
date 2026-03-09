---
title: StabilityNexus/Gluon-Ergo-Contracts — GluonWTxProxyContract.es
description: "ErgoScript contract analysis: modules/gluonw-base/src/main/resources/ErgoContracts/GluonW/Ergs/ProxyContract/GluonWTxProxyContract.es"
tags: [stabilitynexus, gluon-ergo-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Gluon-Ergo-Contracts"
contract_file: modules/gluonw-base/src/main/resources/ErgoContracts/GluonW/Ergs/ProxyContract/GluonWTxProxyContract.es
project: stabilitynexus-gluon-ergo-contracts
---
# GluonW Transaction Proxy Contract Analysis

## Purpose

This contract serves as a **Proxy Contract** for the GluonW protocol, managing the atomic state and token reserves for Neutrons and Protons within a single Box. It acts as the authoritative container for tracking dual-token supplies and coordinating multi-stage transactions that interact with the GluonW system's core state machine.

## Inputs / Outputs

### Expected Inputs
- **Proxy Box** (self): The current state box containing:
  - ERG value (for storage rent and transaction fees)
  - Native tokens: GluonW NFT (1), Neutrons (quantity ≤ IntMax), Protons (quantity ≤ IntMax)
  - State data in R4 and R5

### Expected Outputs
- **Updated Proxy Box**: Continuation of the same state with:
  - Preserved or updated ERG balance (covering storage rent)
  - Modified Neutron/Proton token quantities (reflecting protocol operations)
  - Updated supply totals in R4
  - Updated or preserved token IDs in R5
  - GluonW NFT preserved (Singleton pattern) for state authenticity

## Key Logic

The contract enforces the following validation invariants:

1. **Singleton Enforcement**: The output box must contain exactly one GluonW NFT (identified by `_GluonWNFTId`), ensuring state continuity and preventing fork attacks on the state machine.

2. **Token Supply Tracking**: 
   - Reads current supplies from R4: `(Total Neutrons, Total Protons)`
   - Validates that output supply values reflect net changes from protocol operations
   - Ensures no unauthorized token minting (Neutrons/Protons creation outside protocol rules)

3. **Token ID Immutability**: R5 maintains the canonical token IDs for both Neutrons and Protons—these must remain constant across all state transitions.

4. **Storage Rent Compliance**: Output box must retain minimum ERG value (enforced via `_MinFee` constant) to satisfy Ergo's storage rent protocol and enable future state transitions.

5. **Transaction Authorization**: Only transactions signed by authorized off-chain logic (via Sigma protocol context) can modify this box, preventing unauthorized state mutations.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `(Long, Long)` | **(Total Neutrons Supply, Total Protons Supply)** — Maintains cumulative counts of both token types; updated when Neutrons/Protons are minted or burned via protocol transactions. |
| **R5** | `(Coll[Byte], Coll[Byte])` | **(NeutronsTokenId, ProtonsTokenId)** — Immutable references to the canonical token IDs; allows off-chain and downstream contracts to identify which tokens represent Neutrons vs. Protons. |

## Tokens

| Token | Quantity | Purpose |
|-------|----------|---------|
| **GluonW NFT** | 1 | **Singleton / State Token**: Authenticates this box as the authoritative state container; prevents state fork attacks by enforcing single-chain-of-boxes invariant. Token ID = `_GluonWNFTId` (hard-coded constant). |
| **Neutrons** | ≤ IntMax | **Native token** representing one side of the dual-token system; quantity tracked in R4; minted/burned by authorized protocol operations. |
| **Protons** | ≤ IntMax | **Native token** representing the other side of the dual-token system; quantity tracked in R4; minted/burned by authorized protocol operations. |

## Integration Pattern

### Off-Chain Construction Requirements

1. **Read Current State**: 
   - Retrieve the Proxy Box (identified by GluonW NFT singleton)
   - Extract R4 (current supplies) and R5 (token IDs)

2. **Compute State Transition**:
   - Determine new supply totals based on protocol rules (e.g., Neutron/Proton issuance or redemption)
   - Calculate required ERG balance for storage rent

3. **Build Transaction**:
   - **Input**: Current Proxy Box + any auxiliary input boxes (protocol contracts, user boxes)
   - **Output**: New Proxy Box with:
     - Updated R4 containing new `(neutronSupply, protonSupply)` values
     - Preserved R5 with token IDs
     - Adjusted Neutron/Proton token quantities
     - Minimum ERG (≥ `_MinFee`)

4. **Sign & Submit**:
   - Create valid Sigma protocol signature(s) authorizing the state transition
   - Broadcast transaction to the Ergo network

### Verification Logic (Contract-Side)

- Validate that output box contains the GluonW NFT (singleton check)
- Confirm R5 token IDs remain unchanged
- Verify R4 supplies are consistent with token quantity deltas
- Ensure ERG balance covers storage rent (`_MinFee`)
- Check authorization via Sigma context

## Related Contracts

While the provided snippet does not contain explicit references, the **GluonW Proxy Contract** integrates within a multi-stage contract architecture:

- **GluonW State Machine Contracts**: Upstream contracts that read the Proxy Box's state (R4, R5) and validate protocol operations (e.g., Neutron mint/burn, Proton equilibration)
- **Auxiliary Protocol Contracts**: Contracts that consume the Proxy Box as a *data input* (read-only reference) to verify current supplies without modifying state
- **Headless dApp / Off-Chain Bot**: Service layer that monitors the Proxy Box, computes new state, and constructs authorized transactions

---

## Implementation Status

**Current State**: `In Progress` (v1.0, as of July 29th, 2023)

The contract scaffold is defined but the core validation logic (Sigma protocol conditions, supply calculation rules, and authorization checks) is not yet populated in the provided snippet. Full implementation would include:

- Explicit box selection logic to ensure singleton property
- Supply arithmetic invariants
- Authorized signer predicates or multi-signature thresholds
- Potential AVL tree integration for historical supply tracking (if auditing is required)