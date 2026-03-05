---
title: PhoenixErgo/phoenix-hodlcoin-contracts — phoenix_v1_hodltoken_fee.es
description: "ErgoScript contract analysis: hodlToken/contracts/phoenix_fee_contract/v1/ergoscript/phoenix_v1_hodltoken_fee.es"
tags: [phoenixergo, phoenix-hodlcoin-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/PhoenixErgo/phoenix-hodlcoin-contracts"
contract_file: hodlToken/contracts/phoenix_fee_contract/v1/ergoscript/phoenix_v1_hodltoken_fee.es
project: phoenixergo-phoenix-hodlcoin-contracts
---
# Phoenix HodlToken Fee Contract Analysis

## Purpose

This contract guards a fee box within the Phoenix HodlToken protocol and enforces deterministic distribution of accumulated protocol fees to three designated developer addresses (Bruno, Phoenix, Kushti) plus a miner fee. It ensures that only properly structured fee distribution transactions can spend accumulated tokens from this box.

## Inputs / Outputs

### Inputs
- **PhoenixFee boxes** (1 to M): eUTXOs locked by this contract, each containing:
  - Native tokens identified by `$baseTokenId`
  - No registers used

### Outputs
- **Output 0 (Bruno Box)**: eUTXO locked to Bruno's address containing his proportional fee share in `$baseTokenId`
- **Output 1 (Phoenix Box)**: eUTXO locked to Phoenix's address containing his proportional fee share in `$baseTokenId`
- **Output 2 (Kushti Box)**: eUTXO locked to Kushti's address containing his proportional fee share in `$baseTokenId`
- **Output 3 (Miner Fee Box)**: eUTXO containing Ergo value (no tokens) locked to a standardized miner fee address

## Key Logic

The contract validates a **Fee Distribution Transaction** through these atomic checks:

1. **Token Aggregation**: Sum all `$baseTokenId` tokens across all outputs to calculate total fees accumulated
2. **Proportional Distribution**: 
   - Bruno receives `($brunoNum / 100) × totalFees`
   - Phoenix receives `($phoenixNum / 100) × totalFees`
   - Kushti receives `($kushtiNum / 100) × totalFees`
   - Each developer box uses `>=` comparison (allows rounding surplus)

3. **Developer Box Validation** (for each of the 3 developer outputs):
   - First token must be `$baseTokenId`
   - Token amount must meet or exceed calculated proportion
   - `propositionBytes` must match the designated developer's `SigmaProp` (prevents address hijacking)

4. **Miner Fee Validation**:
   - Ergo value must be ≥ `$minerFee` constant
   - `blake2b256` hash of `propositionBytes` must equal the canonical miner fee address hash (`e540ccef...`)
   - No tokens in miner fee box (it only collects Ergo)

5. **Output Structure**: Exactly 4 outputs required (no extraneous boxes)

6. **Authorization**: At least one of the three developers (Bruno, Phoenix, or Kushti) must sign the transaction, creating economic incentive against fee spam

## Registers Used

**None.** This contract does not read or write any auxiliary registers (R4–R9). All state is encoded in token amounts within the eUTXOs themselves.

## Tokens

- **Primary Token**: `$baseTokenId` (Compile-time constant)
  - Type: Native token
  - Role: Fee denomination and distribution medium
  - Multiple fee boxes aggregate their `$baseTokenId` amounts and split them proportionally to developers
  - Token ID rule enforced: only boxes containing this specific token ID are summed

- **No NFT used**: Unlike singleton state machine contracts, this fee distributor does not use a State NFT or token-locked singleton. It is stateless and can process multiple accumulated fee boxes in a single transaction.

## Integration Pattern

### Off-chain Bot / Headless dApp Responsibilities:
1. **Monitor** fee boxes locked to this contract (via Blockchain state query)
2. **Aggregate** all available Phoenix fee boxes
3. **Calculate** proportional splits:
   ```
   totalFees = sum of all $baseTokenId in input boxes
   brunoShare = (totalFees × $brunoNum) / 100
   phoenixShare = (totalFees × $phoenixNum) / 100
   kushtiShare = (totalFees × $kushtiNum) / 100
   ```
4. **Construct** exactly 4 output boxes:
   - Verify each developer box contains sufficient tokens and is locked to correct address
   - Verify miner fee box is locked to address matching `minerFeeErgoTreeBytesHash`
5. **Sign** transaction with at least one developer's private key (Bruno, Phoenix, or Kushti)
6. **Submit** transaction ensuring minimum transaction fee is included

### Constant Segregation:
- `$baseTokenId`, `$minerFee`, `$brunoNum`, `$phoenixNum`, `$kushtiNum` are compile-time constants embedded in the ErgoTree
- Changing these requires recompilation and contract redeployment

### No Context Extension or Data Inputs:
- Transaction context variables (`_`) are unused
- No data inputs referenced, making this contract fully deterministic and auditable on-chain

## Related Contracts

- **Phoenix HodlToken Main Contract**: Likely emits fees to this fee box during protocol operations (minting/burning of hodl coins, liquidations, etc.)
- **Other Phoenix Protocol Contracts**: May redirect transaction outputs to this fee contract for centralized fee accumulation before distribution
- The contract structure suggests integration with a **Multi-stage contract** state machine where the fee distributor is a terminal spending rule called by higher-level protocol logic

---

## Security Notes

- **Atomic Distribution**: All three developers + miner are paid in a single transaction; no partial or failed distributions
- **Non-custodial**: Developers cannot unilaterally withdraw; the contract enforces exact proportions
- **Miner Alignment**: Spam prevention via signature requirement from one of three parties; miner fee covers block inclusion costs
- **Address Pinning**: Developer addresses and miner fee target are hardcoded via `propBytes` comparison, preventing redirect attacks