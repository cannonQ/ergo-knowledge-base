---
title: duckpools/lend-protocol-contracts — pool.md
description: "ErgoScript contract analysis: contracts/pools/eSIGUSD-POOL/pool.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/eSIGUSD-POOL/pool.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: eSIGUSD Pool

## Purpose

This contract manages a lending pool for the eSIGUSD protocol, maintaining the state machine for a decentralized lending/borrowing system with collateralized loans. It validates deposits, withdrawals, exchanges, and liquidations while tracking lend token valuations, borrowed assets, and service fees through state transitions.

## Inputs / Outputs

### Inputs
- **SELF (Current Pool Box)**: 
  - Box value in nanoERG
  - Token 0: Pool NFT (singleton, identifies this pool state)
  - Token 1: Lend tokens (LP shares, variable supply)
  - Token 2: Borrow tokens (debt instruments, variable supply)
  - Token 3: Pooled assets (underlying collateral token)

### Data Inputs (Context-dependent)
- **Service Parameter Box** (operations with fees): Contains fee configuration via NFT `ParamaterBoxNft`
- **Collateral Box** (loans): Holds borrower's collateral and interest index pointers
- **DEX Pool Box** (liquidations): External DEX state for price discovery
- **Parent/Child Interest Boxes** (loans): Track compounding interest rates
- **Parameter Box** (loans): Liquidation thresholds, penalties, collateral asset IDs

### Outputs
- **Output(0) - Successor Pool Box**: Updated pool state with modified token supplies and asset balances
- **Output(1)** (conditional):
  - Fee scenario: Service fee destination box
  - Loan scenario: Collateral box (modified state)

## Key Logic

### Universal Validations (All Paths)
1. **Script Preservation**: Successor box must execute identical ErgoScript (`successorScript == currentScript`)
2. **Pool NFT Singleton**: Pool NFT immutable across state transition
3. **Token ID Integrity**: Lend/borrow/pooled token IDs unchanged
4. **Minimum Box Value**: Successor holds ≥ `MinimumBoxValue` (1 ERG)
5. **Lend Token Valuation**: 
   - Formula: `LendTokenValue = LendTokenMultiplier × (PooledAssets + TotalBorrowed) / LendTokensCirculating`
   - Invariant: Value must never decrease (prevents LP dilution)

### Deposit Operation
- **Trigger**: Pooled assets increase AND borrow tokens decrease
- **Validations**:
  - Assets flow INTO pool (`deltaAssetsInPool > 0`)
  - Borrow tokens returned (`deltaTotalBorrowed < 0`)
  - Lend tokens circulating unchanged (no new LP issuance)
- **Outcome**: Increases pool reserves; borrowers repay loans

### Exchange Operation (Asset Swap)
- **Trigger**: Borrow token supply unchanged
- **Validations**:
  - Service fee collected (tiered structure based on asset delta)
  - Lend token value maintained/increased
  - Service fee box created with proper script (from parameter box R8)
- **Fee Tiers**:
  - ≤ 2000 units: 1/160 of amount
  - 2000–200000 units: 1/200 of amount
  - > 200000 units: 1/250 of amount

### Loan Validation (Partial logic shown; truncated)
- **Collateral Verification**: Checks collateral box via NFT matching
- **Interest Compounding**: Validates parent/child interest history boxes
- **Liquidation Conditions**: Compares current collateral value vs. liquidation threshold
- **DEX Integration**: Uses DEX pool (data input) for price discovery in liquidations

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** | `Coll[Byte]` | Collateral owner pubkey (collateral box) | Read |
| **R5** | `(Int, Int)` | Interest indexes (parent, child) pointers | Read |
| **R6** | `(Long, Long)` | Threshold penalty amounts | Read |
| **R7** | `Coll[Byte]` | DEX NFT identifier | Read |
| **R8** | `GroupElement` / `Coll[Byte]` | User public key OR service fee script | Read |
| **R9** | `(Long, Long)` | Forced/buffer liquidation amounts | Read |

**Parameter Box Registers**:
- **R4**: `Coll[Long]` — Liquidation thresholds per collateral type
- **R5**: `Coll[Coll[Byte]]` — Collateral asset token IDs
- **R6**: `Coll[Coll[Byte]]` — DEX pool NFTs for price oracles
- **R7**: `Coll[Long]` — Liquidation penalties

## Tokens

### Pool Box Token Structure
| Index | Token ID | Supply Type | Purpose |
|-------|----------|-------------|---------|
| 0 | Pool NFT (singleton) | Always 1 | State machine identity & authorization |
| 1 | Lend Token | Variable (max 9×10¹⁵) | LP shares; holders receive yields |
| 2 | Borrow Token | Variable (max 9×10¹⁵) | Represents outstanding debt |
| 3 | Pooled Asset | Variable | Native currency or wrapped token backing loans |

### NFT Identifiers (Constants)
- **ChildBoxNft**: Interest accrual child box
- **ParamaterBoxNft**: Protocol parameter configuration
- **ParentBoxNft**: Interest accrual parent box

### Token Rules
- Lend tokens: Minted when deposits exceed repayments; supply capped to preserve per-token valuation
- Borrow tokens: Issued when loans originate; destroyed when repaid
- Minimum loan: 50 ERG (`MinLoanValue`)

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Deposit Operation**:
   - Construct OUTPUTS(0) with increased pooled token quantity
   - Decrease borrow tokens (borrower repaying)
   - Calculate lend token value post-state;