---
title: duckpools/lend-protocol-contracts — proxyWithdraw.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/proxy-contracts/proxyWithdraw.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/proxy-contracts/proxyWithdraw.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: proxyWithdraw

## Purpose

This contract acts as a **withdrawal proxy** in the ERG-POOL lending protocol, mediating user withdrawals with time-locked refund protection. It validates either a user withdrawal (transferring ERG to the user's address) or a public refund (returning funds after a deadline), ensuring atomic safety through singleton NFT tracking.

## Inputs / Outputs

### Inputs
- **SELF** (Proxy Box): Contains withdrawal request state
  - **Value**: ERG amount to be withdrawn
  - **Tokens**: State NFT (singleton) in index 0 for multi-box safety
  - **R4**: User's public key hash (Coll[Byte])
  - **R5**: Requested withdrawal amount (Long)
  - **R6**: Public refund deadline height (Long)

### Outputs

**Refund Scenario** (`OUTPUTS.size < 3`):
- **OUTPUTS(0)**: Refund box
  - **propositionBytes**: Must equal `user` (user's address)
  - **Value**: `SELF.value - minTxFee` (dust preserved)
  - **R4**: Must contain `SELF.id` (backward reference for multi-box safety)
  - **Tokens(0)**: Must match `SELF.tokens(0)` (state NFT passes through)

**Withdrawal Scenario** (`OUTPUTS.size >= 3`):
- **OUTPUTS(2)**: User withdrawal box
  - **propositionBytes**: Must equal `user`
  - **Value**: ≥ `requestAmount`
  - **R7**: Must contain `SELF.id` (backward reference for multi-box safety)

## Key Logic

### Refund Path (Early Output Count)
Triggers when transaction has **fewer than 3 outputs**, allowing refund after deadline:

1. **Sender Validation**: `OUTPUTS(0).propositionBytes == user`
   - Ensures refund goes to the authorized user address

2. **Fee Preservation**: `SELF.value - OUTPUTS(0).value ≤ minTxFee`
   - Validates only protocol fees are deducted (≤ 1 ERG)

3. **Deadline Check**: `HEIGHT >= publicRefund`
   - Refund only permitted after `R6` block height reached

4. **Multi-Box Safety**: `OUTPUTS(0).R4 == SELF.id`
   - Backward reference prevents orphaned/replayed refunds
   - Ensures refund box explicitly references this proxy box

5. **Token Preservation**: `OUTPUTS(0).tokens(0) == SELF.tokens(0)`
   - State NFT must accompany refund (if tokens present)

### Withdrawal Path (3+ Outputs)
Triggers when transaction has **3 or more outputs**, enabling withdrawal before deadline:

1. **Recipient Validation**: `OUTPUTS(2).propositionBytes == user`
   - Withdrawal must go to authorized user

2. **Amount Validation**: `OUTPUTS(2).value ≥ requestAmount`
   - User receives at least the requested amount

3. **Multi-Box Safety**: `OUTPUTS(2).R7 == SELF.id`
   - Backward reference prevents replay; withdrawal box references proxy box
   - Uses **R7** (distinct from refund's **R4**) to differentiate paths

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** | `Coll[Byte]` | User's public key hash (requester address) | Read |
| **R5** | `Long` | Withdrawal amount requested in ERG | Read |
| **R6** | `Long` | Block height threshold for public refund eligibility | Read |
| **R7** | `Coll[Byte]` (in output) | Backward reference to SELF.id in withdrawal box | Write (output validation) |

## Tokens

- **SELF.tokens(0)**: **State NFT / Singleton**
  - Unique identifier for this proxy box instance
  - Must be preserved in output (either refund or withdrawal)
  - Prevents token duplication across protocol instances
  - Enables off-chain indexing of related boxes

## Integration Pattern

### Off-Chain Bot / Headless dApp Interaction

1. **Monitor Phase**:
   - Off-chain service watches for proxy boxes with this contract
   - Indexes by state NFT (`tokens(0)`)

2. **Withdrawal Request Construction**:
   - User submits withdrawal request → off-chain constructs proxy box
   - Sets R4 = user address, R5 = amount, R6 = deadline height
   - Mints singleton NFT as `tokens(0)`

3. **Execution Decision**:
   - **Before R6 height**: Bot constructs withdrawal transaction
     - OUTPUTS(2) = user box with R7 = SELF.id
     - OUTPUTS(0,1) = protocol/fee boxes
   - **At/After R6 height**: Anyone can trigger refund
     - OUTPUTS(0) = refund box with R4 = SELF.id
     - Fewer than 3 total outputs

4. **Verification**:
   - Off-chain validates backward references (R4/R7) match SELF.id before signing
   - Ensures singleton NFT flows to output
   - Confirms no funds are lost (delta ≤ minTxFee for refunds)

## Related Contracts

- **proxyDeposit** (implied): Complementary deposit proxy that mirrors this withdrawal flow
- **ERG-POOL main contract**: Parent pool contract that mints/manages state NFTs and validates refund deadline consensus
- **Multi-stage contract architecture**: This proxy is Stage 1 of 2-3 stage withdrawal process:
  - Stage 0: Pool validates request, creates proxy box
  - **Stage 1 (SELF)**: User withdraws or deadline triggers refund
  - Stage 2+: Pool settlement/rebalancing (implied)

---

### Security Notes

- **Atomicity**: Multi-box safety (backward references in R4/R7) prevents orphaned outputs in concurrent txs
- **Time-lock**: R6 deadline enables dispute resolution without external oracle
- **Storage rent**: minBox