---
title: SavonarolaLabs/crystal-pool — sell-token-for-erg.es
description: "ErgoScript contract analysis: src/lib/contracts/sell-token-for-erg.es"
tags: [savonarolalabs, crystal-pool, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/SavonarolaLabs/crystal-pool"
contract_file: src/lib/contracts/sell-token-for-erg.es
project: savonarolalabs-crystal-pool
---
# ErgoScript Contract Analysis: `sell-token-for-erg.es`

## Purpose

This contract implements a **decentralized token-for-ERG swap mechanism** where sellers can list tokens at specified rates, and a pool operator can execute partial or full fills of orders. It manages multi-input consolidation of sell orders, calculates weighted average rates, and ensures sellers receive fair compensation in nanoERGs for their tokens while maintaining state invariants across transaction outputs.

---

## Inputs / Outputs

### Inputs
- **Multiple Sell Order Boxes** (self-referential): Boxes locked by this contract, each containing:
  - Tokens to be sold (in `tokens(0)`)
  - Seller's public key and pool operator's public key (in R4)
  - Unlock height, token ID, sell rate, and multisig address (in R5–R8)
  
- **Data Inputs** (implicit): Context box providing HEIGHT and transaction metadata

### Outputs
- **Change Box(es) at Max Rate**: Boxes returned to the seller containing unsold tokens (those at the maximum sell rate only)
- **Payment Box(es)**: Boxes locked to the seller's multisig address containing nanoERGs earned from the sale, with constraints:
  - Must unlock at the same height as original inputs (`unlockHeight`)
  - Must match the seller's multisig address in `propositionBytes`

---

## Key Logic

### Core Validation Flow

1. **Identify Legitimate Input Boxes**
   - Must be locked by the same contract (`isSameContract`)
   - Must contain the same token ID (`isSameToken`)
   - Must have matching seller PKs and pool PKs (`isSameSeller`)
   - Must have matching multisig address (`isSameMultisig`)
   - Must have positive sell rate (`isGreaterZeroRate`)

2. **Aggregate Across Multiple Orders**
   - **`tokensIn`**: Sum all tokens from legitimate inputs
   - **`avgRateInputs`**: Weighted average sell rate = Σ(rate × tokenAmount) / tokensIn
   - **`maxSellRate`**: Maximum rate among all input boxes

3. **Validate Output State**
   - **Change Boxes**: Only boxes at `maxSellRate` are allowed as outputs; any tokens at lower rates are "sold"
   - **`tokensBack`**: Sum of tokens in change boxes (max-rate only)
   - **`tokensSold`**: tokensIn − tokensBack
   - **Payment Boxes**: Must match seller identity and unlock height

4. **Price Verification**
   - **`valueOfSoldTokens`**: tokensIn × avgRate − tokensBack × maxRate
   - **`avgTokenPrice`**: valueOfSoldTokens / tokensSold
   - **`sellerPaid`**: tokensSold × avgTokenPrice ≤ nanoErgsPaid (seller gets ≥ owed amount)
   - **`sellOrderChangeBoxIsFine`**: tokensAtMaxRate > tokensBack (no over-return)

5. **Authorization**
   - **After unlock height** (`HEIGHT > unlockHeight`): Seller can unilaterally withdraw via `getSellerPk(SELF)`
   - **Before unlock height**: 
     - Pool operator (`getPoolPk`) can execute the swap if `orderFilled` is true, OR
     - Seller and pool operator must both sign

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[SigmaProp]` | Seller's public key (index 0) and Pool operator's public key (index 1) |
| **R5** | `Int` | `unlockHeight` — block height after which seller can unilaterally reclaim tokens |
| **R6** | `Coll[Byte]` | Token ID of the token being sold |
| **R7** | `Long` | Sell rate (nanoERGs per token unit); used for weighted averaging |
| **R8** | `Coll[Byte]` | Seller's multisig address (or withdrawal address); used to validate payment outputs |

---

## Tokens

### Native Tokens
- **Primary Token** (index 0 in box): The token being sold; identified by `getTokenId()` extracted from R6
  - All input boxes must contain the same token ID
  - Amount varies per order; aggregated as `tokensIn`
  - Change boxes return tokens at max rate only

### Authentication & State
- **No NFT/Singleton Token** used; state coherence relies on:
  - **Contract Bytecode Matching** (`propositionBytes` comparison)
  - **Register Consistency** (R4–R8 match across inputs)
  - **Deterministic Rate Calculation** (weighted average prevents arbitrage)

---

## Integration Pattern

### Off-Chain Bot / Pool Operator Responsibilities

1. **Order Discovery**
   - Scan blockchain for boxes locked by this contract
   - Group by seller, token, and rate
   - Aggregate multi-input transactions

2. **Transaction Construction**
   - **Select Inputs**: Collect one or more legitimate sell-order boxes
   - **Calculate Outputs**:
     - Compute `tokensIn`, `avgRateInputs`, `maxSellRate`
     - Create change boxes only for tokens at `maxSellRate`
     - Create payment boxes to seller's multisig address with:
       - Value = tokensSold × avgTokenPrice (in nanoERGs)
       - Lock height = `unlockHeight`
       - Recipients = `getSellerMultisigAddress`
   - **Ensure Invariants**:
     - `sellerPaid == true`: nanoErgsPaid ≥ tokensSold × avgTokenPrice
     - `sellOrderChangeBoxIsFine == true`: tokensAtMaxRate > tokensBack
     - All output boxes have value ≥ minimum box value (storage rent)

3. **Signing & Submission**
   - If `HEIGHT ≤ unlockHeight(SELF)`:
     - Pool operator signs (via `getPoolPk` in R4)
     - Seller may sign if `orderFilled == false` (to reject)
   - If `HEIGHT > unlockHeight(