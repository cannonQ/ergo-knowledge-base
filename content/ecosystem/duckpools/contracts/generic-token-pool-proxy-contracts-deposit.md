---
title: duckpools/lend-protocol-contracts — deposit.md
description: "ErgoScript contract analysis: contracts/pools/Generic-Token-Pool/proxy-contracts/deposit.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/Generic-Token-Pool/proxy-contracts/deposit.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Deposit Proxy

## Purpose

This contract serves as a **deposit proxy** in the DuckPools lending protocol, acting as an intermediary that validates either a successful token exchange (deposit fulfillment) or a refund of the original deposit request. It enforces that deposits are either completed atomically with the correct token amounts or safely refunded after a deadline, preventing fund loss through improper routing.

---

## Inputs / Outputs

### Input
- **SELF**: The deposit proxy box containing:
  - User credentials and deposit parameters in registers
  - Ergs for transaction fees
  - Optionally, tokens to be refunded

### Outputs (Two Paths)

**Path 1: Refund (OUTPUTS.size < 3)**
- **OUTPUTS(0)**: Refund box
  - Sent to the user's address
  - Contains unspent Ergs (minus `minTxFee`)
  - Carries the same tokens as SELF (if any)
  - May be a multi-box refund (linked via R4)

**Path 2: Exchange/Deposit Fulfillment (OUTPUTS.size ≥ 3)**
- **OUTPUTS(2)**: Successor box
  - Contains the exchanged tokens (lent tokens)
  - Locked to the user's script
  - Carries a back-reference to SELF via R7 (multi-box spend safety)
  - Other outputs (0, 1) handled by the pool/exchange contract

---

## Key Logic

### Refund Path (OUTPUTS.size < 3)

The contract validates a **safe refund** if ALL conditions hold:

1. **Valid Recipient** (`validRefundScript`): Refund box's script must match the stored user address (R4)
2. **Minimal Erg Loss** (`validDeltaErg`): Only `minTxFee` (1 ERG) is deducted as transaction cost
3. **Height Check** (`validHeight`): Current blockchain HEIGHT ≥ `publicRefund` deadline (time-lock enforcement)
4. **Multi-box Linkage** (`multiBoxRefund`): If R4 is set in the refund box, it must point back to SELF.id (prevents UTXO confusion in multi-box refunds)
5. **Token Consistency** (`validTokens`): If tokens exist in refund box, they must match SELF's first token

### Exchange Path (OUTPUTS.size ≥ 3)

The contract validates **successful deposit** if ALL conditions hold:

1. **Valid Recipient** (`validSuccessorScript`): Successor box (OUTPUTS(2)) is locked to the user's address (R4)
2. **Sufficient Tokens** (`validTokens`): 
   - Successor contains tokens
   - First token's ID matches the lend pool token (R7)
   - Token amount ≥ requested amount (R5)
3. **Multi-box Spend Safety** (`multiBoxSpendSafety`): If R7 is set in successor, it must reference SELF.id (audit trail and atomicity enforcement)

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User's **public address** (lock script); acts as authorization key |
| **R5** | `Long` | **Requested token amount** for the deposit |
| **R6** | `Long` | **Public refund height**; deadline after which refund is permitted (time-lock) |
| **R7** | `Coll[Byte]` | **Lend pool token ID**; identifies the asset being lent |

*Note: R4 in refund/successor boxes (if set) stores a back-reference to SELF.id for multi-box transaction safety.*

---

## Tokens

### Native Tokens Involved

1. **Refund Token** (SELF.tokens(0))
   - Original token sent with the deposit (if any)
   - Must be present in the refund box unchanged
   - Acts as a state invariant for single-token deposits

2. **Lend Pool Token** (identified by ID in R7)
   - The token the user receives upon successful deposit
   - Validated in the successor box during exchange
   - Must match the amount/ID specified in the pool contract
   - Serves as proof of deposit fulfillment

### Authentication Model
- **No signature required**; instead, the **script lock** (user's propositionBytes) acts as authorization
- Multi-box linkage via register back-references replaces signature-based atomicity

---

## Integration Pattern

### Off-Chain Bot / dApp Flow

1. **Construct Deposit Request**
   - Create a box with:
     - SELF.value = requested deposit + minTxFee
     - R4 = user's public key / address
     - R5 = token amount desired
     - R6 = current HEIGHT + refund deadline (e.g., 100 blocks)
     - R7 = lend pool token ID
   - Submit to the blockchain

2. **Monitor Two Outcomes**

   **Scenario A: Refund (timeout or rejection)**
   - Listen for transactions with OUTPUTS.size < 3
   - Verify OUTPUTS(0) validates against this contract
   - Off-chain: Confirm refund Erg appears at user address

   **Scenario B: Successful Deposit (pool accepts)**
   - Listen for transactions with OUTPUTS.size ≥ 3
   - Verify OUTPUTS(2) contains expected lend tokens
   - Off-chain: User receives tokens at their address

3. **Validation (Off-Chain Verification)**
   - Check that propositionBytes in refund/successor match stored user address
   - Verify register back-references (R4/R7) are set correctly
   - Ensure token IDs and amounts satisfy pool constraints
   - Confirm HEIGHT compliance for refund

### Constant Segregation
- `minTxFee` and `minBoxValue` are hardcoded constants; no context extension needed
- Register values are **not** malleable by the transaction builder (signed by user)

---

## Related Contracts

### Inferred Relationships

1. **Generic Token Pool Contract** (parent)
   - Consumes this deposit proxy as an input