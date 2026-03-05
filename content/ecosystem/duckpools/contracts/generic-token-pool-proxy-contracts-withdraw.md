---
title: duckpools/lend-protocol-contracts — withdraw.md
description: "ErgoScript contract analysis: contracts/pools/Generic-Token-Pool/proxy-contracts/withdraw.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/Generic-Token-Pool/proxy-contracts/withdraw.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Generic Token Pool Withdraw Proxy

## Purpose

This contract functions as a **withdrawal proxy** for the Generic Token Pool, managing user requests to either withdraw tokens (in the normal case) or refund ERG when withdrawal conditions are not met. It enforces safety invariants around box succession, token transfers, and timing constraints to prevent unauthorized fund extraction.

## Inputs / Outputs

### Inputs
- **SELF (Proxy Request Box)**: 
  - Contains the user's withdrawal request state
  - Holds the requested tokens (in SELF.tokens(0))
  - Value: ERG covering transaction fees

### Outputs

**Refund Path** (OUTPUTS.size < 3):
- **OUTPUTS(0)**: Refund successor box
  - Recipient: user address (from R4)
  - Must contain original tokens or be empty
  - Receives refunded ERG (SELF.value minus minTxFee)

**Withdrawal Path** (OUTPUTS.size >= 3):
- **OUTPUTS(2)**: User's successor box
  - Recipient: user address (from R4)
  - Contains the requested tokens (requestedToken with amount ≥ requestAmount)

## Key Logic

### Refund Branch (Triggered when OUTPUTS.size < 3)
The contract validates a refund transaction using a time-lock and safety checks:

1. **Recipient Validation**: `refundSuccessor.propositionBytes == user`
   - Ensures ERG goes back to the original requester

2. **Fee Deduction**: `deltaErg <= minTxFee`
   - Only the minimum transaction fee (1,000,000 nanoERG) may be consumed

3. **Time-Lock**: `HEIGHT >= publicRefund`
   - Refund is only permitted after a deadline block height stored in R6

4. **Multi-Box Safety**: `refundSuccessor.R4 == SELF.id`
   - Prevents replay attacks by requiring the successor box to reference this SELF box's ID

5. **Token Preservation**: `refundSuccessor.tokens(0) == SELF.tokens(0)`
   - Tokens must be returned unchanged (or successor has no tokens, indicating burn/loss)

### Withdrawal Branch (Triggered when OUTPUTS.size >= 3)
The contract validates a successful token withdrawal:

1. **Recipient Validation**: `successor.propositionBytes == user`
   - Token delivery goes to the authorized user

2. **Token Amount & Type**: `successor.tokens(0)._2 >= requestAmount && successor.tokens(0)._1 == requestedToken`
   - Correct token type (requestedToken from R7) must be delivered
   - Quantity must meet or exceed the requested amount

3. **Multi-Box Spend Safety**: `successor.R7 == SELF.id`
   - Successor box must reference this SELF box to prevent unauthorized reuse

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | **User address** — the requester's public key/address for fund recipient validation |
| **R5** | `Long` | **Request amount** — quantity of tokens the user is requesting to withdraw |
| **R6** | `Long` | **Public refund height** — block height after which an unclaimed withdrawal can be refunded |
| **R7** | `Coll[Byte]` | **Requested token ID** — native token ID to be withdrawn (TokenID rule identifier) |

## Tokens

- **SELF.tokens(0)**: The native token being held in escrow
  - In refund path: returned unchanged to user
  - In withdrawal path: transferred to successor box with `tokens(0)._1` (token ID) and `tokens(0)._2` (quantity)

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Request Creation**:
   - Construct SELF box with user's withdrawal parameters in R4–R7
   - Fund box with sufficient ERG (minBoxValue + minTxFee)
   - Lock requested tokens in SELF.tokens(0)

2. **Withdrawal Path** (normal flow):
   - Monitor blockchain for the pool's fulfillment transaction
   - Verify OUTPUTS(2) is correctly formed with user address and promised tokens
   - Ensure successor box includes `R7 = SELF.id` (back-reference safety)

3. **Refund Path** (fallback after timeout):
   - After HEIGHT ≥ publicRefund, construct a refund transaction
   - Create OUTPUTS(0) with:
     - User's address (from R4)
     - Original tokens (SELF.tokens(0))
     - `R4 = SELF.id` (to satisfy multiBoxSafetyRefund)
   - Submit transaction to return funds

### Context Extension
- No explicit Context extensions are used; all state is in Registers (R4–R7)

---

## Related Contracts

- **Generic Token Pool Main Contract**: This proxy is a sub-stage contract that handles withdrawal state. The main pool contract likely:
  - Receives deposit transactions
  - Validates withdrawal requests by checking proxy box constraints
  - Produces OUTPUTS(2) with fulfilled tokens when conditions are met
  
- **Deposit Contract** (inferred): Likely mirrors this logic for the deposit side, managing user fund locks with similar timeout-refund safety patterns

- **Pool State Machine**: This contract participates in a multi-stage state machine where:
  1. User submits withdrawal request (this proxy box created)
  2. Pool fulfills or times out
  3. Refund occurs if not fulfilled by publicRefund height

---

## Security Observations

- ✅ **Replay protection**: Multi-box safety checks via R4/R7 back-references prevent box ID reuse
- ✅ **Atomic delivery**: Tight coupling between request validation (R5, R7) and output verification ensures no slippage
- ✅ **Time-bounded refunds**: publicRefund height prevents indefinite fund lockup
- ⚠️ **Unused register slots**: The final `&& true && true && true` suggests placeholder logic or incomplete implementation
- ⚠️ **Token count assumption**: Code assumes SELF.tokens(0) exists; no