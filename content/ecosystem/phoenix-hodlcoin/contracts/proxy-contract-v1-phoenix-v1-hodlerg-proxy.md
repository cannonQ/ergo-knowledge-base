---
title: PhoenixErgo/phoenix-hodlcoin-contracts — phoenix_v1_hodlerg_proxy.es
description: "ErgoScript contract analysis: hodlERG/contracts/proxy_contract/v1/ergoscript/phoenix_v1_hodlerg_proxy.es"
tags: [phoenixergo, phoenix-hodlcoin-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/PhoenixErgo/phoenix-hodlcoin-contracts"
contract_file: hodlERG/contracts/proxy_contract/v1/ergoscript/phoenix_v1_hodlerg_proxy.es
project: phoenixergo-phoenix-hodlcoin-contracts
---
# Phoenix HodlERG Proxy Contract Analysis

## Purpose

The Phoenix HodlERG Proxy contract guards temporary custodial boxes that hold ERG during minting and burning operations of the hodlERG token. It validates that users receive correct token/ERG amounts based on dynamic pricing, enforces fee distributions (miner fees, operator fees, protocol fees), and permits refunds if the transaction fails to complete.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Bank box (State NFT) containing:
  - Token 0: Bank Singleton NFT (identified by `bankSingletonTokenId`)
  - Token 1: hodlERG token reserve
  - R4: Total token supply
  - R5: Precision factor
  - R7: Bank fee numerator
  - R8: Dev fee numerator
  - Value: ERG reserve

- **INPUTS(1)** (Mint/Burn only): Proxy box (SELF) containing:
  - Registers R4–R9: Configuration (buyer PK, token IDs, fees)
  - Value: ERG to be locked/unlocked
  - Tokens (Burn only): hodlERG tokens to burn

### Outputs

**Mint Transaction (4 outputs):**
1. Bank box (updated state)
2. Buyer box: hodlERG tokens at `minBoxValue` ERG
3. Miner fee box: `minerFee` ERG to known miner fee address
4. Operator fee box: `txOperatorFee` ERG to operator

**Burn Transaction (5 outputs):**
1. Bank box (updated state)
2. Buyer box: ERG (after fee deductions) at `minBoxValue` minimum
3. Phoenix dev fee box: Protocol share of withdrawn ERG
4. Miner fee box: `minerFee` ERG
5. Operator fee box: `txOperatorFee` ERG

**Refund Transaction (≥2 outputs):**
1. Buyer box: All ERG from proxy + any tokens returned
2. (optional) Miner fee box: `minerFee` ERG

## Key Logic

### Bank Validation
```
isValidBank = INPUTS(0) contains both bankSingletonTokenId and hodlERGTokenId
```
All minting and burning logic is gated by a valid Bank input. If the bank is invalid, only refunds are permitted.

### Mint Transaction Flow
1. **Price Calculation**: `price = (reserveIn × precisionFactor) / hodlERGCircIn`
   - Determines ERG per hodlERG token based on current reserve and circulating supply.

2. **Mint Detection**: `isMintTx = (hodlERGIn > hodlERGOut)`
   - hodlERG tokens are *removed* from bank during minting (supply decreases in bank, increases in buyer).

3. **Amount Validation**: 
   - `expectedAmountDeposited = (hodlERGCircDelta × price) / precisionFactor`
   - Proxy must hold sufficient ERG after deducting `minBoxValue`, `minerFee`, and `txOperatorFee`.

4. **Output Enforcement**:
   - Buyer receives exactly `hodlERGCircDelta` hodlERG tokens.
   - Miner fee box matches blake2b256 hash of known miner ErgoTree.
   - Operator fee must meet minimum (`$minTxOperatorFee`).
   - Exactly 4 outputs required.

### Burn Transaction Flow
1. **Burn Detection**: `hodlERGCircDelta < 0` (hodlERG tokens increase in bank)
   - hodlERG tokens are *added* to bank during burning.

2. **Fee Calculation**:
   - `expectedAmountBeforeFees = (hodlCoinsBurned × price) / precisionFactor`
   - `bankFeeAmount = (expectedAmountBeforeFees × bankFeeNum) / 1000`
   - `devFeeAmount = (expectedAmountBeforeFees × devFeeNum) / 1000`
   - `expectedAmountWithdrawn = expectedAmountBeforeFees - bankFeeAmount - devFeeAmount`

3. **Burn Validation**:
   - Bank token reserve must increase by exactly `SELF.tokens(0)._2` (burned amount).
   - Buyer receives `expectedAmountWithdrawn` ERG (after protocol and bank fees).

4. **Output Enforcement**:
   - Exactly 5 outputs required.
   - Same miner fee and operator fee validation as mint.

### Refund Transaction
- Triggered when bank is invalid (not a valid state machine continuation).
- Buyer receives **all** ERG from proxy box (no fee deductions).
- If proxy holds tokens, **all** tokens must return to buyer.
- Miner fee deducted from buyer's ERG allocation.
- Ensures atomicity: either the full transaction succeeds or proxy reverts to buyer.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | Buyer's public key; controls refund and post-trade fund receipt |
| **R5** | `Coll[Byte]` | Bank Singleton Token ID; identifies valid state box |
| **R6** | `Coll[Byte]` | hodlERG Token ID; authenticates token transfers |
| **R7** | `Long` | Minimum box value; dust limit for buyer output |
| **R8** | `Long` | Miner fee in nanoERG; standard Ergo network fee |
| **R9** | `Long` | Operator fee in nanoERG; dApp service fee |

## Tokens

### hodlERG Token (Native Token)
- **ID**: Stored in R6; retrieved from bank R5.
- **Purpose**: ERC-20-style governance/utility token minted/burned against ERG reserve.
- **State Machine Role**: Bank box tracks total supply (R4) and reserve (tokens(1)._2); proxy transfers between bank and buyer.
- **Invariant**: Total hodlERG = bank reserve + circulating supply (enforced via state update validation).

###