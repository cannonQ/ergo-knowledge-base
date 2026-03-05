---
title: duckpools/lend-protocol-contracts — withdraw.md
description: "ErgoScript contract analysis: contracts/pools/drafts/SIGUSD-POOL/Proxy-Contracts/withdraw.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/drafts/SIGUSD-POOL/Proxy-Contracts/withdraw.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: SIGUSD-Pool Withdraw Proxy

## Purpose

This contract acts as a **withdrawal proxy** in the duckpools lending protocol, enabling users to atomically withdraw tokens (likely stablecoins like SigmaUSD) from a liquidity pool. It validates either a **refund path** (if conditions aren't met by a deadline) or a **withdrawal path** (if the pool fulfills the request), using multi-stage validation to ensure atomic composability between user, pool, and successor boxes.

---

## Inputs / Outputs

### Inputs
- **SELF** (Proxy Request Box):
  - Contains user withdrawal request metadata in registers
  - Holds native tokens (pool-issued tokens or request markers) as identifiers
  - Value: ERG amount sufficient for transaction fees

### Outputs

**Refund Path** (OUTPUTS.size < 3):
- **OUTPUTS(0)**: Refund successor box
  - Must lock to user's address (derived from R4)
  - Contains original token from SELF
  - Carries reference to SELF.id in R4 for multi-box safety

**Withdrawal Path** (OUTPUTS.size ≥ 3):
- **OUTPUTS(2)**: User's withdrawal receipt box
  - Must lock to user's address
  - Contains requested token (verified against R7)
  - Carries SELF.id in R7 as proof of origin
- **OUTPUTS(0-1)**: Pool settlement boxes (validated externally)

---

## Key Logic

### Validation Branches

**Refund Conditions** (executed when OUTPUTS.size < 3):
1. **validRefundSuccessor**: `OUTPUTS(0).propositionBytes == user`
   - Ensures refund box locks to the user's public key/script
2. **validDeltaErg**: `SELF.value - OUTPUTS(0).value ≤ minTxFee`
   - Confirms only transaction fees are consumed; refund is nearly complete
3. **validHeight**: `HEIGHT ≥ publicRefund`
   - Enables refund only after deadline block height (stored in R6)
4. **multiBoxSafetyRefund**: `OUTPUTS(0).R4[Coll[Byte]] == SELF.id`
   - Prevents replay by linking refund box to this specific SELF request
5. **validTokens**: `OUTPUTS(0).tokens(0) == SELF.tokens(0)`
   - Ensures original request token is returned unchanged

**Withdrawal Conditions** (executed when OUTPUTS.size ≥ 3):
1. **validSuccessorScript**: `OUTPUTS(2).propositionBytes == user`
   - Routes withdrawal to correct user address
2. **validTokens**: `OUTPUTS(2).tokens(0)._2 ≥ requestAmount && OUTPUTS(2).tokens(0)._1 == requestedToken`
   - Verifies pool supplied correct token ID and minimum requested amount
3. **multiBoxSpendSafety**: `OUTPUTS(2).R7[Coll[Byte]] == SELF.id`
   - Prevents token duplication by tagging withdrawal box with SELF.id

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Byte]` | User's address/public key (blake2b256 hash or serialized proposition) |
| **R5** | `Long` | Requested withdrawal amount (token quantity) |
| **R6** | `Long` | Block height deadline for refund eligibility |
| **R7** | `Coll[Byte]` | Requested token ID (NFT or native token identifier) |

**Refund Flow**: R4 → OUTPUTS(0).R4 (safety link)  
**Withdrawal Flow**: R7 → OUTPUTS(2).R7 (safety link)

---

## Tokens

- **SELF.tokens(0)**: Request marker token or pool state NFT
  - Authenticates this as a legitimate pool request
  - Must be propagated to OUTPUTS(0) in refund path
  - Implicitly validated in withdrawal path (though not explicitly carried forward)

- **OUTPUTS(2).tokens(0)** (withdrawal path): Requested stablecoin or pool asset
  - Token ID must match R7
  - Quantity must be ≥ R5 (requestAmount)
  - Sourced from pool settlement logic (OUTPUTS 0-1)

---

## Integration Pattern

### Off-Chain Responsibilities

1. **Request Construction**:
   - Create SELF box with user pubkey in R4, amount in R5, deadline in R6, token ID in R7
   - Attach pool request marker token

2. **Transaction Composition**:
   - **Refund scenario**: Construct minimal OUTPUTS(0) and submit after HEIGHT ≥ R6
   - **Withdrawal scenario**: Pool off-chain bot constructs OUTPUTS(0-1) with settlement logic; dApp constructs OUTPUTS(2) with user's token

3. **Validation Triggers**:
   - Monitor HEIGHT; auto-trigger refund if pool doesn't respond by deadline
   - Verify pool provides OUTPUTS(0-1) with correct reserve changes

### Multi-Box Safety Pattern
- **Self-referencing**: SELF.id stored in successor registers to prevent:
  - Token theft (same token used in multiple withdrawals)
  - Replay attacks (old request boxes reused)

---

## Related Contracts

### Inferred Relationships (from duckpools architecture)

1. **Pool Deposit/Settlement Contract** (OUTPUTS 0-1 sources):
   - Validates reserve updates when user withdraws
   - Ensures token supply conservation across SELF → OUTPUTS(2) transition

2. **User Request Factory**:
   - Mints request marker token (SELF.tokens(0)) to uniquely identify this withdrawal

3. **Stablecoin Contracts** (e.g., SigmaUSD backing):
   - May validate token rules for OUTPUTS(2).tokens(0) if using wrapped asset pattern

### State Machine Composition
This contract implements a **two-stage state machine**:
```
[Pending Request] ──(timeout)──> [Refunded to User]