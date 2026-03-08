---
title: skyharbor-market/contracts — Overview
description: SkyHarbor NFT marketplace smart contracts — sale/offer ErgoScript with royalty logic
tags: [skyharbor-market, contracts, analytics, ergoscript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/skyharbor-market/contracts"
project: skyharbor-market-contracts
group: analytics
priority: medium
languages: [ergoscript]
contract_count: 2
pattern_match_count: 0
---
# SkyHarbor NFT Marketplace — Developer Overview

## Overview

SkyHarbor is an NFT marketplace built on the Ergo blockchain, and this repository contains the core ErgoScript smart contracts that govern the on-chain mechanics of NFT listings, sales, and offer settlements. The contracts encode the full lifecycle of an NFT trade — from listing creation and price enforcement to fee distribution and royalty routing — entirely within the eUTXO model. Each listing is represented as a Box carrying the NFT as a Native token alongside sale parameters packed into Registers, with spending conditions defined by an ErgoTree that enforces correct fund distribution at transaction validation time.

The project's primary role in the Ergo ecosystem is to serve as the on-chain trust layer for a decentralized NFT marketplace. Because Ergo's eUTXO model requires that all spending conditions be satisfied at the time a Transaction is submitted, the contracts guarantee that sellers, the marketplace service, and royalty recipients all receive their correct shares without requiring any trusted intermediary or upgradeable proxy. The ErgoScript logic is self-contained and deterministic: a buyer constructing a valid purchase Transaction must satisfy every constraint encoded in the ErgoTree, or the Transaction is rejected by the network.

From an analytics perspective, the contracts expose a well-structured on-chain data footprint. Every listing Box carries structured Register data (sale price, seller address, issuer box reference, seller public key), and every completed purchase produces a canonical set of output Boxes whose values and proposition bytes directly encode the trade terms. This makes SkyHarbor listings and sales straightforwardly indexable by any chain-scanning analytics tool that can decode Box Registers and Token IDs.

---

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    SkyHarbor Listing Box (SELF)                 │
│                                                                 │
│  tokens(0): NFT being sold  (Singleton / State NFT)            │
│  R4: Long          — sale price in nanoErg                     │
│  R5: Coll[Byte]    — seller propositionBytes                   │
│  R6: Box           — issuer/royalty Box reference              │
│  R7: GroupElement  — seller public key (Schnorr)               │
└──────────────────────┬──────────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
   OUTPUTS.size > 2/3          OUTPUTS.size ≤ 2/3
   (Purchase Path)              (Refund Path)
          │                         │
          ▼                         ▼
┌──────────────────┐      ┌──────────────────────┐
│ OUTPUTS(0)       │      │ proveDlog(SELF.R7)   │
│ Seller Box       │      │ Seller reclaims NFT  │
│ R4 = SELF.id     │      └──────────────────────┘
├──────────────────┤
│ OUTPUTS(1)       │
│ Service Fee Box  │
│ 2% of sale price │
├──────────────────┤
│ OUTPUTS(2)       │
│ Royalty Box      │◄── conditional on R6.R4[Int] defined
│ price × R% / 1000│    and 0 < R% < 900
└──────────────────┘
          ▲
          │
┌─────────┴────────┐
│ Issuer Box (R6)  │  ← read as Data input / embedded Box
│ R4: Int royalty% │    royaltyBox.id == SELF.tokens(0)._1
│ propBytes: addr  │
└──────────────────┘
```

### Data Flow

1. **Listing creation**: An off-chain bot or EIP-12 wallet connector constructs a Transaction that places the NFT (Native token) and all Register data into a new Box whose ErgoTree is the marketplace guard script.
2. **Purchase**: A buyer's Transaction spends the listing Box. The ErgoScript context evaluates OUTPUTS at validation time — price distribution, Replay protection via `OUTPUTS(0).R4 == SELF.id`, royalty routing via the embedded issuer Box, and currency Token ID consistency are all checked without any external call.
3. **Refund**: The seller provides a Schnorr proof (`proveDlog(SELF.R7)`) in a Transaction with `OUTPUTS.size ≤ 2` (V1) or `≤ 3` (V1 Erg Edits), reclaiming the NFT with no fee deduction.
4. **Offers contract path**: In the V1 Erg Edits variant, a recognized offers contract (identified by `blake2b256` of its propositionBytes) can trigger the refund/offer-settlement path as an alternative spending authority.

### Versioning

| Contract File | Currency | Outputs threshold | Offers support |
|---|---|---|---|
| `SigUSDV1.txt` | SigUSD token (hardcoded Token ID) | `> 2` purchase | No |
| `V1_ErgEditsAndOffersV1.md` | ERG (nanoErg) | `> 3` purchase | Yes |

---

## Smart Contracts

### List NFT Guard Script — SigUSD V1 (`SigUSDV1.txt`)

**Responsibility**: Guards a listing Box holding an NFT priced in SigUSD (a specific hardcoded currency Token ID: `GYATox71P9XAERmzoDdTGELa62f5ALyjxJLRSfJfKsh`). Enforces that any spending Transaction either satisfies the full purchase distribution invariant or carries a valid seller Schnorr signature.

**Key ErgoScript conditions**:

- **Purchase invariant**:
  ```
  serviceGets  = max(salePrice / 50, 1)
  royaltyGets  = max(salePrice * royaltyPct / 1000, 0)
  sellerGets   = salePrice - serviceGets - royaltyGets

  OUTPUTS(0).tokens(0)._2 >= sellerGets        // seller share in currency token
  OUTPUTS(1).tokens(0)._2 == serviceGets       // exact service fee
  OUTPUTS(2).tokens(0)._2 >= royaltyGets       // royalty recipient
  ```
- **Replay protection**: `OUTPUTS(0).R4[Coll[Byte]].get == SELF.id`
- **Issuer validation**: `royaltyBox.id == SELF.tokens(0)._1` — the royalty Box must be the minting Box of the NFT, enforcing Token ID rule provenance
- **Refund**: `proveDlog(SELF.R7[GroupElement].get)`
- **Royalty branches**:
  - If `royaltyBox.R4[Int]` is defined and non-zero → three-output path with royalty
  - If undefined → two-output path, service fee only, royalty waived

**Invariants enforced**:
- Currency Token ID is constant across all payment outputs
- Sale price cannot be partially fulfilled (minimum box value constraints)
- Seller address (`SELF.R5`) cannot be substituted
- Hardcoded service address cannot be redirected

---

### Erg Edits + Offers V1 (`V1_ErgEditsAndOffersV1.md`)

**Responsibility**: An updated listing guard script priced in ERG (nanoErg values rather than currency tokens) with an additional spending path for an integrated offers contract. Follows the same royalty and replay-protection logic but extends the state machine with offer acceptance.

**Key differences from SigUSD V1**:

- Payment distribution is in ERG box values, not Token quantities
- `OUTPUTS.size > 3` threshold (one additional output slot for offer-related boxes)
- Offers contract integration: if `blake2b256(INPUTS(0).propositionBytes)` matches the hardcoded offers contract hash, the refund/Sigma path is unlocked — this allows the offers contract to atomically settle a counter