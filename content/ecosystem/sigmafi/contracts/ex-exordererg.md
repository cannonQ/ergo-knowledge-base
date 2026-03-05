---
title: K-Singh/Sigma-Finance — ExOrderERG.ergo
description: "ErgoScript contract analysis: contracts/ex/ExOrderERG.ergo"
tags: [k-singh, sigma-finance, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
contract_file: contracts/ex/ExOrderERG.ergo
project: k-singh-sigma-finance
---
# ErgoScript Analysis: ExOrderERG Contract

## Purpose

This contract implements an **open exchange order** for selling native tokens (or ERG) at a fixed price in nanoERG. A seller deposits assets into a box under this contract, specifying their desired sale price. When a buyer matches the order, the contract validates that the exchange is executed correctly, fees are paid to the developer and optional UI provider, and the seller receives their payment.

## Inputs / Outputs

### Inputs
- **SELF**: The open order box containing:
  - Assets to be sold (native tokens in `SELF.tokens`)
  - ERG reserve (`SELF.value`)
  - Seller's public key in **R4** (SigmaProp)
  - Sale price in nanoERG in **R5** (Long)

### Outputs (on order closure)
- **OUTPUTS(0)**: Exchange box — holds the original assets; must reference SELF by ID in R4
- **OUTPUTS(1)**: Seller payment box — receives `salePrice` nanoERG; locked to seller's PK
- **OUTPUTS(2)** *(conditional)*: Developer fee box — receives dev fee in `_tokenId` tokens (0.5% of sale price)
- **OUTPUTS(3)** *(conditional)*: UI fee box — receives UI fee in `_tokenId` tokens (0.4% of sale price, if UI fee enabled)

### Refund Path
If order is not closed, the contract permits spending by `sellerPK` alone (unilateral cancellation).

---

## Key Logic

### Order Closure Detection
```
orderIsClosed = (OUTPUTS(0).propositionBytes != sellerPK.propBytes)
```
If the first output is **not** locked to the seller's key, the order is considered matched/closed.

### Closure Validation (`orderMade`)
When `orderIsClosed == true`:
1. **Exchange box integrity**: OUTPUTS(0) must contain identical tokens and ERG as SELF
2. **Exchange box linkage**: OUTPUTS(0).R4 must store SELF's box ID (prevents reuse of stale orders)
3. **Seller payment**: OUTPUTS(1) must send exactly `salePrice` nanoERG to the seller's PK
4. **Minimum box value**: Both exchange and payment boxes maintain 1 ERG minimum

### Fee Calculation
- **Dev fee**: 0.5% (500 basis points ÷ 100,000) of `salePrice`, denominated in `_tokenId`
- **UI fee** *(optional)*: 0.4% (400 basis points ÷ 100,000) additional, enabled via context variable
- **Fee arithmetic**: Uses `BigInt` to prevent Long overflow on large sale prices
- **Fee outputs**: Each fee receiver must be a separate box with exactly 1 ERG + the allocated token amount

### Refund Path
If the order is not closed (first output remains locked to `sellerPK.propBytes`), the seller may unilaterally spend SELF by satisfying `sellerPK` alone.

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Seller's public key; gates refund and validates seller payment output |
| **R5** | `Long` | Sale price in nanoERG; buyer must send this amount to the seller |
| OUTPUTS(0).R4 | `Coll[Byte]` | References SELF's box ID to link exchange order to original SELF box |

---

## Tokens

- **`_tokenId`** *(constant, must be injected)*: The token in which fees are denominated and paid to dev/UI addresses
  - All fee outputs carry native tokens identified by `_tokenId`
  - Not ERG itself (fees are paid in a separate token type)
  - Likely the protocol's governance or fee token (e.g., SigmaUSD or a custom token)

---

## Integration Pattern

### Off-Chain Responsibilities

1. **Order Creation**:
   - Off-chain bot constructs a box with the seller's tokens/ERG
   - Writes seller's PK to **R4** and sale price (in nanoERG) to **R5**
   - Submits to the blockchain

2. **Order Matching** (Buyer/Bot):
   - Observes the open order box (SELF)
   - Constructs a matching transaction with:
     - **OUTPUTS(0)**: New box with SELF's tokens/ERG, R4 = SELF.id, locked to any address (signaling closure)
     - **OUTPUTS(1)**: Box sending `salePrice` nanoERG to `sellerPK`
     - **OUTPUTS(2)**: Dev fee box (if dev fee > 0), with fee amount in `_tokenId` to `_devPK`
     - **OUTPUTS(3)**: UI fee box (if UI fee enabled and fee > 0), with fee amount to UI provider
   - Ensures total input ERG ≥ `salePrice` + fees (in `_tokenId`)

3. **Context Extension**:
   - Optional context variable 0 (getVar[SigmaProp](0)): UI provider's PK (enables 0.4% UI fee)

4. **Validation**:
   - Contract verifies output box ordering and values match the order parameters
   - Rejects if exchange box is re-locked to seller (prevents double-spending the order)

5. **Refund** (Seller):
   - If order is not matched, seller signs with their private key to unlock SELF and retrieve assets

---

## Related Contracts

### Inferred Integrations

- **Matching/Swap Orchestrator** *(likely)*: A contract that consumes multiple ExOrderERG boxes to perform multi-leg atomic swaps (e.g., SIGUSD ↔ tokens)
  
- **Fee Distribution / Treasury** *(likely)*: A contract that collects all dev fee outputs and redistributes rewards or governance tokens

- **State Machine Coordinator** *(optional)*: If this is part of a larger order-book protocol (e.g., Dexy-style), a contract managing global order indexes or price feeds

- **NFT/Token Registry