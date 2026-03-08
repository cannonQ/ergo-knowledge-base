---
title: ThierryM1212/SigmaO — Overview
description: SigmaO — decentralized options trading on Ergo, call/put option contracts, buy/sell/exercise flows
tags: [thierrym1212, sigmao, defi, ergoscript, javascript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SigmaO"
project: thierrym1212-sigmao
group: defi
priority: medium
languages: [ergoscript, javascript]
contract_count: 8
pattern_match_count: 0
---
# SigmaO Developer Overview

## Overview

SigmaO is a decentralized options trading protocol built natively on the Ergo blockchain, implementing European and American-style financial derivatives using eUTXO-based smart contracts written in ErgoScript. The protocol enables any user to issue, trade, and exercise call or put options on EIP-4 native tokens, with all positions fully collateralized on-chain — call options are backed by the underlying token reserve locked in the contract box, while put options are backed by ERG collateral sized to the strike price obligation. There is no trusted intermediary at any stage of the lifecycle; minting, pricing, order matching, and exercise settlement are all enforced by the contract logic itself.

Within the Ergo DeFi ecosystem, SigmaO occupies the options layer of the derivatives stack, complementing spot DEX infrastructure such as Spectrum Finance. Its pricing model is built around a Black-Scholes approximation using oracle-sourced price feeds, making it one of the more sophisticated financial primitives on Ergo in terms of on-chain computation. The protocol is deliberately permissionless: any party can issue an option for any EIP-4 token that has a compatible price oracle, and option tokens issued by the contract are freely transferable and tradeable as standard native tokens once minted.

The architecture follows a headless dApp pattern: ErgoScript contracts enforce all invariants at transaction validation time, while an off-chain bot handles transaction construction, oracle monitoring, order matching, and state-machine advancement. A React-based front-end provides a user interface, and a shared `script_constants.js` file generated from the contract build ensures that on-chain constants (script hashes, token IDs, fee parameters) remain synchronized across all layers without duplication.

---

## Architecture

SigmaO is composed of three independently deployable layers that communicate through the shared eUTXO set and a generated constants file.

```
┌─────────────────────────────────────────────────────┐
│                    Front-End (React)                 │
│  EIP-12 wallet connector · Black-Scholes UI pricing  │
│  Order book display · Exercise/buy/sell flows        │
└───────────────────┬─────────────────────────────────┘
                    │ script_constants.js (shared)
┌───────────────────▼─────────────────────────────────┐
│                 Off-Chain Bot (Node.js)               │
│  UTXO scanner · TX builder · Oracle monitor          │
│  Order matcher · State-machine advancer              │
└───────────────────┬─────────────────────────────────┘
                    │ signed transactions
┌───────────────────▼─────────────────────────────────┐
│              Ergo Node / Explorer API                │
└───────────────────┬─────────────────────────────────┘
                    │ eUTXO state
┌───────────────────▼─────────────────────────────────┐
│              ErgoScript Contracts                    │
│  Option.es · Option_Sell.es · Exercise_Option_Request│
│  Buy_Token_Request.es · Sell_Token_Request.es        │
│  ValidOracle.mu.es · ValidOracleAMM.mu.es            │
└─────────────────────────────────────────────────────┘
```

**Data flow across layers:**

1. **Contract build → constants file.** The `contract/` directory compiles ErgoScript sources and emits `script_constants.js`, which encodes ErgoTree hashes, oracle token IDs, fee addresses, and other compile-time constants. Both the bot and the front-end import this file, ensuring they operate against the same on-chain scripts.

2. **Option lifecycle as a state machine.** An option progresses through discrete states — Definition → Minted → Delivered → [Exercised | Expired] — where each state transition corresponds to a transaction that spends the current Box and produces the next. The Singleton / State NFT pattern anchors identity: the option token ID equals the ID of the Option Creation Box (the input consumed during minting), making it globally unique and unforgeable.

3. **Order books as open UTXO sets.** Buy and sell orders are not aggregated in a central ledger. Each open order is an independent Box on-chain (`Buy_Token_Request`, `Sell_Token_Request`). The off-chain bot scans the UTXO set for matchable pairs, constructs the matching transaction, and submits it. Partial fills of sell orders are supported via Box replication with a reduced token balance.

4. **Oracle as a data input.** Price data for option pricing and sell-order validation is read from an oracle Box included as a Data Input in the transaction — it is read but not spent, preserving the oracle's UTXO for concurrent readers. Two oracle adapters exist: a register-based oracle (`ValidOracle`) reading `(price: R4[Long], height: R5[Int])`, and an AMM LP-based oracle (`ValidOracleAMM`) deriving price from `box.value / (tokens(2).amount / decimalFactor)`.

---

## Smart Contracts

### `Option.es` — Core Option Reserve Contract

The central multi-stage contract governing the full option lifecycle. It implements a state machine over a single persistent Box (the option reserve) and enforces all collateralization and settlement invariants.

**State transitions:**

| Transition | Trigger | Key validation |
|---|---|---|
| Mint | Option Definition Box spent | Single input; OUTPUTS(0) becomes reserve; exactly 1 reserve token retained |
| Delivery | Reserve Box spent by issuer | `(totalAmount / shareSize)` option tokens sent to issuer; 1 singleton retained |
| Exercise (Call) | Option token holder spends reserve | Time window valid; exerciser pays `shareSize × strikePrice` nanoERG; receives `shareSize` underlying tokens |
| Exercise (Put) | Option token holder spends reserve | Time window valid; exerciser delivers `shareSize` underlying tokens; receives `shareSize × strikePrice` nanoERG |
| Expiry/Settlement | After exercise window closes | Issuer recovers all remaining collateral |

**Style enforcement:**
- **European**: exercisable only within the 24-hour window after `maturityDate`
- **American**: exercisable at any time up to `maturityDate`

**Register layout:**

| Register | Type | Content |
|---|---|---|
| R4 | `Coll[Byte]` | Option name (display) |
| R5 | `Coll[Byte]` | Underlying token ID |
| R6 | `Coll[Byte]` | Decimal encoding string |
| R7 | `Box` | Option Creation Box reference (config anchor) |
| R8 | `Coll[Long]` | `[optionType, style, shareSize, maturityDate, strikePrice, dAppUIMintFee, TxFee]` |
| R9 | `Coll[Coll[Byte]]` | `[issuerECPoint, dAppUIFeeErgoTree]` |

The issuer is authenticated via `proveDlog(decodePoint(issuerECPoint))`, a Sigma protocol proof rather than a hardcoded P2PK address, allowing any key pair to issue options without a registry.

---

### `Option_Sell.es` — Priced Sell Order Contract

Manages the on-chain sell order for option tokens at a dynamically computed Black-Scholes price. The contract reads a price oracle via Data Input and enforces that buyers pay the correct premium before receiving option tokens.

**Black-Scholes approximation (on-chain):**

```
Call intrinsic = max(0, (spot - strike) × shareSize)
Put  intrinsic = max(0, (strike - spot) × shareSize)
Time value     = 0.4 × σ × strike × √T × (1 - K1 × (|spot - strike| / (strike × √T))²)
American adj.  = time value × (1 + K2 × √T)
```

Square roots are computed via a precomputed lookup table to avoid overflow in integer arithmetic. The oracle freshness check (`HEIGHT ≤ oracleHeight + 30`) is inlined from the `ValidOracle` template.

**States:**
- **Active**: Not