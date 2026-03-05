---
title: kushti/dexy-stable — bank.es
description: "ErgoScript contract analysis: contracts/bank/bank.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/bank.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Bank (kushti/dexy-stable)

## Purpose

The Bank contract is a **Singleton State box** that manages the emission of dexyUSD stablecoins in the Dexy protocol. It serves as the canonical ledger for dexyUSD token supply, preserving its identity (via bankNFT) and token ID across all transactions while delegating the complex minting/burning logic to specialized auxiliary contracts (FreeMint, ArbitrageMint, Intervention, Payout).

## Inputs / Outputs

### Expected Inputs (depends on transaction type)

| Transaction Type | Input 0 | Input 1 | Input 2 | Data-Inputs |
|---|---|---|---|---|
| **Arbitrage Mint** | ArbitrageMint box | Bank (SELF) | Buyback box | Oracle, LP |
| **Free Mint** | FreeMint box | Bank (SELF) | Buyback box | Oracle, LP |
| **Intervention** | LP box | Bank (SELF) | Intervention box | Oracle, Tracking (98%) |
| **Payout** | Payout box | Bank (SELF) | Buyback box | Oracle |
| **Update** | Update box | Bank (SELF) | — | — |

### Expected Outputs

| Output Index | Box | Purpose |
|---|---|---|
| **1** | Bank (successor) | Updated state copy of SELF with modified dexyUSD token amount |
| **Other** | Varies by tx type | Outputs from auxiliary contracts (FreeMint, Payout, etc.) |

The Bank box must always output at its index position (selfOutIndex = 1) to maintain state continuity.

## Key Logic

The Bank contract enforces **three orthogonal validation paths**, all requiring preservation of core state invariants:

### 1. **Valid Successor Preservation** (Lines 42–45)
All valid transactions must output a successor box at index 1 that maintains:
- **bankNFT** in tokens(0) — singular identifying token (Singleton pattern)
- **propositionBytes** — contract script unchanged
- **dexyUSD token ID** in tokens(1)._1 — stablecoin ID immutable (amount allowed to vary)

### 2. **Mint Path** (Lines 47–48)
Either FreeMint OR ArbitrageMint box (identified by NFT) must be at input index 0:
- **FreeMint**: User-initiated minting (off-chain oracle price feed)
- **ArbitrageMint**: Protocol arbitrageur minting to capture price discrepancies
- Both encode their own validation logic; Bank only enforces their presence

### 3. **Intervention Path** (Line 50)
Intervention box (identified by interventionNFT) must be at input index 2:
- Triggered when protocol health degrades (e.g., collateral ratio <98% per Tracking box in data-input)
- Allows emergency stabilization flows

### 4. **Payout Path** (Line 52)
Payout box (identified by payoutNFT) must be at input index 0:
- Manages stablecoin redemptions and user withdrawals

### 5. **Update Path** (Lines 54–55)
Update box (identified by updateNFT) at input index 0 allows contract upgrades:
- Bypasses all other validation rules
- Enables governance-driven parameter changes or bug fixes

### Final Guard (Line 57)
```
sigmaProp((validSuccessor && (validMint || validIntervention || validPayout)) || validUpdate)
```
**Valid iff:**
- (Successor preserved **AND** at least one auxiliary flow NFT present) **OR** Update path activated

## Registers Used

| Register | Type | Purpose | Read/Write |
|---|---|---|---|
| **R4** (Oracle data-input) | Long | Exchange rate: nanoErgs per USD | Read (via data-input) |
| **None (SELF)** | — | Bank box uses no custom registers | — |

**Note:** The Bank box itself carries no registers. Complex state (collateral ratios, fee parameters) is tracked by auxiliary boxes (Tracking, LP) passed as data-inputs or inputs to different transaction types.

## Tokens

| Token Index | Token | Purpose | Mutability |
|---|---|---|---|
| **tokens(0)** | **bankNFT** (singleton) | Identifies this box as the canonical Bank | **Immutable** (enforced in validSuccessor) |
| **tokens(1)._1** | **dexyUSD token ID** | Minted stablecoin identity | **Immutable** (enforced in validSuccessor) |
| **tokens(1)._2** | dexyUSD amount | Stablecoin supply | **Mutable** (amount changes per mint/burn) |

**NFTs used for routing:**
- `freeMintNFT` — identifies FreeMint contract box
- `arbitrageMintNFT` — identifies ArbitrageMint contract box
- `interventionNFT` — identifies Intervention contract box
- `payoutNFT` — identifies Payout contract box
- `updateNFT` — governance upgrade token

All NFTs injected as **Constant segregation** (Base64 placeholders: `$freeMintNFT`, etc.) during contract compilation.

## Integration Pattern

### Off-Chain Bot/Headless dApp Responsibilities

1. **For Mint Transactions (Arbitrage or Free):**
   - Construct FreeMint or ArbitrageMint box with correct NFT
   - Read **Oracle data-input** R4 (exchange rate)
   - Calculate dexyUSD emission amount (logic internal to FreeMint/ArbitrageMint)
   - Construct Buyback box output
   - Ensure Bank successor output at index 1 with:
     - bankNFT preserved
     - dexyUSD amount incremented
   - Satisfy minimum transaction fee & box value constraints

2. **For Intervention Transactions:**
   - Monitor Tracking box (98% threshold via data-input)
   - Trigger only when collateral ratio breaches emergency threshold
   - Construct Intervention box at input index 2
   - Pass Oracle and Tracking boxes as data-inputs

3. **For Payout Transactions