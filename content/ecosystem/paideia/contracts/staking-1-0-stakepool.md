---
title: paideiadao/paideia-contracts — stakePool.es
description: "ErgoScript contract analysis: paideia_contracts/contracts/staking/ergoscript/1.0/stakePool.es"
tags: [paideiadao, paideia-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-contracts"
contract_file: paideia_contracts/contracts/staking/ergoscript/1.0/stakePool.es
project: paideiadao-paideia-contracts
---
# ErgoScript Contract Analysis: stakePool.es

## Purpose

The **stakePool** contract governs a Singleton (State NFT) box that holds DAO tokens reserved for emission to stakers. It validates two transaction types: **Emit Tx** (daily withdrawal of tokens into an Emission box with a 1% fee) and **Remove Funds Tx** (governance-controlled fund withdrawal). This contract is the treasury mechanism for a stake-based DAO incentive system.

---

## Inputs / Outputs

### Emit Tx (Primary Flow)
**Inputs:**
- `INPUTS(0)`: Stake State Box (contains staking metrics: total staked, checkpoint, staker count, cycle duration)
- `INPUTS(1)`: Stake Pool Box (`SELF`) — the contract box holding DAO tokens
- `INPUTS(2)`: Emission Box — carry-over from previous cycle with remaining tokens
- `INPUTS(3)`: Staking Incentive Box (auxiliary)

**Outputs:**
- `OUTPUTS(0)`: New Stake State Box (updated staking metrics)
- `OUTPUTS(1)`: New Stake Pool Box (reduced token supply after emission)
- `OUTPUTS(2)`: New Emission Box (DAO tokens to distribute)
- `OUTPUTS(3)`: Emission Fee Box (1% of emission amount)
- `OUTPUTS(4)`: Staking Incentive Box (passthrough)
- `OUTPUTS(5)`: Tx Operator Output (miner/bot fee)

### Remove Funds Tx (Alternative Flow)
**Inputs:**
- Stake Pool Box (`SELF`)
- Staking Incentive Box

**Outputs:**
- Any box carrying the Stake Pool Key (governance retrieval)
- Any other box(es)

---

## Key Logic

### Emit Tx Validation

**1. Input Authentication**
```
✓ INPUTS(0) holds the Stake State NFT (StakeStateNFT)
✓ INPUTS(1) is SELF (stake pool box identity check via Box.id)
```

**2. Token Flow Calculation**
```
remainingStakePoolTokens = SELF.tokens(1)._2 + emissionDust
emissionFee = emissionAmount / 100  (1% fee)
newStakePoolTokens = remainingStakePoolTokens - emissionAmount
```

**3. New Stake Pool Box Validation**
```
✓ Value preserved (ERG amount unchanged)
✓ Contract preserved (propositionBytes == SELF.propositionBytes)
✓ Stake Pool NFT carried forward (token(0) unchanged)
✓ Emission amount constant (R4 unchanged)
✓ Stake Pool Key preserved (R5 unchanged)
✓ Remaining token amount correctly decremented
✓ If insufficient tokens remain, token array size reduced to 1 (NFT only)
```

**4. Stake State Box Update**
```
newTotalStaked = totalAmountStaked + (emissionAmount - emissionFeeAmount) - emissionDust
(accounts for fee deduction and dust cleanup)
```

**5. Emission Fee Box**
```
✓ Created only if newStakePoolBox still holds DAO tokens (tokens.size > 1)
✓ Fee amount: emissionAmount / 100
✓ Sent to EmissionFeeAddress (hardcoded constant)
```

**6. New Emission Box**
```
✓ Holds Emission NFT (token(0)._1 == emissionNFT)
✓ Contains DAO tokens for distribution: emissionAmount - emissionFeeAmount
✓ Value sufficient for storage rent
```

### Remove Funds Tx Validation

```
✓ Stake Pool Key must appear in some output box (enables governance fund recovery)
✓ Allows arbitrary fund withdrawal when properly authorized
```

---

## Registers Used

### Stake Pool Box (SELF)

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` (via `Coll[Long]`) | **Emission Amount** — DAO tokens allocated per emission cycle (immutable parameter) |
| **R5** | `Coll[Byte]` | **Stake Pool Key** — Identifier for fund recovery (immutable) |

### Stake State Box (INPUTS(0))

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Array: `[totalAmountStaked, checkpoint, stakers, lastCheckpointTimestamp, cycleDuration]` |

### New Stake State Box (OUTPUTS(0))

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Updated with new total staked (accounting for fee and dust) |

### Emission Box (INPUTS(2), OUTPUTS(2))

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Array: `[totalAmountStaked, checkpoint, stakers, emissionAmount]` |

### Stake Box (referenced in design docs)

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Coll[Long]` | Array: `[checkpoint, stakingTime]` |
| **R5** | `Coll[Byte]` | **Stake Key ID** — Reference for unstaking authorization |

---

## Tokens

### Token Structure in Stake Pool Box (SELF)

| Index | Type | Amount | Purpose |
|-------|------|--------|---------|
| **tokens(0)** | **Stake Pool NFT** | 1 (immutable) | **Singleton identifier** — ensures only one authoritative stake pool box exists per DAO |
| **tokens(1)** | **DAO Token ID** | `<= Total DAO Supply` | **Emission reserve** — DAO tokens waiting to be distributed; depleted with each emit cycle |

### Token Structure in Related Boxes

**Stake State Box:**
- `tokens(0)`: Stake State NFT (singleton)
- `tokens(1)`: Stake Token (proof of valid stake creation; supply <= 1