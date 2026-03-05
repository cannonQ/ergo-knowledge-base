---
title: duckpools/lend-protocol-contracts — borrow.md
description: "ErgoScript contract analysis: contracts/pools/rsAda/proxy-contracts/borrow.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/rsAda/proxy-contracts/borrow.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Borrow Proxy (rsAda Lending Protocol)

## Purpose

This contract acts as a **proxy/intermediary box** in the duckpools lending protocol that orchestrates borrow transactions. It accepts user borrow requests, validates collateral box creation, and either executes the loan issuance (exchange of collateral for borrowed tokens) or processes a refund if the request expires. The contract enforces atomic swap semantics between user collateral and pool-issued loan tokens.

---

## Inputs / Outputs

### Inputs
- **SELF** (Index 0): The borrow proxy box itself, containing user request metadata in registers
- **INPUTS(0)** (required in exchange path): Pool box holding the **poolNFT** (State NFT) and lending state
- Additional inputs may be present for transaction fees

### Outputs

**Refund Path** (OUTPUTS.size < 3):
- **OUTPUTS(0)**: Refund box returning ERG to the user (when `publicRefund` height is reached)

**Exchange Path** (OUTPUTS.size ≥ 3):
- **OUTPUTS(0)**: Pool box (updated state, passed through)
- **OUTPUTS(1)**: Collateral box (newly created, holds user's locked collateral + borrow token receipt)
- **OUTPUTS(2)**: User box (newly created, holds the borrowed loan tokens)

---

## Key Logic

### Two Operation Modes

The contract validates one of two mutually exclusive paths:

#### **Refund Operation** (OUTPUTS.size < 3)
Triggered when the borrow request expires. Validates:
1. **validRefundRecipient**: Refund box recipient is the original user (`user` from R4)
2. **validDeltaErg**: ERG loss ≤ `minTxFee` (1 ERG) — only tx fee consumed
3. **multiBoxSpendRefund**: Refund box contains SELF's box ID in R4 (prevents reuse/confusion)
4. **validHeight**: Current height ≥ `publicRefund` deadline (R6)
5. **Success condition**: All four checks pass

#### **Exchange Operation** (OUTPUTS.size ≥ 3)
Triggers the actual borrow. Validates:

**Collateral Box (OUTPUTS(1)) Requirements:**
- **validCollateralBoxScript**: Collateral box enforces `collateralBoxScript` (blake2b256 hash match)
- **validCollateralTokens**: ERG value = SELF.value − 1 ERG (minBoxValue) − minTxFee (atomic swap math)
- **validBorrower**: Collateral R4 records the borrower as the request's `user`
- **validThresholdPenalty**: Collateral R6 matches the user's penalty threshold pair (R7)
- **validDexNFT**: Collateral R7 matches user's DEX NFT identifier (R8)
- **validUserPk**: Collateral R8 matches user's public key (R9)
- **validForcedLiquidation**: Collateral R9._1 (liquidation height) is in range `[HEIGHT + 65480, HEIGHT + 65520]` (~45 days on mainnet; prevents manipulation)
- **validLoanAmount**: Borrow token ID matches `BorrowTokenId`; loan amount in collateral box matches loan amount in user box

**Pool Box (INPUTS(0)) Requirements:**
- **validInterestIndex**: INPUTS(0) holds the `poolNFT` (State NFT) — ensures pool box is the authoritative state box

**User Box (OUTPUTS(2)) Requirements:**
- **validUserScript**: User box owner is the original `user` (R4 of SELF)
- **validUserLoanAmount**: User box holds exactly `requestAmount` (R5) of the pool's native currency (`PoolNativeCurrency`)
- **multiBoxSpendSafety**: User box R4 contains SELF's ID (prevents reuse; links box to this request)

**Success condition**: All validations pass

### Final Authorization
The contract **always allows** spending if:
```
operation || proveDlog(userPk)
```
- The operation (refund OR exchange) passes validation, **OR**
- The user proves knowledge of their private key (`userPk` from R9)

This dual-authorization pattern allows:
- **Automatic execution** (off-chain bot) if all validations pass
- **Manual override** (user can spend if validations fail, reclaiming their box)

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User/borrower address (Ergo address bytes); recipient of refunds or owner of collateral |
| **R5** | `Long` | `requestAmount` — exact amount of pool native currency to borrow |
| **R6** | `Int` | `publicRefund` — block height deadline for refund eligibility (if borrow not executed by this height, user can refund) |
| **R7** | `(Long, Long)` | `userThresholdPenalty` — pair encoding liquidation threshold ratio and penalty multiplier for this borrow |
| **R8** | `Coll[Byte]` | `userDexNft` — DEX NFT ID associated with the user (used for yield tracking or multi-pool accounting) |
| **R9** | `GroupElement` | `userPk` — user's public key (Sigma protocol witness for `proveDlog` fallback) |

---

## Tokens

### Native Tokens Used

| Constant | Type | Purpose |
|----------|------|---------|
| **poolNFT** | Token ID | Singleton State NFT identifying the authoritative pool box in INPUTS(0); prevents state machine fragmentation |
| **BorrowTokenId** | Token ID | Receipt token minted by the pool; one unit per borrowed ERG; tracks debt on collateral box |
| **PoolNativeCurrency** | Token ID | The loan asset (typically ERG or stablecoin); quantity transferred to user on borrow |

### Token Flow
1. User provides **collateral ERG** (SELF.value − minBoxValue − minT