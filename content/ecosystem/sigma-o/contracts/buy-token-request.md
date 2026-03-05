---
title: ThierryM1212/SigmaO — Buy_Token_Request.es
description: "ErgoScript contract analysis: contract/Buy_Token_Request.es"
tags: [thierrym1212, sigmao, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
contract_file: contract/Buy_Token_Request.es
project: thierrym1212-sigmao
---
# ErgoScript Contract Analysis: Buy_Token_Request

## Purpose

This contract implements an **open buy order** mechanism where a user deposits ERG and specifies a desired token to purchase. The contract ensures that either the buyer receives the requested minimum token amount in a subsequent transaction, or the buyer can refund their ERG by providing a valid Sigma proof.

## Inputs / Outputs

**Input:**
- **SELF** (Spending Box): 
  - Box value: ERG amount available for purchase
  - R4: SigmaProp (buyer's public key)
  - R5: Token ID to be purchased (Coll[Byte])
  - R6: Minimum token amount requested (Long)

**Outputs:**
- **OUTPUTS(1)**: Payment box (must contain ≥ requested token amount)
  - Must be locked to the buyer's P2PK address
  - Must contain exactly 1 token of the requested type with amount ≥ R6 value
- **OUTPUTS(0)**: Implicitly the seller's box (not validated by this contract; off-chain responsibility)

## Key Logic

The contract implements **dual-path validation** using `||` (OR):

1. **Refund Path**: `userPKIn`
   - If the buyer provides a valid Sigma proof matching their stored SigmaProp (R4), the transaction is approved
   - Allows the buyer to cancel the buy order and recover their ERG at any time

2. **Token Delivery Path**: `sigmaProp(validBuyToken)`
   - Validates that OUTPUTS(1) contains exactly 1 token
   - Verifies the token's ID matches SELF.R5
   - Confirms the token amount is ≥ the requested amount in SELF.R6
   - Ensures OUTPUTS(1) is locked to the buyer's address (userPKIn.propBytes)
   - Approval requires either refund OR valid token delivery

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | SigmaProp | Buyer's public key (P2PK); enables refund authorization and validates payment recipient |
| **R5** | Coll[Byte] | Token ID of the desired token to purchase; matched against OUTPUTS(1).tokens |
| **R6** | Long | Minimum token amount (raw units) required; e.g., 100 for 1 SigUSD (2 decimals) |

## Tokens

- **Single NFT/Token Role**: The token specified in R5 is the **purchase target**
  - Not a State NFT or authentication token, but rather the commodity being exchanged
  - Uses **Token ID rule** to identify the exact asset
  - Amount constraint: OUTPUTS(1) must deliver ≥ R6 units to satisfy the order
  - No token in SELF; tokens arrive via OUTPUTS(1) from the seller

## Integration Pattern

**Off-chain Bot/Headless dApp Responsibilities:**

1. **Order Creation Phase**:
   - Construct a box with user's ERG value and store buyer's SigmaProp in R4
   - Encode desired token ID in R5 and minimum amount in R6
   - Submit to blockchain as an eUTXO

2. **Order Matching Phase**:
   - Monitor for matching sell orders or liquidity
   - Construct transaction spending SELF with:
     - OUTPUTS(0): Seller's change/profit box
     - OUTPUTS(1): Token payment box locked to buyer's P2PK, containing ≥ R6 tokens
   - Validate that box value ≥ minimum transaction fee requirement
   - Submit signed transaction

3. **Cancellation Phase** (user-initiated):
   - Construct refund transaction spending SELF
   - Prove ownership via buyer's private key (satisfies userPKIn SigmaProp)
   - Return ERG to buyer's address

**Context Extension:** None required; all data is in registers.

## Related Contracts

- **Likely Upstream**: A **Sell_Token_Offer** or equivalent contract that provides tokens in OUTPUTS(0)
  - Forms atomic swap pair: sell order's output feeds into this buy order's input
- **Likely Companion**: A **DEX matcher** or **order book aggregator** contract that:
  - Coordinates multiple buy/sell requests
  - Ensures OUTPUTS(1) constraints are satisfied before submission

---

## Security Considerations

⚠️ **Invariants Maintained**:
- Buyer cannot be paid wrong token (Token ID checked)
- Buyer cannot receive insufficient amount (≥ R6 enforced)
- Buyer cannot lose refund rights (userPKIn always available)

⚠️ **Potential Risks**:
- **No price validation**: Contract does not verify exchange rate; off-chain bot must ensure fair pricing
- **Dust attack**: Minimal box value constraints not explicitly checked (relies on minimum box value rule)
- **Slippage**: Off-chain code must handle token amount >= R6 (allows overpayment)