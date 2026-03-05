---
title: ThierryM1212/SigmaO — Exercise_Option_Request.es
description: "ErgoScript contract analysis: contract/Exercise_Option_Request.es"
tags: [thierrym1212, sigmao, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
contract_file: contract/Exercise_Option_Request.es
project: thierrym1212-sigmao
---
# ErgoScript Contract Analysis: Exercise_Option_Request

## Purpose

This contract validates requests to **exercise option contracts** (both Call and Put variants) on the Ergo blockchain. When a user wants to exercise their option tokens, this contract ensures they provide the correct strike price payment (Call options) or underlying assets (Put options), and that the proceeds are correctly routed to the option holder's address.

## Inputs / Outputs

### Inputs
- **SELF**: The Exercise Request box containing:
  - Token 0: Option tokens (NFT-like, quantity = N, ID matches option creation box)
  - Token 1: (Optional) Underlying asset tokens (for Put exercises)
  - R4: User's public key (SigmaProp) for payment recipient
  - R5: Reference to the Option Creation box (data input, contains option parameters)

### Outputs
- **OUTPUTS(0)**: Refund box (validated to NOT be the Option Call script, preventing issuer re-exercise)
- **OUTPUTS(1)**: Payment/settlement box sent to user's address (userPKIn.propBytes)
- **OUTPUTS(2)** and **OUTPUTS(3)**: Additional transaction outputs (contract requires exactly 4 outputs total)

## Key Logic

The contract validates two **mutually exclusive** execution paths:

### 1. **Call Option Exercise** (`validExcerciseCall`)
- Requires: `optionType == 0L`
- User must receive underlying asset tokens in OUTPUTS(1):
  - Token type matches `underlyingAssetTokenId` from creation box
  - Token quantity = `N * shareSize` (N option tokens × shares per contract)
- User's ERG value received must satisfy:
  ```
  value(OUTPUTS(1)) >= value(SELF) - TxFee - BoxMinValue - (N * shareSize * strikePrice)
  ```
  This ensures strike price payment is retained in the request box for the option issuer.

### 2. **Put Option Exercise** (`validExcercisePut`)
- Requires: `optionType == 1L`
- OUTPUTS(1) must contain **zero** underlying tokens
- User must receive ERG payment:
  ```
  value(OUTPUTS(1)) >= N * shareSize * strikePrice
  ```
  This is the strike price payout from the put writer.

### 3. **Common Validations**
- Option token (SELF.tokens(0)) must match the **Option Creation box ID** (singleton pattern)
- Creation box must hash to `OptionCallScriptHash` (immutable option parameters)
- OUTPUTS(1) proposition must equal `userPKIn.propBytes` (payment goes to requestor)
- Exactly 4 outputs required in the transaction

### 4. **Refund Path** (Alternative)
- User's signature (`userPKIn`) can authorize a refund if OUTPUTS(0) is **not** the option issuer's script
- This prevents the issuer from frontrunning and re-exercising the option

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `SigmaProp` | User's public key; controls payment destination and refund authorization |
| **R5** | `Box` (data input) | Option Creation box reference; immutably stores option parameters via its ID |
| **R8** (from creation box) | `Coll[Long]` | Packed array of option parameters: `[optionType, ?, shareSize, ?, strikePrice, ?, TxFee, ...]` |

## Tokens

1. **Token 0 (Option NFT)**
   - Token ID: Equals the Option Creation box ID (singleton state token)
   - Quantity: N (number of option contracts being exercised)
   - Purpose: Authenticates the request and links it to a specific option issuance

2. **Token 1 (Underlying Asset)**
   - Token ID: `underlyingAssetTokenId` from creation box R5
   - Quantity: N * shareSize
   - Purpose: Transferred to user on Call exercise; validates Put exercise has zero quantity

## Integration Pattern

### Off-Chain Construction Flow

1. **Read Option Creation Box**: Retrieve the singleton option box containing R8 parameters
2. **Build Exercise Request**:
   - Input: Create box with this script, attach option tokens (token 0), set R4 = user PK, R5 = option creation box ID
   - Outputs: 
     - OUTPUTS(0): Dummy/change box (not issuer's script to prevent frontrun)
     - OUTPUTS(1): User's address with proceeds (ERG for Put, underlying tokens for Call)
     - OUTPUTS(2-3): Fee/routing boxes
3. **Calculate Value**:
   - **Call**: SELF must hold `TxFee + BoxMinValue + (N * shareSize * strikePrice)` ERG
   - **Put**: Underlying tokens required in SELF equal `N * shareSize`
4. **Sign Transaction**: User signs with private key corresponding to R4

### Verification (On-Chain)
- Blake2b256 hash validation ensures creation box parameters are immutable
- Token ID matching enforces 1:1 linkage between request and issuance
- Sigma protocol (SigmaProp) validates user authorization via R4

## Related Contracts

- **Option_Call_Script** (`OptionCallScriptHash`): 
  - The issuer-controlled box that holds strike price (Call) or underlying collateral (Put)
  - Referenced by hash in validation; prevents malicious OUTPUTS(0) boxes
  - Creates the singleton option NFT and stores parameters in R8
  
- **Option Creation Box**: Stateful contract that:
  - Mints option tokens (Token 0)
  - Stores `underlyingAssetTokenId` in R5 and option config in R8
  - Forms the immutable reference point for all exercises

---

## Key Invariants

✓ **Singleton Property**: Only one valid option creation box per option (ID = token ID)  
✓ **No Double-Exercise**: Once option tokens are exercised, they're consumed; cannot be re-spent  
✓ **Strike Price Conservation**: Call exercises extract exactly `N * shareSize * strikePrice` ERG  
✓ **Type Exclus