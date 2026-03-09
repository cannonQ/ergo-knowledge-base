---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — dev_fee.es
description: "ErgoScript contract analysis: contracts/dev_fee.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/dev_fee.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: `dev_fee.es`

## Purpose

This contract guards a fee box on the Bountiful Bounty Platform and enforces deterministic distribution of accumulated fees to four designated recipients (Bruno, Lgd, Jossemii, and The Stable Order) plus a miner fee. It acts as a **treasury guard** ensuring fees are split proportionally and only via authorized transactions.

---

## Inputs / Outputs

### Inputs
- **Multiple BountifulFee boxes** (M fee-collecting UTXOs): Fee boxes locked under this contract's ErgoTree, holding accumulated ERG value from the platform.
- **No data inputs** required.

### Outputs
- **Output 0 (Bruno box)**: ERG value to Bruno's address
- **Output 1 (Lgd box)**: ERG value to Lgd's address
- **Output 2 (Jossemii box)**: ERG value to Jossemii's address
- **Output 3 (The Stable Order box)**: ERG value to The Stable Order's address
- **Output 4 (Miner fee box)**: Minimum fee amount for transaction inclusion; must lock to a miner-fee address (verified by ErgoTree hash)

**Total outputs: exactly 5 boxes**

---

## Key Logic

The contract validates **Fee Distribution Transactions** through a single predicate `validFeeDistributionTx`, which enforces:

### 1. **Minimum Total Output** (`validMinAmount`)
- Total ERG across all outputs ≥ 5,000,000 nanoERG (5 ERG)
- Prevents dust/spam transactions

### 2. **Correct Dev Fee Splits** (`validDevBoxes`)
- Calculates each recipient's share as: `(recipientNum × devAmount) / feeDenom`
  - **Bruno**: 32/100 = 32% of dev amount
  - **Lgd**: 32/100 = 32% of dev amount
  - **Jossemii**: 32/100 = 32% of dev amount
  - **The Stable Order**: 4/100 = 4% of dev amount
  - **Miner fee**: deducted before distribution
- Validates each output box:
  - Holds **exact calculated amount** (no rounding tolerance)
  - Locked to **correct recipient's public key** (via `propositionBytes` match against `sigmaAddress.propBytes`)

### 3. **Miner Fee Validation** (`validMinerFee`)
- Miner fee box value ≥ 1,100,000 nanoERG (allows for future increases)
- Miner fee box ErgoTree **blake2b256 hash** matches hardcoded hash:
  ```
  e540cceffd3b8dd0f401193576cc413467039695969427df94454193dddfb375
  ```
  - Ensures miner fee locks to an authorized miner-fee address (singleton pattern)

### 4. **Output Count** (`validOutputSize`)
- Transaction must produce **exactly 5 outputs** (no extra boxes allowed)

### Final Predicate
```ergoscript
sigmaProp(validFeeDistributionTx)
```
All conditions must pass (`allOf`) for the transaction to be valid.

---

## Registers Used

**No registers (R4–R9) are used.** This contract relies solely on:
- **Compile-time constants** (`$` substitution): receiver addresses
- **Box properties**: `OUTPUTS`, `value`, `propositionBytes`
- **Cryptographic verification**: blake2b256 hashing

---

## Tokens

**No native tokens** are handled by this contract. The contract operates exclusively on **ERG value** (`Box.value`), the native currency of the Ergo blockchain.

---

## Integration Pattern

### Off-Chain Bot/Application Responsibilities

1. **Accumulation Phase**
   - Off-chain service collects fees into one or more UTXOs locked under this contract's ErgoTree

2. **Distribution Tx Construction**
   - When threshold is reached (≥ 5 ERG), construct a transaction with:
     - **Inputs**: One or more fee boxes currently guarded by this contract
     - **Outputs**: Five boxes with exact allocations:
       ```
       Output[0]: value = (32 × devAmount) / 100, address = Bruno
       Output[1]: value = (32 × devAmount) / 100, address = Lgd
       Output[2]: value = (32 × devAmount) / 100, address = Jossemii
       Output[3]: value = (4 × devAmount) / 100,  address = Order
       Output[4]: value = 1100000+ nanoERG,      address = Miner fee singleton
       ```
     where `devAmount = total_input_value - miner_fee`

3. **Signature Requirements**
   - Transaction does **not** require signatures from Bruno, Lgd, Jossemii, or Order (commented out: `// && atLeast(1, ...)`), only from the fee-box owner/operator
   - Miner includes transaction and provides the miner fee

4. **Verification Pre-Submission**
   - Off-chain code must verify:
     - All proportions calculate correctly (exact value matching)
     - Recipient addresses match constants
     - Miner fee box ErgoTree blake2b256 hash matches the hardcoded singleton identifier

---

## Related Contracts

Based on the code structure, this contract composes with:

1. **Bounty/Platform Contract** (inferred as `BountifulFee`)
   - Feeds accumulated platform fees into boxes locked under `dev_fee.es`

2. **Miner Fee Contract/Singleton** (identified by blake2b256 hash)
   - The Output[4] box locks to a **state singleton** that manages miner fee distribution or collection
   - The hash `e540cceffd3b8dd0f401193576cc413467039695969427df94454193dddfb375` is the ErgoTree hash of this singleton's contract

### Contract Composition Pattern
```
Platform Contracts → Accumulate Fees → dev_fee.es (Guard) → 
  Fee Distribution Tx → 