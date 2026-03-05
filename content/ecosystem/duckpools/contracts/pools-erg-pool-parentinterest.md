---
title: duckpools/lend-protocol-contracts — parentInterest.md
description: "ErgoScript contract analysis: contracts/pools/ERG-POOL/parentInterest.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/ERG-POOL/parentInterest.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: `parentInterest.md`

## Purpose

This contract manages a parent box in a hierarchical interest-accrual system for a lending protocol. It orchestrates the accumulation of compound interest across child boxes by validating state transitions where the parent records accumulated interest rates in its history while spinning off new child boxes to continue the accrual chain.

## Inputs / Outputs

### Inputs
- **SELF** (Parent Box): The current parent contract box containing:
  - Parent State NFT (tokens(0))
  - Child pool token (tokens(1)) with decreasing quantity
  - Interest history collection in R4

- **CONTEXT.dataInputs(0)** (Head Child - Data Input): Reference box providing:
  - Child contract script and token
  - Accumulated interest history
  - Height (R5) and index (R6) metadata
  - Used read-only; does not consume value

### Outputs
- **OUTPUTS(0)** (Successor Parent): Updated parent box that:
  - Maintains identical script and token IDs
  - Appends computed total interest to history
  - Decrements child token quantity by 1
  - Retains minimum value after execution fees
  - Includes dummy registers (R5-R9) as sentinels

- **OUTPUTS(1)** (New Child): Fresh child box that:
  - Clones the head child's script
  - Receives single child token
  - Initializes interest history to denominator value
  - Carries forward height metadata
  - Index incremented to successor's history length

## Key Logic

### Core Validation Flow

1. **Parent State Machine Invariants**
   - Successor must execute identical ErgoScript (`successorScript == currentScript`)
   - Parent NFT must be preserved atomically across transition
   - Value conservation: `successorValue >= currentValue - MaximumExecutionFee - (MaxHistorySize × ChildExecutionFee)`
   - Token supply: Child tokens decrease by exactly 1 per execution

2. **Interest Accumulation (Compound Rate Calculation)**
   ```
   totalInterestAccrued = fold(headInterestHistory, 100000000L, {
     accumulator × rate / 100000000L
   })
   ```
   - Uses multiplicative composition of interest rates from head child's history
   - Result appended to parent's R4 history: `currentInterestHistory + [totalInterestAccrued]`
   - Enables compound interest tracking without external oracle

3. **Head Child Validation** (Data Input Verification)
   - Token ID must match parent's child token ID
   - Index must equal current history size (sequential ordering)
   - History size ≥ 430: prevents new child creation if head hasn't accumulated sufficient history
   - Acts as "gating" mechanism—protocol cannot advance until child matures

4. **Child Lifecycle**
   - New child always clones head child's script (deterministic deployment)
   - Receives copy of parent's child token (enables pool distribution)
   - Resets interest history to denominator (100000000L) for fresh accrual cycle
   - Index = successor's history length (tracks generation in chain)

5. **Sentinel Register Checks**
   - Successor R5-R9 must all be `true` (dummy boolean sentinels)
   - New child R7-R9 must be `true`
   - Prevents register pollution; enforces protocol schema

## Registers Used

| Register | Type | Purpose | Box(es) |
|----------|------|---------|---------|
| **R4** | `Coll[Long]` | Interest rate history; append-only accumulation log | Parent (SELF, Successor, Head Child, New Child) |
| **R5** | `Long` (Head/New Child); `Boolean` (Successor) | Height metadata (children); Sentinel flag (parent) | All boxes |
| **R6** | `Int` (Head/New Child); `Boolean` (Successor) | Index in sibling chain (children); Sentinel (parent) | All boxes |
| **R7** | `Boolean` | Sentinel flag (dummy) | Successor, New Child |
| **R8** | `Boolean` | Sentinel flag (dummy) | Successor, New Child |
| **R9** | `Boolean` | Sentinel flag (dummy) | Successor, New Child |

## Tokens

### Parent State NFT
- **tokens(0)** of SELF and Successor
- Ensures singleton identity across state transitions
- Immutable; preserved via `retainParentToken` check

### Child Pool Token
- **tokens(1)** of SELF and Successor
- Fungible; quantity decreases by 1 per execution
- Token ID: `successorChildTokens._1 == currentChildTokens._1`
- Used to spawn new child boxes (each receives one token)
- Depletion eventual; protocol terminates when supply exhausted

### Head Child Token
- **tokens(0)** of CONTEXT.dataInputs(0)
- Cloned to new child output; ensures child boxes form homogeneous pool
- Acts as identity for child contract instances

## Integration Pattern

### Off-Chain Bot / dApp Responsibilities

1. **Identify Boxes**
   - Locate parent box via Parent State NFT
   - Scan UTXO set for head child box (matching child token ID + highest index)

2. **Construct Transaction**
   - **Input 0**: Parent box (SELF)
   - **Data Input 0**: Head child box (read-only reference)
   - **Output 0**: New parent box with:
     - Interest history = `currentHistory ++ [fold(...)]`
     - Decremented child token quantity
     - Preserved value (minus fees)
   - **Output 1**: New child box cloned from head child

3. **Verify Pre-Conditions**
   - Head child's history size ≥ 430 (sufficient maturation)
   - Head child index == current parent history size (no gaps)
   - Off-chain oracle / protocol computes interest rates for head child's history

4. **Execute & Monitor**
   - Submit transaction
   - Verify successor box created with new history entry
   - Track new child generation index for subsequent calls

### Execution Fee Management
- Maximum fee per call: 5,000,000 nanoERGs (5 