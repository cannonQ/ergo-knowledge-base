---
title: duckpools/lend-protocol-contracts — child.md
description: "ErgoScript contract analysis: contracts/pools/rsbtc/child.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsbtc/child.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Child Pool Interest Contract

## Purpose

This contract manages the interest rate history for a child pool in the DuckPools lending protocol. It periodically records interest rate calculations based on pool utilization metrics and maintains a chronological history in a Register, ensuring that interest rates are updated only at specified intervals and stored compliantly within height constraints.

## Inputs / Outputs

**Inputs:**
- **SELF (Primary Input):** The child box itself, containing the interest history in R4, last recorded height in R5, and child index in R6. Must hold the State NFT (via `preservedInterestNFT` check).
- **CONTEXT.dataInputs(0) (Pool Box):** A read-only data input holding the pool state, including borrowed token amounts at index 2 and total pool assets at index 3. Authenticated via `PoolNft` token.
- **CONTEXT.dataInputs(1) (Parameter Box):** A read-only data input holding interest rate polynomial coefficients in R4. Authenticated via `InterestParameterBoxNft` token.

**Outputs:**
- **OUTPUTS(0) (Successor Box):** The updated child box with an extended interest history in R4, new height in R5, and preserved child index in R6. Must retain the same script (`ErgoTree`), tokens, and sufficient ERG value.

## Key Logic

The contract validates a single atomic transition following this state machine:

1. **Update Eligibility:** `deltaHeight >= updateFrequency` (120 blocks minimum since last update)
2. **Utilization Calculation:** 
   - `borrowed = MaximumBorrowTokens - pool.tokens(2)._2` (tokens not yet withdrawn)
   - `util = (Interest * borrowed) / (poolAssets + borrowed)` (normalized 0–100M)
3. **Interest Rate Computation:** Polynomial function `f(x) = M + a + bx + cx² + dx³ + ex⁴ + fx⁵` where `x = util`, evaluated using coefficients from the parameter box. Each division is denominated to prevent overflow.
4. **History Extension:** The final history must equal the old history plus exactly one new rate entry: `finalInterestHistory == oldHistory ++ [currentRate]`
5. **Height Constraint:** `finalInterestHistory.size <= MaximumHistoryHeight` (430 entries max) prevents unbounded growth.
6. **Box Preservation:** Successor retains same script, tokens, and child index; ERG value decreases by at most `MaximumExecutionFee` (2M nanoERG).
7. **Finality Check:** `deltaFinalHeight` (HEIGHT relative to finalHeight in successor) must be 0–5 blocks, ensuring the successor is being spent soon after creation (anti-replay).

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Interest rate history (array of rates in basis units). Old: `interestHistory`; New: `finalInterestHistory` with appended `currentRate`. |
| **R5** | `Long` | Last recorded block height for update frequency tracking. Old: `recordedHeight`; New: `finalHeight` (set to `HEIGHT` implicitly). |
| **R6** | `Int` | Child pool index (immutable identifier). Must remain unchanged: `finalChildIndex == childIndex`. |
| **R7, R8, R9** | `Boolean` | Dummy registers (unused in logic, required for script compliance). All checked `== true` in successor. |

## Tokens

- **State NFT (PoolNft):** `6wu6NgonXKFYQ32mvLbwj9XGzURVB7Z4r1QEhdUmHRcD`  
  Held in successor to ensure this is the authoritative child pool instance; prevents counterfeiting.
  
- **Interest Parameter NFT (InterestParameterBoxNft):** `H4sGBJihCfpm5xXYXJktjauuCSmmMyEbCmxn5QRtYFrK`  
  Authenticates the data input providing polynomial coefficients; allows governance to update rates by retiring old parameter box and issuing a new one.

- **No native token transfers:** `noMoreTokens` ensures successor holds identical tokens as SELF.

## Integration Pattern

**Off-chain Bot/Dapp Responsibilities:**

1. **Monitor Pool State:** Track `SELF` (child box) and `pool` box in the blockchain; detect when `HEIGHT - R5[Long] >= 120`.
2. **Fetch Parameters:** Read the current `InterestParameterBoxNft` box to obtain coefficients in R4.
3. **Calculate Interest:** 
   - Extract borrowed tokens and pool assets from the pool box.
   - Compute utilization and polynomial rate using the provided coefficients.
   - Append to the interest history array from SELF.R4.
4. **Construct Transaction:**
   - **Input 0 (spend SELF):** Sign with the pool operator (via Sigma protocol / Schnorr signature).
   - **DataInputs:** Include pool box and parameter box (no signatures required).
   - **Output 0 (successor):** Set R4 to new history, R5 to current HEIGHT, preserve R6, set R7/R8/R9 to true, retain script and tokens, preserve ERG (minus fee).
5. **Validate Before Submission:** Off-chain code must verify all polynomial arithmetic to avoid ledger rejection.

## Related Contracts

- **Pool Contract:** The primary pool box (data input 0) manages borrowing/lending state; this child contract is one of possibly multiple satellite boxes recording interest history per pool child instance.
- **Interest Parameter Box Contract:** Manages the polynomial coefficients; likely a singleton updated by governance that this contract reads immutably.
- **Parent/Multi-stage Orchestrator (inferred):** A parent contract likely manages the relationship between multiple child boxes and the primary pool, potentially collecting interest updates across children.

---

### Technical Notes

- **Constant Segregation:** All contract constants (NFT IDs, denominations, limits) are compile-time values, reducing on-chain computation.
- **Invariants Enforced:**
  - History is monotonically growing (no deletion, only append).
  