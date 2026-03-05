---
title: duckpools/off-chain-bot — withdraw_liquidity.md
description: "ErgoScript contract analysis: optionPools/contracts/proxy_contracts/withdraw_liquidity.md"
tags: [duckpools, off-chain-bot, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/off-chain-bot"
contract_file: optionPools/contracts/proxy_contracts/withdraw_liquidity.md
project: duckpools-off-chain-bot
---
# ErgoScript Contract Analysis: `withdraw_liquidity`

## Purpose

This contract governs the withdrawal of liquidity from an option pool, allowing users to either claim their requested ERG and token amounts in a normal withdrawal, or reclaim their full deposit via refund after a timeout period. It acts as a liquidity request handler in a multi-stage contract system where off-chain bots fulfill withdrawal requests.

## Inputs / Outputs

### Inputs
- **SELF (Request Box)**: Contains user withdrawal request with:
  - ERG value (the user's deposit)
  - Native tokens held in the pool request
  - Registers encoding request parameters

### Outputs

**Refund Path** (`OUTPUTS.size < 3`):
- **OUTPUTS(0)**: Refund successor box
  - Script: User's public key (must spend to user)
  - Receives remaining ERG after tx fees
  - Must carry the same NFT/state token as SELF

**Withdrawal Path** (`OUTPUTS.size ≥ 3`):
- **OUTPUTS(1)**: Settlement box
  - Script: User's public key
  - Receives requested ERG amount
  - Receives requested token amount
  - References SELF via R7 register (multi-box safety)
- **OUTPUTS(0), OUTPUTS(2+)**: Other boxes (pool state updates, bot fees, etc.)

## Key Logic

### Refund Conditions (Emergency Recovery)
Refund is valid if **all** of the following hold:

1. **`validRefundSuccessor`**: Output box(0) script is the user's public key
2. **`validDeltaErg`**: ERG burned for transaction fees ≤ `minTxFee` (1M nanoERG)
3. **`validHeight`**: Current block height ≥ `publicRefund` deadline (timeout has passed)
4. **`multiBoxSafetyRefund`**: Output box(0) carries R4 register containing SELF's box ID (prevents box reuse attacks)
5. **`validTokens`**: Output box(0) receives the same token that was in SELF

**Semantic**: After a deadline, users can unilaterally reclaim their deposit if the bot failed to fulfill the request.

### Withdrawal Conditions (Normal Fulfillment)
Withdrawal is valid if **all** of the following hold:

1. **`validSuccessorScript`**: Output box(1) script is the user's public key
2. **`validValue`**: Output box(1) contains ≥ `requestERGAmount` ERG
3. **`validTokens`**: Output box(1) contains:
   - Token ID matching `requestedToken` (R8)
   - Amount ≥ `requestYAmount` (R6)
4. **`multiBoxSpendSafety`**: Output box(1) R7 register contains SELF's box ID (prevents replay/reuse)

**Semantic**: Bot fulfills the request by sending the user their requested amounts, verified via cross-box reference.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User's public key (Sigma proof point for spending) |
| **R5** | `Long` | Requested ERG amount to withdraw |
| **R6** | `Long` | Requested Y-token amount to withdraw |
| **R7** | `Long` | Public refund height (deadline); after this HEIGHT, refund is enabled |
| **R8** | `Coll[Byte]` | Token ID of the Y-token being requested |

## Tokens

### Native Tokens
- **State/NFT Token** (SELF.tokens(0)): 
  - Distinguishes this request box as legitimate pool request
  - Must be carried through to successor box to prevent double-spending
  - Acts as a singleton/state NFT ensuring request authenticity
  
- **Y-Token** (identified by `requestedToken` ID in R8):
  - The liquidity pool's output token
  - Requested amount validated in withdrawal path
  - Amount: `requestYAmount` (R6)

## Integration Pattern

### Off-Chain Bot Responsibilities

1. **Monitor**: Watch for request boxes matching pool's contract script
2. **Validate Request**: 
   - Parse R4–R8 to extract user PK, amounts, deadline
   - Fetch current HEIGHT from node
3. **Construct Withdrawal Transaction** (if fulfilling):
   - Output(0): Pool state update box
   - Output(1): Settlement box with:
     - Script = user's PK (from R4)
     - Value ≥ R5 (requestERGAmount)
     - tokens(0) = (requestedToken ID from R8, amount ≥ R6)
     - R7 = SELF.id (the request box ID)
   - Output(2+): Bot fee/change boxes
   - Sign with bot's key (if needed for intermediate state)

4. **Or Construct Refund** (if deadline passed):
   - Output(0): Refund box with:
     - Script = user's PK (from R4)
     - Value = SELF.value - minTxFee
     - tokens(0) = SELF.tokens(0) (state NFT)
     - R4 = SELF.id (back-reference)

### Context Extension / Off-Chain Construction
- Bot provides unsigned transaction; user may co-sign if required
- Constant segregation: `minTxFee`, `minBoxValue` are inline constants (immutable in contract)
- Sigma protocol: User's PK in R4 determines spending capability (Schnorr signature)

## Related Contracts

### Implied Composition
- **Pool State Contract** (likely OUTPUTS(0) in withdrawal):
  - Maintains liquidity reserves
  - Updates after withdrawal
  - May enforce invariant: `totalY_out ≤ poolReserve`

- **Request Submission Contract**:
  - Creates this `withdraw_liquidity` box
  - Validates initial deposit and token locking

- **Multi-Stage Pattern**:
  - This contract is **Stage 2** (fulfillment/refund)
  - Follows eUTXO state machine: `UserRequest