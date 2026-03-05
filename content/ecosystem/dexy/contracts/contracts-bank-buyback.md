---
title: kushti/dexy-stable — buyback.es
description: "ErgoScript contract analysis: contracts/bank/buyback.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/buyback.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `buyback.es`

## Purpose

This contract manages a GORT (Gold Oracle Reward Token) buyback mechanism that accepts ERG deposits, executes swaps via an ERG/GORT Liquidity Pool to acquire GORT tokens, and distributes GORT back to the Oracle Pool. It operates as a state machine with three distinct actions: swap, top-up, and return.

## Inputs / Outputs

### Swap Action (action == 0)
| Position | Input | Output | Purpose |
|----------|-------|--------|---------|
| 0 | ERG/GORT LP Box | LP Box (updated) | Provides liquidity and price oracle for swap execution |
| 1 | BuyBack Box (SELF) | BuyBack Box | Executes swap; receives GORT from LP |
| 2+ | — | Fee/change outputs | Transaction fees and ERG change |

### Top-up Action (action == 1)
| Position | Input | Output | Purpose |
|----------|-------|--------|---------|
| 0 | Mint action Box | Mint action Box | Triggers minting if needed |
| 1 | Bank Box | Bank Box | Provides initial funds or context |
| 2 | BuyBack Box (SELF) | BuyBack Box | Receives additional ERG deposit |

### Return Action (action == 2)
| Position | Input | Output | Data-Input | Purpose |
|----------|-------|--------|-----------|---------|
| 0 | Oracle Pool Box | Oracle Pool Box (updated) | — | Receives GORT tokens; state updated with rewards |
| 1 | Refresh Box | Refresh Box | — | Manages refresh/reward logic |
| 2 | BuyBack Box (SELF) | BuyBack Box | — | Sends GORT to Oracle Pool |
| 2+ | Data inputs | — | Oracle data points | Validates reward distribution |

## Key Logic

### Action Dispatch
The contract reads `Context extension` variable at index 0 (`getVar[Int](0)`) to determine which of three actions to execute: swap (0), top-up (1), or return (2).

### Swap Action (action == 0)
1. **LP Validation**: First input must be the ERG/GORT LP pool, verified by comparing its first token (LP NFT) to the constant `$gortLpNFT`.
2. **Token Conservation**: All outputs after position 1 (fee/change outputs) must have zero tokens—ensuring GORT only appears in LP and BuyBack outputs.
3. **BuyBack Invariant**: Output at position 1 must preserve the BuyBack NFT (token 0) and contain GORT tokens (token 1).
4. **Price & Slippage**: 
   - Calculate fair price: `price = poolInput.value / poolInput.tokens(2)._2` (ERG per unit of third token, likely LP tokens).
   - Calculate GORT acquired: `gortObtained = SELF.tokens(1)._2 - selfOut.tokens(1)._2`.
   - Enforce max slippage of 5%: `ergDelta <= price * gortObtained / 100 * 105`.
   - Verify LP absorbs exact ERG delta: `poolOutput.value == poolInput.value + ergDelta`.

### Top-up Action (action == 1)
1. Output at position 2 must preserve all tokens and proposition bytes (contract code).
2. BuyBack box value must strictly increase (`SELF.value < selfOut.value`).
3. Allows accumulation of ERG without executing swaps.

### Return Action (action == 2)
1. **Oracle Data Validation** (copied from Oracle Pool contract):
   - Filter data inputs to find valid oracle price points.
   - Each point must:
     - Have `R6[Long]` register defined (timestamp).
     - Be created within `$epochLength` blocks from current height.
     - Hold Oracle Token (verified by `$oracleTokenId`).
     - Match pool epoch (`R5[Int]`).
   - Calculate rewards emitted: `2 GORT per data point`.
2. **GORT Transfer**:
   - Deduct 1 GORT from BuyBack as permanent reserve: `selfGort = SELF.tokens(1)._2 - 1`.
   - Verify Oracle Pool receives: `GORT >= poolIn.tokens(1)._2 + selfGort - rewardEmitted`.
3. **BuyBack Invariant**:
   - Output at position 2 preserves BuyBack NFT, GORT token ID, and proposition bytes.
   - ERG value unchanged (`SELF.value == selfOut.value`).

## Registers Used

| Register | Type | Read/Write | Purpose |
|----------|------|-----------|---------|
| R5 | `Int` | Read | Pool epoch identifier (cross-validated with oracle data points in return action) |
| R6 | `Long` | Read | Oracle data point timestamp (validates freshness within `$epochLength`) |
| None in SELF | — | — | BuyBack contract does not use R4-R9; relies entirely on tokens and value |

Note: Registers are read from *input boxes* (LP, Oracle Pool, data points), not written by this contract.

## Tokens

### Token 0: BuyBack NFT
- **Purpose**: Singleton / State NFT for contract authentication and state continuity.
- **Action**: Present in all outputs; immutable across all three actions.
- **Used in**: Validates that the correct contract instance is executing.

### Token 1: GORT
- **Purpose**: Reward token; subject to swaps and distribution.
- **Action**: 
  - *Swap*: Increased via LP swap (token amount increases).
  - *Top-up*: Unchanged.
  - *Return*: Decreased; transferred to Oracle Pool with 1 token reserved.
- **Invariant**: Must always have at least 1 GORT in BuyBack box (seen in return action: `selfGort = ... - 1`).

### LP NFT Token (at pool input, position 0)
- **Purpose**: Identifies the ERG/GORT LP pool