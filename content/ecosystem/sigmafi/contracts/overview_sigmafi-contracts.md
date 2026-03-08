---
title: K-Singh/Sigma-Finance — Overview
description: Sigma-Finance — P2P bond contracts (ERG + token), open orders (fixed-height + on-close), covered call options
tags: [k-singh, sigma-finance, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/K-Singh/Sigma-Finance"
project: k-singh-sigma-finance
group: defi
priority: high
languages: [ergoscript, scala]
contract_count: 13
pattern_match_count: 0
---
# Sigma-Finance Developer Overview

## Overview

Sigma-Finance is a decentralized peer-to-peer lending and options protocol built on Ergo, implementing collateralized bond contracts and covered call options using the eUTXO model. The protocol enables two principal actors — borrowers and lenders — to enter into on-chain debt agreements without intermediaries. A borrower locks ERG and/or native tokens as collateral into a Bond Box, while a lender supplies a principal loan amount denominated in either ERG or a native token (typically SigmaUSD). Repayment terms, maturity height, and participant identities are encoded directly in Box Registers, making every bond fully self-describing and auditable from chain data alone.

The protocol offers two distinct order-flow patterns: **Fixed-Height orders**, where the bond maturity is set to an absolute block height at order creation time, and **On-Close orders**, where maturity is computed relative to the block height at which the order is matched. This flexibility allows borrowers to express time preferences precisely while tolerating mempool confirmation variance (the On-Close variant enforces a ±8 block window to prevent transaction loss under chain-tip movement). Both ERG-denominated and token-denominated (e.g., SigmaUSD) variants of each pattern are provided, yielding four OpenOrder contract archetypes. Bond contracts follow the same ERG/token split. An experimental bond variant (`EXP_BondContractERG`) extends the liquidation path with a hashed custom liquidation script, enabling pluggable oracle- or governance-driven liquidation conditions via Context extension without storing the full script on-chain.

Within the broader Ergo DeFi ecosystem, Sigma-Finance occupies the lending and structured-credit layer. It is complementary to AMM-based protocols (e.g., Spectrum Finance) and stablecoin infrastructure (SigmaUSD), since SigmaUSD-denominated bonds are a first-class use case. The exchange-order contracts (`ExOrderERG`) further allow open token-sale orders with protocol fee extraction, forming the nucleus of a simple order-book layer. The covered call option contracts complete the derivatives surface alongside the bond primitives, making Sigma-Finance one of the more comprehensive DeFi building blocks in the Ergo ecosystem.

---

## Architecture

### Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│                        Off-Chain Layer                          │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │ Lender Bot │  │ Borrower Bot │  │  UI / EIP-12 Wallet   │   │
│  └─────┬──────┘  └──────┬───────┘  └──────────┬────────────┘   │
│        │                │                      │                │
│        │  Context Ext.  │   Context Ext.        │ optUIFee var  │
└────────┼────────────────┼──────────────────────┼───────────────┘
         │                │                      │
         ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Open Order Layer                           │
│                                                                 │
│  OpenOrderFixedHeightERG   OpenOrderFixedHeightToken            │
│  OpenOrderOnCloseERG       OpenOrderOnCloseToken                │
│  OpenOfferFixedHeightERG   OpenOfferFixedHeightToken            │
│                                                                 │
│  Each box: Registers R4–R8 encode borrower/lender PK,          │
│  principal, repayment, maturity. Collateral in value+tokens.    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Transaction (order match)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Bond Layer                               │
│                                                                 │
│  BondContractERG          BondContractToken                     │
│  EXP_BondContractERG      (covered call contracts)              │
│                                                                 │
│  Two-path state machine:                                        │
│  HEIGHT < maturityHeight → Repayment path (borrowerPK signs)   │
│  HEIGHT ≥ maturityHeight → Liquidation path (lenderPK signs)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   Repayment Transaction         Liquidation Transaction
   Output(0): repayment → lender  Output(0): collateral → lender
   Output(1): collateral → borrower
```

### Data Flow

**Order Creation → Bond Activation**

1. Borrower (OpenOrder) or Lender (OpenOffer) constructs an Order Box, encoding terms in R4–R8 and locking collateral or principal as Box value and tokens.
2. A counterparty (or off-chain bot) constructs a matching Transaction that:
   - Spends the Order Box
   - Creates a Bond Box at `OUTPUTS(0)` whose ErgoTree hash matches the constant `_bondContractHash`
   - Creates a Loan Box at `OUTPUTS(1)` sending principal to the borrower
   - Creates fee Boxes at `OUTPUTS(2–3)` for dev and optional UI recipients
3. The Bond Box inherits R4 = `SELF.id` (the Order Box ID), forming a traceable audit link between the originating order and the active bond.

**Bond Lifecycle**

```
Bond Box (collateral locked)
        │
        ├─ HEIGHT < R7 ──► Borrower signs repayment tx
        │                   Output(0): repayment to lenderPK
        │                   Output(1): collateral back to borrowerPK
        │
        └─ HEIGHT ≥ R7 ──► Lender signs liquidation tx
                            Output(0): all collateral to lenderPK
```

All outputs in both paths must carry `R4 = SELF.id` of the Bond Box, maintaining a complete chain of custody through Registers.

---

## Smart Contracts

### Bond Contracts

#### `BondContractERG.ergo`
Holds ERG and native token collateral for an ERG-denominated loan. Implements a height-gated two-path state machine using `HEIGHT` as the state discriminator (no State NFT required). Registers encode borrower and lender SigmaProps (R5, R8), repayment amount in nanoERG (R6), and maturity height (R7). The critical invariant is that collateral exits only via the repayment path (before maturity, borrower signature required) or the liquidation path (after maturity, lender signature required). Token collateral is preserved exactly — no partial transfers permitted.

#### `BondContractToken.ergo`
Structurally identical to `BondContractERG` but the repayment path requires the borrower to supply a specific native token (identified by constant `_tokenId`, typically SigmaUSD) at amount R6, rather than ERG. The repayment Box must contain `(tokenId, repayment)` as its first token slot. This makes the contract suitable for stablecoin-denominated lending where collateral is ERG but the debt is expressed in a token unit.

#### `EXP_BondContractERG.ergo` (Experimental)
Extends the standard ERG bond with a pluggable liquidation condition. R9 stores the `blake2b256` hash of an optional liquidation SigmaProp's `propBytes`. At liquidation time, the spender may provide the actual SigmaProp via Context extension variable 0; the contract verifies its hash matches R9 and evaluates it as an additional Sigma protocol condition. This enables oracle-price-based or governance-vote-based liquidation without embedding the full script in the bond Box, achieving **constant segregation** of the liquidation logic. The default time-based liquidation path (`HEIGHT >= maturityHeight`) remains available when