---
title: kushti/dexy-stable — payout.es
description: "ErgoScript contract analysis: contracts/bank/payout.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/payout.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `contracts/bank/payout.es`

## Purpose

This contract enforces periodic reward payouts from the Dexy stablecoin bank to incentivize liquidity providers. It validates that payouts occur at safe intervals, respect collateralization thresholds (≥800%), and transfer only a bounded percentage (0.5%) of bank reserves to a buyback/reward mechanism.

## Inputs / Outputs

### Inputs
| Index | Role | Purpose |
|-------|------|---------|
| 0 | **Payout Box** (SELF) | State machine singleton holding payout schedule and NFT authentication |
| 1 | **Bank Box** | Holds DEXY token reserves and bank state; provides funds for payout |
| 2 | **Buyback Box** | Receives payout amount; rewards liquidity providers |

### Data Inputs
| Index | Role | Purpose |
|-------|------|---------|
| 0 | **Oracle Box** | Price feed (nanoErgs per kg of gold); R4 contains rate data |
| 1 | **LP Box** (referenced but not actively validated in this contract) | Liquidity provider state |

### Outputs
| Index | Role | Purpose |
|-------|------|---------|
| 0 | **Successor Payout Box** | Preserved payout box with updated R4 (last payment height) |
| 1 | **Bank Box Out** | Bank box after withdrawal, tokens/NFT preserved |
| 2 | **Buyback Box Out** | Receives payout nanoErgs |

## Key Logic

### Collateralization Verification
```
collateralized = oracleRate * dexyInCirculation * 8 < bankBoxIn.value
```
- Oracle rate: nanoErgs per DEXY (derived from oracle's kg-of-gold rate ÷ 1,000,000)
- Ensures bank maintains **≥800% collateral ratio** before any payout
- Protects stablecoin peg by preventing over-leverage

### Payment Amount Constraints
1. **Payment Size**: `0 < paymentAmount ≤ 0.5% of bank reserves`
   - Bank releases funds: `bankBoxIn.value - bankBoxOut.value`
   - Buyback receives same amount: `buybackBoxOut.value - buybackBoxIn.value == paymentAmount`
   - Prevents excessive single-transaction withdrawals

2. **Payment Timing**: `lastPayment + 5,040 blocks ≤ HEIGHT`
   - ~1 week delay between payouts (Ergo ≈ 2 min blocks)
   - Retrieved from payout box R4 register (last payment height)
   - Prevents reward spam

3. **Height Update**: `successor.R4[Int].get ≥ HEIGHT - 5 blocks`
   - New payout box records current height (with ±5 block error margin)
   - Enables next payout after 5,040 block delay from this transaction

### State Machine Preservation
- **Payout box**: Script and NFT preserved; value ≥ SELF.value (non-decreasing)
- **Bank box**: All tokens preserved (DEXY NFT + DEXY token quantity unchanged)
- **Oracle validity**: Oracle box authenticated by oracleNFT token ID

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R4** (Payout Box) | `Int` | Height of last payment | Read (SELF); Write (Successor) |
| **R4** (Oracle Box) | `Long` | Oracle rate (nanoErgs per kg Au) | Read (oracleBox) |

- **R4 initialization**: Set to `0` on contract deployment to allow first payout immediately
- **Non-nullable**: R4 always exists; no `.get.orElse()` pattern needed

## Tokens

### NFTs (Singleton Authentication)

| Token ID | Box | Purpose |
|----------|-----|---------|
| `$oracleNFT` | Oracle data input | Authenticates price feed; prevents spoofing |
| `$lpNFT` | (Referenced in comments; not validated here) | Likely marks LP pool state |
| `$buybackNFT` | Buyback input | Authenticates reward/buyback destination box |

### Native Tokens

| Token | Location | Purpose |
|-------|----------|---------|
| **DEXY** | Bank box (tokens(1)) | Stablecoin token; quantity checked for circulation via `$initialDexyTokens - bankDexy` |

**Token ID Rule**: NFTs enforce box lineage; only one authentic Payout/Bank/Buyback box per transaction.

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Monitor Conditions**:
   - Check collateralization: `oracleRate * (initialDexy - bankDexy) * 8 < bankValue`
   - Verify block height: `currentHeight ≥ lastPaymentHeight + 5,040`

2. **Construct Transaction**:
   - Fetch current Oracle box (data input at index 0)
   - Select Bank box (input 1) with correct DEXY tokens
   - Select Buyback box (input 2) with `$buybackNFT`
   - Calculate payment: `min(0.005 * bankValue, maxSafeAmount)`
   - Create successor Payout box (output 0) with `R4 = currentHeight`
   - Transfer Bank box (output 1) with reduced nanoErgs
   - Increase Buyback box value (output 2) by payment amount

3. **Sign & Submit**:
   - Payout box holder signs (Sigma protocol)
   - Bank may require additional signatures (not enforced here; assumed multi-sig or oracle-controlled)

### Context Extension
- None required (all data from boxes or blockchain context)

## Related Contracts

| Contract | Relationship | Purpose |
|----------|--------------|---------|
| **Bank Contract** | Input/Output validation | Holds DEXY reserves; must enforce consistent state across transactions |
| **Oracle Pool Contract** | Data input provider | Supplies gold-backed price feed; enforces rate updates |
|