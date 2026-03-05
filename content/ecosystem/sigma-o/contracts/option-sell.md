---
title: ThierryM1212/SigmaO — Option_Sell.es
description: "ErgoScript contract analysis: contract/Option_Sell.es"
tags: [thierrym1212, sigmao, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
contract_file: contract/Option_Sell.es
project: thierrym1212-sigmao
---
# ErgoScript Contract Analysis: Option_Sell.es

## Purpose

This contract implements the **seller side** of a European/American options market using Black-Scholes pricing emulation on Ergo. A seller deposits option tokens (representing the right to buy/sell underlying assets at a strike price) and receives nanoERG premiums from buyers, with pricing dynamically adjusted based on oracle data, volatility, time-to-maturity, and moneyness.

---

## Inputs / Outputs

### Inputs
1. **SELF (Spend)**: The Sell contract Box containing:
   - Option tokens to be sold (token0)
   - Seller's PK, option metadata, pricing parameters in registers
   - Minimum nanoERG value: `2,100,000` (BoxMinValue + TxFee)

2. **INPUTS(1)** (optional, for option sales): Buyer's input or payment source
3. **Data Input (CONTEXT.dataInputs(0))**: Oracle Box providing current underlying asset price and height validation

### Outputs
- **OUTPUT(0)**: Replicated Sell Box (same contract) with:
  - Remaining option tokens after sale
  - Updated state (same R4–R7 registers)
  - Minimum reserve value maintained

- **OUTPUT(1)**: dApp UI fee recipient Box (2 nanoERG minimum)
- **OUTPUT(2)** (implicit): Issuer payment to seller for premium revenue

---

## Key Logic

### Validation Branches

#### 1. **Valid Option Sale** (`validSellOption`)
Executed when **NOT frozen** AND **2 inputs** AND **oracle data input present**:

- **Oracle Verification**:
  - Oracle Box token must match `OracleTokenId`
  - Oracle height ≤ 30 blocks old
  - Extracts current price in nanoERG per token unit

- **Black-Scholes Premium Calculation**:
  ```
  Intrinsic Value = max(0, (Spot - Strike) × ShareSize)  [Call]
                   max(0, (Strike - Spot) × ShareSize)  [Put]
  
  Time Value = 0.4 × σ × Strike × √Duration × (1 + K1 × √|Spot−Strike|/(Strike×Duration))
  
  American Premium = (1 + K2 × √Duration) × European Premium
  ```
  - Uses precomputed SQRT lookup table for approximation (avoids overflow)
  - Caps option price: Call ≤ Spot × ShareSize, Put ≤ Strike × ShareSize

- **State Mutation**:
  - Calculates `deliveredOptions = selfToken0._2 - output0Token0._2`
  - `totalOptionPrice = deliveredOptions × optionPrice / UnderlyingAssetDecimalFactor`
  - Deducts dApp UI fee: `dAppUIFee = totalOptionPrice × dAppUIFeePerThousand / 1000`
  - Seller receives: `valueIn - TxFee + totalOptionPrice - dAppUIFee`

- **Invariants Enforced**:
  - OUTPUT(0) replicates self with same R4–R7
  - OUTPUT(0) token count decreases (options sold)
  - Value balance: inputs ≥ outputs + TxFee
  - OUTPUT(1) receives UI fee to dApp address

#### 2. **Valid Replicated Output** (`validBasicReplicatedOutput0`)
When continuing the contract state (no sale):
- Output script hash = SELF script hash (eUTXO state machine pattern)
- Same SigmaProp seller PK, option creation box, pricing parameters
- Token remains option token or is empty
- Output value ≥ reserve minimum

#### 3. **Valid Close Sell Contract** (`validCloseSellContract`)
Triggered when **frozen** OR **empty** (all options sold/withdrawn):
- OUTPUT(0) transfers to `sellerPK.propBytes` (seller redeems box)
- Output value ≥ valueIn - TxFee (seller receives remaining ERG)
- Token transferred unchanged to seller
- Exactly 2 outputs (seller + dApp fee recipient)

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Seller's public key (Sigma proposition for spending authorization) |
| **R5** | `Box` | Reference to Option Creation Box (boxId = optionTokenId); immutable source of truth |
| **R6** | `Coll[Long]` | Pricing parameters: `[sigma, K1, K2, FreezeDelay, dAppUIFeePerThousand]` |
| **R7** | `Coll[Byte]` | dApp UI ErgoTree (recipient for platform fees) |
| **R8** (read-only from R5) | `Coll[Long]` | Option metadata from creation box: `[isCall, isEuropean, shareSize, maturityDate, strikePrice, _, TxFee]` |

---

## Tokens

### Native Token: Option Token (NFT-like)
- **Token ID**: `optionTokenIDIn = optionCreationBox.id` (singleton rule)
- **Purpose**: Represents N option contracts to sell
- **Validation**: 
  - Must appear in SELF token(0)
  - Decreases in OUTPUT(0) as options are sold
  - Can be fully withdrawn when frozen/empty
- **Quantity**: Tracked as `selfToken0._2` (amount)

### Oracle Token
- **Token ID**: `OracleTokenId` (constant, defined externally)
- **Location**: `CONTEXT.dataInputs(0)` (data input, not spent)
- **Purpose**: Authenticates oracle data source

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Monitor Oracle**:
   - Watch oracle Box for price updates every ~5 blocks
   - Extract `R4: Long` (nanoERG price) and `R5: Int` (block height)
   - Validate age: `HEIGHT ≤ oracleHeight + 30`