---
title: SavonarolaLabs/crystal-pool — buy-token-for-erg.es
description: "ErgoScript contract analysis: src/lib/contracts/buy-token-for-erg.es"
tags: [savonarolalabs, crystal-pool, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/SavonarolaLabs/crystal-pool"
contract_file: src/lib/contracts/buy-token-for-erg.es
project: savonarolalabs-crystal-pool
---
# ErgoScript Contract Analysis: `buy-token-for-erg.es`

## Purpose

This contract implements a **time-locked token purchase order** where a buyer commits ERG (Ergo's native token) to acquire a specific token at a predetermined rate. The contract enforces that either both the buyer and pool operator must authorize the transaction before an unlock height, or the pool operator alone can execute if the buyer receives their promised token amount after the unlock height.

## Inputs / Outputs

### Inputs
- **Legitimate Buy Order Inputs**: Boxes matching `isLegitBuyOrderInput` criteria—same buyer, unlock height, token ID, buy rate, multisig address, and contract proposition bytes.
- **Data Inputs** (implicit): Referenced but not consumed; may include price feeds or state boxes.

### Outputs
- **Legitimate Buy Order Outputs**: Boxes with identical buyer, unlock height, token ID, and the minimum buy rate among all input boxes.
- **Payment Boxes**: Boxes sent to the buyer's multisig address containing the purchased tokens, same unlock height and buyer reference.
- **Implicit outputs**: Change boxes, fee boxes (handled by transaction structure).

## Key Logic

### Time-Lock Authorization Mechanism
```
If HEIGHT > unlockHeight(SELF):
  → Only buyerPk required (buyer can claim after lock expires)
Else (HEIGHT ≤ unlockHeight(SELF)):
  → (buyerPk AND poolPk)  OR  (isBuyerPaid AND poolPk)
    - Both signatures required, OR
    - Pool operator can execute unilaterally if buyer is paid
```

### Token Purchase Invariants
1. **Rate Consistency**: All input boxes use the minimum buy rate (`minBuyRate`) detected across inputs.
2. **Value Conservation**: `valuesIn ≥ valuesOut` (ERG amounts don't increase).
3. **Token Accounting**: `amountsIn - amountsOut ≤ sentToBuyer`
   - The buyer receives at least as many tokens as ERG value consumed at the buy rate.
4. **Multisig Enforcement**: Payment boxes must be locked to `getBuyerMultisigAddress(SELF)`, ensuring only the designated multisig can claim tokens.

### Helper Validators
- `isLegitBuyOrderInput/Output`: Enforces structural consistency across transaction boxes.
- `includesToken`: Confirms token presence in first slot.
- `isSameBuyer`, `isSameUnlockHeight`, `isSameMultisig`: Guard state mutations.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[SigmaProp]` | Stores `[buyerPk, poolPk]`—buyer and pool operator signatures required for early execution. |
| **R5** | `Int` | `unlockHeight`—block height after which buyer can act unilaterally. |
| **R6** | `Coll[Byte]` | `tokenId`—the token ID being purchased (typically token's first 32 bytes). |
| **R7** | `Long` | `buyRate`—exchange rate (ERG nanoErgs per token unit). |
| **R8** | `Coll[Byte]` | `buyerMultisigAddress`—propositionBytes of multisig address receiving tokens. |

## Tokens

### Native Token Usage
- **Token ID (R6)**: The contract tracks a single token type (accessed via `box.tokens(0)._1`).
- **Token Amount**: `box.tokens(0)._2` holds the quantity of tokens in a box.
- **Invariant**: All boxes in the transaction must reference the same token ID (`isSameTokenId`), enforced via the Token ID rule.

### No Singleton NFT
Unlike stateful multi-stage contracts, this contract uses **register-based state** rather than a Singleton / State NFT, making it suitable for batched order processing.

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities
1. **Order Aggregation**: Scan UTXO set for boxes matching this contract and accumulate buy orders.
2. **Rate Detection**: Extract `getBuyRate` from each box; compute `minBuyRate`.
3. **Token Sourcing**: Obtain the required token quantity from a liquidity pool or reserve.
4. **Transaction Construction**:
   - Select all legitimate buy order inputs.
   - Create outputs with `minBuyRate` in R7 (if continuing the order state).
   - Create payment boxes locked to each buyer's multisig address with tokens.
   - Ensure `sumTokensOut ≥ deltaAmounts` at minimum rate.
5. **Signature Collection**:
   - **Before `unlockHeight`**: Collect both `buyerPk` and `poolPk` (2-of-2 Sigma protocol).
   - **After `unlockHeight`**: Only `buyerPk` required; pool operator signature optional.
6. **Validation**: Verify `isBuyerPaid` in Context before signing.

### Constant Segregation
- Register values are **immutable state**; new outputs must reproduce them (or contract enforces reversion).
- The `minBuyRate` is computed **in-context** and used to validate all outputs.

## Related Contracts

### Inferred Relationships
- **Liquidity Pool Contract** (implicit):
  - Provides tokens to fulfill buy orders.
  - Likely authenticated via `poolPk` (R4[1]).
  - Not directly referenced in this contract; composition happens off-chain.

- **Buyer Multisig Contract** (R8):
  - The `buyerMultisigAddress` is a separate contract deployed at the multisig script hash.
  - Acts as the final custodian of purchased tokens.
  - This contract enforces routing but does not replicate its logic.

- **Price Feed / Oracle** (data input):
  - Not referenced in code, but `buyRate` (R7) likely originates from off-chain oracle data.
  - Validated during off-chain transaction construction.

### Contract Composition Pattern
```
Buy Order (this contract)
  ↓ (outputs)
Liquidity Pool (inferred; consumes tokens)
  ↓ (
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
