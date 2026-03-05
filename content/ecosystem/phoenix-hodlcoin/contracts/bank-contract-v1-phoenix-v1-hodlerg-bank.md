---
title: PhoenixErgo/phoenix-hodlcoin-contracts — phoenix_v1_hodlerg_bank.es
description: "ErgoScript contract analysis: hodlERG/contracts/bank_contract/v1/ergoscript/phoenix_v1_hodlerg_bank.es"
tags: [phoenixergo, phoenix-hodlcoin-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/PhoenixErgo/phoenix-hodlcoin-contracts"
contract_file: hodlERG/contracts/bank_contract/v1/ergoscript/phoenix_v1_hodlerg_bank.es
project: phoenixergo-phoenix-hodlcoin-contracts
---
# Phoenix HodlERG Bank Contract Analysis

## Purpose

This contract manages the reserve pool and token supply for the **hodlERG protocol**, a bonding curve mechanism that allows users to mint hodlERG tokens by depositing ERG (the Ergo native asset) and burn them to withdraw ERG at a dynamically calculated price. The contract enforces the invariants that preserve the bonding curve relationship and ensures proper fee distribution across mint and burn transactions.

---

## Inputs / Outputs

### Inputs
- **Bank Box (SELF)**: The singleton state box containing:
  - ERG reserve (nanoERG value)
  - hodlERG token supply locked in the bank
  - Metadata in registers (R4–R8)
  - Bank Singleton NFT (for authentication)

- **Proxy Box**: Facilitates the transaction but is not directly validated in this contract (validation occurs at the Proxy level)

### Outputs

**Mint Transaction:**
- `OUTPUTS(0)`: Recreated Bank Box with updated reserve and hodlERG token amount
- `OUTPUTS(1)`: Buyer's payment box (containing newly minted hodlERG and change)
- `OUTPUTS(2)`: Miner fee box
- `OUTPUTS(3)`: Transaction operator fee box

**Burn Transaction:**
- `OUTPUTS(0)`: Recreated Bank Box with decreased reserve and returned hodlERG tokens
- `OUTPUTS(1)`: Buyer's withdrawal box (containing ERG minus fees)
- `OUTPUTS(2)`: Phoenix fee box (sends `devFeeAmount` to the fee contract)
- `OUTPUTS(3)`: Miner fee box
- `OUTPUTS(4)`: Transaction operator fee box

---

## Key Logic

### Core Invariants

1. **Bank Box Recreation**: The output bank box must:
   - Maintain the same contract bytecode (ErgoTree)
   - Preserve the Bank Singleton NFT (State NFT)
   - Hold at least `minBankValue` nanoERG
   - Keep the hodlERG token ID unchanged with ≥1 token retained
   - Preserve all register values (R4–R8)

2. **Bonding Curve Price Calculation**:
   ```
   price = (reserve * precisionFactor) / hodlERGInCirculation
   ```
   Where:
   - `hodlERGInCirculation = totalTokenSupply - hodlERGInBank`
   - The price increases monotonically as reserve grows or supply decreases

### Mint Transaction (`isMintTx = true`)

- **Prerequisite**: `hodlERGCircDelta > 0` (hodlERG amount decreases in bank, so tokens are minted)
- **Validation**:
  - `expectedAmountDeposited = (hodlERGCircDelta * price) / precisionFactor`
  - Reserve must increase by **at least** `expectedAmountDeposited`: `reserveOut ≥ reserveIn + expectedAmountDeposited`
  - This ensures users deposit the correct amount of ERG at the current bonding curve price

### Burn Transaction (`isMintTx = false`)

- **Prerequisite**: `hodlERGCircDelta ≤ 0` (hodlERG amount increases in bank, so tokens are burned)
- **Fee Structure**:
  - **Bank Fee** (`bankFeeNum`): Portion retained in reserve to increase future prices
  - **Dev Fee** (`devFeeNum`): Portion sent to Phoenix fee contract (authenticated via bytecode hash)
  - Both fees are calculated as: `(expectedAmountBeforeFees * feeNumerator) / feeDenom` where `feeDenom = 1000`

- **Validation**:
  - `hodlCoinsBurned = hodlERGOut - hodlERGIn` (positive when burning)
  - `expectedAmountBeforeFees = (hodlCoinsBurned * price) / precisionFactor`
  - Reserve must decrease by exactly: `reserveOut = reserveIn - expectedAmountBeforeFees + bankFeeAmount`
  - Phoenix fee box must receive exactly `devFeeAmount` at the fee contract address

---

## Registers Used

| Register | Type | Purpose | Mutability |
|----------|------|---------|-----------|
| **R4** | `Long` | `totalTokenSupply` – Total hodlERG ever minted (including circulating + in bank) | Immutable |
| **R5** | `Long` | `precisionFactor` – Scaling factor for BigInt arithmetic in price calculations | Immutable |
| **R6** | `Long` | `minBankValue` – Minimum nanoERG required in bank box at all times | Immutable |
| **R7** | `Long` | `bankFeeNum` – Numerator for bank fee; e.g., 50 = 5% of 1000 | Immutable |
| **R8** | `Long` | `devFeeNum` – Numerator for dev fee; e.g., 30 = 3% of 1000 | Immutable |

All registers are **read-only** after box creation; the contract enforces they remain unchanged across transactions.

---

## Tokens

### Token 1: Bank Singleton NFT
- **Index**: `SELF.tokens(0)`
- **Amount**: Always 1 (Singleton / State NFT)
- **Purpose**: Authenticates this as the unique bank box; prevents creation of multiple competing banks
- **Invariant**: Amount never changes; token ID must be preserved in outputs

### Token 2: hodlERG Token
- **Index**: `SELF.tokens(1)`
- **ID**: `HodlERGTokenId` (compile-time or initialization constant)
- **Amount**: Varies based on transaction type
  - **Decreases on mint** (users receive hodlERG)
  - **Increases on burn** (users return hodlERG)
- **Constraint**: At least 1 token must remain in the bank box at all times (`hodlERGOut ≥ 1`)
- **Purpose**: Represents the protocol's token supply; minting/burning adjusts the supply curve

---

## Integration Pattern

### Off-Chain Bot / dApp