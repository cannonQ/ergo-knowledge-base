---
title: duckpools/lend-protocol-contracts — treasury.md
description: "ErgoScript contract analysis: contracts/treasury-system/treasury.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/treasury-system/treasury.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Treasury System

## Purpose

This contract implements a **treasury state machine** that manages a multi-token vault controlled by a voting system. It supports two operations: (1) **deposits** that increase treasury value and optionally add new token types via governance votes, and (2) **withdrawals** that distribute proportional shares of assets to recipients based on vote outcomes, with the option to spawn a new treasury under different governance.

## Inputs / Outputs

### Inputs
| Position | Role | Description |
|----------|------|-------------|
| `INPUTS(0)` | Branching signal + Vote box (withdrawal) | In deposits: the treasury itself; in withdrawals: the vote result box |
| `INPUTS(1)` | Vote box (deposit) / Treasury box (withdrawal) | In deposits: governance vote with token additions; in withdrawals: the treasury being withdrawn from |
| Data inputs | Optional governance data | May include vote results or governance state |

### Outputs
| Position | Role | Description |
|----------|------|-------------|
| `OUTPUTS(0)` | Treasury successor or recipient | Recreated treasury (with updated state) or new treasury under different script |
| `OUTPUTS(1)` | Recipient box (withdrawal only) | Payment box to vote winner's address |

## Key Logic

### Deposit Branch (`INPUTS(0) == SELF`)
Validates that the treasury can accept deposits while optionally expanding its token portfolio:

1. **Script Invariant**: Successor treasury retains identical proposition bytes (ErgoTree)
2. **Value Monotonicity**: Successor holds ≥ incoming value (no fund loss)
3. **Token Preservation**: All existing tokens maintained at minimum quantities (no token burning without governance)
4. **Token Addition Gate**:
   - If `INPUTS(1)` carries the `counterToken` NFT (governance marker), read `R6` for `Coll[Coll[Byte]]` (list of new token IDs to add)
   - Validate all tokens in R6 appear in successor box
   - Verify successor token count = current token count + new tokens added
   - If no vote (`INPUTS(1)` lacks `counterToken`), token count must remain identical

### Withdrawal Branch (`INPUTS(1) == SELF`)
Splits treasury assets according to a vote result, with two sub-modes:

#### Vote Result Validation
- `INPUTS(0)` must carry `counterToken` with amount = **2** (state marker for completed vote)
- Read `R4[Long]` → `proportionAwared` (numerator, denominator = 10,000,000)
- Read `R5[Coll[Byte]]` → `recipient` (recipient's ErgoTree script hash)

#### Regular Withdrawal (`proportionAwared ≠ 10,000,000`)
Proportional distribution of treasury assets:

1. **Treasury Successor Validation**:
   - Script retained (same ErgoTree)
   - Value ≥ treasury value − awarded amount
   - First token (treasury NFT at index 0) unchanged

2. **Asset Distribution Formula**:
   ```
   valueAwarded = SELF.value × proportionAwared / 10,000,000
   tokenAwarded = tokenAmount × proportionAwared / 10,000,000
   ```

3. **Recipient Box**:
   - Script must match `recipient` (ErgoTree from R5)
   - Value ≥ `valueAwarded`
   - Tokens: only non-zero awarded tokens (filters out dust via `> 0` check)
   - Token array must exactly match computed expected amounts

4. **Treasury State Update**:
   - Tokens remaining: original − awarded (for each token in slice `[1, size)`)
   - NFT (index 0) stays in treasury
   - Token count unchanged

#### New Treasury Mode (`proportionAwared == 10,000,000`)
Transfer full control to new treasury under different governance:

1. New treasury script = `recipient` (new governance script, not an address)
2. New treasury receives all assets unchanged (full NFT + tokens)
3. Value ≥ current treasury value (preservation)
4. Token count and content identical to current treasury

## Registers Used

| Register | Branch | Type | Purpose |
|----------|--------|------|---------|
| `R6` | Deposit | `Coll[Coll[Byte]]` | List of token IDs to add (read from governance box `INPUTS(1)`) |
| `R4` | Withdrawal | `Long` | Proportion numerator (0 to 10,000,000) |
| `R5` | Withdrawal | `Coll[Byte]` | Recipient's ErgoTree script bytes or new treasury script |

## Tokens

| Token | Type | Purpose | Location |
|-------|------|---------|----------|
| `counterToken` (Base58: `62ATdscxMts7bNB45c7Md5GXYTPk1bQAvb7hDKB5LhXp`) | State NFT / Governance marker | Identifies governance votes; amount = 2 indicates completed vote result in withdrawal mode | `INPUTS(0).tokens(0)` (withdrawal) or `INPUTS(1).tokens(0)` (deposit) |
| Treasury NFT | State NFT | Singleton token ensuring treasury continuity; always at token index 0; never transferred to recipients | `SELF.tokens(0)` |
| Vault tokens | Managed assets | Arbitrary ERC20-style tokens held in treasury; quantities scaled by vote proportion | `SELF.tokens[1..]` |

## Integration Pattern

### Off-Chain Coordinator (Bot) Responsibilities

1. **Deposit Flow**:
   - Monitor treasury box for deposit requests
   - Aggregate incoming funds and optional token additions
   - Build governance vote box (if new tokens proposed):
     - Place `counterToken` NFT in box
     - Populate `R6` with new token IDs
     - Ensure this box is at `INPUTS(1)`
   - Construct successor treasury output with updated balances
   - Ensure treasury box is at `INPUTS(0)` (self-reference)

2. **Withdrawal Flow**:
   - Execute governance/voting protocol separately (off-chain)
   - Create vote result box containing:
     - `counter