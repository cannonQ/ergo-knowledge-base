---
title: PhoenixErgo/phoenix-hodlcoin-contracts — Overview
description: HodlCoin / Phoenix — proof-of-hodl mechanics, time-locked value accrual
tags: [phoenixergo, phoenix-hodlcoin-contracts, defi, ergoscript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/PhoenixErgo/phoenix-hodlcoin-contracts"
project: phoenixergo-phoenix-hodlcoin-contracts
group: defi
priority: medium
languages: [ergoscript]
contract_count: 6
pattern_match_count: 0
---
# PhoenixErgo/phoenix-hodlcoin-contracts — Developer Overview

---

## Overview

Phoenix HodlCoin implements the **hodlCoin protocol** on the Ergo blockchain — a cryptographically enforced proof-of-hodl mechanism where token value accrues monotonically through a bonding curve. Users mint hodl tokens by depositing a reserve asset (ERG or an arbitrary native token), and burn them to withdraw the reserve asset at a dynamically calculated price. Crucially, burn fees are partially retained in the reserve rather than fully extracted, ensuring the price per hodl token can only increase over time. This time-locked value accrual design is formally described in the [hodlCoin paper](https://eprint.iacr.org/2023/1029.pdf) and faithfully implemented here under the protocol's Fair Forking Rule.

The repository ships two parallel implementations: **hodlERG**, where the reserve asset is ERG (the Ergo base currency), and **hodlToken**, which generalizes the mechanism to any Ergo native token as the reserve. Both variants share the same three-contract architecture — a Bank contract, a Proxy contract, and a Fee distribution contract — but differ in how storage rent, ERG accounting, and token slot layout are handled. The hodlERG bank uses ERG value as the reserve directly, while the hodlToken bank tracks reserve as a third token slot alongside the Singleton NFT and the hodl token itself.

Within the Ergo DeFi ecosystem, Phoenix HodlCoin occupies a niche as a **capital-retention primitive**: it creates a one-way ratchet on token price that appeals to long-conviction holders and can serve as a building block for broader protocol treasuries or yield instruments. Its on-chain mechanics are fully non-custodial and permissionless, relying entirely on ErgoScript invariant enforcement rather than governance keys or admin roles.

---

## Architecture

The system is a classic **multi-stage contract** pipeline composed of three eUTXO contract roles that interact in a directed flow:

```
User Wallet
    │
    ▼
Proxy Box  ──────────────────────────────────────────────────────────▶  Refund Path
    │                                                                        │
    │  (consumed in same tx as Bank Box)                                     ▼
    ▼                                                                   User Wallet
Bank Box (Singleton State NFT)
    │
    ├── Mint Tx   →  Updated Bank Box  +  Buyer Box (hodlTokens)
    │
    ├── Burn Tx   →  Updated Bank Box  +  Buyer Box (reserve)  +  Phoenix Fee Box
    │
    └── Deposit Tx →  Updated Bank Box  (hodlToken variant only)
                                               │
                                               ▼
                                       Fee Contract Box(es)
                                               │
                                               ▼
                                   Fee Distribution Tx
                                   (Developer addresses + Miner fee)
```

**Bank Box** is the heart of the system. It is a **Singleton** authenticated by a State NFT in `tokens(0)`. It stores all reserve assets and the unissued hodl token supply, tracks protocol parameters in immutable registers R4–R8, and enforces the bonding curve invariant on every state transition. Because it is a singleton, there is exactly one authoritative bank box at any moment; the Token ID rule prevents forgery.

**Proxy Box** is an ephemeral escrow created by the user's wallet before the main transaction is assembled. It holds the user's deposit (ERG or base tokens) and encodes transaction intent in registers R4–R9 (buyer `SigmaProp`, token IDs, fee parameters). The proxy contract validates the entire transaction context — confirming the bank input is authentic, the correct amounts flow to the buyer, and fees are distributed — then self-destructs in the same transaction that updates the Bank Box. If the transaction is never assembled, the proxy can be refunded to the buyer unilaterally.

**Fee Contract Box** accumulates the developer portion of burn fees. It is a simple collector address that any number of fee-generating transactions can pay into. A separate fee distribution transaction — authorized by at least one developer signature — sweeps all accumulated fee boxes and splits the proceeds to hardcoded developer addresses in fixed proportions.

Data flows in one direction per transaction: the off-chain bot reads the current Bank Box state (reserve, token balances, registers) and the Proxy Box configuration, computes all output amounts, constructs the full transaction, and submits it. The Bank Box's next state is fully determined by its previous state plus the delta enforced by the contract.

---

## Smart Contracts

### `phoenix_v1_hodlerg_bank.es` / `phoenix_v1_hodltoken_bank.es`

The Bank contract is the protocol's **state machine core**. It guards the Singleton State NFT box and enforces three mutually exclusive transition types determined by the sign of `hodlTokensCircDelta` (the change in circulating hodl token supply):

| Transition | Condition | Reserve Change | Supply Change |
|---|---|---|---|
| Mint | `circDelta > 0` | Increases by `≥ circDelta × price / precisionFactor` | Decreases in bank |
| Burn | `circDelta < 0` | Decreases by `expectedAmount − bankFee` | Increases in bank |
| Deposit (hodlToken only) | `circDelta == 0` | Increases by proxy deposit | Unchanged |

**Bonding curve price formula:**
```
price = (reserveIn × precisionFactor) / hodlTokensInCirculation
```
where `hodlTokensInCirculation = totalTokenSupply (R4) − hodlTokensInBank`.

**Universal invariants enforced on every transaction:**
- Output Bank Box has identical ErgoTree bytecode (`validContract`)
- Singleton NFT quantity and Token ID are preserved (`validBankSingleton`)
- All registers R4–R8 are read-only and must be byte-identical in the output box (`validRegisters`)
- At least 1 hodl token remains in the bank at all times (prevents division-by-zero in the price formula)
- Reserve never drops below `minBankValue` (R6), protecting against storage rent depletion

**Burn fee model (dual-fee):**
- `bankFeeAmount`: Retained in the reserve, causing the bonding curve price to ratchet upward — this is the core proof-of-hodl mechanic.
- `devFeeAmount`: Routed to the Phoenix fee contract address, authenticated by blake2b256 hash of the fee contract's ErgoTree bytecode.
- Fee numerators are stored in R7 (`bankFeeNum`) and R8 (`devFeeNum`); denominator is hardcoded as 1000.
- An **adjustment rule** in the hodlToken variant handles edge cases where integer division would round the bank fee to zero: in such cases all combined fees are reallocated to the bank, preserving monotonic price growth.

**Registers:**

| Register | Type | Content |
|---|---|---|
| R4 | `Long` | `totalTokenSupply` — fixed maximum supply |
| R5 | `Long` | `precisionFactor` — scaling factor for integer arithmetic |
| R6 | `Long` | `minBankValue` — minimum reserve (nanoERG or base token units) |
| R7 | `Long` | `bankFeeNum` — bank fee numerator (denominator 1000) |
| R8 | `Long` | `devFeeNum` — dev fee numerator (denominator 1000) |

**Token layout (hodlToken variant):**

| Slot | Token | Invariant |
|---|---|---|
| `tokens(0)` | Bank Singleton NFT | Amount always 1 |
| `tokens(1)` | hodlToken | Amount ≥ 1 |
| `tokens(2)` | Base reserve token | Amount ≥ `minBankValue` |

---

### `phoenix_v1_hodlerg_proxy.es` / `phoenix_v1_hodltoken_proxy.es`

The Proxy contract is the **transaction validation layer** closest to the user. It reads the Bank Box as `INPUTS(0)` and verifies the complete output structure before allowing the proxy box to be consumed.

**Key validations performed by the proxy:**

- **Bank authentication**: Confirms