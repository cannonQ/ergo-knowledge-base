---
title: duckpools/lend-protocol-contracts — borrow.md
description: "ErgoScript contract analysis: contracts/pools/QUACKS-POOL/proxy_contracts/borrow.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/QUACKS-POOL/proxy_contracts/borrow.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: QUACKS-POOL Borrow Proxy

## Purpose

This contract serves as a **borrow request proxy** in the QUACKS lending protocol. It validates either a refund operation (if the loan request expires or is rejected) or a loan execution operation (if sufficient collateral is provided). The contract acts as an intermediary that routes user borrow requests to the pool contract and ensures proper collateral setup before disbursing loans.

## Inputs / Outputs

### Inputs
- **SELF (INPUTS(0))**: The borrow request proxy box itself, containing user metadata and loan parameters
- **INPUTS(1)** (implicit): The pool box, validated indirectly via the NFT presence check (`poolNFT` in tokens)
- **Data inputs** (via context): May reference collateral or pool state (implicit from pattern)

### Outputs

**Refund Path** (OUTPUTS.size < 3):
- **OUTPUTS(0)**: Refund box returned to the user, containing unspent ERG minus transaction fee

**Borrow/Exchange Path** (OUTPUTS.size ≥ 3):
- **OUTPUTS(0)**: Updated pool box (validated by pool contract)
- **OUTPUTS(1)**: Collateral box holding the user's collateral and borrow token record
- **OUTPUTS(2)**: User box receiving the loan amount in PoolNativeCurrency tokens

## Key Logic

### Refund Operation (timeout/rejection)
The contract validates a refund when `OUTPUTS.size < 3`:
1. **Recipient validation**: Refund box must be owned by the original user (`user` from R4)
2. **Delta ERG check**: ERG difference ≤ minimum transaction fee (no leakage)
3. **Multi-box spend safety**: Refund box's R4 must reference this contract's box ID (`SELF.id`)
4. **Height lock**: Current block height must be ≥ `publicRefund` threshold, preventing refunds before maturity

### Borrow/Exchange Operation (loan execution)
When `OUTPUTS.size ≥ 3`, the contract orchestrates a three-way atomic exchange:

1. **Collateral box validation**:
   - Script hash matches the expected `collateralBoxScript` (State machine enforcement)
   - Register fields match user inputs (R4: borrower, R5: indexes, R6: threshold/penalty, R7: dex NFT, R8: user public key, R9: forced liquidation height)
   - Forced liquidation height is reasonable: `HEIGHT + 65480` to `HEIGHT + 65520` (~455 days forward, preventing abuse)
   - Collateral amount equals SELF value minus minimum box value and fee

2. **Token flow validation**:
   - Borrow tokens in collateral box match request (BorrowTokenId, loanAmount)
   - User box receives exactly `requestAmount` in PoolNativeCurrency
   - Loan amount consistency across all boxes

3. **User authorization**:
   - User's public key (`userPk` from R9) matches collateral box's record
   - Threshold and penalty parameters match between request and collateral
   - Dex NFT identifier matches (for liquidation integration)

4. **Multi-box spend safety**: User box's R4 contains this contract's ID, preventing reuse in malicious transactions

5. **Pool integration**: Pool NFT presence verified in first input (delegated validation to pool contract)

### Signature Authorization
The entire operation succeeds if `operation` is true **OR** the user proves knowledge of their private key via `proveDlog(userPk)`, allowing recovery of unspent funds.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User identity (script/address); also used in output boxes to prevent reuse |
| **R5** | `Long` | Requested loan amount |
| **R6** | `Int` | Block height deadline for refund eligibility |
| **R7** | `(Long, Long)` | User's threshold and penalty parameters for liquidation |
| **R8** | `Coll[Byte]` | User's DEX NFT identifier (links to liquidation pool) |
| **R9** | `GroupElement` | User's public key (Sigma protocol, used for signature validation) |

**Collateral box outputs** mirror R4–R9 for state machine continuity.

## Tokens

| Token | Role | Usage |
|-------|------|-------|
| **poolNFT** | Singleton NFT | State machine identifier; validates pool box authenticity in INPUTS(0) |
| **BorrowTokenId** | Native token | Represents loan obligation; held in collateral box as (TokenId, loanAmount) pair |
| **PoolNativeCurrency** | Native token | The actual loan proceeds; transferred to user box in (TokenId, requestAmount) pair |

The **Token ID rule** ensures that only borrow tokens issued by the pool contract can fulfill requests, preventing counterfeiting.

## Integration Pattern

### Off-Chain Responsibilities

1. **Request Construction**:
   - Off-chain bot constructs the borrow request box with user identity, loan amount, and deadline in R4–R9
   - Derives user's public key from seed and stores in R9
   - Sets `publicRefund` height (e.g., current height + timeout period)

2. **Borrow Execution**:
   - Fetches the pool box (identified by `poolNFT`)
   - Constructs collateral box with matching registers and ERG value
   - Constructs user output box to receive loan tokens
   - Calls this contract along with pool contract in a **multi-stage transaction**

3. **Validation Path**:
   - Off-chain code verifies collateral sufficiency (oracle price feed)
   - Computes forced liquidation height based on collateral ratio
   - Ensures transaction fee + min box value ≤ SELF.value

4. **Refund Path** (timeout):
   - After `publicRefund` height, user or bot can claim refund
   - Constructs refund box with R4 = SELF.id and user as recipient
   - No signature required if height condition satisfied; otherwise requires `proveDlog(userPk)`

### Multi