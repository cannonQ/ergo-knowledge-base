---
title: kushti/dexy-stable — Overview
description: Dexy stablecoin — oracle-pegged minting, LP, cross-tracker, anti-drain mechanisms
tags: [kushti, dexy-stable, defi, ergoscript, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
project: kushti-dexy-stable
group: defi
priority: high
languages: [ergoscript, scala]
contract_count: 22
pattern_match_count: 0
---
# Dexy Stable — Developer Overview

---

## Overview

Dexy is an oracle-pegged algorithmic stablecoin protocol built on the Ergo blockchain, designed to issue tokens backed by external price feeds (initially gold and USD) while maintaining peg stability through a combination of LP arbitrage mechanics, bank intervention, and anti-drain rate limiting. The protocol is architecturally distinct from SigmaUSD in that it introduces a two-sided stabilization model: rather than relying solely on reserve ratios, Dexy couples a singleton Bank box (the core reserve vault) with an AMM-style Liquidity Pool to create market-driven peg correction in both directions. When Dexy trades above peg in the LP, arbitrage minting is permitted; when it trades below peg, the Bank intervenes by buying back Dexy from the LP using ERG reserves.

The protocol also introduces GORT (Gold Oracle Reward Token), a purpose-built tokenomic layer that closes a critical feedback loop absent in most oracle-dependent DeFi systems on Ergo. Because eUTXO contracts consume oracle data via read-only Data inputs rather than calls, oracles cannot charge per-use fees on-chain. GORT resolves this: a portion of every Dexy mint fee (0.2%) is routed to a Buyback contract, which purchases GORT from a GORT/ERG LP and returns it to the oracle pool contract as operator rewards. This makes oracle security economically self-sustaining and ties stablecoin usage volume directly to oracle operator compensation.

Dexy is deployed in two variants — DexyGold (pegged to XAU via gold oracle pool 2.0) and DexyUSD — and is one of the most architecturally complete multi-stage contract systems in the Ergo ecosystem. It demonstrates advanced eUTXO patterns including State NFT-based singleton state machines, multi-path ErgoScript guards, off-chain bot coordination, governance via ballot contracts, and cross-contract composability achieved entirely through transaction structure rather than inter-contract calls.

---

## Architecture

Dexy is organized as a graph of singleton state boxes, each identified by a unique NFT and governed by a dedicated ErgoScript contract. All composability is expressed through transaction shape: inputs, outputs, and Data inputs carry state between components without any direct contract-to-contract invocation. The following describes the primary component relationships and data flow.

```
Oracle Pool Box ──(Data input)──► ArbitrageMint / FreeMint / Intervention / Payout
LP Box          ──(Data input)──► ArbitrageMint / FreeMint / Intervention
Tracking Boxes  ──(Data input)──► ArbitrageMint / Intervention
                    │
     ┌──────────────┼──────────────────────────────────┐
     ▼              ▼                                  ▼
ArbitrageMint   FreeMint                         Intervention
     │              │                                  │
     └──────┬───────┘                                  │
            ▼                                          │
         Bank Box ◄─────────────────────────────────────┘
            │
            ├──► Buyback Box ──► GORT/ERG LP ──► Oracle Pool (GORT return)
            └──► Payout Box  ──► Buyback Box
```

**Bank Box** is the central reserve vault holding ERG collateral and the full Dexy token supply. It does not encode emission logic itself; instead it acts as a permissioned state machine that accepts transitions only when a valid mint, intervention, payout, or update box appears at a designated input index. This delegation pattern keeps the Bank contract minimal and upgradeable.

**Mint Boxes** (FreeMint, ArbitrageMint) are rate-limited state machines that track per-epoch quotas in Registers R4 (reset height) and R5 (remaining quota). Each epoch (~30–360 blocks depending on type) they recompute allowable issuance from live LP and oracle data read via Data inputs.

**LP Box** implements a constant-product AMM augmented with Dexy-specific redemption restrictions. It is referenced as a Data input for rate comparisons in mint and intervention contracts, and as a spending input during intervention transactions when the Bank buys back Dexy.

**Tracking Boxes** (95%, 98%, 101%) are sentinel State NFT boxes whose creation height records when LP/oracle rate divergence first crossed a threshold. They gate arbitrage minting (tracking101 must have been active for ≥30 blocks) and intervention (tracking98 must be active), providing cooldown enforcement without mutable registers.

**Buyback Box** accumulates ERG fees from minting operations and executes three actions discriminated by a Context extension variable: swap ERGs for GORT in the GORT/ERG LP, accept top-up ERGs from mint transactions, or return accumulated GORT to the oracle pool contract.

**Governance** is implemented as a multi-stage update system: an Update Box (holding updateNFT) accepts a transaction only when ≥3 of 5 Ballot Boxes carry matching R5 (update box ID) and R6 (blake2b256 of proposed new ErgoTree), then replaces the target contract's propositionBytes in-place while preserving its NFT and ERG value.

---

## Smart Contracts

All contracts are written in ErgoScript and compiled to ErgoTree bytecode. NFT Token IDs and fee parameters are embedded as constants at compile time (constant segregation pattern), producing distinct ErgoTree instances per deployment.

### `bank/bank.es` — Bank (Central Reserve)
The hub of the protocol. Holds `bankNFT` (Singleton / State NFT) and the full Dexy token reserve. Enforces a disjunctive guard:
```
(validSuccessor && (validMint || validIntervention || validPayout)) || validUpdate
```
`validSuccessor` checks that output index 1 preserves the Bank's NFT and propositionBytes. Each of the four action paths is authorized by the presence of the corresponding NFT at a fixed input index. The Bank itself reads no registers and encodes no emission math; all invariants are delegated to child contracts.

### `bank/freemint.es` — Free Mint
Permits issuance of up to 1% of LP Dexy reserves per epoch (~360 blocks). R4 stores the reset height; R5 stores remaining quota. Requires LP rate to be within 2% of oracle rate (`lpRate * 100 > oracleRate * 98`). Charges 0.3% to Bank and 0.2% to Buyback. Validates both recipient boxes by NFT at fixed input indices.

### `bank/arbmint.es` — Arbitrage Mint
Permits issuance only when LP rate exceeds oracle rate by >1% (`lpRate * 100 > 101 * oracleRateWithFee`). Minting is capped to the quantity that would restore price parity. Requires the tracking101 box to have been created ≥30 blocks prior (enforced via `tracking101Box.R7[Int]`). Same fee structure and register semantics as FreeMint. Epoch reset period is ~30 blocks.

### `bank/intervention.es` — Bank Intervention
Allows the Bank to sell ERGs into the LP to buy back Dexy when LP price ≤98% of oracle price. Rate-limited to once per 360 blocks via `SELF.creationInfo._1`. Enforces constant-product swap invariant (`deltaLpY * lpReservesXIn <= deltaLpX * lpReservesYIn`), a 1% bank reserve spending cap per action, a 2% slippage limit, and a post-swap LP rate ceiling of 99.5% of oracle to prevent over-correction. Uses tracking98 Data input for cooldown check.

### `bank/buyback.es` — GORT Buyback
Three-action contract dispatched by Context extension variable 0:
- **Action 0 (swap):** Exchanges ERG from Buyback into GORT/ERG LP with 5% slippage tolerance. Validates LP NFT, pool invariant, and token containment across all outputs.
- **Action 1 (top-up):** Accepts ERG from mint transactions. Validates token preservation, script preservation, and strictly increasing ERG value.
- **Action 2 (return):** Sends accumulated GORT to oracle pool. Validates oracle data points by epoch ID (R