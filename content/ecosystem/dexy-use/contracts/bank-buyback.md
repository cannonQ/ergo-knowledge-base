---
title: kushti/dexy-stable — buyback.es
description: "ErgoScript contract analysis: contracts/bank/buyback.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/buyback.es
project: dexy-use
---
# ErgoScript Contract Analysis: GORT Buyback

## Purpose

This contract implements a **buyback mechanism** for GORT (Gold Oracle Reward Token) within the Dexy ecosystem. It performs three core functions: (1) swapping ERG for GORT tokens via an ERG/GORT liquidity pool, (2) accepting top-ups of ERG value while preserving contract state, and (3) returning accumulated GORT tokens back to the oracle pool as rewards.

## Inputs / Outputs

### Buyback Action (action == 0)
**Inputs:**
- `INPUTS(0)`: LP pool box (contains ERG/GORT liquidity pool NFT)
- `INPUTS(1)`: Self (BuyBack contract box)

**Outputs:**
- `OUTPUTS(0)`: LP pool output (receives ERG from swap)
- `OUTPUTS(1)`: Self output (BuyBack box with increased GORT balance)
- `OUTPUTS(2+)`: Fee and change boxes (must contain no tokens)

### Top-Up Action (action == 1)
**Inputs:**
- `INPUTS(0)`: Mint action box
- `INPUTS(1)`: Bank box
- `INPUTS(2)`: Self (BuyBack contract box)

**Outputs:**
- `OUTPUTS(2)`: Self output (increased ERG value, tokens unchanged)

### Give-Back Action (action == 2)
**Inputs:**
- `INPUTS(0)`: Oracle Pool box
- `INPUTS(1)`: Refresh box
- `INPUTS(2)`: Self (BuyBack contract box)
- Additional data inputs: Oracle data point boxes (filtered by `isValidDataPoint`)

**Outputs:**
- `OUTPUTS(0)`: Oracle Pool output (receives GORT tokens)
- `OUTPUTS(2)`: Self output (GORT balance reduced, preserving minimal state)

## Key Logic

### Action Routing
The contract reads a **Context extension variable** (`getVar[Int](0)`) to determine execution path: buyback (0), top-up (1), or give-back (2).

### Buyback (action == 0)
1. **Pool validation**: Verifies first input holds the correct LP NFT (`$gortLpNFT`)
2. **Token containment**: Ensures GORT tokens only appear in the LP and BuyBack outputs (no tokens in fee/change)
3. **Self-preservation**: Validates output box maintains:
   - Same BuyBack NFT and GORT token IDs
   - Identical proposition (smart contract ErgoTree)
   - R4 register pointing to its own box ID (singleton pattern)
4. **Slippage protection**: Calculates maximum ERG delta at 5% slippage tolerance:
   ```
   maxErgDelta = (ERG_price × GORT_obtained × 105) / 100
   ergDelta ≤ maxErgDelta
   ```
5. **Pool consistency**: Confirms pool output receives exactly the ERG delta from this box

### Top-Up (action == 1)
1. Validates tokens remain unchanged (`selfOut.tokens == SELF.tokens`)
2. Confirms proposition and R4 register are preserved (State machine invariant)
3. Enforces value increase (`SELF.value < selfOut.value`)

### Give-Back (action == 2)
1. **Oracle pool validation**: Checks first input holds oracle pool NFT (`$oracleNFT`)
2. **Data point filtering**: Collects valid oracle data points from inputs using three criteria:
   - Timestamp within `$epochLength` blocks of current height
   - Contains oracle token ID (`$oracleTokenId`)
   - Matches pool's oracle ID in R5
3. **Reward calculation**: Computes `rewardEmitted = dataPoints.size × 2`
4. **Token transfer verification**: Ensures oracle pool output receives at least:
   ```
   poolIn.GORT_amount + selfGort - rewardEmitted
   ```
   (where `selfGort = SELF.GORT_amount - 1`, preserving 1 GORT minimum)
5. **Self-preservation**: Validates R4, proposition, and ERG value unchanged

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **Self-reference ID** – stores this box's own transaction ID, enforcing singleton pattern and preventing script abuse via box copying |

No other registers (R5–R9) are written by this contract; they are only *read* from input boxes during oracle data point validation.

## Tokens

### Primary Tokens
1. **BuyBack NFT** (`SELF.tokens(0)._1`)
   - **Role**: Singleton authenticator; ensures only one active BuyBack box exists
   - **Rule**: Token ID constraint enforced by NFT ownership in R4 self-reference

2. **GORT Token** (`$gortId`)
   - **Role**: State variable storing accumulated GORT balance
   - **Quantity tracking**: Monitored across all three actions to prevent loss

### Supporting Token References (as Base64 constants)
- **`$gortLpNFT`**: LP pool NFT ID (validated in buyback action)
- **`$oracleTokenId`**: Oracle participant tokens (validated in data point filtering)
- **`$oracleNFT`**: Oracle pool singleton NFT (validated in give-back action)

## Integration Pattern

### Off-Chain Bot Requirements

1. **Action Selection**:
   - Construct transaction with `Context extension` variable: `getVar[Int](0) = {0, 1, or 2}`

2. **Buyback Flow**:
   - Fetch current LP pool box and GORT exchange rate
   - Calculate swap amount with slippage tolerance
   - Construct inputs: `[LP_box, BuyBack_box]`
   - Build outputs: `[LP_output, BuyBack_output, fee_outputs]`
   - Ensure BuyBack output maintains R4 self-reference and proposition

3. **Top-Up Flow**:
   - Acquire ERG from mint action or bank
   - Construct inputs: `[mint_action, bank, BuyBack