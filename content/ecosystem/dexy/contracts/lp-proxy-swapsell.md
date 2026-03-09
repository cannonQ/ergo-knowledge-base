---
title: kushti/dexy-stable — SwapSell.es
description: "ErgoScript contract analysis: contracts/lp/proxy/SwapSell.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/SwapSell.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: SwapSell.es

## Purpose

This contract implements a **liquidity pool swap mechanism** that exchanges ERG (native currency) for tokens in a decentralized exchange (DEX) context within the Dexy protocol. It validates that a user's swap transaction receives fair pricing, correct fees are distributed, and the pool state remains consistent. The contract acts as a **proxy validator** ensuring atomic execution of the swap operation.

---

## Inputs / Outputs

### Expected Inputs
- **INPUTS(0)**: Pool box (eUTXO) containing:
  - Token 0: Pool NFT (State token / Singleton)
  - Token 2: Reserve of quote asset (the token being swapped out)
  - Native value: ERG reserves (base asset being swapped in)
- **INPUTS(1..n)**: Additional inputs (typically user input or action box)
- **SELF**: This proxy contract box (ephemeral)

### Expected Outputs
- **OUTPUTS(0)**: Updated pool box (maintained state)
- **OUTPUTS(1)**: Action box (state machine progression)
- **OUTPUTS(2)**: Reward/redemption box sent to redeemer with quote tokens
- **OUTPUTS(n)**: Miner fee box (to MinerPropBytes)

---

## Key Logic

The contract validates a **swap transaction** through five core conditions (all must be true):

1. **Structural Validity**
   - Transaction must have exactly **3 inputs** (`INPUTS.size == 3`)
   - Pool input must contain exactly **3 tokens** (NFT + 2 reserve tokens)

2. **Pool Authentication**
   - First token in pool input must match **PoolNFT** constant (State NFT verification)
   - Ensures the pool being swapped with is legitimate

3. **Quote Asset Verification**
   - Output box at index 2 (reward box) must contain token matching **QuoteId** constant
   - Quote amount must exceed **MinQuoteAmount** (slippage/minimum output protection)

4. **Fair Dex Fee Distribution**
   - Reward box native value ≥ (SELF.value − fee deduction − BaseAmount)
   - Fee deduction = `quoteAmount × DexFeePerTokenNum / DexFeePerTokenDenom`
   - Ensures protocol extracts correct swap fee (2/10 = 20% of quote asset per token)

5. **Fair Price Validation** (Constant Product Formula)
   ```
   poolReservesY × BaseAmount × FeeNum 
   ≤ relaxedOutput × (poolReservesX × FeeDenom + BaseAmount × FeeNum)
   ```
   - Enforces **AMM invariant**: `x × y = k` (adjusted for fees)
   - FeeNum = 996, FeeDenom = 1000 → 0.4% protocol fee on ERG input
   - `relaxedOutput = quoteAmount + 1` accounts for rounding errors
   - Prevents unfair pricing that extracts value from the pool

6. **Miner Fee Bound**
   - Sum of all outputs sent to **MinerPropBytes** ≤ **MaxMinerFee**
   - Prevents excessive network fee extraction

### Refund Path
- Transaction is valid if either:
  - `RefundProp` is satisfied (refund signature), OR
  - All `validTrade` conditions pass

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4–R9** | *Not explicitly used* | Contract logic relies entirely on UTXO context (boxes, tokens, values) |

**Note:** This contract uses **constant propagation** (compile-time constants: PoolNFT, QuoteId, RedeemerPropBytes, MinerPropBytes, MaxMinerFee) rather than register-based state. These are injected into the ErgoTree bytecode during compilation.

---

## Tokens

### Token 0: Pool NFT
- **Purpose**: State authentication & singleton enforcement
- **Rule**: Must match **PoolNFT** constant
- **Effect**: Only the designated pool can execute swaps with this proxy

### Token 2: Quote Asset (Variable)
- **Purpose**: The token being dispensed to the redeemer
- **Constraint**: Must match **QuoteId** constant
- **Amount**: Validated against MinQuoteAmount and fair pricing

### Miner Fee Distribution
- **Native tokens**: Only ERG (native currency) used; no auxiliary token fees

---

## Integration Pattern

### Off-Chain Bot / dApp Responsibility

1. **Transaction Construction**
   - Select pool box (INPUTS(0)) with valid PoolNFT
   - Create proxy input (SELF) with ERG amount to swap
   - Construct action box and reward box (OUTPUTS(1–2))
   - Attach miner fee output

2. **Fair Price Calculation**
   - Fetch current pool reserves (poolReservesX, poolReservesY)
   - Compute expected quote amount using constant product formula:
     ```
     quoteAmount = (BaseAmount × poolReservesY × FeeNum) 
                   / (poolReservesX × FeeDenom + BaseAmount × FeeNum)
     ```
   - Add slippage tolerance check against user parameters
   - Verify `quoteAmount ≥ MinQuoteAmount`

3. **Fee Calculation & Distribution**
   - DEX fee: `quoteAmount × 2 / 10`
   - Distribute to reward box
   - Calculate miner fee from network conditions
   - Ensure total ≤ MaxMinerFee

4. **Context Extension** (if needed for complex scenarios)
   - May provide external data if contract complexity expanded

5. **Proof Generation**
   - If `validTrade` fails, provide **RefundProp** signature
   - User can recover input ERG via refund path

### Verification Steps (On-Chain)
1. ErgoTree bytecode executes all conditions atomically
2. Pool NFT prevents pool substitution
3. AMM invariant prevents arbitrage/sandwich attacks
4. Miner fee bound prevents tx censoring

---

## Related Contracts

### **Likely Compositions**
- **Pool Contract** (reference: `INPUTS(