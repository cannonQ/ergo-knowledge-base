---
title: kushti/dexy-stable — hodlcoin.es
description: "ErgoScript contract analysis: contracts/hodlcoin/hodlcoin.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/hodlcoin/hodlcoin.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: hodlcoin.es

## Purpose

HodlCoin is a collateralized stablecoin protocol where users deposit ERG (Ergo's native token) into a reserve to mint hodlERG tokens, and burn hodlERG to redeem ERG at a price determined by the reserve ratio. The contract enforces the invariant that the BankBox maintains adequate collateral, applies burn fees (3% protocol fee + 0.3% developer fee), and enables periodic treasury withdrawals to three developer addresses.

## Inputs / Outputs

**Inputs:**
- **BankBox (SELF)**: The singleton state box holding:
  - ERG reserve (balance minus treasury amount)
  - hodlERG token supply (tokens(0))
  - Bank NFT identifier (tokens(1)) — authentication token
  - Treasury accumulator in R4

**Outputs:**
- **Output(0)**: Updated BankBox with preserved ErgoTree, adjusted reserve/treasury, and token counts
- **Output(1–3)** (treasury withdrawal only): Three equal-valued boxes to developer addresses
- Additional outputs created by user during mint/burn (not constrained by this contract)

## Key Logic

The contract validates one of three mutually exclusive actions:

### 1. **Mint Action** (`hodlCoinsCircDelta >= 0`)
- User deposits ERG into the reserve; hodlERG is minted at the current price
- **Price formula**: `price = (reserve × 1000) / circulatingHodlCoins`
- **Validation**: 
  - ERG deposited equals `hodlCoinsMinted × price / 1000`
  - Treasury unchanged (`treasuryDelta == 0`)
  - Reserve increases by exact deposit amount

### 2. **Burn Action** (`hodlCoinsCircDelta < 0`)
- User burns hodlERG to redeem ERG, paying protocol fee (3%) + dev fee (0.3%)
- **Fee calculation**:
  - Redeem amount (before fees) = `hodlCoinsBurned × price / 1000`
  - Protocol fee = `9/1000` of redeem amount
  - Dev fee = `3/1000` of redeem amount
  - User receives = redeem amount − both fees
- **Validation**:
  - Reserve decreases by (user withdrawal + dev fee)
  - Treasury increases by dev fee amount
  - hodlERG tokens removed from circulation

### 3. **Treasury Withdrawal Action** (`treasuryDelta < 0`)
- Dev team withdraws accumulated fees; treasury splits equally to 3 hardcoded addresses
- **Validation**:
  - Treasury delta divides evenly by 3 (no rounding error)
  - Each developer receives `|treasuryDelta| / 3` ERG (minimum 0.05 ERG per box)
  - Each output locks to a specific public key
  - hodlERG supply in BankBox unchanged

### General Constraints (All Actions):
- BankBox minimum value: 10 mERG (storage rent)
- Treasury always ≥ 0 (cannot go negative)
- BankBox ErgoTree unchanged (same script, same spending conditions)
- hodlERG token ID and Bank NFT ID preserved in outputs

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | **Treasury accumulator**: stores ERG fees from burns, withdrawable by devs |

All other registers (R5–R9) are unused; the contract uses only two tokens: hodlERG and the Bank NFT for authentication.

## Tokens

| Token Position | Role | Purpose |
|---|---|---|
| **tokens(0)** | hodlERG (native token) | ERC-20-like stablecoin; quantity tracks mint/burn; total supply fixed at ~97.74M |
| **tokens(1)** | Bank NFT (Singleton) | State machine authentication; presence proves this is the canonical BankBox |

**Token ID Rule**: Both token IDs are immutable across all transactions (enforced by `tokenIdsConserved` check).

## Integration Pattern

**Off-chain bot / dApp workflow:**

1. **Mint hodlERG**:
   - User creates a transaction with:
     - BankBox as input
     - New BankBox as output(0) with updated reserve + minted hodlERG
     - User receives hodlERG in a separate output (not validated by this contract)
   - Off-chain calculates mint amount: `hodlCoinsToMint = (ergDeposited × 1000) / currentPrice`
   - Verifies: `currentPrice = (currentReserve × 1000) / currentCirculation`

2. **Burn hodlERG**:
   - User creates a transaction with:
     - BankBox as input
     - New BankBox as output(0) with reduced hodlERG, updated treasury, reduced reserve
     - User receives ERG redemption in output(1) = `(hodlCoinsBurned × price / 1000) − 3% − 0.3%`
   - Off-chain calculates: `redeemPrice = (currentReserve × 1000) / currentCirculation`

3. **Withdraw Treasury** (dev action):
   - Create transaction with BankBox input
   - Output(0): BankBox with treasury reset to zero
   - Outputs(1–3): Three boxes to hardcoded addresses, each receiving `treasuryAmount / 3`
   - Off-chain verifies 3-way split is exact and each box meets 0.05 ERG minimum

**Context Extension**: None used; all data is on-chain in SELF and output boxes.

## Related Contracts

No other contracts are explicitly referenced in this code. However, the hodlcoin system likely composes with:

- **Reserve management contracts** (if separate): might hold additional ERG collateral off-chain or in a separate utxo
- **Oracle feed** (implied): off-chain price feeds determine the reserve ratio; the contract itself is price-agnostic and only validates reserve accounting
- **Multi-sig or DAO contracts**: the three hardcoded developer addresses may be controlled by a multisig or governance contract

The contract is a **State Machine** with