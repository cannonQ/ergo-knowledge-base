---
title: kushti/dexy-stable — bank.es
description: "ErgoScript contract analysis: contracts/bank/bank.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/bank/bank.es
project: dexy-use
---
# ErgoScript Contract Analysis: `bank.es`

## Purpose

The Bank contract is the central state machine for the Dexy stablecoin protocol. It maintains a Singleton box that holds the dexyUSD token supply and enforces that all token emission/management flows (minting, intervention, payouts) are routed through authorized satellite contracts. The Bank itself does not encode emission logic—it delegates validation to downstream boxes (FreeMint, ArbitrageMint, Intervention, Payout) that must be present as inputs.

---

## Inputs / Outputs

### Inputs (Box Context)

| Index | Role | Purpose |
|-------|------|---------|
| **0** | Mint Box (FreeMint OR ArbitrageMint) *OR* Payout Box | Triggers emission or payout; contains the logic for how many dexyUSD to mint/burn |
| **1** | Bank (Self) | Current state of the Bank Singleton; carries NFT + dexyUSD tokens |
| **2** | Buyback / Intervention Box (optional, context-dependent) | Participates in specific flows (arbitrage buyback, intervention) |

### Outputs (Box Context)

| Index | Role | Purpose |
|-------|------|---------|
| **1** | Bank (Self) | Updated Bank Singleton; same NFT + script, but dexyUSD token quantity may change |
| Other | Downstream boxes | Outputs required by the specific mint/intervention/payout box logic |

### Data Inputs (Read-Only Context)

- **Oracle box**: Provides exchange rate (nanoErgs per USD) in R4 as Long
- **LP box** (in mint flows): Price feedback
- **Tracking box** (in intervention, 98% threshold): Collateral ratio monitoring

---

## Key Logic

### Core Validation Rule

```
(validSuccessor AND (validMint OR validIntervention OR validPayout)) OR validUpdate
```

**Decoded:**

1. **Normal flows** (Mint / Intervention / Payout):
   - A successor Bank box must exist at output index 1
   - The successor **must preserve**:
     - The Bank's NFT (Singleton identifier) at `tokens(0)`
     - The script (`propositionBytes`) unchanged
     - The dexyUSD token ID at `tokens(1)._1` (amount may vary)
   - **AND** one of these must be true:
     - Input 0 contains **FreeMint NFT** → standard user minting flow
     - Input 0 contains **ArbitrageMint NFT** → arbitrage minting with buyback
     - Input 2 contains **Intervention NFT** → protocol intervention (e.g., collateral shortfall)
     - Input 0 contains **Payout NFT** → stablecoin redemption/payout

2. **Update flow**:
   - Input 0 contains **Update NFT** → allows contract upgrade (e.g., new logic, emergency pause)
   - No output validation required (trust the Update box logic)

### Invariants Enforced

- **Singleton preservation**: Bank NFT never changes hands or is duplicated
- **Script immutability**: The Bank script cannot be modified mid-stream (prevents malicious logic injection)
- **Token ID stability**: dexyUSD token class is fixed; only quantity can change
- **Authorization**: Only recognized NFTs (FreeMint, ArbitrageMint, Intervention, Payout, Update) can trigger state transitions

---

## Registers Used

| Register | Type | Purpose | Read/Write |
|----------|------|---------|-----------|
| **R4** | Long | (Oracle box, not Bank) Stores nanoErgs-per-USD exchange rate | Read (data input) |
| None | — | Bank box uses **no custom registers**; state is encoded purely in token amounts | — |

The Bank is intentionally **register-minimal** to reduce validation complexity and storage rent. All state is tracked via the dexyUSD token quantity in `tokens(1)._2`.

---

## Tokens

### Token 0: Bank NFT
- **Type**: NFT (fixed quantity = 1)
- **Purpose**: Singleton identifier; ensures only one authorized Bank box exists
- **Rule**: Must be preserved exactly in the successor output
- **Base64 constant**: `$bankNFT` (injected at compile time, not shown in source)

### Token 1: dexyUSD
- **Type**: Native token (variable quantity)
- **Purpose**: The stablecoin supply; increased by minting, decreased by payouts/burns
- **ID**: Constant across all transactions (enforced by `tokens(1)._1 == SELF.tokens(1)._1`)
- **Token ID Rule**: Once established, the dexyUSD token ID cannot change (tied to this specific Bank box at genesis)
- **Base64 constant**: `$dexyUSDTokenId` (implicit in validation; amount at `tokens(1)._2`)

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

The off-chain system must:

1. **Monitor the Bank box** (via Singleton NFT lookup)
   ```
   Filter: tokens(0) == bankNFT
   ```

2. **Route transactions through specialized contracts**:
   - **FreeMint flow**: User → FreeMint box (R4/R5: collateral proof, amount) → Bank input
   - **ArbitrageMint flow**: Arbitrage bot → ArbitrageMint box → Bank + Buyback inputs
   - **Payout flow**: User → Payout box (proof of dexyUSD burn) → Bank input
   - **Intervention flow**: Protocol bot → LP box (input 0) + Intervention box (input 2) → Bank (input 1)

3. **Construct the transaction**:
   ```
   tx.inputs = [MintBox, BankBox, BuybackOrInterventionBox]
   tx.outputs = [MintBox.successor, BankBox.successor, ...]
   tx.dataInputs = [OracleBox, LPBox, TrackingBox?]
   ```

4. **Verify oracle rate** (off-chain):
   - Extract R4 from oracle data input
   - Use it to validate mint amounts / collateral ratios in the mint/intervention boxes

5. **