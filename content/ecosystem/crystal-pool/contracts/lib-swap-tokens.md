---
title: SavonarolaLabs/crystal-pool — swap-tokens.es
description: "ErgoScript contract analysis: src/lib/contracts/swap-tokens.es"
tags: [savonarolalabs, crystal-pool, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/SavonarolaLabs/crystal-pool"
contract_file: src/lib/contracts/swap-tokens.es
project: savonarolalabs-crystal-pool
---
# ErgoScript Contract Analysis: swap-tokens.es

## Purpose

This contract implements a **multi-order atomic token swap mechanism** where multiple sell orders can be aggregated and settled in a single transaction. It enforces fair-rate pricing across batched orders by normalizing exchange rates to a common denominator, and supports dual unlock conditions: after a deadline, only the seller can withdraw; before the deadline, the Pool operator can execute the swap if the buyer pays the fair aggregated rate.

## Inputs / Outputs

### Inputs
- **Legitimate swap order boxes**: Multiple eUTXOs matching this contract's ErgoTree, each containing:
  - Selling tokens (primary token in `tokens(0)`)
  - Seller and Pool SigmaProps in R4
  - Unlock height in R5
  - Token pair identifiers in R6
  - Exchange rate in R7
  - Denominator in R9
  
### Outputs
- **Updated swap order boxes**: Remaining sell orders (after partial fills) with identical contract logic and updated token amounts
- **Payment boxes**: Receiver boxes with the buyer token, locked to the seller's multisig address from R8, valid until unlock height

## Key Logic

1. **Order Legitimacy Filter** (`isLegitInput`):
   - Input box must have identical ErgoTree (same contract)
   - Same seller (R4 SigmaProp pair) and unlock height
   - Matching token pair (R6)
   - Contains the selling token with non-zero quantity
   - Rate > 0 and same multisig address (R8)

2. **Rate Normalization** (`maxDenom`, `getRateInMaxDenom`):
   - Finds maximum denominator across all inputs
   - Normalizes all rates to common denominator to prevent rounding arbitrage
   - Formula: `normalized_rate = rate × maxDenom / denom`

3. **Fair-Rate Enforcement** (`isPaidAtFairRate`):
   - Computes volume-weighted average rate: `(Σ sell_tokens × normalized_rate) / Σ sell_tokens`
   - Validates buyer payment meets fair rate: `maxDenom × tokens_paid / tokens_sold ≥ expected_rate`

4. **Dual Unlock Mechanism**:
   - **After unlock height** (`HEIGHT > unlockHeight(SELF)`): Seller can withdraw unilaterally
   - **Before unlock height**: Requires both:
     - Pool operator signature (R4 second element), OR
     - Fair-rate payment proof + Pool operator signature

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[SigmaProp]` | Seller public key (index 0) and Pool operator public key (index 1) for dual-sig conditions |
| **R5** | `Int` | Unlock height; after this block, seller can withdraw; before this, Pool must co-sign or buyer must pay fair rate |
| **R6** | `(Coll[Byte], Coll[Byte])` | Tuple of selling token ID and buying token ID (native token identifiers) |
| **R7** | `Long` | Exchange rate (selling tokens per unit of buying token × denominator) |
| **R8** | `Coll[Byte]` | Seller's multisig address; payment boxes must lock buyer tokens here |
| **R9** | `Long` | Rate denominator; used to normalize rates across orders with different precisions |

## Tokens

- **Selling token** (`tokens(0)` in legitimate inputs):
  - Native token ID stored in R6._1
  - Amount decreases as swap executes
  - Must be present and non-zero in all input boxes

- **Buying token** (in payment output boxes):
  - Native token ID stored in R6._2
  - Sent to seller's multisig address (R8)
  - Amount must satisfy fair-rate invariant relative to selling tokens spent

## Integration Pattern

### Off-Chain Construction Requirements

1. **Aggregation Phase**:
   - Collect multiple eUTXOs with identical seller (R4), unlock height (R5), and token pair (R6)
   - Extract rates (R7) and denominators (R9) from each box
   - Calculate `maxDenom = max(denom₁, denom₂, ...)`

2. **Rate Normalization**:
   - Normalize each rate: `norm_rate[i] = rate[i] × maxDenom / denom[i]`
   - Compute weighted average: `fair_rate = Σ(tokens[i] × norm_rate[i]) / Σ tokens[i]`

3. **Payment Calculation**:
   - Determine `tokens_sold = Σ input_tokens - Σ output_tokens`
   - Calculate minimum buyer payment: `min_payment = tokens_sold × fair_rate / maxDenom`
   - Construct payment output box with at least this many buying tokens

4. **Output Box Construction**:
   - Spend only swap-order inputs with `isLegitInput = true`
   - Remaining output swap-order boxes must satisfy `isLegitSellOrderOutput` (same contract, same seller, same unlock height, same token pair, `rate × maxDenom == denom × maxSellRate`)
   - Payment output locked to R8 address with buyer tokens

5. **Signature Requirements**:
   - **Before unlock height**: Require Pool operator signature (R4[1]) to authorize execution
   - **After unlock height**: Seller (R4[0]) can spend unilaterally

### Validation Context

- Contract verifies `isPaidAtFairRate` predicate within the script; off-chain bot must ensure payment boxes satisfy `isPaymentBox` filter
- No Context extension used; all data in registers and transaction structure

## Related Contracts

- **Pool/Oracle contract** (referenced as getPoolPk): Likely a separate contract managing the Pool operator's authorization and fee collection; the Pool's SigmaProp (R4[1]) gates pre-unlock swaps
- **Multisig contract** (R8 propositionBytes): Buyer's destination likely a M-of-N multisig; contract does not validate its internals, only that payment boxes lock to this address
- **Potential state machine**: