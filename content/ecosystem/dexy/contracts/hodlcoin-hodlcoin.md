---
title: kushti/dexy-stable — hodlcoin.es
description: "ErgoScript contract analysis: contracts/hodlcoin/hodlcoin.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/hodlcoin/hodlcoin.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: hodlcoin.es

## Purpose

HodlCoin is a collateralized stablecoin contract that implements an algorithmic reserve-backed token system where users can mint hodlERG tokens by depositing ERG into a reserve, or burn hodlERG to withdraw ERG at a price determined by the reserve-to-circulation ratio. The contract also manages developer fee accumulation and withdrawal through a treasury mechanism.

## Inputs / Outputs

**Inputs:**
- **BankBox** (SELF): The singleton state box holding:
  - Native ERG value (reserve + treasury)
  - Token 0: hodlERG token (the stablecoin)
  - Token 1: hodlERG Bank NFT (State NFT for singleton authentication)
  - R4 register: Treasury balance (Long)

**Outputs:**
- **Output 0 (BankBox)**: Updated singleton state box with:
  - Modified ERG reserve
  - Updated hodlERG token quantity
  - Potentially updated treasury in R4
  - Same token IDs preserved
- **Outputs 1-3** (conditional, treasury withdrawal only): Three equal-value boxes sent to hardcoded developer PKs

## Key Logic

The contract enforces three mutually exclusive actions, determined by analyzing deltas:

### **1. Mint Action** (`hodlCoinsCircDelta >= 0`)
- User deposits ERG to mint new hodlERG tokens
- **Price formula**: `price = (reserve × 1000) / circulatingSupply`
- **Invariant**: ERG deposited must equal `tokensMinted × price / 1000`
- Treasury remains unchanged
- Reserve increases by deposit amount

### **2. Burn Action** (`hodlCoinsCircDelta < 0` AND no treasury withdrawal)
- User burns hodlERG to withdraw ERG
- **Fees applied** (on withdrawn amount):
  - Protocol fee: 3% → stays in reserve
  - Developer fee: 0.3% → transferred to treasury
- **Invariant**: ERG withdrawn = `tokensBurned × price × (1 - 0.03 - 0.003) / 1000`
- Reserve decreases by withdrawal + dev fee amounts
- Treasury increases by dev fee amount

### **3. Treasury Withdrawal Action** (`treasuryDelta < 0`)
- Authorized withdrawal of accumulated developer fees
- Treasury split **equally among 3 hardcoded developer addresses**:
  - `9hHondX3uZMY2wQsXuCGjbgZUqunQyZCNNuwGu6rL7AJC8dhRGa`
  - `9gnBtmSRBMaNTkLQUABoAqmU2wzn27hgqVvezAC9SU1VqFKZCp8`
  - `9iE2MadGSrn1ivHmRZJWRxzHffuAk6bPmEv6uJmPHuadBY8td5u`
- Minimum withdrawal threshold: 0.05 ERG per developer (dust prevention)
- hodlERG token quantity in BankBox must remain unchanged

### **General Conditions** (all actions)
- BankBox output maintains minimum 0.1 ERG value
- BankBox ErgoTree (proposition bytes) unchanged (State machine invariant)
- Both token IDs conserved (hodlERG + Bank NFT)
- Treasury balance never negative

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R4** | `Long` | Treasury balance (accumulated dev fees) | Read from input; written to output |
| **R5–R9** | — | Unused | — |

## Tokens

| Token Index | Type | Purpose | Rules |
|-------------|------|---------|-------|
| **Token 0** | Native Token (hodlERG) | Stablecoin; minted/burned per reserve ratio | Total supply capped at `97,739,924 ERG` (same as ERG emission); circulating supply = total - bank balance |
| **Token 1** | State NFT (hodlERG Bank) | Singleton authenticator; ensures only one BankBox can update per transaction | Must be present in both input and output; ID immutable |

**Token Supply Invariant:**
- `hodlCoinsCirculating = 97,739,924,000,000,000 - hodlCoinsInBank`
- Initial burn: 1 hodlERG token removed post-initialization to prevent zero-division in price calculation

## Integration Pattern

**Off-chain Bot / Headless dApp must:**

1. **Mint Transaction Construction:**
   - Read current BankBox (data input or UTXO scan)
   - Calculate mint price: `price = (reserve × 1000) / circulatingSupply`
   - Build transaction:
     - Input: BankBox + user's ERG deposit
     - Output 0: Updated BankBox with new hodlERG quantity, reserve increased
     - Output 1+: hodlERG tokens to user's address
   - Verify: `depositAmount == mintQuantity × price / 1000`

2. **Burn Transaction Construction:**
   - Read BankBox
   - Calculate burn price (same formula)
   - Calculate fees: `fee = withdrawAmount × 0.03`, `devFee = withdrawAmount × 0.003`
   - Build transaction:
     - Input: BankBox + user's hodlERG tokens
     - Output 0: BankBox with reduced hodlERG, reserve decreased, treasury increased by devFee
     - Output 1+: ERG to user (withdrawAmount - fee)
   - Verify fee deductions are correct

3. **Treasury Withdrawal (privileged):**
   - Authorized signer must construct:
     - Input: BankBox
     - Outputs 1-3: Three boxes with equal ERG amounts to dev addresses
     - Verify: 3 outputs with correct PKs, equal values, dust threshold met

4. **Data Input Strategy:**
   - BankBox can be referenced as data input in user transactions (read-only), allowing off-chain indexing without consuming the box
   - Actual state mutation requires