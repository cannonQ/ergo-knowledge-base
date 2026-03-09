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
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `buyback.es`

## Purpose

This contract implements a **GORT (Gold Oracle Reward Token) buyback mechanism** for the Dexy protocol. It performs three distinct operations: (1) swaps ERGs for GORT tokens via an ERG/GORT liquidity pool, (2) accepts ERG top-ups to increase buyback capacity, and (3) returns accumulated GORT tokens back to the oracle pool as rewards.

## Inputs / Outputs

### Swap Action (action == 0)
**Inputs:**
- `INPUTS(0)` — LP pool Box containing ERG/GORT liquidity (identified by LP NFT token)
- `INPUTS(1)` — Buyback Box (SELF) holding buyback NFT and GORT tokens

**Outputs:**
- `OUTPUTS(0)` — Updated LP pool Box (receives ERGs, emits GORT)
- `OUTPUTS(1)` — Updated Buyback Box (holds NFT + increased GORT balance)
- `OUTPUTS(2+)` — Fee and change boxes (must be token-free)

### Top-Up Action (action == 1)
**Inputs:**
- `INPUTS(0)` — Mint action Box
- `INPUTS(1)` — Bank Box
- `INPUTS(2)` — Buyback Box (SELF)

**Outputs:**
- `OUTPUTS(0)` — Mint action Box (passthrough)
- `OUTPUTS(1)` — Bank Box (passthrough)
- `OUTPUTS(2)` — Updated Buyback Box (same tokens, increased ERG value)

### Return Action (action == 2)
**Inputs:**
- `INPUTS(0)` — Oracle Pool Box
- `INPUTS(1)` — Refresh Box
- `INPUTS(2)` — Buyback Box (SELF)
- Additional data inputs — Oracle data points (filtered by `isValidDataPoint`)

**Outputs:**
- `OUTPUTS(0)` — Updated Oracle Pool Box (receives GORT tokens)
- `OUTPUTS(1)` — Refresh Box (passthrough)
- `OUTPUTS(2)` — Updated Buyback Box (same structure, one GORT token reserved)

## Key Logic

### Swap Validation (action == 0)
1. **LP Pool Verification:** Confirms `INPUTS(0)` is the authentic ERG/GORT pool by validating its NFT token ID against the constant `$gortLpNFT`.
2. **Token Containment:** Ensures tokens (GORT) appear **only** in the LP pool output and Buyback output; all other outputs must be token-free (preventing token loss).
3. **Self Output Correctness:** Validates that `OUTPUTS(1)` (updated Buyback) maintains the buyback NFT and holds a GORT token (same ID).
4. **Slippage Protection:** Calculates max allowed ERG spend as `(price × gortObtained × 105) / 100` (5% slippage tolerance), then verifies actual ERG delta (`ergDelta`) does not exceed this.
5. **Pool Invariant:** Confirms pool receives exactly the ERGs deducted from Buyback (`poolOutput.value - poolInput.value == ergDelta`).

### Top-Up Validation (action == 1)
1. **Token Preservation:** Checks that `OUTPUTS(2)` (new Buyback state) holds identical tokens to SELF.
2. **Script Preservation:** Confirms the contract's `propositionBytes` are unchanged (same ErgoTree).
3. **Value Increase:** Ensures `selfOut.value > SELF.value` (ERGs are added, never removed).

### Return Validation (action == 2)
1. **Oracle Data Validation:** Filters input boxes using `isValidDataPoint`:
   - Creation height ≥ `HEIGHT - $epochLength` (recent data only)
   - Holds oracle token with ID `$oracleTokenId`
   - Same epoch ID (`R5`) as the oracle pool
2. **Reward Emission:** Calculates reward as `dataPoints.size × 2` (2 nanoERGs per oracle submission).
3. **Proper Giving:** Validates that the Oracle Pool output receives `selfGort - rewardEmitted` additional GORT tokens (where `selfGort = SELF.tokens(1)._2 - 1`, reserving 1 GORT in Buyback).
4. **Giveback Invariant:** Confirms Buyback output preserves tokens, script, and ERG value (immutable except token count).

## Registers Used

**None.** This contract uses **Context extension variables only**:
- `getVar[Int](0)` — Action discriminator (0=swap, 1=topup, 2=return)

The contract relies entirely on box tokens and ERG values; no R4–R9 data is read or written.

## Tokens

### Buyback NFT
- **Role:** Singleton / State NFT identifying the Buyback contract box.
- **Usage:** Ensures only the authentic Buyback box is operated; must persist in all outputs.
- **ID:** Resolved as `SELF.tokens(0)._1`.

### GORT Token
- **Role:** Native token representing Gold Oracle Reward Token.
- **ID:** Constant `$gortId` (base64-encoded in contract).
- **Quantities:**
  - Swap: Increases in Buyback output (amount obtained from LP).
  - Top-up: Preserved as-is.
  - Return: Decreased by amount given to Oracle Pool (minus emissions cost).
  - Invariant: At least 1 GORT must remain in Buyback at all times (post-return).

### LP NFT
- **Role:** Identifies the ERG/GORT liquidity pool.
- **ID:** Constant `$gortLpNFT` (base64-encoded).
- **Usage:** Validates that `INPUTS(0)` is the correct pool for swap operations.

### Oracle Token & Oracle NFT
- **Oracle Token ID:** `$oracleTokenId` — identifies valid oracle data points in return action.
- **Oracle NFT:** `$oracleNFT`