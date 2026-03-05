---
title: duckpools/lend-protocol-contracts — asset_sharing.md
description: "ErgoScript contract analysis: contracts/treasury-system/voting/spending_presets/asset_sharing.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/treasury-system/voting/spending_presets/asset_sharing.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Asset Sharing (Treasury Voting)

## Purpose

This contract manages a dual-phase treasury asset distribution mechanism within the duckpools lending protocol. It enables token exchanges before a governance cutoff block and transitions to proportional withdrawal logic afterward, allowing stakeholders to claim treasury assets based on receipt token redemption.

## Inputs / Outputs

### Inputs
- **SELF (Input Box 0):** The treasury state box containing:
  - Native ERG value (`iValue`)
  - Receipt tokens (NFT/token ID with quantity)
  - QUACK tokens (protocol token with quantity)
  - Additional protocol tokens (sliced from index 2+)
  - Script locked under this ErgoScript

### Outputs
- **OUTPUTS(0) (Successor Box):** The updated treasury state box with:
  - Potentially modified ERG value (`fValue`)
  - Updated Receipt token quantity (`fReceiptTokens._2`)
  - Updated QUACK token quantity (`fQuacks._2`)
  - Proportionally adjusted protocol token quantities
  - Same script (`fScript == iScript`)

## Key Logic

### Phase 1: Exchange Period (HEIGHT < emissionBlock 1272551)
The contract validates **1:1 token swaps**:
- `deltaQuacks == -1 * deltaReceiptTokens` — QUACK tokens burned must equal Receipt tokens minted
- `deltaQuacks > 0` — Net flow must increase QUACK supply
- All other state preserved: script, ERG value, auxiliary tokens, token IDs

### Phase 2: Withdrawal Period (HEIGHT ≥ emissionBlock)
The contract enforces **proportional treasury withdrawal**:
1. **Calculate user share:**
   - `circulatingReceipts = MaxReceiptTokens - iReceiptTokens._2` (total minted, not in treasury)
   - `userShare = (deltaReceiptTokens / circulatingReceipts) × precision` (share as basis points)
2. **Validate ERG withdrawal:**
   - `fValue ≥ iValue - (userShare × iValue) / precision`
   - User receives at least their pro-rata share of ERG
3. **Validate token proportions:**
   - All token quantities (except Receipt tokens) are reduced by `userShare` percentage
   - Minimum token dust: 1 unit (prevents rounding to zero)
4. **Preserve invariants:** Script, Receipt token ID, token count remain unchanged

### Fallback Authorization
- Emergency override: `PK("") && HEIGHT > (emissionBlock + blocksInThreeMonths)` (empty public key—disabled, requires future activation)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **propositionBytes** | `Coll[Byte]` | Stores ErgoTree script; validated for immutability across phases |
| **value** | `Long` | ERG balance; protected in Phase 1, reduced proportionally in Phase 2 |
| **tokens** | `Coll[(Coll[Byte], Long)]` | Token array: `[Receipt, QUACK, ...otherTokens]`; IDs immutable, quantities phase-dependent |

## Tokens

### Receipt Tokens (Index 0)
- **Type:** Singleton state token (NFT-like)
- **Purpose:** Governance proof-of-stake; burned in Phase 1, redeemed in Phase 2
- **Invariant:** Token ID (`iReceiptTokens._1`) never changes; quantity increases Phase 1, decreases Phase 2

### QUACK Tokens (Index 1)
- **Type:** Native fungible token
- **Purpose:** Protocol utility token; minted via Receipt exchange, held in treasury
- **Max Supply:** Implicit (controlled by Phase 1 exchange rate)
- **Phase 1 Role:** Accepts QUACK inflows when Receipt tokens are minted

### Auxiliary Tokens (Index 2+)
- **Purpose:** Protocol reserve assets (e.g., stablecoins, collateral)
- **Behavior:** 
  - Phase 1: Locked (cannot change)
  - Phase 2: Distributed proportionally to redeemers

## Integration Pattern

### Off-Chain Construction Requirements

1. **Phase 1 Exchange (HEIGHT < 1272551):**
   ```
   Transaction {
     inputs: [treasuryBox]
     outputs: [
       {
         value: treasuryBox.value
         tokens: [
           (receiptTokenId, treasuryBox.tokens(0)._2 + X),    // Mint receipts
           (quackTokenId, treasuryBox.tokens(1)._2 - X),      // Burn QUACK
           ...otherTokens unchanged
         ]
         script: treasuryBox.script
       }
     ]
   }
   ```
   - Off-chain bot validates `isValidExchange` before submission

2. **Phase 2 Withdrawal (HEIGHT ≥ 1272551):**
   ```
   Transaction {
     inputs: [treasuryBox]
     outputs: [
       {
         value: treasuryBox.value - (userShare × treasuryBox.value) / precision
         tokens: [
           (receiptTokenId, treasuryBox.tokens(0)._2 + X),    // Burn receipts
           (quackTokenId, adjusted_quantity),
           (otherTokenId1, adjusted_quantity),
           ...
         ]
         script: treasuryBox.script
       },
       userBox {
         value: userShare × treasuryBox.value / precision
         tokens: [
           (otherTokenId1, userShare × quantity / precision),
           ...
         ]
       }
     ]
   }
   ```
   - Off-chain calculates exact proportions, respecting minimum dust (1 unit)
   - Verifies `isValidValue` and `isValidTokens` conditions

### Context Requirements
- **HEIGHT:** Must be accessible; determines phase logic
- **Self Reference:** SELF box must be at input index 0
- **Successor Box:** Output index 0 must be successor state

## Related Contracts

Based on naming conventions:

1. **`treasury-system/` parent contracts:** Likely a master Treasury Manager that creates/initializes this