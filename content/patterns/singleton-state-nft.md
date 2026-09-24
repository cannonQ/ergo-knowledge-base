---
title: Singleton / State NFT
description: Singleton / State NFT — identity tokens for multi-stage contract state boxes, one-token-per-box invariant
tags: [singleton-state-nft, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repos: [kushti/dexy-stable, DjedAlliance/Djed-Ergo, ergoplatform/oracle-core, paideiadao/paideia-contracts]
---
# Singleton / State NFT Pattern: Comprehensive Developer Guide

## Overview

### What Is It?

The **Singleton / State NFT** pattern is a foundational eUTXO design primitive in which a unique, non-fungible token (NFT) with a total supply of exactly 1 serves as a **persistent identity anchor** for a stateful contract box. Because an NFT minted on Ergo carries a globally unique Token ID derived from the ID of the UTXO consumed during minting (the **Token ID rule**: `tokenId = boxId(inputBox[0])`), no two tokens can share the same identifier. This guarantee is enforced at the consensus layer without any registry or trusted issuer.

In a multi-stage contract system, many transactions over the system's lifetime must all refer to *the same logical component* — a bank, an oracle accumulator, a governance vault, a liquidity pool. The State NFT solves the **identity problem**: any ErgoScript clause can assert `SELF.tokens(0)._1 == expectedNftId` to prove, cryptographically and without oracle trust, that it is executing inside the correct box.

### Why It Exists

Ergo's eUTXO model destroys and recreates boxes in every transaction. Unlike account-based chains (Ethereum), there is no persistent "contract address" that retains state across calls. A box consumed in block *N* is gone; a successor box is created in the same transaction. Without an identity mechanism, successor boxes are indistinguishable from impostors.

The State NFT pattern compensates for the absence of persistent addresses by:

1. Binding logical identity to a token rather than a box ID or address.
2. Forcing every transaction in the protocol to **carry the NFT forward** into the successor box.
3. Allowing any participant — including Data inputs — to locate the authoritative state box by filtering on the known NFT ID.

### When to Use It

| Scenario | Use State NFT? |
|---|---|
| A contract box must survive across many transactions (bank, pool, treasury) | ✅ Yes |
| A contract box holds mutable state in Registers across epochs | ✅ Yes |
| A contract box is a one-shot spend (simple payment) | ❌ No |
| You need multiple parallel instances (fungible pool shares) | ❌ Use fungible tokens |
| A box must be referenced as a Data input without being consumed | ✅ Yes — NFT makes it findable |
| A box participates in a multi-stage contract pipeline | ✅ Yes |

Real-world users of this pattern include:

- **Dexy Stable** — `bankNFT`, `arbMintNFT`, `freeMintNFT`, `interventionNFT`, `buybackNFT`, `lpNFT`
- **Oracle Core** — oracle pool accumulator NFT
- **Djed/COTI** — reserve box NFT
- **Paideia DAO** — DAO config box NFT, governance action NFTs

---

## How It Works

### Step 1 — Minting the NFT

The NFT is minted in the **genesis transaction** of the protocol. Ergo's Token ID rule guarantees uniqueness:

```
tokenId == blake2b256(inputBox[0].id ++ index_bytes)
```

For the standard case (index 0), `tokenId = boxId(INPUTS(0))`. Because a box ID is unique (derived from the transaction ID and output index, themselves unique by consensus), no other token can ever share this ID.

The minting transaction:
- Consumes a plain ERG box as `INPUTS(0)`
- Creates the State Box as an output containing `(nftId, 1L)` in `tokens(0)`
- Sets the box's **ErgoTree** to the contract script
- Optionally initialises **Registers** R4–R9 with bootstrap state

```
INPUTS(0) [plain ERG box, id = X]
  └─► OUTPUTS(0) [State Box, tokens(0) = (blake2b256(X ++ 0), 1)]
```

### Step 2 — The One-Token-Per-Box Invariant

The contract script enforces that:

1. The NFT enters `OUTPUTS(successorIndex)` with quantity exactly 1.
2. The successor box carries the same ErgoTree (or a whitelisted upgraded tree).
3. No other output in the transaction holds a token with the same ID.

This creates a **linear chain of state boxes**:

```
[State Box v1] ──tx1──► [State Box v2] ──tx2──► [State Box v3] ──···
   (nftId, 1)              (nftId, 1)              (nftId, 1)
```

Each box is destroyed (spent) and a successor is created atomically. There is never a moment when two live UTXOs both hold the NFT.

### Step 3 — State Mutation via Registers

Mutable protocol state lives in **Registers** R4–R9 of the State Box. Common patterns:

| Register | Type | Example Usage |
|---|---|---|
| R4 | `Int` | Epoch counter, reset height |
| R5 | `Long` | Remaining quota, reserve ratio |
| R6 | `Long` | Accumulated fees, timestamp |
| R7 | `Coll[Byte]` | Merkle root, AVL tree digest |
| R8 | `SigmaProp` | Guardian public key |
| R9 | `Coll[Byte]` | Arbitrary metadata |

The script reads predecessor state via `SELF.R4[Int].get` and asserts successor state via `OUTPUTS(i).R4[Int].get == newValue`.

### Step 4 — Referencing the State Box as a Data Input

Other boxes in the system often need to **read** state from the NFT box without spending it. Ergo supports **Data inputs**: boxes referenced in a transaction that contribute to script evaluation but are not consumed and do not appear as outputs.

```
Transaction:
  Inputs:    [User Box]
  DataInputs:[State NFT Box]   ← read-only, not consumed
  Outputs:   [User Output]
```

Any script can validate the Data input's authenticity:

```scala
val stateBox = CONTEXT.dataInputs(0)
val isGenuine = stateBox.tokens(0)._1 == stateNftId
```

### Step 5 — Multi-Stage Interaction

In protocols like Dexy, multiple NFT boxes interact in a single transaction. Each box's script validates the presence and integrity of *other* NFT boxes:

```
Transaction Inputs:  [LP Box (lpNFT)]  [Bank Box (bankNFT)]
Transaction DataInputs: [Oracle Box (oracleNFT)]
Transaction Outputs: [LP Box']         [Bank Box']
```

Every script cross-validates siblings using their NFT IDs, creating a **trustless multi-party state machine** with no privileged coordinator.

### Step 6 — Storage Rent Considerations

Ergo's **Storage rent** mechanism charges boxes approximately 0.13 ERG per 4 years if they are not spent. State NFT boxes must maintain sufficient ERG value (above **Minimum box value**, currently ~0.001 ERG for small boxes, higher for boxes with tokens) to avoid being claimed by miners. Protocol designers should:

- Fund the State Box with enough ERG at genesis.
- Include ERG top-up logic in transaction scripts.
- Account for rent in off-chain transaction builders.

---

## Implementation

### ErgoScript — Core NFT Continuity Guard

The minimal pattern every State NFT box script must include:

```scala
// Verify this box holds the singleton NFT
val selfNft = SELF.tokens(0)._1

// Find successor output — by convention, same output index
val successor = OUTPUTS(0)

// Invariant 1: NFT must be preserved in successor
val nftPreserved = successor.tokens(0)._1 == selfNft &&
                   successor.tokens(0)._2 == 1L

// Invariant 2: Successor must use the same contract (ErgoTree)
val scriptPreserved = successor.propositionBytes == SELF.propositionBytes

sigmaProp(nftPreserved && scriptPreserved)
```

### ErgoScript — Dexy Bank Box (`bank.es`)

The Bank box is the canonical real-world example. It holds the `bankNFT` in `tokens(0)` and a supply of `dexyUSD` tokens in `tokens(1)`. Multiple transaction types (Arbitrage Mint, Free Mint, Intervention, Liquidation) all interact with it; each validates the Bank box's NFT identity.

```scala
{
  // Bank script
  //
  // This box: (Bank box)
  //
  // TOKENS
  //   tokens(0): bankNFT  — singleton identity token
  //   tokens(1): dexyUSD  — fungible stablecoin supply
  //
  // TRANSACTIONS
  // [1] Arbitrage Mint
  //   Input         |  Output         |   Data-Input
  // --------------------------------------------------
  // 0 ArbMint       |  ArbMint        |   Oracle
  // 1 Bank          |  Bank           |
  // 2 Buyer         |  Buyer          |
  //
  // [2] Free Mint
  //   Input         |  Output         |   Data-Input
  // --------------------------------------------------
  // 0 FreeMint      |  FreeMint       |   Oracle
  // 1 Bank          |  Bank           |
  // 2 Buyer         |  Buyer          |

  val bankNFT       = fromBase64("$bankNFT")      // compile-time constant
  val freeMintNFT   = fromBase64("$freeMintNFT")
  val arbMintNFT    = fromBase64("$arbMintNFT")
  val interventionNFT = fromBase64("$interventionNFT")

  // ------------------------------------------------------------------
  // Self-identification: confirm we are the genuine Bank box
  // ------------------------------------------------------------------
  val selfBankNft = SELF.tokens(0)._1
  val isBankBox   = selfBankNft == bankNFT        // sanity; enforced by NFT uniqu
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
