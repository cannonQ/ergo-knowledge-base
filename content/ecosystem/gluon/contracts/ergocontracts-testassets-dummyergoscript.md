---
title: StabilityNexus/Gluon-Ergo-Contracts — DummyErgoScript.es
description: "ErgoScript contract analysis: modules/gluonw-base/src/main/resources/ErgoContracts/TestAssets/DummyErgoScript.es"
tags: [stabilitynexus, gluon-ergo-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Gluon-Ergo-Contracts"
contract_file: modules/gluonw-base/src/main/resources/ErgoContracts/TestAssets/DummyErgoScript.es
project: stabilitynexus-gluon-ergo-contracts
---
# DummyErgoScript Contract Analysis

## Purpose

This is a minimal test contract that unconditionally validates any transaction attempting to spend its box. It serves as a placeholder for testing contract infrastructure, box creation, and transaction construction without enforcing any real spending conditions.

## Inputs / Outputs

**Inputs:**
- Any box protected by this contract's ErgoTree can be spent.
- No specific box structure or register requirements.

**Outputs:**
- No constraints on outputs produced by spending transactions.
- Any number of output boxes with any structure are permitted.

## Key Logic

The contract contains a single validation condition:

```
sigmaProp(true)
```

This evaluates to a **satisfied Sigma protocol statement** (a trivial tautology). Since `true` is a boolean constant that always evaluates to `true`, the `sigmaProp()` wrapper produces a **tautological proof obligation** that requires no cryptographic verification. Any transaction spending this box will pass validation unconditionally.

**In plain English:** "This box can be spent by anyone, under any circumstances, without proof."

## Registers Used

**None.** The contract does not reference any registers (R4–R9). It contains no state, counter, timestamp, or auxiliary data.

## Tokens

**None.** The contract does not authenticate, validate, or track Native tokens or NFTs. No Token ID rule constraints are enforced.

## Integration Pattern

**Off-chain construction:**
1. Create a box with this contract's ErgoTree as its guarding script.
2. Assign any value (in nanoERG) and optional tokens to the box.
3. To spend the box, construct a transaction that includes it as an input.
4. No special Context extension, witness data, or proof structure is required.

**Verification:**
- The ErgoScript context evaluator will reduce `sigmaProp(true)` to a satisfied `SigmaBoolean` without requiring Sigma protocol proofs.
- No off-chain signing, Ring signatures, or advanced cryptographic validation is needed.

## Related Contracts

**None identifiable.** This is a standalone test artifact with no composition references to other contracts in the StabilityNexus/Gluon-Ergo-Contracts project.

---

## Classification

| Aspect | Value |
|--------|-------|
| **Contract Type** | Trivial test script |
| **State Machine** | None (stateless) |
| **Multi-stage** | No |
| **Singleton/State NFT** | Not applicable |
| **Atomic swap capable** | No |
| **Production ready** | ❌ No |

---

## Security Note

⚠️ **This contract should never be used in production.** It provides no access control. Any funds locked in boxes protected by this script are accessible to all participants and offers no security guarantees.