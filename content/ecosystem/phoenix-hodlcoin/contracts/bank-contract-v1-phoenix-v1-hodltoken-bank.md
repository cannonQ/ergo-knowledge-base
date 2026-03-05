---
title: PhoenixErgo/phoenix-hodlcoin-contracts — phoenix_v1_hodltoken_bank.es
description: "ErgoScript contract analysis: hodlToken/contracts/bank_contract/v1/ergoscript/phoenix_v1_hodltoken_bank.es"
tags: [phoenixergo, phoenix-hodlcoin-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/PhoenixErgo/phoenix-hodlcoin-contracts"
contract_file: hodlToken/contracts/bank_contract/v1/ergoscript/phoenix_v1_hodltoken_bank.es
project: phoenixergo-phoenix-hodlcoin-contracts
---
# Phoenix HodlToken Bank Contract Analysis

## Purpose

The Phoenix HodlToken Bank contract is the central state machine managing the HodlToken protocol's reserve pool and token supply. It validates Mint, Burn, and Reserve Deposit transactions, ensuring atomic swaps between HodlTokens and a base reserve token occur at a fair bonding-curve price while collecting protocol fees.

## Inputs / Outputs

### Inputs
- **Bank Box (SELF)**: The primary eUTXO containing:
  - 3 native tokens: Bank Singleton NFT, HodlToken amount, Base Token reserve
  - 5 immutable registers (R4–R8) encoding protocol parameters
  - Fixed ERG value (never changes)
- **Proxy Box**: Secondary input funding transaction costs and facilitating operations

### Outputs
- **Bank Box (OUTPUTS(0))**: Recreated singleton state box with updated token balances
- **Buyer/Recipient Box**: User receives minted HodlTokens or base tokens post-burn
- **Fee Boxes**: Miner fee, Operator fee, and optionally Phoenix fee output
- Context extension may carry additional data (though none used here)

---

## Key Logic

### State Machine Conditions

The contract is a **three-state finite state machine** identified by token delta (`hodlTokensCircDelta`):

1. **Mint Transaction** (`isMintTx: hodlTokensCircDelta > 0`)
   - User deposits base tokens into reserve; receives newly minted HodlTokens
   - **Invariant**: `reserveOut ≥ reserveIn + (hodlTokensCircDelta × price ÷ precisionFactor)`
   - Price increases monotonically as reserve grows
   - Validation: tokens deposited must meet minimum required amount

2. **Burn Transaction** (`isBurnTx: hodlTokensCircDelta < 0`)
   - User deposits HodlTokens back to bank; receives base tokens minus fees
   - **Fee Calculation** (dual-fee model):
     - Combined fee = `divUp((hodlTokensBurned × price × (bankFeeNum + devFeeNum)) ÷ feeDenom)`
     - Developer allocation = `divUp(combinedFee × devFeeNum ÷ (bankFeeNum + devFeeNum))`
     - Bank allocation = Combined fee − Developer allocation
     - **Adjustment rule**: If bank fee rounds to zero, reallocate all fees to bank (preserves price monotonicity)
   - User receives: `reserveOut + expectedAmountBeforeFees − bankFeeAmountAdjusted − devFeeAmountAdjusted`

3. **Deposit Transaction** (`isDepositTx: hodlTokensCircDelta == 0`)
   - Pure reserve increase (no minting/burning)
   - Reserve tokens flow in; protocol receives no fees
   - HodlToken supply unchanged

### Universal Bank Invariants

All three transaction types enforce:

| Invariant | Purpose |
|-----------|---------|
| `validValue`: ERG value unchanged | HodlToken protocol is base-token-only; ERG reserved for storage rent |
| `validContract`: Bytecode unchanged | Ensures singleton box remains at same ErgoTree address |
| `validBankSingleton`: Singleton NFT preserved | State token ID rule: prevents box substitution attacks |
| `validHodlTokenAmount ≥ 1`: At least 1 HodlToken remains | Prevents division by zero in circulating supply calculation |
| `validBaseTokenMinBankValue`: `reserveOut ≥ minBankValue` | Enforces minimum reserve buffer (storage rent safety) |
| `validRegisters`: R4–R8 immutable | Parameters locked at initialization (no protocol upgrades on-chain) |

### Price Formula (Constant Product)

```
price = (reserveIn × precisionFactor) ÷ hodlTokensCircInCirculation
```

- **Bonding curve**: Price increases as reserve grows, decreases as tokens burned
- **Precision factor**: Scales calculation to avoid floating-point issues (e.g., if base token has 6 decimals, factor = 10^6)
- **Integer division handling**: `divUp()` helper rounds up to prevent rounding errors favoring users over protocol

---

## Registers Used

| Register | Type | Name | Purpose |
|----------|------|------|---------|
| **R4** | `Long` | `TotalTokenSupply` | Fixed maximum HodlToken supply (immutable); used to derive circulating supply |
| **R5** | `Long` | `PrecisionFactor` | Decimal scaling factor for base token price calculations (e.g., 1000000 for 6 decimals) |
| **R6** | `Long` | `MinBankValue` | Minimum reserve token amount required in bank (storage rent buffer) |
| **R7** | `Long` | `BankFeeNum` | Numerator for bank fee ratio (denominator = 1000); e.g., 50 = 5% |
| **R8** | `Long` | `DevFeeNum` | Numerator for developer fee ratio (denominator = 1000); can be zero |

**Register Mutation Policy**: All five registers are **read-only**. Immutability is validated in `validRegisters` block; any modification causes transaction rejection.

---

## Tokens

### Singleton NFT (tokens(0))
- **Token ID**: `BankSingletonId` (compile-time constant derived from initial transaction)
- **Amount**: Always 1
- **Purpose**: Uniquely identifies the authentic bank box (prevents forking; enables atomic swaps)
- **Validation**: `validBankSingleton` ensures identity and quantity never change

### HodlToken (tokens(1))
- **Token ID**: `HodlTokenId` (minted during protocol initialization)
- **Amount**: Tracks tokens stored in bank reserve
  - Decreases on mints (user buys, receives HodlTokens)
  - Increases on burns (user sells, sends HodlTokens back)
- **Invariant**: `hodlTokensOut ≥ 1` (prevents liquidity depletion)
- **Supply tracking**: Circulating supply =