---
title: nautls/machina-finance — Settings.es
description: "ErgoScript contract analysis: packages/contracts/src/contracts/Settings.es"
tags: [nautls, machina-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/nautls/machina-finance"
contract_file: packages/contracts/src/contracts/Settings.es
project: nautls-machina-finance
---
# ErgoScript Contract Analysis: Settings.es

## Purpose

This contract serves as an immutable configuration box for the Machina Finance protocol. It stores execution-related settings and parameters that other contracts reference during order processing. Currently, all settings are locked (non-updatable), with plans to integrate governance mechanisms in future iterations.

## Inputs / Outputs

**Inputs:**
- This contract is typically consumed as a **data input** (read-only reference) rather than a regular input
- Other contracts query its registers to retrieve protocol parameters without modifying the box state

**Outputs:**
- No standard outputs are produced by this contract directly
- The settings box itself remains on-chain as a singleton, referenced by spending transactions
- When governance is implemented, a new settings box (State NFT pattern) may replace this one

## Key Logic

```
Validation Rule: sigmaProp(false)
```

The contract enforces an **impossible condition**: `sigmaProp(false)` always fails, meaning:

1. **This box can never be spent directly** — attempting to consume it as a regular input will fail validation
2. **It can only be referenced as a data input** — other transactions access its registers without unlocking it
3. **Immutability by design** — settings cannot be modified until governance logic replaces this contract code

This is a common pattern in multi-stage eUTXO contracts where configuration boxes are read-only references rather than mutable state.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | (Implied, not shown) | Likely holds execution fees, slippage tolerance, or oracle parameters |
| **R5** | (Implied, not shown) | Possible minimum order size, timeout values, or protocol version |
| **R6–R9** | (Implied, not shown) | Reserved for future governance parameters or multi-signature endorsements |

*Note: Actual register contents are not defined in this contract stub; they must be documented in calling contracts or initialization scripts.*

## Tokens

**No native tokens are directly used in this contract.**

However, the settings box itself may contain:
- A **State NFT** (singleton token) to ensure only one authoritative settings box exists on-chain
- This NFT would be embedded in the box's `tokens` field and enforced by contracts that reference this box

## Integration Pattern

**Off-chain Bot / Headless dApp Responsibilities:**

1. **Initialization:**
   - Deploy this settings box once with a State NFT in its tokens field
   - Populate R4–R9 with execution parameters (fees, oracle addresses, thresholds)

2. **Contract Integration:**
   - Order-matching contracts must declare this box as a **data input**:
     ```ergoscript
     val settings = CONTEXT.dataInputs(settingsIndex)
     val executionFee = settings.R4[Long].get
     ```

3. **Verification:**
   - Spending transactions verify the settings box is unspent (remains immutable)
   - If governance activates, off-chain code must construct a new settings box with updated parameters and a migration transaction

4. **Atomic Swap / Order Execution:**
   - When executing swaps, contracts read fee percentages or slippage caps from this singleton
   - No transaction fees are validated against this box (that's handled by the Ergo protocol's minimum transaction fee rule)

## Related Contracts

Based on naming conventions in Machina Finance:

- **Order Contracts** (e.g., `Order.es`, `LimitOrder.es`) — consume settings as data input to retrieve execution parameters
- **Swap Router** — reads fee tiers from this settings box
- **Oracle Contract** — may reference price source addresses stored in R4–R9
- **Governance Contract** (future) — will implement a multi-stage contract to update settings while rotating the State NFT

---

## Design Notes

- **Why `sigmaProp(false)`?** This is a well-known pattern in Ergo for **read-only state machines**. The box is cryptographically prevented from being spent, ensuring protocol consistency.
- **Upgrade Path:** When governance launches, a separate governance contract will validate the transition from this immutable settings box to a new one controlled by voting logic (e.g., multi-signature or DAO threshold).
- **Scalability:** Using data inputs avoids bloating the transaction size; hundreds of orders can reference a single settings box without increasing proof complexity.