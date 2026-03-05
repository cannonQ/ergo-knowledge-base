---
title: ThierryM1212/SigmaO — ValidOracleAMM.mu.es
description: "ErgoScript contract analysis: contract/templates/ValidOracleAMM.mu.es"
tags: [thierrym1212, sigmao, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
contract_file: contract/templates/ValidOracleAMM.mu.es
project: thierrym1212-sigmao
---
# ErgoScript Contract Analysis: ValidOracleAMM

## Purpose

This contract fragment validates oracle data for an Automated Market Maker (AMM) by verifying that an oracle box contains authentic oracle and underlying asset tokens, then derives a price feed from the box's value and token quantities. It serves as a safety gate ensuring only legitimate price data from designated oracles influences AMM swap operations.

## Inputs / Outputs

**Inputs:**
- **Oracle Box** (`oracleBox`): A UTXO that must contain:
  - Native tokens at index `0` (the oracle credential token)
  - Native tokens at index `2` (the underlying asset being priced)
  - A value (in nanoErgs) used in the price calculation

**Outputs:**
- Implicitly: Any AMM box or swap transaction that depends on the validated `oraclePrice` value; the contract does not directly produce outputs but gates downstream transaction validity.

## Key Logic

The contract enforces two critical invariants:

1. **Oracle Token Validation** (`oracleBox.tokens(0)._1 == OracleTokenId`):
   - Verifies that the box's first token is the designated Oracle Token (a Singleton or State NFT).
   - Prevents unauthorized or stale oracle boxes from being accepted.
   - Uses **Token ID rule** — the token's unique identifier must match a hardcoded constant.

2. **Underlying Asset Verification** (`oracleBox.tokens(2)._1 == UnderlyingAssetTokenId`):
   - Confirms that the box's third token slot holds the specific asset being priced (e.g., USDT, GORT, or SigmaUSD).
   - Ensures price feeds are matched to their correct underlying assets.

3. **Price Derivation**:
   ```
   oraclePrice = oracleBox.value / (oracleBox.tokens(2)._2 / UnderlyingAssetDecimalFactor)
   ```
   - **Numerator**: The box's nanoErg balance (value in base Ergo units).
   - **Denominator**: Token quantity adjusted for decimal places.
   - **Result**: A ratio representing Ergs-per-asset-unit; used by the AMM to set swap rates.
   - Decimal normalization (`UnderlyingAssetDecimalFactor`) handles tokens with varying precision (e.g., 6-decimal stablecoins vs. 2-decimal assets).

## Registers Used

No explicit register reads/writes in this fragment. However, the context implies:

- **R4–R9** (context-dependent): Likely in the calling transaction context, register storage for:
  - `OracleTokenId` (constant, typically in R4 or hardcoded)
  - `UnderlyingAssetTokenId` (constant, typically in R4 or hardcoded)
  - `UnderlyingAssetDecimalFactor` (constant, typically in R4 or hardcoded)

These constants are typically **segregated** as compile-time or Context extension parameters rather than stored in box registers.

## Tokens

1. **Oracle Token** (index `0`):
   - Type: **Singleton** or **State NFT** (unique token ID).
   - Purpose: Authentication — proves the box is an official oracle data point.
   - Origin: Issued by a trusted oracle operator.

2. **Underlying Asset Token** (index `2`):
   - Type: **Native token** (fungible, but may be a stablecoin like SigmaUSD, Dexy, or GORT).
   - Purpose: Identifies the asset being priced (e.g., SigmaUSD reserve, GORT governance token).
   - Quantity: Used in denominator of price calculation; tied to decimal factor.

## Integration Pattern

**Off-chain Bot / Headless dApp Responsibilities:**

1. **Oracle Update Loop**:
   - Monitor external price feeds (e.g., from Coingecko, CoinMarketCap, or on-chain aggregators).
   - Construct a new oracle UTXO with:
     - Nanoerg value = intended price numerator
     - Token `0` = oracle credential token (copied from previous oracle box)
     - Token `2` = underlying asset tokens (updated quantity if price changes)
   - Sign and submit transaction containing the new oracle box.

2. **AMM Consumption**:
   - When an AMM swap is triggered, it reads the oracle box as a **Data input** (non-consumed).
   - Validates `validOracle == true` via this contract.
   - Extracts `oraclePrice` and enforces price bounds (e.g., minimum acceptable rate).

3. **Verification in Context Extension**:
   - Constants (`OracleTokenId`, `UnderlyingAssetTokenId`, `UnderlyingAssetDecimalFactor`) may be passed via **Context extension** or hardcoded in ErgoTree.
   - Off-chain code must match these constants when constructing transactions.

4. **Atomic Swap Pattern**:
   - The oracle validation is typically part of a larger multi-stage contract ensuring:
     - Price feed is fresh and valid.
     - Swap amounts respect the oracle price.
     - Liquidity is sufficient.

## Related Contracts

Based on naming and structure, this contract integrates with:

1. **AMM Liquidity Pool Contract**:
   - Consumes the oracle box as data input.
   - Uses `validOracle` and `oraclePrice` to validate swap amounts.

2. **Oracle Update Contract** (if separate):
   - Manages oracle box state transitions.
   - Ensures only authorized operators can update price feeds.
   - Maintains the Singleton token ID consistency.

3. **Potential Dexy / SigmaUSD Integration**:
   - If `UnderlyingAssetTokenId` is SigmaUSD, the oracle feeds reserve-backing ratios.
   - If underlying is GORT, may relate to governance token pricing.

4. **Multi-stage Contract Pattern**:
   - This validation logic is a **stage** or **guard clause** within a larger state machine.
   - Other stages handle liquidity provision, swap settlement, and fee distribution.

---

## Security Notes

- **No freshness check**: The contract does not verify the oracle box's age;