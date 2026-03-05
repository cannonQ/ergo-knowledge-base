---
title: ThierryM1212/SigmaO — ValidOracle.mu.es
description: "ErgoScript contract analysis: contract/templates/ValidOracle.mu.es"
tags: [thierrym1212, sigmao, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
contract_file: contract/templates/ValidOracle.mu.es
project: thierrym1212-sigmao
---
# ErgoScript Contract Analysis: ValidOracle.mu.es

## Purpose

This contract fragment validates oracle data freshness and authenticity by checking that an oracle box holds the correct Oracle State NFT and that its price data has been published within the last 30 blocks. It serves as a reusable validation template for dApps that depend on timely, authenticated price feeds.

## Inputs / Outputs

### Inputs
- **Oracle Box** (data input or spent input):
  - Must contain the Oracle State NFT (singleton token with ID: `OracleTokenId`)
  - Carries price data in R4 and height metadata in R5
  - Not directly spent; typically used as a **Data Input** to avoid state mutation conflicts

### Outputs
- No direct output specification in this fragment; validation results inform the calling contract's output conditions
- The calling contract typically produces outputs conditional on `validOracle == true`

## Key Logic

The validation enforces three conditions, all of which must be satisfied:

1. **Token Authenticity**  
   `oracleBox.tokens(0)._1 == OracleTokenId`  
   The first native token in the oracle box must be the designated Oracle State NFT (singleton). This ensures the box is the authoritative oracle state, not a counterfeit.

2. **Price Data Retrieval**  
   `oraclePrice: Long = oracleBox.R4[Long].get`  
   Reads the current price (in nanoerg per token) from Register R4. Type: `Long`.

3. **Data Freshness Check**  
   `oracleHeight: Long = oracleBox.R5[Int].get` and `HEIGHT <= oracleHeight + 30`  
   - Extracts the block height at which the oracle price was published (Register R5, typed as `Int` but cast to `Long`)
   - Validates that the current block height (`HEIGHT`, a blockchain context variable) is ≤ 30 blocks after publication
   - Prevents use of stale prices older than ~5 minutes (30 blocks × ~10 seconds per block on Ergo)

## Registers Used

| Register | Type | Source | Purpose |
|----------|------|--------|---------|
| **R4** | `Long` | Read | Oracle price in nanoerg per token |
| **R5** | `Int` | Read | Block height when price was published; used for freshness validation |

**Note:** Registers R0–R3 are reserved for standard box properties (value, tokens, guarding script, creation height). R4+ store application-specific data.

## Tokens

- **Oracle State NFT** (`OracleTokenId`):
  - **Type:** Singleton token (unique instance across network)
  - **Role:** Authenticates the oracle box as the canonical price source
  - **Quantity:** Expected to be 1 (first token in the box)
  - **Used for:** Authorization and state machine identity
  - **Token ID Rule:** The token's ID is fixed at oracle initialization; all price updates must move this token to the new oracle box, maintaining singleton semantics

## Integration Pattern

### Off-Chain Bot / Oracle Operator
1. **Publish Oracle Update:** Creates a new box containing:
   - The Oracle State NFT
   - Updated price in R4
   - Current block height in R5
   - Sufficient nanoerg value (minimum box value + storage rent)

2. **Transaction Construction:**
   ```ergoscript
   // Pseudo-code: off-chain transaction builder
   val newOracleBox = OutBox(
     value = oracleValue,
     tokens = Seq((OracleTokenId, 1L)),
     R4 = newPrice: Long,
     R5 = HEIGHT: Int
   )
   ```

### Consuming Smart Contract
1. **Data Input Inclusion:** References the oracle box as a **data input** (read-only), avoiding UTxO locking conflicts
2. **Conditional Logic:** 
   ```ergoscript
   val validOracle: Boolean = /* validation logic above */
   if (validOracle) {
     // Proceed with swap, mint, or other action using oraclePrice
   } else {
     // Reject transaction or use fallback price
   }
   ```
3. **Context Extension:** May pass price acknowledgment or staleness tolerance via Context extension (if needed for multi-party validation)

### Verification Responsibility
- **Off-chain:** Ensure oracle box is tracked; verify publication height before building dependent transactions
- **On-chain:** The consuming contract validates freshness at transaction validation time (current block height available via `HEIGHT`)

## Related Contracts

Without access to the full project codebase, likely relationships include:

- **PriceConsumer / SwapContract:**  
  Likely calls this validation to gate atomic swaps (e.g., nanoerg ↔ SigmaUSD) contingent on fresh oracle prices

- **OraclePool (State Machine):**  
  May orchestrate multi-oracle consensus; this contract validates individual oracle outputs before aggregation

- **Liquidation / Stability Contract (e.g., SigmaUSD):**  
  Uses oracle prices to determine collateral ratios and trigger liquidations; depends on `validOracle`

- **DEX Router / Price Feed Aggregator:**  
  Selects among multiple oracle boxes; this template ensures only fresh prices are consumed

---

## Additional Notes

- **Soft Fork Compatibility:** The script uses standard Ergo opcodes and `HEIGHT` (a blockchain context variable); compatible with current protocol
- **Storage Rent Consideration:** Oracle boxes should maintain sufficient nanoerg value to account for Ergo's storage rent fees over time
- **Block Time Assumption:** The 30-block window assumes ~10-second block times; for production, adjust to match network conditions
- **Register Type Mismatch:** R5 is read as `Int` but assigned to `Long` variable; Ergo will implicit widen, but explicit casting improves clarity