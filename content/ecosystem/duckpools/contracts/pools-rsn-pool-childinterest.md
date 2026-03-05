---
title: duckpools/lend-protocol-contracts — childInterest.md
description: "ErgoScript contract analysis: contracts/pools/RSN-POOL/childInterest.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/RSN-POOL/childInterest.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: childInterest.md

## Purpose

This contract maintains a **singleton interest rate history box** for a lending pool, updating accumulated interest rates at regular intervals based on a polynomial curve derived from pool utilization metrics. It acts as a state machine that validates interest computations and preserves historical data across transactions while protecting against unauthorized modifications.

## Inputs / Outputs

### Inputs
- **SELF (Primary Input)**: The current interest history box containing:
  - Accumulated interest history (R4)
  - Last recorded block height (R5)
  - Child index identifier (R6)
  - Native tokens (pool NFT references)
  - ERG value for transaction fees

- **CONTEXT.dataInputs(0) [Pool Box]**: Read-only data input referenced for:
  - Current borrowed token amount (tokens(2)._2)
  - Total pool assets (tokens(3)._2)
  - Pool NFT authentication (tokens(0)._1)

- **CONTEXT.dataInputs(1) [Parameter Box]**: Read-only data input containing:
  - Polynomial coefficient set (R4): [a, b, c, d, e, f]
  - Interest parameter NFT (tokens(0)._1)

### Outputs
- **OUTPUTS(0) [Successor Box]**: Updated interest history box with:
  - Extended interest history (R4) with new computed rate appended
  - Updated block height (R5)
  - Preserved child index (R6)
  - Dummy registers R7, R8, R9 (validation flags)
  - Same tokens as input
  - ERG ≥ SELF.value - MaximumExecutionFee

## Key Logic

### Update Gate
```
isReadyToUpdate = (HEIGHT - recordedHeight) >= updateFrequency (120 blocks)
```
Prevents excessive updates; ensures minimum 120-block intervals between rate recalculations.

### Interest Rate Computation
Polynomial evaluation based on **pool utilization**:

```
utilization = (borrowed / (poolAssets + borrowed)) × 10^8

rate = M + a + (b·x)/D + (c·x²)/M/D + (d·x³)/M²/D + (e·x⁴)/M³/D + (f·x⁵)/M⁴/D

where:
  x = utilization
  M = 10^8 (InterestDenomination)
  D = 10^8 (CoefficientDenomination)
```

This implements a **6th-degree polynomial** interest curve, allowing sophisticated rate behavior:
- Low utilization → lower base rate (a)
- Rising utilization → accelerating rates via higher-order terms
- Coefficients externalized to parameter box for governance updates

### Successor Validation
1. **Script Invariance**: `successor.propositionBytes == SELF.propositionBytes`
   - Ensures contract lock-in continues; prevents privilege escalation

2. **Interest History Integrity**:
   - `successor.R4[0..n-1] == SELF.R4[0..n-1]` (previous history immutable)
   - `successor.R4[n] == currentRate` (new rate appended)
   - `successor.R4.size == SELF.R4.size + 1` (exactly one entry added)

3. **State Preservation**:
   - `successor.R6 == SELF.R6` (child index unchanged)
   - `successor.tokens == SELF.tokens` (NFT/token set immutable)
   - `successor.value >= SELF.value - 2,000,000` (ERG loss bounded)

4. **Height Validation**:
   - `0 ≤ (successor.R5 - HEIGHT) ≤ 5` (height set to near-future block)
   - Prevents timestamp manipulation

5. **Capacity Gate**:
   - `successor.R4.size ≤ 430` (MaximumHistoryHeight)
   - Archive rotation or cleanup required when limit approached

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R4** | `Coll[Long]` | Interest rate history (accumulated compounded rates) | Read from SELF, write to successor |
| **R5** | `Long` | Block height of last update | Read from SELF, write to successor |
| **R6** | `Int` | Child/shard index for multi-instance pools | Read from SELF, write to successor (unchanged) |
| **R7** | `Boolean` | Dummy flag (validation placeholder) | Read from successor only |
| **R8** | `Boolean` | Dummy flag (validation placeholder) | Read from successor only |
| **R9** | `Boolean` | Dummy flag (validation placeholder) | Read from successor only |

## Tokens

### Singleton NFTs (Authentication)
- **PoolNft** (`BJt8g3gZqEhCL9rzfDsfp7Me67DTuM8HvYBW5yHoHxs`):
  - Carried in SELF and successor
  - Used to identify parent pool box in data inputs
  - Prevents confusion with unrelated pools

- **InterestParameterBoxNft** (`E9emgoNfXgLHWXs612Cv6bf1aE1PC27Fa4aKT8SEcnQy`):
  - Identifies governance-controlled coefficient box
  - Allows rate curve updates without redeploying contract

### Token Invariants
- `successor.tokens == SELF.tokens` (no token injection/removal)
- `successor.tokens.size == SELF.tokens.size` (size must match exactly)

## Integration Pattern

### Off-Chain Bot/Headless dApp Workflow

1. **Monitor** (`HEIGHT - recordedHeight ≥ 120`):
   - Listen for pool state changes
   - Query current pool utilization and parameter box coefficients

2. **Compute**:
   - Extract `borrowed` and `poolAssets` from pool box
   - Evaluate 6th-degree polynomial with coefficients [a, b, c, d, e, f]
   - Calculate `currentRate`

3. **Construct Transaction