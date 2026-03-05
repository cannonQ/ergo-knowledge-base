---
title: duckpools/lend-protocol-contracts — repay.md
description: "ErgoScript contract analysis: contracts/pools/Generic-Token-Pool/proxy-contracts/repay.md"
tags: [duckpools, lend-protocol-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/duckpools/lend-protocol-contracts"
contract_file: contracts/pools/Generic-Token-Pool/proxy-contracts/repay.md
project: duckpools-lend-protocol-contracts
---
# ErgoScript Contract Analysis: Repay Proxy

## Purpose

This contract serves as a **repayment proxy** in a lending protocol, enabling borrowers to either complete a loan repayment by depositing collateral into a borrower box, or to refund their locked funds if the repayment deadline passes. It acts as a gating mechanism that validates the legitimacy of repayment transactions or timeout-based refunds.

## Inputs / Outputs

### Inputs
- **SELF**: The proxy box containing:
  - Value: ERG amount (locked repayment collateral or refund funds)
  - R4: `Long` – the amount of collateral/value needed for repayment
  - R5: `Coll[Byte]` – the borrower's script bytes (contract address)
  - R6: `Int` – the deadline height for refund eligibility
  - Tokens: Any native tokens associated with the repayment obligation

### Outputs
**Two scenarios:**

1. **Successful Repayment Path** (OUTPUTS.size >= 3):
   - **OUTPUTS(0)**: Borrower box receiving collateral
     - Must match borrower's script
     - Must contain at least `neededAmount` ERG
     - Must reference SELF.id in R4 (multi-box spend safety)
   - **OUTPUTS(1+)**: Additional boxes (loan settlement, fee collection, etc.)

2. **Refund Path** (OUTPUTS.size < 3):
   - **OUTPUTS(0)**: Refund box sent back to borrower
     - Must match borrower's script
     - Must contain original value minus minimum transaction fee
     - Must preserve all tokens from SELF

## Key Logic

The contract enforces **two mutually exclusive transaction paths**:

```
IF transaction has 3+ outputs THEN
  ✓ Repayment mode: borrower receives collateral
    └─ Validate borrower box script matches stored borrower address
    └─ Validate borrower box receives sufficient value (≥ neededAmount)
    └─ Validate borrower box references this proxy in R4 (prevents double-spend via multi-box contracts)
    
ELSE (fewer than 3 outputs)
  ✓ Refund mode: return funds after deadline
    └─ Current block height (HEIGHT) must exceed deadline (R6)
    └─ Refund box script must match stored borrower address
    └─ Refund value must equal original value minus ~1 ERG (minTxFee)
    └─ All native tokens must be preserved in refund box
```

The **multi-box spend safety check** (`multiBoxSpendSafety`) prevents a single transaction from simultaneously spending multiple instances of this proxy contract by forcing each to reference the previous box's ID.

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | Repayment amount needed; in refund path, used to store SELF.id reference (multi-box safety) in the borrower box |
| **R5** | `Coll[Byte]` | Borrower's script bytes (contract address) – immutable reference to who receives funds |
| **R6** | `Int` | Deadline height (block number) – enables refund after this point |
| **Value** | `Long` | ERG amount being locked for repayment or refund |
| **Tokens** | Array | Native tokens tied to the repayment (must be preserved in refund) |

## Tokens

- **Input tokens**: Arbitrary native tokens attached to SELF are preserved and must be passed through to OUTPUTS(0) in the refund scenario
- **No singleton NFT**: This contract does not use a State NFT for identity; instead, it relies on script bytes matching for validation
- **Purpose**: Tokens track the repayment obligation or represent collateral types

## Integration Pattern

### Off-Chain Bot / Transaction Builder Responsibilities:

1. **Repayment Scenario**:
   - Construct a transaction with ≥3 outputs
   - Create OUTPUTS(0) as a borrower box with:
     - Script matching R5
     - Value ≥ R4 (neededAmount)
     - R4 set to SELF.id
   - Include loan settlement boxes in OUTPUTS(1+)
   - Sign with borrower's key

2. **Refund Scenario**:
   - Monitor blockchain height; trigger only when HEIGHT ≥ R6
   - Construct transaction with <3 outputs
   - Create OUTPUTS(0) refund box:
     - Script matching R5
     - Value = SELF.value - 1000000L (1 ERG minimum transaction fee)
     - Tokens copied from SELF
   - Off-chain code must track the proxy box's deadline and initiate refund after expiry

3. **Context Requirements**:
   - No Context extension data required
   - Relies on blockchain state (HEIGHT) for deadline validation

## Related Contracts

From the file path `contracts/pools/Generic-Token-Pool/proxy-contracts/repay.md`, this likely integrates with:

- **Loan/Borrow contract**: Likely creates this proxy box with repayment terms
- **Lending pool contract**: Receives repayment through OUTPUTS(1+) in the successful path
- **Borrower contract**: Referenced by script bytes in R5; may validate incoming collateral
- **Other proxy contracts** (in the same `proxy-contracts/` directory): Probably handle deposit, withdraw, or liquidation flows

---

### Design Pattern Notes

This is a **multi-stage contract** operating as a **state machine proxy**:
- **Stage 1** (Pending): Proxy holds locked funds awaiting repayment
- **Stage 2a** (Repay): Transitions funds to borrower box upon valid collateral proof
- **Stage 2b** (Timeout): Enables refund after deadline expires

The **multi-box spend safety** mechanism is crucial for batching operations while preventing replay attacks across multiple proxy instances.