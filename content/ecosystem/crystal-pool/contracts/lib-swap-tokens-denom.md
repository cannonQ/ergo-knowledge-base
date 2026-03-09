---
title: SavonarolaLabs/crystal-pool — swap-tokens-denom.es
description: "ErgoScript contract analysis: src/lib/contracts/swap-tokens-denom.es"
tags: [savonarolalabs, crystal-pool, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/SavonarolaLabs/crystal-pool"
contract_file: src/lib/contracts/swap-tokens-denom.es
project: savonarolalabs-crystal-pool
---
# ErgoScript Contract Analysis: swap-tokens-denom

## Purpose

This contract implements a **multi-party token swap mechanism** with denomination normalization, allowing multiple sellers to pool sell orders for the same token pair while enforcing fair-rate execution. It enables atomic exchange of selling tokens for buying tokens, with optional time-locked seller authorization and pool-operator validation of pricing.

## Inputs / Outputs

### Inputs
- **Legitimate swap boxes** (`isLegitInput`): Boxes locked by this contract containing:
  - Selling tokens (identified by `R6._1`)
  - Identical seller PKs, pool PKs, unlock heights, and token pairs
  - Valid positive exchange rates stored in `R7`
  
- **Self-referential inputs**: Multiple instances of this same contract (eUTXO pattern) can be consumed together to pool liquidity

### Outputs
- **Remaining swap order boxes** (`isLegitSellOrderOutput`): Contract boxes carrying unsold portions of selling tokens, with rates normalized to `maxDenom`
- **Payment boxes**: Arbitrary boxes (identified by seller's multisig script in `propositionBytes`) receiving the buying tokens as settlement

## Key Logic

### Core Validation Flow

1. **Denomination Normalization**: 
   - Identifies the maximum denomination (`maxDenom`) across all legitimate inputs
   - Normalizes all exchange rates to this common denominator: `getRateInMaxDenom(box) = rate × maxDenom / denom`
   - Ensures all output swap orders use the `maxDenom` to maintain rate consistency

2. **Rate Fairness Check**:
   - Calculates total selling tokens consumed: `tokensSold = sumSellTokensIn(INPUTS) - sumSellTokensOut(OUTPUTS)`
   - Calculates total buying tokens received: `tokensPaid = sumBuyTokensPaid(OUTPUTS)`
   - Computes weighted rate of consumption: `expectedRate = (Σ sellTokens × normalizedRate) / tokensSold`
   - Validates: `maxDenom × tokensPaid / tokensSold ≥ expectedRate` (buyer doesn't pay below fair weighted average)

3. **Authorization Logic** (context-dependent):
   - **Post-unlock** (`HEIGHT > unlockHeight(SELF)`): Only seller's signature required
   - **Pre-unlock**: Either:
     - Both seller **and** pool operator sign, **OR**
     - Pool operator signs **and** `isPaidAtFairRate` evaluates to true (fair-rate bypass)
   
   This enables pool operators to execute swaps before unlock if pricing is fair, without waiting for seller signatures.

### Helper Predicates

| Function | Purpose |
|----------|---------|
| `isSameContract(box)` | Verifies box is locked by identical ErgoTree (same contract instance) |
| `isSameTokenPair(box)` | Ensures token IDs match across swaps (no token switching) |
| `hasSellingToken(box)` | Confirms box holds the correct selling token |
| `hasBuyingToken(box)` | Confirms box holds the correct buying token |
| `isSameSeller(box)` | Matches seller and pool operator PKs |
| `isSameUnlockHeight(box)` | Enforces synchronized unlock times across pooled orders |
| `hasMaxSellRate(box)` | Validates output rate equals normalized `maxSellRate` |

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[SigmaProp]` | Tuple of signing keys: `[sellerPk, poolPk]` |
| **R5** | `Int` | Unlock height (`unlockHeight`) — block number after which seller can unilaterally withdraw |
| **R6** | `(Coll[Byte], Coll[Byte])` | Token ID pair: `(sellingTokenId, buyingTokenId)` |
| **R7** | `Long` | Exchange rate: units of selling token per unit of buying token |
| **R8** | `Coll[Byte]` | Seller's multisig address (script bytes) for receiving payment boxes |
| **R9** | `Long` | Denomination (`denom`) — denominator for rate normalization |

**State Machine Property**: All registers except token balances are immutable across the transaction; they define the swap's invariants.

## Tokens

### Native Tokens
- **Selling Token** (`R6._1`): Identified by token ID, holds the asset the seller wishes to exchange. Quantity tracked in box tokens field `tokens(0)._2`.
- **Buying Token** (`R6._2`): Identified by token ID, the asset the seller receives in return. Delivered to payment boxes.

### Authentication
- No State NFT explicitly used; authentication via Sigma protocol signatures (seller PK, pool PK in R4)
- The contract itself serves as a **state machine** via the eUTXO model: outputs re-lock remaining balances in new boxes satisfying the same ErgoScript

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Order Pool Construction**:
   - Gather multiple UTXO instances of this contract from the blockchain (same `propositionBytes`)
   - Verify they share identical `R4`, `R5`, `R6`, `R8` values
   - Compute `maxDenom` as the maximum `R9` across inputs

2. **Rate Normalization**:
   - For each input box, compute normalized rate: `normalizedRate = rate × maxDenom / denom`
   - Calculate `maxSellRate` as the highest normalized rate
   - Generate output boxes with `R7` and `R9` adjusted so all outputs have the same effective rate

3. **Swap Execution**:
   - Determine total selling tokens available after satisfying all output orders
   - Source buying tokens (may come from external liquidity provider or aggregated from other swap orders)
   - Construct payment box(es) with:
     - Correct buying token amounts
     - Script bytes = `R8` (seller's multisig address from input)
     - Same `R4` (seller/pool PKs) and `R5` (unlock height) for future authorization flexibility
   
4. **