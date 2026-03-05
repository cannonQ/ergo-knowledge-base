---
title: duckpools/off-chain-bot — README.md
description: "ErgoScript contract analysis: README.md"
tags: [duckpools, off-chain-bot, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/off-chain-bot"
contract_file: README.md
project: duckpools-off-chain-bot
---
# ErgoScript Contract Analysis: duckpools Off-Chain Bot

## Purpose

This README documents an **off-chain bot infrastructure** for the duckpools protocol that processes pending orders outside the blockchain to improve scalability and concurrency. The bot scans for user-submitted orders via UI, queues them for blockchain submission, and earns fees by handling interest updates, liquidations, and order completions. This represents a **headless dApp** pattern where off-chain automation bridges user intent to on-chain contract execution.

## Inputs / Outputs

### Expected Inputs (Boxes/UTXOs)
- **Order Boxes**: User-created UTXOs representing pending swap/pool orders from the duckpools UI
- **Liquidation Setup Boxes**: UTXOs created during `setup.py` execution (0.074 ERG each) that serve as state containers for liquidation operations
- **User Wallet Box**: The operator's node wallet (minimum 0.1 ERG) to cover transaction fees and operational costs
- **Data Input Boxes**: Pool state, oracle price feeds, or other contract state referenced but not consumed

### Expected Outputs (Produced Boxes)
- **Completed Order Boxes**: UTXOs reflecting fulfilled swaps/liquidity provision with updated assets
- **Fee Collection Boxes**: Boxes accumulating bot operator earnings from transaction processing
- **Updated Liquidation State Boxes**: Boxes carrying forward liquidation state after on-chain execution
- **Change Boxes**: Unspent ERG and tokens returned to operator wallet

## Key Logic

The core validation flow (implicit in the off-chain construction):

1. **Order Discovery**: Off-chain bot polls Ergo node for unspent boxes matching duckpools contract patterns
2. **Batch Validation**: Bot verifies pending orders satisfy:
   - Correct script guards (ErgoTree signature matching)
   - Sufficient collateral/liquidity
   - Oracle price integrity (via data inputs)
   - Minimum box value (storage rent) compliance
3. **Transaction Construction**: Bot assembles atomic transaction with:
   - Multiple order inputs in single multi-input transaction
   - Proper register preservation/updates for state machines
   - Fee deduction to operator box
   - Signable by operator's node wallet (single signature, no ring signatures needed)
4. **Submission & Monitoring**: Bot signs via node wallet, submits to mempool, tracks confirmation
5. **Liquidation Trigger**: Special logic monitors collateral ratios; executes liquidation contracts when thresholds breached
6. **Fee Extraction**: Protocol ensures liquidation + interest-update transactions include bot operator fee output

## Registers Used

While the README does not expose specific ErgoScript register usage, the architecture implies:

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | Long (typical state) | Order amount / collateral value / pool share quantity |
| **R5** | ByteArray (typical state) | Owner public key / Pool ID / Liquidator address |
| **R6** | (Context-dependent) | Price oracle commitment / Deadline timestamp / Fee tier |
| **R7** | (Optional) | Multi-signature threshold / Advanced state machine flags |
| **R8–R9** | (Reserved) | Protocol-reserved; not typically used in duckpools |

**Context Extension**: The off-chain bot may inject via `Context extension`:
- Current oracle prices (to validate liquidation eligibility)
- Timestamp proof (for order expiry checks)
- Node operator's signature (via Sigma protocol)

## Tokens

### Native Tokens & NFTs Likely Present

1. **State/Singleton NFT**: Each liquidation setup box carries a unique token ID (Token ID Rule) ensuring only one "official" state machine instance exists per operation
2. **Pool LP Tokens**: Represents liquidity provision shares; transferred between boxes in liquidity operations
3. **Fee Tokens** (optional): Could represent earned fees; accumulated in operator's fee collection box
4. **Order Identifier Tokens**: Unique tokens minting/burning to mark order lifecycle state transitions

### Token Authentication
- **State NFT**: Ensures only the correct liquidation contract instance executes (prevents replay across pools)
- **Atomic swap guarantee**: LP tokens locked in order box; released only on successful execution
- **Multi-token boxes**: Liquidation boxes may hold multiple tokens (ERG + pool token + fee token)

## Integration Pattern

### Off-Chain Bot → On-Chain Contract Flow

1. **Discovery Phase** (bot logic):
   ```
   Ergo Node RPC → Query UTXOs matching duckpools addresses
                 → Filter unspent, valid script, non-zero registers
   ```

2. **Construction Phase** (bot logic):
   ```
   For each pending order:
     - Read R4 (order amount), R5 (owner), R6 (params)
     - Validate oracle price from data input box
     - Calculate fees, check minimum box value
     - Construct unsigned transaction (multi-input)
   ```

3. **Signing Phase** (node integration):
   ```
   /wallet/transaction/sign endpoint
     ← Unsigned TX
     → Signed TX (Sigma protocol proof from operator's key)
   ```

4. **Submission Phase**:
   ```
   /transactions endpoint → broadcast to mempool
   Monitor /transactions/{txId} → await confirmation
   ```

5. **State Update** (contract invariant):
   ```
   Input Box: [script, R4=old_amount, R5=owner, token=state_nft]
     ↓ (ErgoScript guards fire)
   Output Box: [script, R4=new_amount, R5=owner, token=state_nft]
     + Fee Box: [0.01 ERG to operator]
   ```

### Critical Invariants Bot Must Enforce
- **No script mutation**: Output box's ErgoTree matches input (state machine continuation)
- **Token ID preservation**: State NFT from input appears in output (Singleton pattern)
- **Register consistency**: R5 (owner) unchanged unless explicitly authorized
- **Minimum value**: Every output ≥ storage rent (typically 0.001 ERG × box size in bytes)
- **Atomic execution**: All order processing in single Transaction (all-or-nothing)

## Related Contracts

While not exposed in the README, the architecture references:

1. **Order/Swap Contract**: Validates order box structure, guards spending via owner signature + bot