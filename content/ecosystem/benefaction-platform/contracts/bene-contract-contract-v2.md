---
title: StabilityNexus/BenefactionPlatform-Ergo — contract_v2.es
description: "ErgoScript contract analysis: contracts/bene_contract/contract_v2.es"
tags: [stabilitynexus, benefactionplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
contract_file: contracts/bene_contract/contract_v2.es
project: stabilitynexus-benefactionplatform-ergo
---
# ErgoScript Contract Analysis: Bene Fundraising Platform Contract (v1.2.1)

## Purpose

The **Bene Fundraising Platform Contract** is a multi-token fundraising mechanism that enables projects to receive contributions in any base token (ERG or custom token) in exchange for **Proof of Funding Tokens (PFT)**. It manages the entire lifecycle of a fundraising campaign—from contribution acceptance, to token distribution, to refund handling—while maintaining atomic state invariants and fee distribution to developers.

## Inputs / Outputs

### Input Boxes
- **Self Box (SELF)**: The singleton fundraising contract box containing:
  - **APT (Authority/Project Token)**: NFT identifying the project (1 unit + emission amount)
  - **PFT (Proof of Funding Token)**: Available tokens for distribution (amount = max target base tokens)
  - **Base Token** (optional): If fundraising in non-ERG token, holds accumulated contributions
  - **ERG**: Minimum box value (2 ERG) + accumulated ERG if ERG-denominated fundraising
  - **Registers R4–R9**: Temporal constraints, thresholds, counters, rates, constants, metadata

### Output Boxes
1. **Replication Box** (OUTPUTS(0)): Updated singleton matching Self with modified state (counters, token amounts, or base token balance)
2. **Contribution/Withdrawal Boxes** (OUTPUTS(1+)): 
   - User receives PFT tokens on contribution
   - User receives refunded base tokens on withdrawal
   - Owner receives withdrawn base tokens or fees
3. **Dev Fee Box** (when applicable): Receives fee share sent to developer fee contract

### State Machine Flow
- **Funding Phase**: Accepts contributions, increments `selfSoldCounter`, distributes PFT
- **Refund Phase** (if minimum not met after deadline): Returns base tokens, decrements counters
- **Withdrawal Phase** (if minimum met): Owner/project withdraws accumulated base tokens and unsold PFT

---

## Key Logic

### 1. **Box Replication & State Continuity** (`isSelfReplication`)
Validates that OUTPUTS(0) is a valid state evolution of SELF by verifying:
- Same APT NFT ID (preserves project identity)
- Same R4 block/timestamp limit (temporal constraint unchanged)
- Same R5 minimum tokens sold threshold
- Same R7 exchange rate (base tokens per PFT)
- Same R8 constants (owner, dev fee, token IDs)
- Same R9 metadata (immutable project description)
- Same ErgoTree proposition bytes (contract logic unchanged)
- Valid token count (1–2 for ERG base, 1–3 for custom token base)

**Invariant**: Only counters, token balances, and base token amounts can change; structure is immutable.

### 2. **Contribution Flow**
```
User sends base tokens → Contract receives base tokens
Contract decrements temporary_funding_token_amount (PFT reserve)
Contract increments selfSoldCounter by PFT amount
User receives PFT in output box
```

**Calculation**: 
```
temporary_funding_token = PFT_amount - sold + refunded + exchanged
```
This accounts for:
- **sold**: Cumulative PFT distributed
- **refunded**: PFT bought back during refund phase
- **exchanged**: APT → PFT swaps via auxiliary exchange

### 3. **Refund Mechanism**
- **Precondition**: Block height or timestamp ≥ R4 limit AND sold < minimum threshold (R5)
- **Action**: Return base tokens to user, decrement `selfRefundCounter`, increment `refundCounterRemainsConstant`
- **Validation**: User cannot receive more base tokens than initially contributed (tracked via counters)

### 4. **Minimum Threshold Enforcement**
- **R5 (selfMinimumTokensSold)**: Minimum PFT threshold required to "unlock" withdrawals
- **If sold ≥ R5**: Owner can withdraw accumulated base tokens; PFT remains locked or can be withdrawn per `isWithdrawUnsoldTokens`
- **If sold < R5 + deadline passed**: Users can refund base tokens

### 5. **Base Token Flexibility**
```ergoscript
val isERGBase = baseTokenId.size == 0

if (isERGBase) {
  // Contributions in ERG: use box.value
  baseTokenAmount = box.value
} else {
  // Contributions in custom token: extract from tokens(i) where id == baseTokenId
  baseTokenAmount = box.tokens.filter(t => t._1 == baseTokenId)(0)._2
}
```
- **ERG mode**: Contract receives/sends ERG value directly
- **Custom token mode**: Contract holds custom token native asset; box must contain 3 tokens (APT, PFT, base token)

### 6. **State Counter Validation**
All three counters in R6 must be preserved during replication unless explicitly modified:
- **selfSoldCounter**: Total PFT sold (only increases on contributions)
- **selfRefundCounter**: Total PFT refunded (only increases on refunds)
- **selfAuxiliarExchangeCounter**: APT ↔ PFT exchange adjustments (fine-tuning mechanism)

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `(Boolean, Long)` | **Temporal Limit Tuple**: Boolean (false = block height, true = timestamp) + limit value. Refunds allowed only after this point if minimum not met. |
| **R5** | `Long` | **Minimum Tokens Threshold**: Minimum PFT quantity that must be sold to unlock fund withdrawals. If not met by deadline, refunds enabled. |
| **R6** | `Coll[Long]` | **State Counters** (3 elements): [0] = total sold, [1] = total refunded, [2] = APT↔PFT exchange adjustments. Enables accurate reserve calculation. |
| **R7** | `Long` | **Exchange Rate**: Base token amount per 1 PFT (e.g., 1000 means 1000 base