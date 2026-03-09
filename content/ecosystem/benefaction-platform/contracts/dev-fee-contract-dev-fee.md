---
title: StabilityNexus/BenefactionPlatform-Ergo — dev_fee.es
description: "ErgoScript contract analysis: contracts/dev_fee_contract/dev_fee.es"
tags: [stabilitynexus, benefactionplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/BenefactionPlatform-Ergo"
contract_file: contracts/dev_fee_contract/dev_fee.es
project: stabilitynexus-benefactionplatform-ergo
---
# ErgoScript Contract Analysis: Dev Fee Contract

## Purpose

This contract guards a fee collection box for the BenefactionPlatform fundraising protocol and ensures that accumulated fees are distributed proportionally to four designated beneficiaries (Bruno, Lgd, Josemi, and The Stable Order). The contract validates that fee distribution transactions split the collected value (ERG or tokens) according to predetermined ratios before releasing funds.

## Inputs / Outputs

| Aspect | Details |
|--------|---------|
| **Input Boxes** | One or more `BeneFee` boxes containing accumulated fees (ERG or native tokens) guarded by this contract |
| **Output Boxes** | Exactly 4 boxes: `brunoBoxOUT`, `lgdBoxOUT`, `jmBoxOUT`, `orderBoxOUT` — one for each beneficiary, each containing their proportional share |
| **Data Inputs** | None |

**Box Structure (Input):**
- **Value**: ERG amount (minimum box value + stored fees)
- **Tokens** (optional): Native token(s) to distribute
- **R4** (optional): `Coll[Byte]` — Token ID to distribute; empty if distributing ERG

## Key Logic

1. **Distribution Mode Detection**: Reads R4 to determine if distributing tokens or ERG. If R4 is defined and non-empty, the contract treats the box as holding tokens; otherwise, it distributes raw ERG.

2. **Output Count Validation**: Enforces exactly 4 outputs corresponding to the 4 beneficiaries.

3. **Minimum Value Check**: Verifies total output value ≥ 5,000,000 nanoERG to satisfy storage rent and minimum box value requirements.

4. **Proportional Split Calculation**: Computes each beneficiary's share using the formula:
   - `amount = (numerator × devAmount) / 100`
   - Bruno: 32/100 (32%)
   - Lgd: 32/100 (32%)
   - Josemi: 32/100 (32%)
   - Order: 4/100 (4%)

5. **Output Verification**: For each output box, confirms:
   - The distribution amount (ERG or token amount) matches the calculated share
   - The `propositionBytes` match the hardcoded beneficiary address

6. **All-or-Nothing**: Uses `allOf()` to enforce that all conditions must pass atomically; a single failed check invalidates the transaction.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Option[Coll[Byte]]` | Stores optional Token ID for token distributions. If defined and non-empty, signals token distribution mode; if absent or empty, signals ERG distribution mode. |

**Note**: Registers R5–R9 are not used. The contract relies on compile-time constants for beneficiary addresses rather than runtime registers.

## Tokens

- **Token Distribution Support**: The contract is polymorphic and can distribute any native token whose ID is stored in R4.
- **No NFT/Singleton Pattern**: Unlike state-machine contracts, this is not a Singleton with a state NFT; it is a simple multi-signature fee splitter.
- **Optional Token Payload**: Input boxes may hold native tokens; the contract extracts amounts via token filtering on output boxes.

## Integration Pattern

**Off-chain Bot / Headless dApp Responsibilities:**

1. **Fee Accumulation Phase**:
   - Monitor one or more fee boxes guarded by this contract.
   - Aggregate accumulated fees from the fundraising platform.

2. **Transaction Construction**:
   - Create a transaction with all fee boxes as inputs.
   - Calculate each beneficiary's share: `(numerator × total) / 100`.
   - Construct 4 output boxes in order: Bruno (index 0), Lgd (1), Josemi (2), Order (3).
   - Ensure each output:
     - Contains exactly the calculated amount (ERG or tokens matching R4 ID).
     - Has `propositionBytes` matching the hardcoded beneficiary public key.
     - Meets minimum box value (1.5 ERG = 1,500,000 nanoERG).

3. **Context Extension**:
   - No context variables (`_`) are required.

4. **Signing**:
   - The transaction must be signed by the entity controlling the fee box (or authorized via a multi-sig setup).
   - Output boxes are locked to beneficiary addresses; beneficiaries must sign to spend them in subsequent transactions.

**Example Off-chain Flow**:
```
1. Query fee box state (value, tokens, R4)
2. Determine distribution mode (isTokenDistribution)
3. Calculate 4 output amounts based on fee ratios
4. Build tx: fee_box → [bruno_out, lgd_out, josemi_out, order_out]
5. Verify box values ≥ 1.5 ERG each
6. Submit and sign
```

## Related Contracts

Based on the code structure and naming, this contract is part of the **BenefactionPlatform** (formerly referenced as "Bene Fundraising Platform"). Likely related contracts include:

- **Fundraising Campaign Contract**: Collects donations/pledges and routes fees to this dev fee box.
- **Campaign State Machine**: Manages campaign lifecycle (active → closed → distributing) and triggers fee collection.
- **Beneficiary Distribution Contract** (potential): May handle downstream distribution from beneficiary addresses to final recipients.

**Note**: The contract references "Phoenix HodlERG Fee" as its original inspiration, suggesting it adapted a fee-splitting pattern from the Phoenix protocol's vault mechanics.

---

## Security Considerations

- **Hardcoded Addresses**: Beneficiary addresses are baked into the ErgoTree at compile-time. Changes require recompilation and new contract deployment.
- **No Governance**: No upgrade mechanism; fee split ratios are immutable.
- **Minimum Box Value**: Enforces 5 ERG minimum, but individual outputs must each have ≥ 1.5 ERG; off-chain code must ensure this.
- **Token Filtering**: If R4 specifies a token ID but no matching tokens exist in outputs, the contract will assign 0 amounts; off-chain validation should prevent this state.