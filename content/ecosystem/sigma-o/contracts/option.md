---
title: ThierryM1212/SigmaO — Option.es
description: "ErgoScript contract analysis: contract/Option.es"
tags: [thierrym1212, sigmao, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
contract_file: contract/Option.es
project: thierrym1212-sigmao
---
# SigmaO Option Contract Analysis

## Purpose

This contract implements a **financial derivative contract** enabling the creation and management of European and American options on Ergo tokens. Option holders gain the right (but not obligation) to buy (Call) or sell (Put) an underlying token at a predetermined strike price on or before a maturity date, with all positions collateralized by ERG and underlying tokens held within the contract boxes.

## Inputs / Outputs

### Inputs
- **Option Definition Box** (initial mint state): Contains option parameters in registers, underlying tokens (Call) or ERG collateral (Put), and configuration metadata
- **Option Reserve Box** (minted/delivery/exercise states): Holds the live option token (singleton/State NFT pattern), underlying asset collateral, and maintains option state across transactions
- **Optional Data Inputs**: May reference the Option Creation Box for state verification without consuming it

### Outputs
- **Updated Option Reserve Box**: Propagated with modified state (token counts, collateral adjustments)
- **Issuer Box**: Receives option tokens (at mint delivery) or underlying tokens (at exercise)
- **Fee Boxes**: Separate outputs for dApp UI fees and miner transaction fees
- **User/Exerciser Box**: Receives settlement assets (ERG or tokens) upon exercise

## Key Logic

### State Transitions

1. **Mint Phase** (`validMintOption`):
   - Single-input transaction creates option tokens from the Option Definition Box
   - Validates: Single input, OUTPUTS(0) propagates to reserve state, exactly 1 option token remains in box
   - Fee extraction to OUTPUTS(1) and OUTPUTS(2)

2. **Delivery Phase** (`validMintDeliveryOption`):
   - Option issuer receives `(totalAmount / shareSize)` option tokens
   - OUTPUTS(0) transitions to reserve state with 1 option token retained
   - Validates fee destinations and collateral consistency

3. **Exercise Phase** (`validExerciseOption`):
   - Only exercisable during valid time window:
     - **European**: 24 hours after maturity date
     - **American**: Until maturity date
   - **Call option**: Exerciser sends `shareSize * strikePrice` nanoERG, receives `shareSize` underlying tokens
   - **Put option**: Exerciser sends `shareSize` underlying tokens, receives `shareSize * strikePrice` nanoERG
   - Validates: Correct payment amount, proper collateral transfer, option token spent

4. **Expiration/Settlement**:
   - Empty Call: All underlying tokens returned to issuer (no exercise occurred)
   - Empty Put: All collateral (ERG) returned to issuer (no exercise occurred)

### Core Validation Conditions

```
- isMinted: SELF token ID matches SELF.R7[Box].id (Option Creation Box reference)
- isOptionDelivered: Token has been minted AND exactly 1 option token remains in reserve
- isExercible: Correct style + time window + delivered state
- isEmpty: All collateral consumed (Call) or only minimum value remains (Put)
- validBasicReplicatedOutput0: Reserve box properly propagated with metadata
- strikePrice validation: Ensures correct ERG/token exchange rates
- Collateral sufficiency: Output boxes hold minimum required value + collateral
```

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | Option name (informational, wallet display) |
| **R5** | `Coll[Byte]` | Underlying token ID (asset filtering) |
| **R6** | `Coll[Byte]` | Decimal encoding string (wallet UX, not validated) |
| **R7** | `Box` | Reference to Option Creation Box (immutable config anchor) |
| **R8** | `Coll[Long]` | Option parameters array: `[type, style, shareSize, maturityDate, strikePrice, dAppUIMintFee, TxFee]` |
| **R9** | `Coll[Coll[Byte]]` | Issuer data: `[issuerECPoint, dAppUIFeeErgoTree]` (Sigma protocol signing + fee routing) |

## Tokens

### Native Tokens Used

1. **Option Token (NFT/Singleton)**
   - **Token ID**: `optionCreationBox.id` (derived from transaction inputs)
   - **Role**: State machine token—uniquely identifies and gates the option reserve box
   - **Circulation**: 
     - Total minted: `(totalAmount / shareSize) + 1`
     - Reserve holds: Always `1` token (singleton pattern)
     - Distributed: `totalAmount / shareSize` tokens to issuer
   - **Authentication**: Controls which outputs can transition the contract state

2. **Underlying Asset Token** (for Call options)
   - **Token ID**: `underlyingAssetTokenId` (e.g., SigUSD, GORT)
   - **Amount in reserve**: Collateralizes the option
   - **Call**: `N` tokens locked, exerciser buys at strike price
   - **Put**: Exerciser deposits tokens; issuer receives them

## Integration Pattern

### Off-Chain Bot / Headless dApp Workflow

1. **Mint Request Construction**:
   - User/UI creates Option Definition Box with:
     - Sufficient ERG: `3 * TxFee + 2 * BoxMinValue + dAppUIMintFee + (PUT ? collateral amount)`
     - Call: Underlying tokens attached
     - All registers R4–R9 populated with option parameters
   - Submit to mempool

2. **Mint Transaction**:
   - Off-chain service monitors UTXO set
   - Constructs transaction with Option Definition Box as sole input
   - Generates OUTPUTS(0) (reserve), OUTPUTS(1) (dApp fee), OUTPUTS(2) (miner fee)
   - Signs with issuer private key (via `proveDlog(decodePoint(issuerECPoint))`)
   - Broadcasts

3. **Delivery Transaction**:
   - Off-chain service waits for mint confirmation
   - Constructs tx: Input = minted reserve box
   - OUTPUTS(0) = updated reserve (1 option token)
   