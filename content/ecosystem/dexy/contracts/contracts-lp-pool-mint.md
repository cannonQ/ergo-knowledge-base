---
title: kushti/dexy-stable — mint.es
description: "ErgoScript contract analysis: contracts/lp/pool/mint.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/mint.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: LP Mint (kushti/dexy-stable)

## Purpose

This contract validates **liquidity provider (LP) token minting** in an Automated Market Maker (AMM) pool, implementing the deposit action. It ensures that when liquidity is added to the pool, the newly minted LP tokens are issued fairly according to Uniswap V2 formulas, and the pool state transitions correctly while preserving the mint contract box itself.

## Inputs / Outputs

### Inputs
- **INPUTS(0)** — The pool box containing reserve balances and LP token supply
- **INPUTS(1..)** — User contribution box(es) with deposit assets (implicit, validated off-chain)
- **SELF** — The Mint subcontract box (passed in transaction)

### Outputs
- **OUTPUTS(0)** — Updated pool box with new reserve balances and reduced LP token quantity
- **OUTPUTS(1)** — Successor to SELF (the Mint contract box, must be preserved)
- **OUTPUTS(2..)** — User output box(es) receiving minted LP tokens (validated off-chain)

## Key Logic

The contract enforces five core invariants:

1. **LP Supply Tracking via Token Quantity**
   - Treats the LP token reserve (in the pool box) as a "burned" balance
   - Live supply = `initialLp - lpReservesIn._2` (constant `$initialLp` minus tokens held in reserve)

2. **Mint Amount Calculation**
   - `deltaSupplyLp = lpReservesIn._2 - lpReservesOut._2` (LP tokens withdrawn from reserve)
   - `deltaReservesX/Y` = changes in X and Y asset reserves

3. **Uniswap V2 Fair Pricing**
   - Minted shares must not exceed the minimum of:
     - `deltaReservesX × supplyLpIn / reservesXIn`
     - `deltaReservesY × supplyLpIn / reservesYIn`
   - Ensures proportional liquidity contributions; prevents arbitrage or sandwiching

4. **Positive Deltas**
   - All deltas (`deltaSupplyLp`, `deltaReservesX`, `deltaReservesY`) must be strictly positive
   - Prevents withdrawal-disguised-as-deposit or zero-value transactions

5. **Contract Box Preservation**
   - The successor box must have:
     - Same `propositionBytes` (ErgoTree unchanged)
     - Value ≥ original value (no erosion of minimum box value)
     - Identical tokens (NFT and any held reserves preserved)
   - Ensures the Mint contract can be reused for subsequent deposits

## Registers Used

**No R4–R9 registers are directly read or written** in this contract.

- **`$initialLp`** — Compile-time constant injected at contract deployment, representing the initial LP token supply used to bootstrap the pool (accounts for burned/reserved tokens)

## Tokens

| Token Index | Type | Purpose |
|-------------|------|---------|
| **tokens(0)** (SELF & successor) | NFT (State Token) | Authenticates this Mint box as a legitimate, singleton subcontract instance |
| **tokens(1)** (pool box) | LP Tokens | Reserve of minted LP tokens; quantity decreases when deposits occur (tokens flow to users) |
| **tokens(2)** (pool box) | Y-asset (e.g., stablecoin in Dexy) | Second reserve token; must increase proportionally with X |

The pool box also holds **ERG** (nanoErgs) as reserve for the X asset.

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **User Collection**
   - Gather user deposit requests specifying amounts of X and Y assets
   - Aggregate or batch deposits into a single transaction

2. **Pool State Reading**
   - Fetch current pool box from blockchain
   - Extract `reservesXIn`, `reservesYIn`, `lpReservesIn._2`, and `supplyLpIn`

3. **LP Amount Calculation**
   - Compute fair mint quantity:
     ```
     sharesUnlocked = min(
       depositX × supplyLpIn / reservesXIn,
       depositY × supplyLpIn / reservesYIn
     )
     ```
   - Account for slippage tolerance

4. **Transaction Construction**
   - Create pool output with:
     - Increased X and Y reserves
     - Decreased LP token quantity (to be distributed)
   - Create successor Mint box (copies SELF exactly)
   - Create user output(s) with minted LP tokens
   - Ensure minimum box values and transaction fees

5. **Validation**
   - All arithmetic performed off-chain; contract only verifies invariants
   - Must ensure `deltaSupplyLp <= sharesUnlocked` to pass contract

### Security Model

- **Sigma Protocol** signature ensures only authorized parties can construct valid deposit transactions
- **Constant Segregation** — `$initialLp` cannot be modified post-deployment, anchoring all future mints
- No oracle inputs required; pool balances are the source of truth (Constant Product Model)

## Related Contracts

This contract is part of the **multi-stage AMM pool contract family** in dexy-stable:

- **`pool.es`** (implied) — Master pool box contract defining reserve storage and swap/mint/burn entrypoints
- **`swap.es`** — Validates X↔Y swaps while preserving liquidity
- **`burn.es`** — Validates LP token redemption for reserves (inverse of mint)
- **Pool subcontracts** — `mint.es`, `swap.es`, `burn.es` are likely indexed as different script alternatives or separate validator functions, called via **Multi-stage contract pattern** where pool box selects the active action script

The Mint box itself is a **Singleton** validated by a unique NFT (`tokens(0)`), enabling state machine transitions across mint/swap/burn operations.

---

### Architectural Notes

- **Storage Rent** — Successor box value ≥ SELF value ensures continued pool operation beyond minimum UTXO thresholds
- **Atomic Swaps** — Deposits are atomic within a single transaction; either all succeed or none
-