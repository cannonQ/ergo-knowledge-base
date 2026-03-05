---
title: PhoenixErgo/phoenix-hodlcoin-contracts — phoenix_v1_hodltoken_proxy.es
description: "ErgoScript contract analysis: hodlToken/contracts/proxy_contract/v1/ergoscript/phoenix_v1_hodltoken_proxy.es"
tags: [phoenixergo, phoenix-hodlcoin-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/PhoenixErgo/phoenix-hodlcoin-contracts"
contract_file: hodlToken/contracts/proxy_contract/v1/ergoscript/phoenix_v1_hodltoken_proxy.es
project: phoenixergo-phoenix-hodlcoin-contracts
---
# Phoenix HodlToken Proxy Contract Analysis

## Purpose

This contract guards the **proxy box** in the Phoenix HodlToken protocol, a multi-stage state machine that orchestrates minting, burning, and reserve management for hodlTokens. The proxy acts as an intermediary escrow that validates token transfers between the Bank box and user wallets, ensuring fee collection and atomicity across mint/burn/deposit/refund transactions.

---

## Inputs / Outputs

### Transaction Structure (4 Cases)

#### 1. **Mint Transaction**
- **Inputs:** 
  - `INPUTS(0)`: Bank box (holds HodlToken supply and reserve)
  - `INPUTS(1)`: Proxy box (SELF) containing BaseTokens
- **Outputs:**
  - `OUTPUTS(0)`: Updated Bank box
  - `OUTPUTS(1)`: Buyer's receiving box (HodlTokens + minBoxValue ERG)
  - `OUTPUTS(2)`: Miner fee box
  - `OUTPUTS(3)`: TxOperator fee box

#### 2. **Burn Transaction**
- **Inputs:** 
  - `INPUTS(0)`: Bank box
  - `INPUTS(1)`: Proxy box (SELF) containing HodlTokens to burn
- **Outputs:**
  - `OUTPUTS(0)`: Updated Bank box
  - `OUTPUTS(1)`: Buyer's box (BaseTokens returned)
  - `OUTPUTS(2)`: *Optional* Phoenix dev fee box
  - `OUTPUTS(3)` or `OUTPUTS(4)`: Miner fee
  - Last: TxOperator fee box

#### 3. **Reserve Deposit Transaction**
- **Inputs:** 
  - `INPUTS(0)`: Bank box
  - `INPUTS(1)`: Proxy box (SELF) containing BaseTokens
- **Outputs:**
  - `OUTPUTS(0)`: Updated Bank box
  - `OUTPUTS(1)`: Miner fee box
  - `OUTPUTS(2)`: TxOperator fee box

#### 4. **Refund Transaction**
- **Inputs:** 
  - `INPUTS(0)`: Proxy box (SELF)
- **Outputs:**
  - `OUTPUTS(0)`: Buyer's refund box
  - `OUTPUTS(1)`: Miner fee box

---

## Key Logic

### Core Validation Rules

#### **Bank Box Validation**
```
isValidBank: INPUTS(0) must contain:
  - Token 0: bankSingletonTokenId (State NFT)
  - Token 1: hodlTokenId
  - Token 2: Reserve (BaseTokens)
```
The singleton token authenticates the Bank box as the unique protocol state.

#### **Mint Transaction Flow**
1. **Detect mint:** `hodlTokensCircDelta > 0` (circulating HodlTokens increased)
2. **Validate buyer box:**
   - Receives exactly `hodlTokensCircDelta` HodlTokens
   - Contract = `buyerPK` (buyer's Sigma proposition)
   - Value = `minBoxValue` ERG
3. **Validate fee structure:**
   - Miner fee box identified by blake2b256 hash of ErgoTree
   - TxOperator fee ≥ `$minTxOperatorFee` (compile-time constant)
4. **Validate output count:** exactly 4 boxes

#### **Burn Transaction Flow**
1. **Detect burn:** `hodlTokensCircDelta < 0` (circulating HodlTokens decreased)
2. **Validate token burning:** SELF contains exact amount burned
3. **Validate base token distribution:**
   - `devAndUserAmount = reserveIn - reserveOut`
   - If 5 outputs: split between dev fee (OUTPUTS(2)) and buyer
   - If 4 outputs: all base tokens go to buyer
   - Equation: `devAndUserAmount == devAmount + userAmount`
4. **Validate output count:** 4 or 5 boxes
5. **Buyer contract must equal** `buyerPK`

#### **Deposit Transaction Flow**
1. **Detect deposit:** `hodlTokensCircDelta == 0` (no token delta)
2. **Validate reserve increase:** `SELF.tokens(0)._2 == (reserveOut - reserveIn)`
3. **Output count:** exactly 3 boxes

#### **Refund Transaction Flow**
- Proxy is only input (Bank not involved)
- Outputs: buyer's refund + miner fee
- No fee validation (minimal transaction)

#### **Universal Fee Validation**
```
validMinerFee(minerFee): 
  Sum all OUTPUTS where blake2b256(propositionBytes) 
  == minerFeeErgoTreeBytesHash must equal minerFee parameter
```

---

## Registers Used

| Register | Type | Purpose | Source |
|----------|------|---------|--------|
| **R4** | `SigmaProp` | `buyerPK` - Buyer's signing key for receiving boxes | Proxy box (SELF) |
| **R5** | `Coll[Byte]` | `bankSingletonTokenId` - State NFT authenticating Bank box | Proxy box (SELF) |
| **R6** | `Coll[Byte]` | `hodlTokenId` - Token ID of HodlTokens | Proxy box (SELF) |
| **R7** | `Long` | `minBoxValue` - Minimum ERG required per box (Storage Rent) | Proxy box (SELF) |
| **R8** | `Long` | `minerFee` - Fee for block inclusion | Proxy box (SELF) |
| **R9** | `Long` | `txOperatorFee` - Fee for off-chain operator | Proxy box (SELF) |

### Bank Box Registers (read-only)
| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | `totalTokenSupply` - Total HodlTokens ever minted |
| **R5** | `Long` | `precisionFactor` - Decimal precision (