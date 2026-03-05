---
title: PhoenixErgo/phoenix-hodlcoin-contracts — phoenix_v1_hodlerg_fee.es
description: "ErgoScript contract analysis: hodlERG/contracts/phoenix_fee_contract/v1/ergoscript/phoenix_v1_hodlerg_fee.es"
tags: [phoenixergo, phoenix-hodlcoin-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/PhoenixErgo/phoenix-hodlcoin-contracts"
contract_file: hodlERG/contracts/phoenix_fee_contract/v1/ergoscript/phoenix_v1_hodlerg_fee.es
project: phoenixergo-phoenix-hodlcoin-contracts
---
# Phoenix HodlERG Fee Contract Analysis

## Purpose

This contract guards a fee accumulation box in the PhoenixErgo hodlERG protocol and enforces the distribution of accrued protocol fees to five designated developer addresses plus a miner fee output. It acts as a **state machine exit validator** that ensures fee splits are calculated correctly and routed to the correct recipients whenever fees are withdrawn.

## Inputs / Outputs

### Inputs
- **PhoenixFee1 through PhoenixFeeM**: Multiple fee boxes (eUTXOs) locked under this contract, each containing accumulated ERG. The contract validates when these boxes are spent together in a single fee distribution transaction.

### Outputs
Exactly 6 boxes required:
1. **Bruno's box**: ERG payment to Bruno (25% of dev fees)
2. **Pulsarz's box**: ERG payment to Pulsarz (25% of dev fees)
3. **Phoenix's box**: ERG payment to Phoenix (25% of dev fees)
4. **Kushti's box**: ERG payment to Kushti (15% of dev fees)
5. **Kras's box**: ERG payment to Kras (10% of dev fees)
6. **Miner fee box**: Payment to miners to cover transaction costs

Each output box must contain the exact ERG amount derived from proportional splits of the total fee pool.

## Key Logic

The contract enforces these validation rules:

1. **Output Count**: Exactly 6 outputs must be created (no more, no fewer).

2. **Minimum Value**: Total output value must be ≥ 5,000,000 nanoERG (dust prevention).

3. **Fee Distribution Calculation**:
   - `devAmount` = total output value − miner fee box value
   - Each developer receives a percentage of `devAmount`:
     - Bruno: 25% (25/100)
     - Pulsarz: 25% (25/100)
     - Phoenix: 25% (25/100)
     - Kushti: 15% (15/100)
     - Kras: 10% (10/100)

4. **Developer Box Validation**: Each of the five developer boxes must:
   - Contain the **exact calculated amount** (integer division, truncation-safe)
   - Have a **proposition** (spending script) matching the hardcoded PK for that address

5. **Miner Fee Validation**: The miner fee box must:
   - Contain ≥ `$minerFee` nanoERG (allows for future fee increases)
   - Have a proposition bytes hash matching `minerFeeErgoTreeBytesHash` (a hard-coded miner fee script hash)

6. **Authorization**: The transaction is valid only if **at least one (1)** of the five developers signs it (`atLeast(1, ...)`). This prevents spam while distributing authority.

## Registers Used

**No registers are used** (`R4`–`R9` are not read or written).

- The contract is **stateless**: it performs a one-time fee distribution without tracking internal state.
- All configuration is baked into the contract as Ergo constants or compile-time variables.

## Tokens

**No native tokens** are involved in this contract.

- The contract only manages **ERG** (the base currency).
- No NFTs or Singleton/State NFTs are used for state tracking.

## Integration Pattern

### Off-Chain Bot Responsibility

An off-chain bot or **headless dApp** orchestrates fee distribution:

1. **Monitor**: Collect all fee boxes currently locked under this contract address.
2. **Aggregate**: Sum their ERG values to determine total fee pool.
3. **Calculate**: Compute the five developer amounts using the hardcoded percentages.
4. **Construct**: Build a transaction with:
   - Inputs: all collected fee boxes
   - Outputs: 6 boxes as specified, with correct amounts and proposition bytes
5. **Sign**: Obtain a signature from **at least one** of the five developers (e.g., via a signing service or multi-sig key store).
6. **Submit**: Send the transaction to the Ergo network.

### Key Constraints for Construction

- **Miner Fee Verification**: The off-chain code must know or retrieve the `minerFeeErgoTreeBytesHash` constant and ensure the miner fee output uses the correct script.
- **Address Matching**: Must use the exact Ergo P2PK addresses hardcoded in the contract (PK prefixes like `9gnBtmSRBMaNTkLQUABoAqmU2wzn27hgqVvezAC9SU1VqFKZCp8`).
- **Precise Arithmetic**: Fee splits must use integer division in the same order as the contract to avoid rounding discrepancies.

## Related Contracts

Not directly identifiable from this contract's code alone. However, based on the project structure:

- **HodlERG State Machine**: Likely a separate contract managing the hodlERG staking/minting logic; this fee contract is a **sibling** that captures protocol revenue.
- **Potential Input Contracts**: Other contracts in the hodlERG system may generate UTXOs sent to this fee contract's address for accumulation.

The contract is **not composable** (does not call other contracts via Data inputs or nested execution); it is a **terminal endpoint** that distributes fees outward to developers and miners.

---

## Summary Table

| Aspect | Detail |
|--------|--------|
| **Type** | Fee distribution validator; stateless |
| **State NFT** | None (no registers, no state tracking) |
| **Inputs** | Multiple fee boxes (M ≥ 1) |
| **Outputs** | Fixed 6 boxes (5 devs + miner fee) |
| **Auth** | 1-of-5 developer multisig (SigmaProposition) |
| **Tokens** | ERG only (no native tokens) |
| **Key Invariant** | Fee splits = `(devAmount × numerator) / 100`, exactly matched to outputs |
| **Anti-spam** | Minimum 5M nanoERG output; requires developer signature |