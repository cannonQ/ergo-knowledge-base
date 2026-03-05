---
title: Telefragged/off-the-grid — contract.es
description: "ErgoScript contract analysis: contracts/grid_multi/contract.es"
tags: [telefragged, off-the-grid, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/Telefragged/off-the-grid"
contract_file: contracts/grid_multi/contract.es
project: telefragged-off-the-grid
---
# ErgoScript Contract Analysis: `grid_multi/contract.es`

## Purpose

This contract implements a **decentralized multi-order exchange box** that enables atomic token-for-ERG trading on the Ergo blockchain. It maintains a collection of buy/sell orders in a single state box, validates order state transitions (BUY ↔ SELL), and ensures token and ERG balances are reconciled against executed trades while collecting protocol fees.

## Inputs / Outputs

### Inputs
- **SELF**: The order contract box containing:
  - Owner's group element (public key) in R4
  - Collection of orders in R5
  - Token ID in R6
  - Optional metadata in R7
  - Native tokens (at most one, identified by token ID)
  - ERG value

### Outputs
- **OUTPUTS(selfIndex)**: Recreation of the same contract box with:
  - Identical owner, order structure, token ID, and metadata
  - Updated order states (some BUY→SELL or SELL→BUY transitions)
  - Updated native token balance
  - Updated ERG value
  - Conforming to all validation conditions
- **Fee boxes**: One or more boxes with `propositionBytes == FeeProposition` collecting accumulated protocol fees

## Key Logic

### Core Validation Flow

The contract validates a transaction via **OR composition**:

```
VALID IF: (Owner signs with private key) OR (All swap conditions satisfied)
```

### Swap Validation Sequence

1. **Box Recreation Check**
   - Output box at `selfIndex` must exist and have identical `propositionBytes`
   - Prevents contract bypass

2. **Order Difference Analysis** (fold over zipped order pairs)
   - Compares current orders with recreated orders element-by-element
   - Enforces immutability: `amount`, `buyPrice`, `sellPrice` must not change
   - Detects state transitions only:
     - **BUY → SELL**: tokens decrease (sold), ERGs increase
     - **SELL → BUY**: tokens increase (bought), ERGs decrease
     - **No change or invalid**: rejected
   - Returns tuple: `(isValid: Boolean, (tokenDelta: Long, ergDelta: Long))`

3. **Exchange Consistency Verification**
   - Computed `tokenDiff` from order state changes must match actual token balance delta: `recreatedTokens - currentTokens`
   - Computed `ergDiff` must match actual ERG balance delta: `recreatedBox.value - SELF.value`
   - Both deltas must be non-zero (ensures actual exchange occurred)

4. **Token ID Validation**
   - Output must hold ≤ 1 native token
   - All tokens present must match the stored token ID (prevents token injection)

5. **Register Immutability**
   - R4 (owner group element): unchanged
   - R5 (order collection): size preserved; states may change, amounts/prices fixed
   - R6 (token ID): unchanged
   - R7 (metadata): if present, must be recreated identically

6. **Fee Collection**
   - All outputs with `propositionBytes == FeeProposition` are summed
   - Total must equal `MaxFee` (constant, not shown in snippet)

### Proof Requirements

Transaction is valid if:
- **Signature path**: Owner proves discrete log of `ownerGroupElement` via `proveDlog()`, OR
- **Swap path**: All of `tokenIdOk && orderRecreated && metadataRecreated && exchangeOk && feeOk` evaluate to `true`

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `GroupElement` | Owner's public key (Schnorr/DLog); used in signature validation |
| **R5** | `Coll[((Long, Boolean), (Long, Long))]` | Order collection: `((amount, isBuy), (buyPrice, sellPrice))` |
| **R6** | `Coll[Byte]` | Token ID (blake2b-256 hash); identifies tradable asset |
| **R7** | `Coll[Byte]` (optional) | Metadata for order grouping, profit tracking, or off-chain indexing |

---

## Tokens

### Native Token Handling

- **Single token per box**: At most 1 native token in SELF and OUTPUTS(selfIndex)
- **Token ID verification**: All tokens in output must match the stored token ID in R6
- **Balance tracking**: Token amount encodes exposure position
  - Positive balance: tokens held (ready to sell)
  - Changes reflect BUY (increase) or SELL (decrease) transitions

### No NFT/Singleton Pattern

Unlike typical state machines with a state NFT, this contract **does not enforce singleton semantics**. Multiple instances can exist independently; the contract does not rely on a unique NFT for global state coordination.

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Order Monitoring**
   - Index boxes matching this contract's `propositionBytes`
   - Track R5 order state (`isBuy: Boolean`)

2. **Order Matching & Aggregation**
   - Scan mempool/blockchain for complementary orders (buy/sell pairs)
   - Identify matched orders whose state should flip

3. **Transaction Construction**
   ```
   Inputs:
     - [This contract box (SELF)]
     - [Data inputs: matched order boxes, price feeds, etc.]
   
   Outputs:
     - [Contract box recreated with updated R5 states]
     - [Fee box(es) with totalValue = MaxFee]
     - [Optional change/slippage boxes]
   ```

4. **Invariant Enforcement**
   - Compute expected token delta from order flips
   - Compute expected ERG delta from prices
   - Verify output box balances satisfy: `Δtokens` and `ΔERGs` match computed deltas
   - Ensure fee collection matches `MaxFee` constant

5. **Transaction Fee Handling**
   - Protocol fee (`MaxFee`) collected from output box values
   - Minimum transaction fee (network fee) paid separately
   - Minimum box value (storage rent) enforced by Ergo node validation

6