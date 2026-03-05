---
title: kushti/dexy-stable — Deposit.es
description: "ErgoScript contract analysis: contracts/lp/proxy/Deposit.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/Deposit.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Deposit.es

## Purpose

This contract validates **liquidity provider (LP) deposits into a Constant Function Market Maker (CFMM) n-to-1 token pool** within the Dexy protocol. It ensures that users receive fair LP token rewards proportional to their deposited assets, protecting against slippage and enforcing correct fee handling.

---

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: The **Pool Box** — contains:
  - Pool NFT (token 0) — identifies the pool
  - LP tokens (token 1) — tracks circulating LP supply
  - Reserve token Y (token 2) — the secondary reserve asset
  - ERG value — the primary reserve (reserve X)
- **INPUTS(1+)**: User deposit boxes (at least 2 inputs total)
- **SELF**: The Deposit Proxy Box — contains:
  - Token Y being deposited (SELF.tokens(0))
  - ERG being deposited (SELF.value)

### Outputs
- **OUTPUTS(0)**: Pool Box (updated state)
- **OUTPUTS(1)**: Action Box (Dexy-specific orchestration)
- **OUTPUTS(2)**: Reward Box — sent to user (Pk) containing:
  - LP tokens earned (rewardLP)
  - Optional excess token Y (if deposit unbalanced)
- **OUTPUTS(n)**: Miner fee box (variable position)

---

## Key Logic

The contract enforces **proportional deposit mechanics** with these invariants:

1. **Pool Validation**: INPUTS(0) must be the actual pool (PoolNFT present, 3 tokens)

2. **Fair LP Reward Calculation**:
   - Compute minimum LP tokens earned via two routes:
     - `minByX = deposited_ERG × total_LP_supply / reserve_X`
     - `minByY = deposited_Y × total_LP_supply / reserve_Y`
   - **Actual reward must be ≥ min(minByX, minByY)** — the limiting factor

3. **Excess Handling** (unbalanced deposits):
   - If `minByX < minByY`: user deposits more Y than X relative to pool ratio
     - Calculate excess Y: `excessY = (minByY - minByX) × reserve_Y / total_LP_supply`
     - Return excess Y tokens to user in OUTPUTS(2)
     - Reward box must hold 2 tokens (LP + excess Y)
   - If `minByX ≥ minByY`: balanced or excess X (no token refund needed)
     - Reward box contains only LP tokens

4. **Value Conservation**:
   - Reward box value must cover: `SELF.value - DexFee - (ERG not deposited)`
   - DexFee deducted from user's ERG for protocol revenue

5. **Fee Enforcement**:
   - Total miner fees across all outputs ≤ MaxMinerFee

6. **Authorization**:
   - Either user signs with Pk **OR** all validDeposit conditions pass (multi-sig fallback)

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | Byte[] | PoolNFT ID (constant) |
| **R5** | Byte[] | Pk.propBytes (user's public key) |
| **R6** | Long | SelfX (ERG amount deposited) |
| **R7** | Byte[] | DexFee (protocol fee in nanoERG) |
| **R8** | Byte[] | MinerPropBytes (miner script) |
| **R9** | Long | MaxMinerFee (transaction fee cap) |

*Exact register mappings inferred from constant segregation pattern; compiled bytecode uses optimized indexing.*

---

## Tokens

### Native Tokens Used

| Token | Role | Authentication |
|-------|------|---|
| **PoolNFT** | Pool identity | Verified in poolIn.tokens(0)._1 |
| **LP Token** | LP supply tracker | Tracked in pool state; minted/burned via liquidity operations |
| **Reserve Y Token** | Secondary reserve | Deposited alongside ERG; returned as excess if unbalanced |

### Token ID Rule
- PoolNFT is **singleton** — only one instance exists per pool
- LP tokens use **standard Ergo native token mechanics** (unlimited supply, controlled by pool contract)
- Reserve Y token ID is arbitrary but validated against poolIn.tokens(2)

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Workflow

1. **Read Pool State**:
   ```
   pool_box = fetch_utxo(pool_nft_id)
   reserve_x = pool_box.value
   reserve_y = pool_box.tokens[2]._2
   lp_supply = InitiallyLockedLP - pool_box.tokens[1]._2
   ```

2. **User Input**:
   - User specifies: amount of ERG and amount of Y to deposit
   - Calculate expected LP: `min(erg × lp_supply / reserve_x, y × lp_supply / reserve_y)`

3. **Construct Transaction**:
   - INPUTS(0) = pool_box
   - INPUTS(1) = deposit_proxy_box (created by user, protected by this contract)
   - OUTPUTS(0) = updated pool_box
   - OUTPUTS(1) = action_box (orchestration signal)
   - OUTPUTS(2) = reward_box (to user's address, containing LP + excess tokens)
   - Provide Context Extension with user's signature

4. **Verify On-Chain**:
   - Contract checks all proportionality conditions
   - If valid, reward_box is released to user
   - If invalid, transaction fails (user retains deposit box)

### Context Extension
- Must include user's **sigma proof** (Pk) for fallback authorization
- May include hints for efficient sigma protocol evaluation

---

## Related Contracts

### Inferred Relationships (Dexy Protocol Stack)

| Contract | Interaction | Purpose |
|----------|-------------|------|
| **Pool.