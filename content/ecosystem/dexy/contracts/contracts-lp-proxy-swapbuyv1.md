---
title: kushti/dexy-stable — SwapBuyV1.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapBuyV1.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapBuyV1.es
project: kushti-dexy-stable
---
# SwapBuyV1 Contract Analysis

## Purpose

This contract validates user-initiated Token → ERG swaps in a Constant Function Market Maker (CFMM) n2t (native token to ERG) liquidity pool. It ensures the swap price is fair according to the pool's reserves and applies appropriate DEX fees before releasing the user's quote amount (ERG).

## Inputs / Outputs

### Inputs
- **INPUTS(0)** – Pool Box: Contains the CFMM pool state with:
  - Token(0): Pool NFT (singleton identifier)
  - Token(1): Base token reserve (the token being sold by user)
  - Token(2): Quote token reserve (Y asset)
  - Value: ERG reserve (X asset, in nanoErgs)
  
- **SELF** – User's Swap Request Box: Contains:
  - tokens(0)._2: Base amount (quantity of tokens user is selling)
  - value: User's ERG balance before swap execution
  
- **INPUTS(1+)** – Additional inputs required (total ≥ 3 inputs)

### Outputs
- **OUTPUTS(2)** – Reward Box: Receives the user's quote amount (ERGs received minus execution fees)
  - value: `deltaNErgs` (net ERG output to user)

---

## Key Logic

The contract validates a fair swap by:

1. **Pool Verification:**
   - Confirms INPUTS(0) contains exactly 3 tokens (NFT + reserves)
   - Verifies the pool NFT matches the hardcoded `$lpNFT` constant

2. **Fee Deduction & Quote Calculation:**
   - Computes `deltaNErgs` as the difference between reward box ERG value and SELF's original ERG value
   - Back-calculates `quoteAmount` using the formula:
     ```
     quoteAmount = deltaNErgs × DexFeePerTokenDenom / (DexFeePerTokenDenom - DexFeePerTokenNum)
     ```
   - This reverses the DEX fee (5‱ = 5/1000) applied during swap execution

3. **Price Fairness (Constant Product Rule):**
   - Ensures the swap follows the automated market maker invariant:
     ```
     poolReservesX × baseAmount × (FeeDenom - FeeNum) 
     ≤ relaxedOutput × (poolReservesY × FeeDenom + baseAmount × (FeeDenom - FeeNum))
     ```
   - `relaxedOutput = quoteAmount + 1` accounts for rounding loss
   - The 0.3% fee (FeeNum = 997/1000) is baked into the calculation

4. **Minimum Output Validation:**
   - Requires `quoteAmount >= MinQuoteAmount` (100 nanoErgs minimum to prevent dust)

5. **Conditions for Validity:**
   - All three conditions must be true: valid pool NFT, fair price, minimum amount
   - Contract returns `sigmaProp(validTrade)` – a **zero-knowledge proof obligation** that is either satisfied if `validTrade == true`, or returns false

---

## Registers Used

**None.** This contract does not read or write R4–R9 context registers. All state is embedded in:
- Box values (nanoERGs)
- Native tokens and their quantities
- Hardcoded constants (fees, thresholds)

---

## Tokens

| Token Role | Position | Purpose |
|-----------|----------|---------|
| **Pool NFT** | poolIn.tokens(0) | Singleton identifier for the specific CFMM pool; verified against `$lpNFT` constant |
| **Base Token** | SELF.tokens(0) | The token the user is selling (quantity tracked in `._2`) |
| **Quote Token** | poolIn.tokens(2) | The token held as Y reserve in the pool (updated via pool output) |
| **ERG** | poolIn.value | Native currency; serves as X reserve in n2t pool |

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Construct Swap Transaction:**
   - **INPUTS(0):** Fetch the current pool UTXO (identified by NFT)
   - **INPUTS(1+):** Include user's payment inputs (≥ 3 total inputs required)
   - **SELF:** The swap request box with base tokens and initial ERG value

2. **Calculate Quote Amount:**
   - Query pool reserves (X, Y)
   - Compute fair quote using CFMM formula: `y = (x × baseAmount × 997) / (poolX × 1000 + baseAmount × 997)`
   - Apply DEX fee reversal if needed

3. **Construct Outputs:**
   - Output 0: Updated pool box (new reserves)
   - Output 1: User's change
   - Output 2: Reward box with calculated ERG amount
   - Optional: Miner fee box

4. **Verify Constants:**
   - Substitute actual LP NFT ID for `$lpNFT` placeholder during script compilation (constant segregation)

5. **Sign Transaction:**
   - No explicit user signature check in this contract (commented out: `// && rewardBox.propositionBytes == Pk.propBytes`)
   - Likely uses **data inputs** or **context extension** for signature verification in composite transaction

---

## Related Contracts

### Likely Composition with:

1. **Pool Contract** (INPUTS(0))
   - Validates that pool reserves are updated consistently
   - Enforces that the pool NFT is preserved in outputs

2. **Swap Sell Contract** (SwapSellV1 counterpart)
   - Mirrors this contract for ERG → Token swaps
   - Uses symmetric CFMM pricing logic

3. **Multi-Stage Swap Composition:**
   - This contract may be part of a **multi-stage dApp** where:
     - User submits swap request via this contract (SwapBuyV1)
     - Off-chain bot constructs the full transaction
     - Pool contract atomically updates reserves
   - Follows Ergo's **eUTXO model** with **atomic swaps** pattern

4. **Potential Fee Collector Contract**