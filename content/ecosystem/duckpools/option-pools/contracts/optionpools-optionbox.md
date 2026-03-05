---
title: duckpools/off-chain-bot — optionBox.md
description: "ErgoScript contract analysis: optionPools/contracts/optionBox.md"
tags: [duckpools, off-chain-bot, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/off-chain-bot"
contract_file: optionPools/contracts/optionBox.md
project: duckpools-off-chain-bot
---
# ErgoScript Contract Analysis: optionBox

## Purpose

This contract implements a **European-style options box** in a decentralized options pool protocol. It manages the lifecycle of an option from creation through exercise or expiry, allowing the option holder to exercise their right to buy an underlying asset at a predetermined strike price within a specified time window, or forfeit the option after expiry.

## Inputs / Outputs

### Inputs
- **SELF**: The option box being spent, containing:
  - Native ERG value
  - Option token (identifying this specific option)
  - Register data (strike price, expiry, user public key)

- **INPUTS(0)**: Pool state box (before expiry only)
  - Must hold the `poolNFT` (State NFT) in token position 0
  - Must hold a counter token in position 3 (tracks options issued)

### Outputs

**Before Expiry (isBeforeExpiry)**
- OUTPUTS(0): Updated pool state box with incremented option counter

**During Exercise Window (isExercisable)**
- OUTPUTS(0): Repayment box sent to `repaymentAddress`
  - Contains option token and exercise amount in Y-asset (underlying)
  - Encodes original option box ID in R4
  - Must hold minimum 2× `minTxFee` in ERG

**After Expiry (isUnExercised)**
- OUTPUTS(0): Forfeit box sent to `repaymentAddress`
  - Returns option token to pool
  - Encodes original option box ID in R4

## Key Logic

The contract enforces three mutually exclusive state transitions based on **block height (HEIGHT)**:

### 1. **Before Expiry** (`HEIGHT < t`)
- Requires the option holder's Sigma protocol signature (`proveDlog(userPK)`)
- Validates transaction interacts with the pool state box (poolNFT present)
- Increments the pool's option counter token
- **Purpose**: Allows liquidity pool rebalancing before options expire

### 2. **During Exercise Window** (`t ≤ HEIGHT ≤ t + optionExerciseRange`)
- Requires holder's signature AND validates exercise settlement:
  - Option token must be sent to repayment box
  - **Y-asset amount check** (buggy): Attempts to verify holder provides strike-priced amount:
    ```
    optionSize * strikePrice / optionUnitSize
    ```
  - Repayment box must be locked to `repaymentAddress`
  - Min 2× tx fee retained in repayment box
  - Original option box ID stored in R4 for auditability

### 3. **After Expiry** (`HEIGHT > t + optionExerciseRange`)
- No signature required (anyone can finalize)
- Option token returned to pool via repayment box
- Pool collects the forfeited ERG value minus `minTxFee`

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | **Strike Price (K)** — the fixed price at which the option holder can exercise |
| **R5** | `Long` | **Expiry Block (t)** — the block height at which the option expires |
| **R6** | `GroupElement` | **User Public Key (userPK)** — Sigma protocol public key of the option holder |

## Tokens

| Token | Position | Purpose |
|-------|----------|---------|
| **poolNFT** | INPUTS(0)[0] | State NFT identifying the liquidity pool; ensures transaction only valid against authorized pool |
| **optionYAsset** | Repayment[1] | The underlying asset (e.g., stablecoin) paid by option holder upon exercise |
| **Option Token** | SELF[0] | Singleton token proving this is the authoritative option box; burned/transferred on settlement |
| **Counter Token** | INPUTS(0)[3] | Pool-side tracking of issued options; incremented before expiry to maintain invariant |

## Integration Pattern

The **off-chain bot** must:

### 1. **Pool State Management**
   - Track all active option boxes by their unique token ID
   - Maintain the counter token in INPUTS(0) to validate issuance
   - Ensure poolNFT is present in the pool state box

### 2. **Transaction Construction**

   **Before Expiry**: Increment counter
   ```
   Spend: optionBox + poolStateBox
   Output: Updated poolStateBox with counter + 1
   Sign: optionBox.userPK
   ```

   **During Exercise**: Settle strike price
   ```
   Spend: optionBox + (reserve box with Y-asset)
   Output: Repayment box → repaymentAddress with:
           - option token
           - Y-asset ≥ optionSize × strikePrice / optionUnitSize
           - ERG ≥ 2 × minTxFee
           - R4 = optionBox.id
   Sign: optionBox.userPK
   ```

   **After Expiry**: Forfeit collection
   ```
   Spend: optionBox
   Output: Repayment box → repaymentAddress with:
           - option token
           - ERG ≥ optionBox.value - minTxFee
           - R4 = optionBox.id
   Sign: (anyone — no signature required)
   ```

### 3. **Off-Chain Verification**
   - Validate HEIGHT against R5 (expiry block) to determine which branch executes
   - For exercise: compute required Y-asset amount from R4 (strike price)
   - Verify repaymentAddress matches the hardcoded constant
   - Check that option token in OUTPUTS(0) matches SELF.tokens(0)

## Related Contracts

- **Pool State Contract** (referenced as poolNFT holder): Manages aggregate liquidity, counter tokens, and premium collection. Appears to be a Multi-stage contract with its own state machine.
- **Repayment Contract** (at `repaymentAddress`): Likely handles settlement logic, asset redistribution, and fee accrual on the pool side. Not shown but receives all settled option boxes.

---

## ⚠️ Potential Issues