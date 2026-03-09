---
title: kushti/dexy-stable — bank.es
description: "ErgoScript contract analysis: contracts/bank/bank.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/bank.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Bank (dexy-stable)

## Purpose

The Bank contract is the central vault and state machine for the Dexy stablecoin system. It holds the bankNFT Singleton token and the dexyUSD token reserve, enforcing that dexyUSD emissions occur only through authorized mint boxes (FreeMint or ArbitrageMint) and that the Bank box's identity and script are preserved across all state transitions. The contract does not encode emission logic itself but delegates validation to specialized child contracts.

---

## Inputs / Outputs

### Inputs (transaction-dependent, multiple transaction types supported)

| Transaction Type | Input Index | Box Type | Purpose |
|---|---|---|---|
| **Arbitrage Mint / Free Mint** | 0 | FreeMint or ArbitrageMint | Carries mint NFT; encodes emission logic |
| | 1 | Bank (self) | Current state of the Bank box |
| | 2 | Buyback | Handles token buyback mechanics |
| **Intervention** | 0 | LP | Liquidity Pool box (redirected mint source) |
| | 1 | Bank (self) | Current state of the Bank box |
| | 2 | Intervention | Carries intervention NFT; emergency protocol |
| **Payout** | 0 | Payout | Carries payout NFT; withdrawal logic |
| | 1 | Bank (self) | Current state of the Bank box |
| | 2 | Buyback | Handles token buyback mechanics |
| **Update** | 0 | Update | Carries update NFT; protocol upgrade path |
| | 1 | Bank (self) | Current state of the Bank box |

### Outputs

| Output Index | Box Type | Constraints |
|---|---|---|
| 0 | (Varies by transaction) | Dependent on specific transaction type |
| 1 (selfOutIndex) | Bank | Successor Bank box (validated by `validSuccessor`) |
| 2+ | (Varies by transaction) | Dependent on specific transaction type |

---

## Key Logic

### Core Validation

The contract enforces a **multi-path state machine** that accepts exactly five transaction types, each identified by the NFT present in a specific input:

1. **Singleton Preservation (`validSuccessor`)**
   - The second output (index 1) must be the Bank's successor
   - Must preserve the bankNFT token (checked by token ID at index 0)
   - Must preserve the proposition bytes (same ErgoScript code)
   - Must preserve the dexyUSD token ID (but amount can change, enforced by child contracts)

2. **Mint Authorization (`validMint`)**
   - Input at index 0 must carry either:
     - `freeMintNFT`: For free minting operations
     - `arbitrageMintNFT`: For arbitrage minting operations
   - These child boxes encode the actual emission logic (how many dexyUSD tokens are created, under what conditions)

3. **Intervention Authorization (`validIntervention`)**
   - Input at index 2 must carry the `interventionNFT`
   - Allows emergency protocol actions (e.g., rebalancing during crisis)
   - Data input references a Tracking box (98% collateralization check)

4. **Payout Authorization (`validPayout`)**
   - Input at index 0 must carry the `payoutNFT`
   - Enables withdrawal/redemption flows

5. **Upgrade Path (`validUpdate`)**
   - Input at index 0 must carry the `updateNFT`
   - Allows protocol upgrades without requiring other authorization boxes
   - Provides off-chain governance integration point

### Sigma Protocol Guard

The contract uses a **disjunctive Sigma protocol** (`sigmaProp`):
```
(validSuccessor && (validMint || validIntervention || validPayout)) || validUpdate
```

This means:
- **Normal operation**: Successor is valid AND one of the three authorized transaction types succeeds
- **Governance override**: Update box can trigger state change independently

---

## Registers Used

| Register | Type | Purpose |
|---|---|---|
| **R4** (Oracle data input) | Long (implicit, read from data input) | Exchange rate: nanoErgs per USD; used by child contracts to validate collateralization |
| **R5–R9** | None | Not used in this contract |

**Note**: The Bank box itself uses no registers. Register data comes from:
- **Data input (Oracle box)**: R4 contains the current rate for validating mint/intervention logic
- **Data input (LP box, Tracking box)**: Context-dependent for intervention/payout logic
- **Child boxes** (FreeMint, ArbitrageMint, Intervention, Payout): Encode emission logic and constraints in their own registers

---

## Tokens

### Token 0: Bank NFT (Singleton)

- **Purpose**: Identifies this specific Bank box across all state transitions
- **Type**: Native token with fixed quantity (1)
- **Validation**: Must be present in successor output at `OUTPUTS(1).tokens(0)`
- **Rule**: **Token ID rule** enforces that the NFT is immutable and uniquely identifies the contract instance

### Token 1: dexyUSD

- **Purpose**: The stablecoin being issued and managed by the Bank
- **Type**: Native token (minted/burned by this contract)
- **Validation**: Token ID must be preserved; amount changes are delegated to child contracts
- **Validation**: `successor.tokens(1)._1 == SELF.tokens(1)._1` (ID check only)
- **Off-chain enforcement**: Child contracts (FreeMint, ArbitrageMint) encode how much new dexyUSD is created per transaction

---

## Integration Pattern

### Off-Chain Bot / Dapp Responsibilities

The Bank contract operates as a **State Machine** controlled by off-chain actors (Headless dApp / Off-chain bot):

1. **Transaction Construction**
   - Detect current Bank box (by bankNFT lookup)
   - Route to appropriate child contract based on business logic:
     - **Free minting**: Construct FreeMint input box with emission amount (R4, R5, etc.)
     - **Arbitrage minting**: Construct ArbitrageMint input box with coll