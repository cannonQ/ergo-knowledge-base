---
title: duckpools/off-chain-bot — repayment.md
description: "ErgoScript contract analysis: optionPools/contracts/repayment.md"
tags: [duckpools, off-chain-bot, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/off-chain-bot"
contract_file: optionPools/contracts/repayment.md
project: duckpools-off-chain-bot
---
# ErgoScript Contract Analysis: Repayment Pool

## Purpose

This contract validates the repayment or settlement of an option pool by ensuring that when a user repays into the pool (via `SELF`), the pool state box is correctly updated with the repaid assets and option tokens are properly minted/burned. It prevents double-spending and enforces atomic state transitions.

## Inputs / Outputs

**Inputs:**
- `INPUTS(0)`: The **pool state box** (identified by `PoolNft` token) — contains pool reserves and current option token supply
- `INPUTS(1)`: The **repayment box** (`SELF`) — holds the user's repayment value and optional asset tokens to be deposited
- Optionally other inputs for fees or signatures

**Outputs:**
- `OUTPUTS(0)`: The **updated pool state box** — must retain `PoolNft`, have increased asset reserves, and updated option token quantity

## Key Logic

| Condition | Purpose |
|-----------|---------|
| `validInitialPool && validFinalPool` | Ensures both input and output pool boxes carry the `PoolNft` singleton token, preserving identity across the state transition |
| `isOptionTokensIncreasing` | Validates that option tokens minted/burned are incremented by exactly 1 (at `tokens(3)` position), indicating a single option settlement |
| `validValue` | Confirms the value delta (ERG increase in pool) is at least `SELF.value - transactionFee`, ensuring user's repayment is credited minus network fees |
| `isAssetYValid` | If repayment includes optional asset tokens (`tokens(1)`), verifies they are correctly added to the pool's asset Y reserve (`tokens(2)`) |
| `multiBoxSpendSafety` | Enforces that `SELF == INPUTS(1)`, preventing the same box from being spent twice in different transaction contexts (reentrancy guard) |

## Registers Used

**None explicitly.** This contract operates entirely via:
- **Box value** (native ERG)
- **Box tokens** array (native tokens and NFTs)
- **Context variables** (`INPUTS`, `OUTPUTS`, `SELF`)

No R4–R9 registers are read or written, indicating stateless validation.

## Tokens

| Token Position | Role | Details |
|---|---|---|
| `tokens(0)` | **Pool NFT (PoolNft)** | Singleton/State NFT identifying the pool box; must be present in both input and output to ensure the same pool is being updated |
| `tokens(1)` | **Optional Asset Y** | User-supplied repayment asset; only validated if present in `SELF` |
| `tokens(2)` | **Pool Asset Y Reserve** | Running total of asset Y in the pool; incremented by `SELF.tokens(1)._2` if provided |
| `tokens(3)` | **Option Tokens** | Minted/burned to reflect state change; exactly +1 expected per repayment |

## Integration Pattern

**Off-chain bot must:**

1. **Identify pool and user state:**
   - Fetch the pool box carrying `PoolNft`
   - Identify the user's repayment box with value and optional asset tokens

2. **Construct transaction:**
   - Place pool box as `INPUTS(0)`
   - Place repayment box as `INPUTS(1)` (enforced by `multiBoxSpendSafety`)
   - Compute new pool reserves: `initalPool.value + SELF.value - transactionFee` and `initalPool.tokens(2) + SELF.tokens(1)._2`
   - Increment option token quantity by 1
   - Create updated pool box as `OUTPUTS(0)` with `PoolNft` and new reserves

3. **Fee handling:**
   - Account for `transactionFee = 1000000L` (1 ERG) in value delta validation
   - Ensure sufficient ERG remains for storage rent and minimum box value

4. **Sigma proof:**
   - Include witness signatures satisfying the validator's `sigmaProp`

## Related Contracts

**Inferred dependencies (from context `optionPools/contracts/repayment.md`):**
- **Pool initialization contract** — likely creates the box with `PoolNft` and initial reserves
- **Option minting/burning contracts** — interact with `tokens(3)` to adjust supply
- **Asset deposit/withdrawal contracts** — manage `tokens(2)` (asset Y) reserve
- **Liquidation or settlement contracts** — complementary off-chain settlement logic

## Security Notes

- ✅ **Singleton pattern enforced:** `PoolNft` ensures only one canonical pool state
- ✅ **Multi-box spend safety:** `INPUTS(1) == SELF` prevents same-input reuse
- ⚠️ **No access control register:** Contract does not verify who authorized the repayment (likely delegated to witness signatures in transaction proof)
- ⚠️ **Fixed token positions:** Assumes `tokens(0)`, `tokens(1)`, `tokens(2)`, `tokens(3)` are always present in expected order—brittle if pool token structure varies