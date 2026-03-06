---
title: "Storage Rent"
description: "Ergo's on-chain garbage collection: how storage rent works, the 4-year threshold, economic rationale, implications for dApp developers, and how it ensures long-term blockchain sustainability."
tags: [storage-rent, demurrage, mining, economics, sustainability, concepts]
category: concept
difficulty: beginner
sdk: [none]
updated: 2026-03-05
source: original
---

# Storage Rent

## The Problem

Every blockchain faces the same long-term question: **who pays for state storage forever?**

When you create a box (UTXO) on Ergo, it takes up space in the blockchain state — the set of all unspent boxes that every full node must maintain. A box created in 2019 still consumes node memory and disk in 2026. The creator paid a one-time transaction fee, but the ongoing storage cost is borne by every node operator indefinitely.

Bitcoin largely ignores this problem — its UTXO set grows without bound. Ethereum charges gas for storage but has no mechanism to reclaim abandoned state. Over decades, this leads to **state bloat**: the blockchain state grows continuously, making it harder and more expensive to run a full node.

Ergo solves this with **storage rent** (also called demurrage): a mechanism that charges a small periodic fee on boxes that sit untouched for too long.

## How It Works

The rule is simple:

> **After 4 years of inactivity, a box becomes eligible for miners to collect a storage rent fee from it.**

More precisely:

1. Every box records its **creation height** in register R3
2. When a box has been unspent for more than **1,051,200 blocks** (~4 years at 2-minute block intervals), miners can include it in a special "storage rent" transaction
3. The miner deducts a fee from the box's ERG value (approximately **0.14 ERG per 4-year period** for a minimal box — more for larger boxes)
4. If the box has enough ERG to cover the fee, the miner takes the fee and **recreates the box** with the remaining value, resetting the 4-year clock
5. If the box does **not** have enough ERG to cover the fee, the miner can **fully consume** the box, claiming all remaining ERG and tokens

## The Fee Calculation

The storage rent fee is proportional to the box's size in bytes:

```
rentFee = boxSizeInBytes * storageRentFeePerByte
```

The `storageRentFeePerByte` parameter is set by the protocol and can be adjusted through miner voting. A simple box (just ERG, no tokens, no extra registers) is small — roughly 100 bytes — so its rent is minimal. A box packed with tokens and register data is larger and pays more rent.

This aligns incentives: complex state costs more to store, so it costs more to keep alive.

## What This Means for Users

### Your ERG is safe (if you're active)

If you transact at least once every 4 years, your boxes are never eligible for rent collection. Every transaction creates fresh outputs with a new creation height, resetting the clock.

Even if you don't transact, your ERG isn't immediately at risk. A wallet with 10 ERG in a simple box would survive roughly **280 years** of rent collection before being fully depleted (10 ERG / 0.14 ERG per 4-year cycle * 4 years).

### Tokens and NFTs need ERG protection

This is the critical point for dApp developers and NFT holders: **tokens cannot pay storage rent — only ERG can.** If you have a box containing a valuable NFT but only the minimum ERG, the miner will eventually claim the entire box (including the NFT) if the ERG runs out.

The solution: ensure boxes holding valuable tokens contain sufficient ERG to cover decades of rent. A few ERG is enough for a century of protection.

### Consolidation tools

Several ecosystem tools help users manage storage rent:

- **Nautilus wallet** warns about boxes approaching the 4-year threshold
- **SAFEW wallet** provides box consolidation (merging old boxes into fresh ones)
- **TokenJay** monitors box ages
- **ErgoPort bot** can alert about at-risk boxes

## Why Storage Rent Exists

### 1. Long-term miner revenue

Ergo's block reward emission schedule ends after ~8 years (reaching its final re-emission phase). Unlike Bitcoin, which depends entirely on transaction fees post-emission, Ergo gives miners an additional revenue stream. Storage rent ensures miners are compensated for the ongoing cost of maintaining blockchain state, even during periods of low transaction volume.

### 2. State size control

By incentivizing the recycling of abandoned boxes, storage rent naturally limits blockchain state growth. Boxes belonging to lost keys, dead projects, or forgotten dust outputs are eventually collected and their ERG recycled into circulation.

### 3. Coin circulation

In traditional economics, money that sits idle creates deflationary pressure. Storage rent acts as a mild demurrage — a holding cost that encourages ERG to circulate rather than accumulate indefinitely in dormant addresses. This is a feature of the Ergo economic model, not an accident.

### 4. Spam prevention

Without storage rent, an attacker could create millions of tiny boxes (each holding the minimum ERG) to bloat the state. Storage rent makes this attack progressively more expensive over time — every spam box will eventually need to be consolidated or it will be consumed by miners.

## Implications for dApp Developers

### Keep state boxes active

Protocol state boxes (oracle pools, DEX pools, lending contracts) are regularly spent and recreated through normal protocol operation. This naturally resets their storage rent clock. A well-designed protocol never has state boxes sit idle for 4 years.

### Protect long-lived boxes

Some boxes are designed to be long-lived — for example, a time-locked vault that unlocks after 10 years. These boxes must contain enough ERG to cover rent for their entire lifetime:

```
required ERG = (lockDuration / 4 years) * rentFeePerCycle + margin
```

### Design for graceful expiry

Consider what happens if a box does expire. Can the protocol recover? Some designs intentionally allow old boxes to be cleaned up — expired lottery tickets, fulfilled orders, or completed auctions don't need to persist forever.

### The "minimum ERG" trap

When creating boxes with tokens, don't use the absolute minimum ERG. Include a buffer for storage rent. A box with 0.001 ERG holding an NFT will lose that NFT to miners in ~4 years. A box with 1 ERG will survive ~28 years. A box with 5 ERG will survive ~140 years.

## Storage Rent and Ergo's Long-term Vision

Storage rent is part of a broader design philosophy: **a blockchain should be sustainable without relying on ever-growing usage.**

Bitcoin's security model assumes transaction fee revenue will replace block rewards — an assumption that requires perpetually high transaction demand. Ethereum's state grows indefinitely, pushing hardware requirements higher over time. Both are betting on growth.

Ergo's model is self-correcting: if usage is high, miners earn from transaction fees; if usage is low, miners earn from storage rent on idle state. The blockchain can sustain itself at any activity level because the cost of existing state is never zero.

This is why the Ergo community often calls storage rent "on-chain garbage collection" — it keeps the state clean, funds infrastructure maintenance, and ensures the blockchain can run indefinitely without requiring exponential growth.

## Activation History

Storage rent activated at block **1,051,200** (July 20, 2023). Before this, no boxes were old enough to be eligible (the blockchain launched in July 2019, and the 4-year threshold hadn't been reached). The first storage rent collections occurred shortly after activation.

## Learn More

- [Boxes and Registers](boxes-and-registers.md) — How creation height in R3 determines rent eligibility
- [eUTXO Model](eutxo-model.md) — The transaction model that creates and destroys boxes
- [Guard Script Framework](../guides/ergoscript-fundamentals/02-guard-script-framework.md) — Design contracts that account for box lifecycle
