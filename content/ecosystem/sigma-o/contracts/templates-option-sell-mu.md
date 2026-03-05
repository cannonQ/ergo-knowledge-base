---
title: ThierryM1212/SigmaO — Option_Sell.mu.es
description: "ErgoScript contract analysis: contract/templates/Option_Sell.mu.es"
tags: [thierrym1212, sigmao, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
contract_file: contract/templates/Option_Sell.mu.es
project: thierrym1212-sigmao
---
# ErgoScript Contract Analysis: Option_Sell.mu.es

## Purpose

This contract manages the **seller-side logic for a European/American style options contract** within the SigmaO protocol. It allows option sellers to post sell orders, validates option pricing using a Black-Scholes approximation (with oracle-sourced underlying asset prices), and handles either option delivery to buyers or contract closure when frozen or emptied.

---

## Inputs / Outputs

### Inputs
- **SELF (INPUTS(0))**: The Sell box itself, containing:
  - Option tokens (NFT representing the option contract)
  - ERG reserve (minimum: `TxFee + BoxMinValue`)
  - Seller metadata in R4–R7

- **INPUTS(1)**: Buyer's payment box (implied; contract size = 2 required for valid sell)

- **Data Inputs**: 
  - **CONTEXT.dataInputs(0)**: Oracle box (e.g., SigUSD, Spectrum AMM LP) providing current `oraclePrice` of the underlying asset

### Outputs

**Two paths:**

1. **Sell Execution Path** (normal):
   - **OUTPUTS(0)**: Replicated Sell box (state machine continuation) with:
     - Remaining option tokens (if any)
     - Updated ERG value
     - Preserved seller PK, option creation box reference, parameters in R4–R7
   - **OUTPUTS(1)**: Buyer's delivery box receiving purchased options + change

2. **Contract Closure Path** (frozen or empty):
   - **OUTPUTS(0)**: Seller's wallet (protected by `sellerPK`)
     - All remaining ERG + tokens returned (minus `TxFee`)
   - Must have exactly 2 outputs

---

## Key Logic

### Validation Conditions (Plain English)

1. **Basic Invariants**
   - `validOption`: SELF token[0] must match the Option Token ID (from creation box)
   - `validBasicReplicatedOutput0`: Output 0 replicates SELF with:
     - Same contract script (`propositionBytes`)
     - Minimum reserve value maintained
     - Seller PK, option creation box, and parameters unchanged
     - Token either preserved or zeroed (not partially lost)

2. **Frozen or Empty State** (`validCloseSellContract`)
   - Triggered if:
     - `isFrozen` = current timestamp ≥ (maturity date − freeze delay)
     - **OR** `isEmpty` = no option tokens left in SELF
   - Effect: Seller can unilaterally close and recover ERG (minus TX fee)
   - Output must be signed by `sellerPK`; exactly 2 outputs required

3. **Normal Sell Execution** (`validSellOption`)
   - Preconditions:
     - **Not frozen** and **not empty**
     - **2 inputs + ≥1 data input** (oracle box)
   - **Oracle Validation**: `{{validOracle}}` (template placeholder—checks oracle box authenticity/staleness)
   - **Black-Scholes Pricing**:
     - Computes **intrinsic value**: max(spot − strike, 0) × share size for calls; max(strike − spot, 0) × share size for puts
     - Computes **time value** using approximated SQRT function:
       - Volatility (`sigmaVol`) per 1000 basis points
       - Spread factor (`K1`) penalizes out-of-money options
       - American factor (`K2`) adds premium for early exercise right
     - Final option price = intrinsic + time value (capped at intrinsic for out-of-money)
   - **Output Validation**:
     - Output 0: Total ERG unchanged (premium collected separately in fees)
     - Output 1: Buyer receives `deliveredOptions` tokens
     - dApp fee: `totalOptionPrice × dAppUIFeePerThousand / 1000` sent to dApp UI wallet
     - Issuer payment: `totalOptionPrice` minimum value

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | **Seller's public key** — authorizes contract closure |
| **R5** | `Box` | **Option creation box** — reference to contract parameters; box ID = option token ID |
| **R6** | `Coll[Long]` | **Parameters array** (6 elements): <br> [0] `sigma` = volatility per 1000 <br> [1] `K1` = spread factor per 1000 <br> [2] `K2` = American factor per 1000 <br> [3] `FreezeDelay` = time before maturity when order freezes <br> [4] `dAppUIFeePerThousand` = fee per 1000 to dApp UI <br> [5] unused |
| **R7** | `Coll[Byte]` | **dApp UI fee recipient's ErgoTree** — serialized contract for fee routing |
| **R8** (read from creation box) | `Coll[Long]` | **Option specs** (from creation box): <br> [0] `isCall` (0 = call, 1 = put) <br> [1] `isEuropean` (0 = European, 1 = American) <br> [2] `shareSize` = tokens per option <br> [3] `maturityDate` = Unix timestamp <br> [4] `strikePrice` = nanoERG per asset unit <br> [5] unused <br> [6] `TxFee` = transaction fee |

---

## Tokens

### Token[0]: Option NFT

- **Token ID**: Derived from **option creation box ID** (`optionCreationBox.id`)
- **Purpose**: 
  - Acts as **singleton/state NFT** tracking the option contract
  - Sellers hold it in SELF to authorize selling the underlying option
  - Decremented when options are delivered to buyers
  - Zeroed when all options sold → contract closes
- **Tracking**: Quantity in SELF vs. OUTPUTS(0) determines `deliveredOptions`

### Native