---
title: kushti/dexy-stable — Deposit.es
description: "ErgoScript contract analysis: contracts/lp/proxy/Deposit.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/Deposit.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Deposit.es

## Purpose

This contract validates user deposits into a **Constant Function Market Maker (CFMM) n2t Pool** within the Dexy stable asset protocol. It ensures that liquidity providers receive fair LP token rewards proportional to their capital contribution while enforcing fee constraints and reserve integrity.

---

## Inputs / Outputs

### Inputs
| Position | Box | Role |
|----------|-----|------|
| `INPUTS(0)` | Pool Box | CFMM pool state containing NFT, LP tokens, and reserves (X and Y tokens) |
| `INPUTS(1+)` | User Input Box(es) | Contains user's deposit tokens and ERG for transaction fees |
| `SELF` | Current Box | The deposit proxy box holding user's deposit tokens |

### Outputs
| Position | Box | Role |
|----------|-----|------|
| `OUTPUTS(0)` | Updated Pool Box | Modified reserve balances post-deposit |
| `OUTPUTS(1)` | Action Box | Dexy protocol auxiliary box |
| `OUTPUTS(2)` | Reward Box | Receives LP tokens and change; must be owned by `Pk` |
| `OUTPUTS(n)` | Miner Fee Box | Transaction fee; validated against `MaxMinerFee` |

---

## Key Logic

### Core Validation Flow

1. **Input Structure Check**
   - At least 2 inputs must exist
   - Pool input (`INPUTS(0)`) must contain exactly 3 tokens: Pool NFT, LP token, and reserve Y token

2. **LP Token Calculation** (Fair pricing based on constant product AMM)
   ```
   supplyLP = InitiallyLockedLP (0x7FFF...) - currentLP
   minByX = (userX / reserveX) × supplyLP
   minByY = (userY / reserveY) × supplyLP
   minimalReward = min(minByX, minByY)
   ```
   The user receives LP tokens based on whichever asset gives fewer tokens (prevents arbitrage).

3. **Change Handling** (Handles imbalanced deposits)
   - If `minByX < minByY`: User receives excess Y as change
     - Excess Y amount: `(minByY - minByX) × reserveY / supplyLP`
     - Validates `rewardOut.tokens.size == 2` (LP token + change token)
   - If `minByX >= minByY`: Excess X absorbed; no Y change needed
   - Rejects if both conditions fail

4. **Output Value Validation**
   - Reward output must retain sufficient ERG:
     - If Y change: `value ≥ userX - DexFee`
     - If X excess: `value ≥ userX - excessX - DexFee`

5. **Fee Constraints**
   - Aggregate miner fees across all outputs ≤ `MaxMinerFee`
   - Each miner fee box identified by `MinerPropBytes`

6. **Final Authorization**
   - Reward box must be spendable by `Pk` (user's public key)
   - Received LP tokens ≥ calculated `minimalReward`
   - Pool NFT preserved in output (same token ID as input LP token)

---

## Registers Used

No explicit R4-R9 reads in this contract. All state is derived from:
- **Box values**: ERG amounts for fee calculations
- **Box tokens**: Native token IDs and quantities for reserve tracking
- **Box propositionBytes**: For identifying miner fee outputs and reward recipient

---

## Tokens

| Token | Type | Purpose |
|-------|------|---------|
| **Pool NFT** | Singleton (State NFT) | Identifies the unique CFMM pool; checked against `PoolNFT` constant |
| **LP Token** | Native Token | Represents liquidity provider share; token ID preserved across transactions |
| **Reserve Y** | Native Token | Second reserve asset in the CFMM (X is ERG/native asset) |
| **Change Token** | Native Token | Conditional; returned if deposit is imbalanced (either X or Y excess) |

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Requirements

1. **Box Construction**
   - Fetch current pool box from blockchain (via indexer)
   - Read `INPUTS(0)` state: Pool NFT, LP supply, reserve amounts
   - Calculate user deposit amounts (`userX`, `userY`)

2. **Computation**
   - Pre-compute `minByX`, `minByY`, `minimalReward` 
   - Determine change necessity and amounts
   - Estimate miner fees and total transaction cost

3. **Transaction Building**
   ```
   Inputs:
     - Pool box (unspent)
     - User's UTXOs containing tokens/ERG
     - Data input (optional; for price oracles if used elsewhere)
   Outputs:
     - New pool box (updated reserves & LP tokens)
     - Action box (Dexy protocol state)
     - Reward box (to Pk, with LP tokens + change)
     - Miner fee box
   ```

4. **Proof Generation**
   - Sign transaction with user's private key to satisfy `sigmaProp(Pk || validDeposit)`
   - If `validDeposit` evaluates to true, signature may be waived (OR condition)

5. **Validation Hooks**
   - Verify `poolIn.tokens(0)._1 == PoolNFT` before submission
   - Confirm change token ID matches `reservesY._1` if applicable

---

## Related Contracts

### Inferred Dependencies

1. **Pool Contract** (implicit)
   - The pool box itself enforces CFMM invariant: `reserveX × reserveY = k`
   - Not directly visible but referenced as `INPUTS(0)`

2. **Action Box Contract** (implicit)
   - Dexy state machine; `OUTPUTS(1)` role defined by separate contract
   - Likely maintains protocol-level state

3. **Reward/User Contract** (implicit)
   - The contract at `Pk.propBytes` (user's signature scheme)
   - Receives LP tokens and governs