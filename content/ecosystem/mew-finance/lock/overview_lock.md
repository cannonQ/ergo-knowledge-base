---
title: AcoSmrkas/mew-lock — Overview
description: MEW Lock — token locking, delegation, escrow, lending transactions on Ergo
tags: [acosmrkas, mew-lock, defi, typescript, svelte]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/AcoSmrkas/mew-lock"
project: acosmrkas-mew-lock
group: defi
priority: medium
languages: [typescript, svelte]
contract_count: 0
pattern_match_count: 1
---
# MewLock — Developer Overview

## Overview

MewLock is a non-custodial, time-lock DeFi primitive built on the Ergo blockchain that enables users to lock ERG and native tokens into ErgoScript smart contracts for predetermined durations measured in block heights. Unlike custody-based lock services, all assets are held exclusively in on-chain Boxes governed by an immutable ErgoScript contract; no third party can access or move the assets before the specified unlock height is reached. The protocol enforces withdrawal rules entirely through the eUTXO model, relying on Sigma protocols (`proveDlog`) for depositor authentication and block-height comparisons within the ErgoScript context for temporal enforcement.

Within the Ergo DeFi ecosystem, MewLock occupies the role of a foundational escrow and commitment primitive. Token locking is a prerequisite for numerous higher-order DeFi constructs — vesting schedules, governance participation, delegation mechanisms, and collateral escrow — making MewLock composable with protocols such as SigmaUSD, Dexy, and on-chain governance systems that require provable asset commitment. The project also exposes an escrow-sell transaction pathway (`escrowSellTx.ts`), extending its scope beyond pure time-locking toward peer-to-peer atomic-swap-adjacent settlement patterns.

The frontend is a SvelteKit/TypeScript single-page application that functions as a Headless dApp layer: all transaction construction happens off-chain in TypeScript, wallet signing is delegated to EIP-12-compatible connectors (Nautilus, SAFEW), and the resulting signed transaction is submitted to the Ergo node network. Price data is enriched via the CoinGecko and Spectrum APIs, providing real-time USD valuations for locked assets without any trusted oracle dependency on-chain.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SvelteKit Frontend                    │
│  routes/                                                 │
│    +page.svelte       — Home / lock creation UI          │
│    locks/             — All active MewLock Boxes         │
│    my-locks/          — Per-wallet lock dashboard        │
│    faq/               — Documentation                    │
└───────────────┬─────────────────────────────────────────┘
                │ UI events
┌───────────────▼─────────────────────────────────────────┐
│               lib/contract/  (Off-chain TX builders)     │
│  mewLockTx.ts        — lock & unlock transaction assembly│
│  escrowSellTx.ts     — escrow-sell transaction assembly  │
└───────────────┬───────────────────┬─────────────────────┘
                │ unsigned TX        │ Box queries
┌───────────────▼──────┐  ┌─────────▼──────────────────── ┐
│  EIP-12 Wallet        │  │  Ergo Node / Explorer API     │
│  Connector            │  │  (UTxO set, mempool, height)  │
│  (Nautilus / SAFEW)   │  └───────────────────────────────┘
└───────────────┬───────┘
                │ signed TX
┌───────────────▼───────────────────────────────────────── ┐
│  Ergo Network — eUTXO ledger                             │
│  MewLock Contract Box (ErgoTree)                         │
│    R4: depositorPubKey (GroupElement)                    │
│    R5: unlockHeight    (Int)                             │
│    value: locked ERG                                     │
│    tokens: locked native tokens                          │
└───────────────────────────────────────────────────────────┘
                │ parallel enrichment
┌───────────────▼───────────────────────────────────────── ┐
│  lib/services/priceService.ts                            │
│    CoinGecko API   — ERG/USD spot price                  │
│    Spectrum API    — on-chain token prices               │
└───────────────────────────────────────────────────────────┘
```

**Data flow — Lock path:**
1. User specifies asset amounts and a lock duration (translated to a target block height via a blocks-per-month constant).
2. `mewLockTx.ts` fetches the user's UTxOs via the EIP-12 connector, assembles an unsigned Transaction with one output Box whose ErgoTree is the MewLock contract and whose Registers carry `R4` (depositor `GroupElement`) and `R5` (unlock height `Int`).
3. The unsigned transaction is passed to the EIP-12 connector for signing, then broadcast.

**Data flow — Unlock path:**
1. `mewLockTx.ts` fetches the target MewLock Box from the UTxO set.
2. Fee amounts (ERG and per-Token ID) are computed off-chain mirroring the on-chain ErgoScript arithmetic.
3. The unsigned Transaction is assembled with two outputs: a dev-fee Box (3%) and a recipient Box (97%), then signed and broadcast.

---

## Smart Contracts

### MewLock Contract

**Contract address:**
`5adWKCNFaCzfHxRxzoFvAS7khVsqXqvKV6cejDimUXDUWJNJFhRaTmT65PRUPv2fGeXJQ2Yp9GqpiQayHqMRkySDMnWW7X3tBsjgwgT11pa1NuJ3cxf4Xvxo81Vt4HmY3KCxkg1aptVZdCSDA7ASiYE6hRgN5XnyPsaAY2Xc7FUoWN1ndQRA7Km7rjcxr3NHFPirZvTbZfB298EYwDfEvrZmSZhU2FGpMUbmVpdQSbooh8dGMjCf4mXrP2N4FSkDaNVZZPcEPyDr4WM1WHrVtNAEAoWJUTXQKeLEj6srAsPw7PpXgKa74n3Xc7qiXEr2Tut7jJkFLeNqLouQN13kRwyyADQ5aXTCBuhqsucQvyqEEEk7ekPRnqk4LzRyVqCVsRZ7Y5Kk1r1jZjPeXSUCTQGnL1pdFfuJ1SfaYkbgebjnJT2KJWVRamQjztvrhwarcVHDXbUKNawznfJtPVm7abUv81mro23AKhhkPXkAweZ4jXdKwQxjiAq`

#### Box Register Layout

| Register | Type | Semantics |
|---|---|---|
| `R4` | `GroupElement` | Depositor's public key (base of `proveDlog`) |
| `R5` | `Int` | Absolute unlock height |
| `value` | `Long` (nanoERG) | Locked ERG |
| `tokens` | `Coll[(Coll[Byte], Long)]` | Locked native tokens by Token ID |

#### Invariants Enforced by the ErgoScript

```
1. Sigma guard:        proveDlog(R4[GroupElement].get)
                       → only depositor's private key can satisfy
2. Time guard:         HEIGHT >= R5[Int].get
                       → spending forbidden before unlock height
3. Single-box spend:   INPUTS.filter(_.propositionBytes == SELF.propositionBytes).size == 1
                       → one MewLock Box consumed per Transaction
4. No re-locking:      OUTPUTS.forall(_.propositionBytes != SELF.propositionBytes)
                       → assets cannot be recycled into a new lock in the same TX
5. Dev fee ER
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
