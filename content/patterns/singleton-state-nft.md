---
title: Singleton / State NFT
description: Singleton / State NFT — identity tokens for multi-stage contract state boxes, one-token-per-box invariant
tags: [singleton-state-nft, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [kushti/dexy-stable, DjedAlliance/Djed-Ergo, ergoplatform/oracle-core, paideiadao/paideia-contracts]
---
# Singleton / State NFT Pattern — Ergo Developer Guide

## Table of Contents
1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Implementation](#implementation)
4. [Common Pitfalls](#common-pitfalls)
5. [References](#references)

---

## Overview

### What Is the Singleton / State NFT Pattern?

In Ergo's eUTXO model, a **Box** is the fundamental unit of state: it holds ERG, Native tokens, and up to ten Registers. Unlike account-based blockchains where a contract has a persistent address with mutable storage, every Ergo smart contract interaction *destroys* one or more input Boxes and *creates* new output Boxes. This raises an immediate problem for **multi-stage contracts**: how does a downstream contract — or an off-chain actor — reliably locate the *canonical* current-state Box among potentially thousands of Boxes locked at the same ErgoTree address?

The **Singleton / State NFT** pattern solves this by minting exactly one token (the NFT) and requiring that token to be present in the state Box at all times. Because Ergo's **Token ID rule** guarantees that a token's ID is the ID of the Box in which it was first minted (the `boxId` of the input Box at index 0 of the issuance transaction), and because a given token quantity can never be inflated after issuance, a supply-1 token is cryptographically unique across the entire chain. Any contract or off-chain indexer can locate the live state Box with a single token-ID lookup.

> **Key invariant:** `SELF.tokens(0)._1 == singletonNFT && SELF.tokens(0)._2 == 1L`  
> This invariant must be enforced in every spending path of the contract.

### Why Does It Exist?

| Challenge | Without Singleton NFT | With Singleton NFT |
|---|---|---|
| Box identity | Box ID changes every block | NFT ID is immutable |
| State discovery | Scan all boxes at address | Filter by token ID |
| Forgery resistance | Anyone can create a lookalike box | NFT supply is fixed at 1 |
| Multi-stage chaining | Fragile address matching | Hard token-ID predicate |
| Data input referencing | Ambiguous which box is "live" | Deterministic lookup |

Ergo's **Storage rent** mechanism (a box with insufficient ERG is eventually reclaimed after ~4 years) means boxes *do* get recycled, so the NFT serves as the permanent thread of identity even as the hosting Box is recreated with each transaction.

### When to Use It

Use the Singleton / State NFT pattern when you need:

- **A single authoritative state box** that evolves over time (oracle pools, AMM pools, DAO treasuries, stablecoin banks).
- **Multi-stage contracts** where stage N's script must verify it is spending the *real* stage N−1 output, not a crafted impersonator.
- **Data inputs** that downstream contracts reference by token ID rather than by Box ID (which is unknowable at compile time).
- **Rate limiters / counters** stored in Registers that must persist across transactions (e.g., minting quotas, cooldown heights).
- **Protocol governance** where changing the NFT-holding box requires a hard-to-forge proof.

Real-world examples in the Ergo ecosystem:

| Project | NFT Name | Role |
|---|---|---|
| Dexy Stablecoin | `bankNFT`, `arbMintNFT`, `freeMintNFT`, `interventionNFT`, `buybackNFT` | One NFT per protocol sub-box |
| Oracle Core v2 | Pool NFT, Ballot NFT, Update NFT | Oracle pool state identity |
| Djed (Ergo) | `SC_NFT`, `RC_NFT`, `bank_NFT` | Stablecoin/reserve-coin bank state |
| Paideia DAO | Governance state NFT | DAO config singleton |

---

## How It Works

### Step 1 — Issuance (One-Time Mint)

A Singleton NFT is minted in a **bootstrap transaction**:

```
Bootstrap Tx
  Input[0]:  Any unspent box  (its boxId becomes the NFT's token ID)
  Output[0]: State Box at contract address
               tokens(0) = (Input[0].id, 1L)   ← the NFT, quantity exactly 1
               R4..R9     = initial state
```

Because the Token ID equals `Input[0].id` and Box IDs are unique (they commit to the entire transaction including input references), the NFT can never be re-issued.

The NFT's token ID is then **hard-coded** into every downstream contract that needs to reference or validate this state box. This is the standard pattern used in Dexy, Oracle Core, and Djed.

### Step 2 — State Transition (Normal Operation)

Every spending transaction that updates the state must:

1. **Consume** the current state Box (spending it as `INPUTS(i)`).
2. **Re-create** a new state Box at the same (or an upgraded) ErgoTree address as `OUTPUTS(j)`.
3. **Forward** the NFT: `OUTPUTS(j).tokens(0) == (nftId, 1L)`.
4. **Enforce** business-logic constraints on Register deltas (e.g., a counter decreased, a height check passed).

```
State Transition Tx
  Input[0]:  State Box  (contains NFT)
  Input[1..n]: Auxiliary inputs (user payment, LP box, etc.)
  Output[0]: New State Box (contains NFT, updated Registers)
  Output[1..m]: Auxiliary outputs
  Data-Input[0..k]: Read-only oracle / config boxes (identified by their own NFTs)
```

The ErgoScript in the state Box enforces all of the above. The NFT is the *invariant thread* through every generation of the Box.

### Step 3 — Cross-Contract Referencing via Data Inputs

A **Data input** (introduced in [EIP-0031](https://github.com/ergoplatform/eips/blob/master/eip-0031.md)) allows a Box to be *read* within a transaction without being *spent*. This is how the Singleton / State NFT pattern enables composable, read-only access:

```
Arbitrage Mint Tx
  Input[0]:  ArbMint Box   (arbMintNFT — being updated)
  Input[1]:  Bank Box      (bankNFT — being updated)
  Data-Input[0]: Oracle Box (oracleNFT — read only, not spent)
  Output[0]: ArbMint Box   (arbMintNFT forwarded, R5 decremented)
  Output[1]: Bank Box      (bankNFT forwarded, token balance updated)
```

Within the ArbMint ErgoScript:
```scala
val oracle = CONTEXT.dataInputs(0)
val oracleNFT = fromBase64("...") // hard-coded at compile time
require(oracle.tokens(0)._1 == oracleNFT)  // identity check
val oraclePrice = oracle.R4[Long].get
```

Because the NFT ID is hard-coded into the consuming contract's ErgoTree, there is no way to substitute a fake oracle box — the Sigma protocol proof would fail.

### Step 4 — Upgrade / Destruction

To upgrade a contract, a governance transaction spends the old state Box and re-creates it at a new ErgoTree address, still carrying the NFT. Off-chain indexers following the NFT automatically discover the new address. Some protocols (e.g., Oracle Core) use a separate **Update NFT** and ballot mechanism to authorize this.

---

## Implementation

### 1. ErgoScript — Bank Box (Dexy Stablecoin)

The canonical example. The `bankNFT` is tokens(0) and must be forwarded to `OUTPUTS(0)`.

```scala
// Adapted from kushti/dexy-stable: bank.es
{
  // Bank script
  //
  // TOKENS
  //   tokens(0): bankNFT — identifies this box as the canonical bank
  //   tokens(1): dexyUSD tokens held in reserve (to be emitted)
  //
  // REGISTERS: none (state is implicit in token balances)

  // ---------------------------------------------------------------
  // Singleton identity: the output bank box must carry the same NFT
  // ---------------------------------------------------------------
  val bankNFT        = SELF.tokens(0)._1          // read from self
  val successor      = OUTPUTS(0)                  // bank is always output 0

  val nftPreserved   = successor.tokens(0)._1 == bankNFT &&
                       successor.tokens(0)._2 == 1L

  val scriptPreserved = successor.propositionBytes == SELF.propositionBytes

  // ---------------------------------------------------------------
  // Action dispatch: who is authorised to spend the bank?
  // Each action box is itself identified by its own singleton NFT.
  // ---------------------------------------------------------------
  val arbMintNFT     = fromBase64("$arbMintNFT")
  val freeMintNFT    = fromBase64("$freeMintNFT")
  val interventionNFT = fromBase64("$interventionNFT")
  val payoutNFT      = fromBase64("$payoutNFT")

  // Check which action box is present in the input set
  def hasNFT(nft: Coll[Byte]): Boolean =
    INPUTS.exists { (b: Box) => b.tokens.size > 0 && b.tokens(0)._1 == nft }

  val validAction = hasNFT(arbMintNFT)      ||
                    hasNFT(freeMintNFT)      ||
                    hasNFT(interventionNFT)  ||
                    hasNFT(payoutNFT)

  sigmaProp(nftPreserved && scriptPreserved && validAction)
}
```

**Key points:**
- `SELF.tokens(0)._1` reads the NFT ID from the box being spent.
- `OUTPUTS(