---
title: LiliumErgo/scala-api — SaleLP.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/SaleLP.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/SaleLP.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: SaleLP

## Purpose

This contract guards Liquidity Provider (LP) tokens during a Lilium protocol sale transaction. It enforces two paths: either the LP is consumed in a valid sale (distributing fees to the artist, Lilium, and transaction operator), or it is refunded to the artist with only miner fees deducted. The contract maintains state across sales via a Singleton token and decrements LP supply until exhaustion.

---

## Inputs / Outputs

### Inputs Expected

**Sale Path (`isSale == true`, INPUTS.size > 1):**
- `INPUTS(0)` – **State Box**: Contains the Singleton token, tracks global sale state
- `INPUTS(1)` – **Buyer Proxy Box**: Initiates the purchase action
- `SELF` – **SaleLP Box**: The guarded LP box being spent

**Refund Path (INPUTS.size == 1):**
- `SELF` – **SaleLP Box**: The guarded LP box being refunded

### Outputs Expected

**Sale Path:**
- `OUTPUTS(0)` – **NFT Issuer Box**: Receives minted/transferred NFT to buyer
- `OUTPUTS(1)` – **State Box Out**: Updated state singleton box
- `OUTPUTS(2)` – **User Fee Box**: Payment to artist
- `OUTPUTS(3)` – **Lilium Fee Box**: Payment to Lilium protocol
- `OUTPUTS(4)` or `OUTPUTS(5)` – **Miner Fee Box**: Mining reward (position shifts based on `isLastSale`)
- `OUTPUTS(5)` or `OUTPUTS(6)` – **TX Operator Fee Box**: Operator compensation
- `OUTPUTS(4)` (if not last sale) – **SaleLP Continuation Box**: Recreated SaleLP with decremented LP count

**Refund Path:**
- `OUTPUTS(0)` – **User/Artist Box**: Returns all funds minus miner fee to artist
- `OUTPUTS(1)` – **Miner Fee Box**: Miner reward

---

## Key Logic

### Sale Validation (`isSale == true`)

The contract validates a multi-step transaction by checking:

1. **State Box Integrity**
   - Input state box (INPUTS(0)) must carry the correct Singleton token ID
   - Ensures atomic coordination with global protocol state

2. **Self-Recreation (if not final sale)**
   - Decrements `R5` (LP amount) by 1
   - Calculates required fund outflows: `_minBoxValue + minerFee + liliumFee + _txOperatorFee + minerFee`
   - Verifies remaining ERG in continuation box equals: `SELF.value - fundsToSpend`
   - Ensures continuation box has identical `propositionBytes` (same script) and tokens (Singleton)
   - Guarantees the state machine can continue to the next sale

3. **Final Sale Handling (`isLastSale == true`)**
   - When LP count reaches 1 (one final token exists), the continuation box is NOT created
   - Validates that Singleton tokens in all outputs total < 2 (effectively burned/removed from circulation)
   - Outputs shift by one position (miner fee moves to OUTPUTS(4), operator fee to OUTPUTS(5))

### Refund Validation (`isSale == false`)

1. **Artist Authorization**
   - Retrieves artist's SigmaProp from `R4`
   - Requires artist signature via `sigmaProp(validRefundTx) && artistSigmaProp`

2. **Fund Distribution**
   - User/artist receives: `SELF.value - _minerFee`
   - Box must be locked to artist's SigmaProp
   - Miner fee box receives exactly `_minerFee`

3. **Token Cleanup**
   - All outputs must have zero tokens (Singleton token is burned)
   - Prevents orphaned state tokens

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Artist's Sigma protocol proposition; required to authorize refund path |
| **R5** | `Long` | Current LP (Liquidity Provider token) amount; decremented with each sale; read to determine `isLastSale` and calculate state machine continuation |
| **R6–R9** | — | Unused |

---

## Tokens

### Singleton / State NFT

- **Token ID**: `stateSingletonTokenId` (retrieved from `SELF.tokens(0)._1`)
- **Quantity**: 1 per box (logically a "Singleton," though two instances exist in protocol)
- **Purpose**: 
  - Identifies and authenticates the SaleLP box
  - Verified in State Box input to ensure correct protocol state
  - Burned (count reduced below 2) on final sale to signal collection completion
  - Used to prevent UTXO set pollution and enforce state machine atomicity

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Sale Transaction Construction**
   - Locate the current SaleLP box (by Singleton token)
   - Locate the State Box (also by Singleton)
   - Fetch Buyer Proxy box (initiation signal)
   - Construct six or seven output boxes depending on `isLastSale` flag
   - Calculate and distribute fees:
     - Artist fee → OUTPUTS(2)
     - Lilium fee → OUTPUTS(3)
     - Miner fee → OUTPUTS(4) or OUTPUTS(4) (shifts for final sale)
     - Operator fee → OUTPUTS(5) or OUTPUTS(6)
   - If not final sale, recreate SaleLP at OUTPUTS(4) with:
     - Decremented `R5 = amountLP - 1`
     - Reduced ERG: `SELF.value - (minBoxValue + minerFee + liliumFee + txOperatorFee + minerFee)`
     - Same Singleton token

2. **State Machine Continuation**
   - After each sale, verify the continuation SaleLP box is created (unless final)
   - Index and track `R5` to predict number of remaining sales
   - On final sale, verify Singleton tokens are removed