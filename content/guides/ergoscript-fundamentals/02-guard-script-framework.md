---
title: "ErgoScript Fundamentals: Guard Script Framework"
description: "A systematic box-focused methodology for designing ErgoScript contracts — list components, define spending paths, then translate to code. Adapted from DeCo Education's ErgoScript Developer Course."
tags: [ergoscript, guard-scripts, contract-design, framework, tutorial, deco-education]
category: guide
difficulty: intermediate
sdk: [none]
updated: 2026-03-06
source: adapted
original_source: "https://github.com/DeCo-Education/ErgoScript-Developer-Course"
original_author: "DeCo Education (lgd, kii)"
license: MIT
---

# ErgoScript Fundamentals: Guard Script Framework

> **Attribution:** This guide is adapted from [DeCo Education's ErgoScript Developer Course](https://github.com/DeCo-Education/ErgoScript-Developer-Course) (Week 2), originally created by lgd and kii under the MIT License.

## Prerequisites

- [Boxes, Registers & Blockchain Context](01-boxes-registers-context.md) — ErgoScript syntax and types
- [Boxes and Registers](../../concepts/boxes-and-registers.md) — Box structure reference

## The Problem

When building an ErgoScript contract, jumping straight to code often leads to missed edge cases, forgotten conditions, and contracts that don't compose well. The **Guard Script Framework** is a box-focused design methodology that gives you a structured way to plan contracts before writing a single line of ErgoScript.

The framework starts from the box itself — what it holds, what can change, and under what conditions — then systematically translates that design into code.

## The Framework

A guard script determines whether a box is spendable in a transaction. The framework works by listing every component of the box and every action that can modify it.

### Step 1: List the Box Components

For the box your contract will guard, define:

1. **Value** — How much ERG the box holds
2. **Tokens** — What tokens it carries (identification NFTs, fungible tokens)
3. **Registers** — What data lives in R4–R9 (type and meaning of each)
4. **Spending Paths** — Every valid way the box can be spent

### Step 2: Define Each Spending Path

For each action that can happen to this box, specify:

- **INPUTS Position** — Where this box sits in the transaction's INPUTS
- **OUTPUTS Position** — Where the successor box appears in OUTPUTS
- **Trigger Condition** — What distinguishes this path from others (how the contract knows which path is being taken)
- **Contract Conditions** — What must be true for this path to succeed

### Step 3: Define Box Conditions

Cross-cutting conditions that apply across multiple spending paths:

- **Persisted data** — What must never change between input and output
- **Modified data** — What is allowed to change
- **Other conditions** — Anything that must hold for every transaction (e.g., records updated)

### Step 4: Write the ErgoScript

Translate the framework directly into code: box conditions first, then spending paths using if/else branching on trigger conditions.

## Worked Example: Personal Record Box

Let's design a box that stores someone's personal record — their name, age, math score, and whether they've completed a course.

### Framework

**Value**: 0.1 ERGs

**Token List:**
1. Record NFT — Identification token (quantity: 1)

**Registers:**

| Register | Label | Type | Contents |
|----------|-------|------|----------|
| R4 | Personal Details | `Coll[Coll[Byte]]` | First Name, Last Name, Address |
| R5 | Age, HOB & Grades | `Coll[Long]` | Age, Height of Birth (block height), Math Score |
| R6 | Joined DeCo | `Boolean` | Whether they took the DeCo Layman Course |
| R7 | Records | `Long` | Last recorded block height |

**Spending Paths:**

#### Path 1: Grows Older

- *INPUTS Position*: 0
- *OUTPUTS Position*: 0
- *Trigger Condition*: When all other conditions fail (the else branch)
- *Contract Conditions*:
  1. Everything stays the same except the age
  2. Age can only increment by `n`, where `n = ((HEIGHT - HOB) / heightInAYear) - currentAge`

#### Path 2: Math Score Updated

- *INPUTS Position*: 0
- *OUTPUTS Position*: 0
- *Trigger Condition*: Test Score Identification Token present in INPUTS(1)
- *Contract Conditions*:
  1. Everything stays the same except the Math Score
  2. New Math Score comes from the Test Score Box's R4

#### Path 3: Complete DeCo Course

- *INPUTS Position*: 0
- *OUTPUTS Position*: 0
- *Trigger Condition*: DeCo Award NFT present in INPUTS(1)
- *Contract Conditions*:
  1. Math Score must be >= 98 to qualify

**Box Conditions:**

*Persisted data:*
1. Identification Token (same ID and quantity)
2. Personal details (R4 unchanged)

*Modified data:*
- Varies by spending path (age, math score, or DeCo flag)

*Other conditions:*
1. R7 (records) updated to current HEIGHT for every transaction

### ErgoScript Implementation

Following the framework, we write box conditions first, then spending paths:

```ergoscript
{
  // ===== Box Conditions (apply to all spending paths) =====

  // Persisted data: identification token must survive
  val persistIdentificationToken = allOf(Coll(
    SELF.tokens(0)._1 == OUTPUTS(0).tokens(0)._1,
    SELF.tokens(0)._2 == OUTPUTS(0).tokens(0)._2
  ))

  // Persisted data: personal details unchanged
  val persistPersonalDetails =
    SELF.R4[Coll[Coll[Byte]]].get == OUTPUTS(0).R4[Coll[Coll[Byte]]].get

  // Other condition: records updated every transaction
  val recordsUpdated =
    OUTPUTS(0).R7[Long].get == HEIGHT

  val boxConditionsCheck = allOf(Coll(
    persistIdentificationToken,
    persistPersonalDetails,
    recordsUpdated
  ))

  // ===== Shared checks for spending paths =====

  // Age and Height-of-Birth stay the same (used in paths 2 and 3)
  val ageNHOBCheck = allOf(Coll(
    SELF.R5[Coll[Long]].get(0) == OUTPUTS(0).R5[Coll[Long]].get(0),
    SELF.R5[Coll[Long]].get(1) == OUTPUTS(0).R5[Coll[Long]].get(1)
  ))

  // Math score stays the same (used in paths 1 and 3)
  val mathScoreCheck =
    SELF.R5[Coll[Long]].get(2) == OUTPUTS(0).R5[Coll[Long]].get(2)

  // DeCo flag stays the same (used in path 1)
  val deCoAwardCheck =
    SELF.R6[Boolean].get == OUTPUTS(0).R6[Boolean].get

  // ===== Spending Paths (triggered by what's in INPUTS(1)) =====

  if (INPUTS(1).tokens(0)._1 == deCoNFTAwardToken) {
    // Path 3: Complete DeCo Course
    sigmaProp(allOf(Coll(
      boxConditionsCheck,
      ageNHOBCheck,
      SELF.R5[Coll[Long]].get(2) >= 98  // Must have high math score
    )))
  } else if (INPUTS(1).tokens(0)._1 == testScoreIdentification) {
    // Path 2: Math Score Updated
    sigmaProp(allOf(Coll(
      boxConditionsCheck,
      ageNHOBCheck,
      OUTPUTS(0).R5[Coll[Long]].get(2) == INPUTS(1).R4[Long].get  // Score from test box
    )))
  } else {
    // Path 1: Grows Older (default path)
    val maxAge = (HEIGHT - SELF.R5[Coll[Long]].get(1)) / heightInAYear
    val ageNotExceedMaxAge = OUTPUTS(0).R5[Coll[Long]].get(0) <= maxAge

    sigmaProp(allOf(Coll(
      boxConditionsCheck,
      deCoAwardCheck,
      mathScoreCheck,
      ageNotExceedMaxAge
    )))
  }
}
```

### How the Framework Maps to Code

Notice the direct correspondence:

| Framework Section | Code Section |
|-------------------|-------------|
| Persisted data → Identification Token | `persistIdentificationToken` |
| Persisted data → Personal details | `persistPersonalDetails` |
| Other conditions → Records updated | `recordsUpdated` |
| All box conditions combined | `boxConditionsCheck` |
| Trigger: DeCo Award NFT in INPUTS(1) | `if (INPUTS(1).tokens(0)._1 == deCoNFTAwardToken)` |
| Trigger: Test Score token in INPUTS(1) | `else if (INPUTS(1).tokens(0)._1 == testScoreIdentification)` |
| Trigger: Default (else) | `else { ... }` |

Each spending path references `boxConditionsCheck` plus its own specific conditions. The trigger conditions (what token is in INPUTS(1)) determine which branch executes.

## Design Patterns to Notice

### 1. NFT as Identity

The identification token ensures continuity. Without it, anyone could create a fake box with the same script and arbitrary register data. The NFT ties the box to a specific lineage of state transitions.

### 2. Trigger Tokens

Using tokens in INPUTS(1) as trigger conditions is a clean pattern for routing spending logic. The contract doesn't need to inspect complex state — it just checks what token accompanies it.

### 3. Selective Persistence

Not everything needs to persist across every path. In Path 1 (age update), the DeCo flag and math score must persist. In Path 2 (score update), age and HOB must persist. The framework makes these requirements explicit before coding.

### 4. External Data via Input Boxes

Path 2 reads the new math score from `INPUTS(1).R4[Long]` — the test score box provides the data. This is a common pattern: input boxes carry authoritative data that the contract incorporates into its state transition.

## Blank Framework Template

Use this template when designing your own contracts:

```
**Value**: {amount} ERGs

**Token List:**
1. {Token name}
   - {Role} — {quantity}

**Registers:**
| Register | Label | Type | Contents |
|----------|-------|------|----------|
| R4 | | | |
| R5 | | | |
| R6 | | | |
| R7 | | | |
| R8 | | | |
| R9 | | | |

**Spending Paths:**

1. {Path Name}
   - *INPUTS Position*:
   - *OUTPUTS Position*:
   - *Trigger Condition*:
   - *Contract Conditions*:
     1.

2. {Path Name}
   - *INPUTS Position*:
   - *OUTPUTS Position*:
   - *Trigger Condition*:
   - *Contract Conditions*:
     1.

**Box Conditions:**
*Persisted data:*
1.

*Modified data:*
1.

*Other conditions:*
1.
```

## Real-World Application: Auction House

The [Ergo Auction House](https://github.com/anon-real/ErgoAuctionHouse) uses exactly this kind of structured approach across its contracts:

- **Issue Artwork** — Creates an NFT with metadata in registers
- **New Auction** — Sets up an auction box with starting price, deadline, and seller info
- **New Bid** — Validates bid amount exceeds current price, preserves auction parameters, updates bidder info

Each of these transactions follows the same pattern: persisted data (auction identity), modified data (current bid/bidder), trigger conditions (bid token or deadline reached), and box conditions (script continuity, token preservation).

## What's Next

- [Off-Chain with AppKit](03-offchain-appkit.md) — Build the transactions that interact with these contracts
- [eUTXO Model](../../concepts/eutxo-model.md) — How multi-stage protocols chain boxes together
- [Boxes and Registers](../../concepts/boxes-and-registers.md) — Complete register type reference

---

*Adapted from [DeCo Education ErgoScript Developer Course](https://github.com/DeCo-Education/ErgoScript-Developer-Course) (MIT License) by lgd and kii. The Guard Script Framework is a unique contribution of the DeCo course — see the original materials for additional exercises.*
