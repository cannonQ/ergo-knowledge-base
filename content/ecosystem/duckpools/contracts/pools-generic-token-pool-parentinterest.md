---
title: duckpools/lend-protocol-contracts — parentInterest.md
description: "ErgoScript contract analysis: contracts/pools/Generic-Token-Pool/parentInterest.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/Generic-Token-Pool/parentInterest.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: `parentInterest.md`

## Purpose

This contract manages a **parent-child interest tracking system** for a lending protocol, maintaining a linked-list state machine of interest history snapshots. The parent box stores accumulated interest rates across child boxes and validates the creation of new child boxes when the current child's history reaches capacity, enabling scalable historical record-keeping without storage bloat.

---

## Inputs / Outputs

### Inputs
| Type | Role | Description |
|------|------|-------------|
| **SELF** | Parent Box | Current state container holding parent token, child token count, and interest history register |
| **Data Input (CONTEXT.dataInputs(0))** | Head Child Box | Reference-only input; the most recently created child snapshot being retired due to full history |

### Outputs
| Index | Role | Description |
|-------|------|-------------|
| **OUTPUTS(0)** | Parent Successor | Updated parent box with appended interest history and decremented child token count |
| **OUTPUTS(1)** | New Child Box | Freshly minted child box initialized with base interest rate (1.0 = 10^8) and incremented index |

---

## Key Logic

### Core Validation Conditions

1. **Parent Box Continuity**
   - Successor script must equal current script (same ErgoTree)
   - Successor value ≥ current value minus execution fees (accounts for cost of child creation/retirement)
   - Parent token identity preserved in successor

2. **Child Token Management**
   - Child token ID must remain constant across parent/successor
   - Child token amount decreases by exactly 1 (one child being retired)

3. **Interest History Accumulation**
   - Head child's interest history is read from R4
   - **Interest compounding formula**: `totalInterestAccrued = fold(headInterestHistory, 10^8, (z, base) ⇒ z × base ÷ 10^8)`
   - This accumulated value is appended to parent's history in successor box
   - Enables tracking of compound interest across time periods

4. **Head Child Validation**
   - Head child token matches parent's child token ID
   - Head child index equals current parent history size (proves sequential ordering)
   - Head child history size ≥ MaxHistorySize (100 entries)—this is the retirement trigger

5. **New Child Initialization**
   - New child receives same script as head child (code inheritance)
   - New child value ≥ 100 × ChildExecutionFee (2 ERG min, for future retirement)
   - New child index = successor history size (incremental counter)
   - New child history initialized to `[10^8]` (base rate 1.0)
   - New child height preserved from head child (R5)

---

## Registers Used

| Register | Type | Purpose | Access |
|----------|------|---------|--------|
| **R4** | `Coll[Long]` | Interest history array (rates as fixed-point 10^8) | Parent & Child boxes; updated in successor |
| **R5** | `Long` | Block height when child was created | Child boxes; copied to new child |
| **R6** | `Int` | Sequential index in the linked list | Child boxes; incremented for new child |

---

## Tokens

### Token Types

| Token Position | Type | Purpose | Validation |
|---|---|---|---|
| **tokens(0)** | Parent Token (NFT) | Singleton authenticating the parent box | Must be retained in successor |
| **tokens(1)** | Child Token (Semi-Fungible) | Mints N copies representing N active children | Amount decreases by 1 on retirement; ID constant |

### Token ID Rule
- Child Token ID extracted via `successorChildTokens._1` (tuple unpacking of TokenID and amount)
- Must match across parent/successor and new child to prove lineage

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Monitoring**
   - Track head child box via R6 index
   - Detect when child's R4 history reaches MaxHistorySize (100 entries)

2. **Transaction Construction**
   - **Read**: Current parent box UTXO, head child data input
   - **Compute**: 
     - Compound interest: multiply all head child history rates
     - New parent value: `currentValue - MaximumExecutionFee - ChildExecutionFee`
     - New child index: `currentHistorySize + 1`
   - **Create OUTPUTS(0)**: New parent with appended interest, decremented child tokens
   - **Create OUTPUTS(1)**: New child with reset history

3. **Fee Management**
   - Reserves MaximumExecutionFee (5 ERG) for parent retirement
   - Allocates ChildExecutionFee (2 ERG) × MaxHistorySize for future child retirements
   - This cascading reservation enables unbounded history without storage rent issues

4. **Context Extension**
   - No explicit Context extension required; all data available from R4-R6 reads

---

## Related Contracts

### Inferred Relationships

| Contract | Interaction | Type |
|----------|-------------|------|
| **Child Interest Contract** | `headChild` uses same script logic for rate updates | State machine component |
| **Loan/Pool Contract** | Parent likely receives external interest contributions to R4 | Multi-stage composition |
| **Liquidation/Withdrawal Contract** | May read accumulated interest history for reward distribution | Data consumer |

**Composition Pattern**: This is a **multi-stage contract** where:
- Parent = **State machine root** (immutable script, mutable history)
- Child = **Periodic snapshot container** (reset on each cycle)
- New child = **Next iteration** (linked via index)

The linked-list pattern avoids single-box size limits by distributing history across N child boxes.

---

## Security & Invariants

### Critical Invariants Enforced

```
Invariant 1 (History Monotonicity):
  headIndex == currentInterestHistory.size
  ⟹ each child is indexed sequentially

Invariant 2 (Token Conservation):
  totalSupply(ChildToken) == numActiveChildren
  ⟹ decreasing by 1 per rotation prevents