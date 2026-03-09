---
title: kushti/dexy-stable — Redeem.es
description: "ErgoScript contract analysis: contracts/lp/proxy/Redeem.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/proxy/Redeem.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: Redeem Proxy (Dexy)

## Purpose

This contract validates LP (liquidity provider) token redemptions from a CFMM (Constant Function Market Maker) n2t (native-to-token) pool within the Dexy protocol. It ensures users receive fair value when burning LP tokens, applying a 2% redemption fee and protecting against slippage.

## Inputs / Outputs

### Inputs
- **INPUTS(0)**: Pool box containing:
  - Pool NFT (State NFT for pool identity)
  - LP token (state tracking)
  - Reserve token Y (secondary asset)
  - Native ERG value (reserve X amount)
- **INPUTS(1+)**: User's LP token box (SELF) holding LP tokens to redeem
- **Data inputs**: None explicitly used

### Outputs
- **OUTPUTS(0)**: Pool box (updated state, returned to pool)
- **OUTPUTS(1)**: Action box (Dexy-specific protocol state)
- **OUTPUTS(2)**: Redemption return box to user containing:
  - Calculated ERG amount (reserve X)
  - Calculated token Y amount (reserve Y proportional)
  - Recipient address (verified against Pk)
- **Additional outputs**: Miner fee box (validated separately)

## Key Logic

1. **Pool Validation**: Verifies INPUTS(0) is a valid pool by checking for Pool NFT token in first position
2. **Reserve Calculation**: Computes user's share using:
   - Supply LP = `InitiallyLockedLP - poolLP._2` (outstanding LP tokens)
   - User's proportional share = `userLP / supplyLP`
3. **Slippage Protection with Fee**:
   - Minimum return X: `(userLP / supplyLP) × reservesX × 0.98` (2% fee applied)
   - Minimum return Y: `(userLP / supplyLP) × reservesY × 0.98` (2% fee applied)
4. **Output Validation**:
   - Return box sends to legitimate user (Pk.propBytes check)
   - Token IDs match pool reserves
   - Actual outputs meet or exceed minimum returns
5. **Miner Fee Enforcement**: Total miner fees across all outputs ≤ MaxMinerFee
6. **Sigma Protocol**: Either Pk signs OR validRedeem passes (user or protocol execution)

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| R0-R3 | Implicit | Standard box value, tokens, script bytes |
| R4-R9 | None used | Contract is stateless; all data from input boxes |
| Pk | Constant | User's public key (signer alternative path) |
| PoolNFT | Constant | Pool identifier token ID |
| MinerPropBytes | Constant | Miner reward script (Ergo consensus) |
| MaxMinerFee | Constant | Maximum allowed transaction fee |
| DexFee | Constant | Protocol-level fee extraction |

## Tokens

| Token | Role | Quantity |
|-------|------|----------|
| **Pool NFT** | State NFT / singleton | 1 (pool identity, ensures unique pool) |
| **LP Token** | Liquidity proof, burnt on redemption | User's SELF.tokens(0)._2 amount |
| **Reserve Token Y** | Secondary pool asset | Redeemed proportionally |
| **Native ERG** | Primary pool reserve (value field) | Redeemed proportionally |

**Token ID Rule**: LP token and reserve tokens must match pool's tracked token IDs; no new tokens created in this contract (redemption only).

## Integration Pattern

### Off-chain Bot / Headless dApp Must:

1. **Construct Input Set**:
   - Fetch current pool box (INPUTS(0)) from blockchain
   - Locate user's UTXO holding LP tokens (INPUTS(1))

2. **Calculate Returns**:
   - Query pool state (reserves X, Y; LP supply)
   - Apply 2% fee: `minReturn = userLP × reserves / supply × 0.98`
   - Account for storage rent and DexFee constant

3. **Build Outputs**:
   - OUTPUTS(0): Pool box with updated LP token amount
   - OUTPUTS(1): Action box (Dexy protocol update)
   - OUTPUTS(2): User's return box with calculated amounts
   - Add miner fee box (validate against MaxMinerFee)

4. **Sign Transaction**:
   - If Pk path: user signs with private key
   - If validRedeem path: off-chain bot verifies all conditions, no signature needed

5. **Validate Constants**:
   - Ensure PoolNFT, MinerPropBytes, MaxMinerFee, DexFee match current protocol deployment

### Example Flow:
```
User → "Redeem 100 LP tokens"
Bot → Fetches pool box (reserves: 1000 ERG, 500 TokenY)
    → Calculates: 100/9223372036854775807 × 1000 × 0.98 ≈ 0.106 ERG
    → Creates return box to user
    → Signs or validates validRedeem conditions
    → Submits transaction
```

## Related Contracts

- **Pool Box Contract**: Manages core CFMM invariant and reserve updates; this contract consumes its output
- **Swap Proxy Contract**: Sister contract for token exchanges (n2t or t2n), uses same pool format
- **Action Box Contract**: Dexy-specific protocol sequencing; output OUTPUTS(1) required by this contract
- **SigmaUSD / Dexy Protocol**: Higher-level stablecoin contracts that may compose redemption logic
- **Spectrum CFMM**: Original Spectrum DEX source; Dexy adapted this redemption contract with 2% fee

---

## Notes

- **Atomic Swap Pattern**: This is not a true atomic swap but a **multi-stage contract** requiring pool state verification
- **Minimum Box Value**: All outputs must satisfy Ergo's dust limit; verified indirectly through DexFee constant
- **Storage Rent**: Long-lived pool box incurs ~0.14 ERG/year;