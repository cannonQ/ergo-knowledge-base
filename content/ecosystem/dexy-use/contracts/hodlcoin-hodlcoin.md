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
project: dexy-use
---
# ErgoScript Contract Analysis: hodlcoin.es

## Purpose

The **hodlERG** BankBox contract implements a collateralized stablecoin mechanism where ERG reserves back circulating hodlERG tokens. Users can mint hodlERG by depositing ERG (at a dynamic price), burn hodlERG to withdraw ERG (minus fees), and developers can periodically withdraw accumulated dev fees to three designated addresses.

## Inputs / Outputs

### Inputs
- **SELF (BankBox)**: The singleton state box containing:
  - hodlERG token (tokens(0)) representing the reserve backing
  - BankBox NFT (tokens(1)) for singleton identification
  - ERG reserve (the box value minus treasury)
  - R4 register: treasury balance (accumulated dev fees)

### Outputs
- **OUTPUTS(0) — Updated BankBox**: Must preserve token IDs, proposition bytes, and maintain minimum 0.01 ERG value
- **OUTPUTS(1–3) — Dev Withdrawal (conditional)**: Three equal-value outputs to three hardcoded developer addresses (only during treasury withdrawal actions)
- **User outputs (implicit)**: The transaction may include additional boxes receiving withdrawn ERG or minted hodlERG tokens (validated off-chain)

## Key Logic

The contract validates three mutually exclusive transaction types:

### 1. **Mint Action** (`hodlCoinsCircDelta >= 0`)
- Price is calculated: `price = (reserveIn × 1000) / hodlCoinsCircIn`
- Expected ERG deposit: `hodlCoinsCircDelta × price / 1000`
- Validates: reserve increases by exactly the expected deposit; treasury unchanged
- **Invariant**: hodlERG supply increases, ERG reserve increases proportionally

### 2. **Burn Action** (else clause, `hodlCoinsCircDelta < 0`)
- Tokens burned: `hodlCoinsCircIn - hodlCoinsCircOut`
- Price calculated from input reserve state
- **Fees applied**:
  - Protocol fee: 0.3% of withdrawal
  - Dev fee: 0.3% of withdrawal
- Expected withdrawal: `(burned × price) - fees`
- Validates: reserve decreases by withdrawal + dev fee; treasury increases by dev fee amount
- **Invariant**: hodlERG supply decreases, ERG reserve decreases with fee slippage

### 3. **Treasury Withdrawal Action** (`treasuryDelta < 0`)
- Splits treasury equally among 3 developers: `amountPerDev = -treasuryDelta / 3`
- Validates:
  - No rounding error: `treasuryDelta == -3 × amountPerDev`
  - Minimum dust threshold: `amountPerDev >= 0.05 ERG`
  - Each output matches a hardcoded PK and receives exactly `amountPerDev`
- **Invariant**: hodlERG in bank unchanged; only ERG treasury redistributed

### General Conditions (All Actions)
- Updated BankBox value ≥ 0.01 ERG (storage rent minimum)
- BankBox proposition bytes unchanged (state machine continuity)
- Token IDs preserved (singleton and NFT conservation)
- Treasury never negative (`treasuryIn >= 0 && treasuryOut >= 0`)

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** | `Long` | Treasury balance (accumulated dev fees in nanoERG) | Read (input & output) |

- **R0–R3**: Not used (standard script fields only)
- **R5–R9**: Not used in this contract

## Tokens

### tokens(0) — hodlERG Token
- **Purpose**: Tracks circulating supply and bank reserve
- **Total Supply**: `97,739,924,000,000,000` nanohodlERG (1:1 with ERG nanoErgs)
- **Initial State**: After initialization, 1 token is burned to ensure circulating supply never equals zero (preventing division-by-zero in price calculation)
- **Conservation Rule**: Quantity must be preserved in OUTPUTS(0)

### tokens(1) — BankBox Singleton NFT
- **Purpose**: Identifies the authoritative state box (singleton pattern)
- **Quantity**: Fixed at 1
- **Conservation Rule**: Must appear in OUTPUTS(0) with identical token ID

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Mint Transaction Construction**:
   - Calculate expected hodlERG minted: `erg_amount / current_price`
   - Construct transaction that increases hodlCoinsCircOut by this amount
   - Ensure reserve increases by exactly `erg_amount`
   - Send minted hodlERG to user output boxes (not validated on-chain)

2. **Burn Transaction Construction**:
   - User specifies hodlERG to burn
   - Off-chain calculates: `withdrawal = (burned × price) - fees`
   - Construct transaction reducing hodlCoinsCircOut and extracting ERG
   - Route withdrawn ERG to user; dev fee to treasury in BankBox R4

3. **Treasury Withdrawal Construction**:
   - Monitor treasury balance (BankBox R4)
   - When ready, construct transaction splitting treasury into 3 equal outputs
   - Verify each output matches hardcoded developer address and value
   - Only proceed if `treasuryBalance % 3 == 0` (no rounding error)
   - Enforce minimum per-developer: `treasuryBalance / 3 >= 0.05 ERG`

4. **Price Oracle Integration**:
   - Current price read directly from BankBox state: `price = (reserveIn × 1000) / hodlCoinsCircIn`
   - No external oracle; price is deterministic from on-chain state
   - Off-chain code validates price hasn't moved adversely (slippage protection)

5. **Box Selection & UTxO Management**:
   - Must locate the BankBox (identified by tokens(1) NFT) as INPUTS(0)
   - For mint/burn: construct user outputs separately; script validates only BankBox
   - For treasury withdrawal: construct 3 dev outputs as OUTPUTS(1), OUTPUTS