---
title: Singleton / State NFT
description: Singleton / State NFT — identity tokens for multi-stage contract state boxes, one-token-per-box invariant
tags: [singleton-state-nft, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-07
source: auto-generated
source_repos: [kushti/dexy-stable, DjedAlliance/Djed-Ergo, ergoplatform/oracle-core, paideiadao/paideia-contracts]
---
# Singleton / State NFT: Developer Guide for Ergo Integration

---

## Overview

### What Is This Pattern?

A **Singleton / State NFT** is a Native token with a supply of exactly **1** that is permanently locked inside a specific Box to serve as that box's unforgeable on-chain identity. Because Ergo's **Token ID rule** guarantees that every token ID is globally unique (derived from the box ID of the minting transaction's first input, which can never be re-spent), a token with a fixed supply of 1 cannot be duplicated, making it a cryptographically sound identity primitive.

The pattern creates a strict **one-token-per-box invariant**: ErgoScript guards verify that the singleton token must be present in exactly one output box at all times. This transforms an otherwise anonymous UTXO into a **named, persistent, and stateful box** — the canonical representation of a contract's state on-chain.

### Why Does It Exist?

Ergo's **eUTXO** (extended Unspent Transaction Output) model is stateless by design: boxes are consumed and recreated in every transaction. This means there is no built-in concept of "the same box across time." The Singleton NFT pattern solves this by providing:

1. **Persistent Identity**: Any observer can locate the current state box by filtering UTXOs for a known token ID, regardless of how many times it has been spent and recreated.
2. **Tamper-Evident State**: The ErgoScript guards enforcing the one-token-per-box invariant make it impossible to fork, duplicate, or abandon the state box mid-protocol without explicit contract permission.
3. **Multi-Stage Contract Coordination**: In **multi-stage contracts** — protocols where several interacting boxes must progress through defined state transitions — each stage box carries its own singleton to prevent substitution attacks.
4. **Data Input Eligibility**: A singleton-bearing box can be used as a **Data input** (read-only reference) in transactions it does not participate in as a spendable input, enabling other contracts to trustlessly reference its state.

### When To Use It

| Scenario | Use Singleton NFT? |
|---|---|
| Oracle pool tracking the latest ERG/USD rate | ✅ Yes — oracle core's pool box |
| DEX LP pool holding reserves | ✅ Yes — LP NFT identifies the pool |
| Stablecoin bank holding collateral | ✅ Yes — bank box in Dexy/Djed |
| Action-gating (rate-limiting mint operations) | ✅ Yes — arbmint/freemint boxes |
| Simple one-shot payment | ❌ No — no persistent state needed |
| Fungible reward token | ❌ No — supply > 1 |

The pattern is the foundation of **oracle-core**, **Dexy**, **Djed-Ergo**, and **Paideia**, among many other Ergo protocols.

---

## How It Works

### Step 1 — Minting the Singleton

The singleton is minted in a bootstrap transaction. Ergo's Token ID rule states: the ID of a newly minted token equals the **box ID of the first input** of the minting transaction. Since box IDs are derived from transaction content and are globally unique, the resulting token ID is also globally unique.

```
Bootstrap Transaction
  Input[0]: Funding box (box ID → becomes Token ID)
  Output[0]: State Box
    tokens(0): (tokenId=INPUT[0].id, amount=1)  ← the singleton
    R4..R9: initial contract state
    ErgoTree: <contract script>
```

No other box in the history of Ergo can ever hold a token with this ID at amount 1 unless it receives it from this output. This is the **foundation of the invariant**.

### Step 2 — The One-Token-Per-Box Invariant

Every state transition (transaction that spends the state box) must:

1. **Consume** the current state box (spending the singleton).
2. **Recreate** exactly one successor box at a defined output index.
3. **Transfer** the singleton token with amount 1 to that successor.
4. **Enforce** the ErgoTree of the successor matches the same contract (or a permitted next-stage contract).

The ErgoScript enforcing this typically looks like:

```scala
// Pseudocode invariant core
val successor = OUTPUTS(0)
val selfNFT  = SELF.tokens(0)._1          // the singleton token ID

val nftPreserved     = successor.tokens(0)._1 == selfNFT
val nftAmountIsOne   = successor.tokens(0)._2 == 1L
val scriptPreserved  = successor.propositionBytes == SELF.propositionBytes

sigmaProp(nftPreserved && nftAmountIsOne && scriptPreserved)
```

### Step 3 — State Evolution via Registers

The box's **Registers** (R4–R9) carry the mutable state. On each valid transaction:
- The singleton moves to the output box unchanged.
- Registers are updated to reflect the new state.
- The ErgoScript validates that register transitions are within permitted bounds.

```
Transaction N                          Transaction N+1
┌──────────────────────┐              ┌──────────────────────┐
│ State Box (input)    │   spent by   │ State Box (output)   │
│ tokens(0): NFT #id,1 │ ──────────▶  │ tokens(0): NFT #id,1 │
│ R4: height=1000      │              │ R4: height=1360      │
│ R5: remaining=1000   │              │ R5: remaining=800    │
└──────────────────────┘              └──────────────────────┘
```

### Step 4 — Multi-Stage Coordination

When multiple singleton-bearing boxes participate in one transaction, each contract independently verifies its own NFT invariant **and** the correct presence of peer singletons. This eliminates substitution attacks:

```
Transaction: Arbitrage Mint
  Inputs:  [0] ArbMint box (arbmintNFT), [1] Bank box (bankNFT)
  Outputs: [0] ArbMint box',             [1] Bank box'
  Data:    [0] Oracle box (oracleNFT) ← read-only

  ArbMint script checks: INPUTS(1).tokens(0)._1 == bankNFT
  Bank script checks:    INPUTS(0).tokens(0)._1 == arbmintNFT
  Both check: oracle data input carries oracleNFT
```

### Step 5 — Locating the Live State Box

Off-chain code resolves the current state box by querying the UTXO set for the known singleton token ID:

```
GET /api/v1/boxes/unspent/byTokenId/{tokenId}
→ exactly one result (or zero if protocol is paused/bootstrapping)
```

### Step 6 — Storage Rent Considerations

Boxes on Ergo are subject to **Storage rent**: after approximately 4 years (1,051,200 blocks), miners may collect rent from boxes that fall below the **minimum box value**. Long-lived singleton boxes must maintain sufficient ERG value. Protocol designers must budget for rent or include mechanisms for the contract to receive top-up transactions.

---

## Implementation

### ErgoScript: Core Singleton Invariant (Annotated)

```scala
{
  // -------------------------------------------------------
  // Minimal Singleton / State NFT guard
  // Enforces:
  //   1. Singleton NFT preserved in successor
  //   2. Successor at OUTPUTS(0) carries same ErgoTree
  //   3. No token duplication possible
  // -------------------------------------------------------

  // The token ID that serves as this box's identity.
  // Using SELF.tokens(0)._1 makes the script generic:
  // the same ErgoScript compiles to different ErgoTrees
  // for different NFT IDs (template + constant injection).
  val singleton = SELF.tokens(0)._1

  // Successor box must be the first output (index 0).
  // Using a fixed index prevents a malicious transaction
  // from placing the NFT in an unexpected output that
  // bypasses other checks.
  val successor = OUTPUTS(0)

  // Core invariant: token ID matches, amount is exactly 1.
  val nftPreserved   = successor.tokens(0)._1 == singleton
  val amountIsOne    = successor.tokens(0)._2 == 1L

  // Script continuity: successor must be governed by
  // the same contract. Without this check, a valid
  // transaction could "escape" to an unconstrained script.
  val scriptContinues = successor.propositionBytes ==
                        SELF.propositionBytes

  // Minimum value continuity: prevent gradual ERG drain
  // that could eventually trigger storage rent seizure.
  val valuePreserved  = successor.value >= SELF.value

  sigmaProp(
    nftPreserved    &&
    amountIsOne     &&
    scriptContinues &&
    valuePreserved
  )
}
```

### ErgoScript: Dexy Bank Box (Derived From `bank.es`)

The Bank box demonstrates a production singleton pattern where the NFT coexists with large fungible token reserves and participates in multi-party transactions:

```scala
{
  // Bank script
  //
  // This box: (Bank box)
  //
  // TOKENS
  //   tokens(0): bankNFT  — singleton identifying this bank instance
  //   tokens(1): dexyUSD  — fungible stablecoin supply held in reserve
  //
  // TRANSACTIONS
  // [1] Arbitrage Mint
  //   Input[0]: ArbMint box  | Output[0]: ArbMint box'  | Data[0]: Oracle box
  //   Input[1]: Bank box     | Output[1]: Bank box'     |
  //
  // [2] Free Mint
  //   Input[0]: FreeMint box | Output[0]: FreeMint box' | Data[0]: Oracle box
  //   Input[1]: Bank box     | Output[1]: Bank box'     |
  //
  // [3] Intervention
  //   Input[0]: LP box       | Output