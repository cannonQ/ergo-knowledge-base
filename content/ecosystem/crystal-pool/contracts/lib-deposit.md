---
title: SavonarolaLabs/crystal-pool — deposit.es
description: "ErgoScript contract analysis: src/lib/contracts/deposit.es"
tags: [savonarolalabs, crystal-pool, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/SavonarolaLabs/crystal-pool"
contract_file: src/lib/contracts/deposit.es
project: savonarolalabs-crystal-pool
---
# ErgoScript Contract Analysis: `deposit.es`

## Purpose

This contract implements a **time-locked deposit box** that releases control of funds after a specified block height. Until the unlock height is reached, the deposit remains under joint or shared custody; after unlock, the seller regains unilateral control via their signature.

## Inputs / Outputs

**Inputs:**
- **SELF (Deposit Box):** A Box containing:
  - Seller's public key (in R4, index 0)
  - Pool operator's public key (in R4, index 1)
  - Unlock height threshold (in R5)
  - Value (ERG or tokens) held in escrow

**Outputs:**
- Not explicitly specified by this contract; determined by the spending transaction constructed off-chain.
- Spending transaction must provide the valid Sigma proof matching the contract's guard condition.

## Key Logic

The contract implements a **height-based access control gate**:

```
IF current_block_height > unlock_height THEN
  Allow spending guarded by seller's signature alone
ELSE
  Allow spending guarded by seller's signature (current: commented logic suggests pool cooperation intended)
```

**Critical observation:** The guard condition is identical in both branches:
```ergoscript
getSellerPk(SELF)
```

This means the contract **currently allows the seller to spend at any time**, rendering the time-lock ineffective. The commented code `&& getPoolPk(SELF)` suggests the intended logic was:

- **Before unlock:** Require both seller **AND** pool operator signatures (2-of-2 multisig via `&&` in Sigma protocol)
- **After unlock:** Require seller signature alone

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[SigmaProp]` | Collection of two public keys: `[sellerPk, poolPk]` |
| **R5** | `Int` | Block height at which time-lock expires and seller gains unilateral control |

- **R0–R3:** Standard (unused here; would contain value, tokens, creationInfo, tokens)

## Tokens

No explicit token authentication is enforced. However, the deposit box may carry:
- **Native tokens** (NFTs or fungible tokens) as part of its value
- No **State NFT** or Singleton pattern is visible in this isolated contract

Tokens held in the box are released when the guard condition is satisfied; no token-specific logic is present.

## Integration Pattern

**Off-chain bot / Headless dApp responsibilities:**

1. **Box Selection:** Identify the deposit box by its ErgoTree (contract hash) and register contents.
2. **Height Monitoring:** Poll the blockchain for the current HEIGHT.
3. **Transaction Construction:**
   - If `HEIGHT ≤ unlockHeight`: Construct a transaction that includes both seller and pool operator signatures (once the commented guard is fixed).
   - If `HEIGHT > unlockHeight`: Construct a transaction signed only by the seller.
4. **Proof Submission:** Provide the appropriate Sigma proof in the spending transaction.
5. **Validation:** Ergo node verifies that `SELF.R4` and `SELF.R5` deserialize correctly and that the guard condition evaluates to true under the current context.

## Related Contracts

**Likely composition (inferred from naming):**

- **`pool.es`** or equivalent: The pool contract that holds the poolPk referenced in R4. Likely validates deposits and manages liquidity.
- **`seller.es`** or user contract: Seller's contract or keypair manager.
- **Potential state machine:** This deposit contract may be part of a multi-stage contract sequence where deposits lock funds pending pool operations.

*Note:* Crystal Pool is an Ergo DEX/AMM-like protocol; this deposit contract likely pairs with liquidity pool contracts and withdrawal contracts.

---

## ⚠️ Critical Issues

1. **Time-lock is non-functional:** Both branches return `getSellerPk(SELF)`, so the seller can spend immediately regardless of height.
   
   **Fix:**
   ```ergoscript
   if(HEIGHT > unlockHeight(SELF)){
     getSellerPk(SELF)
   } else {
     getSellerPk(SELF) && getPoolPk(SELF)  // Uncomment & fix
   }
   ```

2. **No value or token preservation:** The contract does not verify that outputs preserve the original box value or tokens, leaving risk of fund loss in careless off-chain bot code.

3. **Missing minimum box value check:** No assertion that output boxes meet `MinBoxValue` (1 ERG), risking storage rent defaults.