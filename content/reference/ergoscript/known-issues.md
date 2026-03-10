---
title: "Known ErgoScript Security Issues"
category: reference
difficulty: intermediate
tags: [ergoscript, security, audit, vulnerabilities]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Context/blob/main/context.md"
updated: 2026-03-09
---
# Known ErgoScript Security Issues

A checklist of known vulnerability categories for ErgoScript smart contracts. Use this when designing or auditing contracts to verify all logic against historical and theoretical flaws.

---

## Vulnerability Categories

### 1. Unvalidated Data Inputs

Data inputs are read-only references consumed without being spent. If the contract does not verify the authenticity of a data input (e.g., checking for a specific NFT or known box ID), an attacker can substitute a malicious box with crafted register values.

**Mitigation:** Always verify data input identity via singleton NFT, expected ErgoTree hash, or known box ID.

### 2. Token Loss / Unpreserved Tokens

Tokens must be explicitly accounted for in all OUTPUTS. If a contract spends a box containing tokens but does not enforce their presence in outputs, tokens can be permanently lost or stolen.

**Mitigation:** Use `OUTPUTS.exists(...)` checks to enforce token preservation. Verify both token ID and quantity.

### 3. OR-Branch Bypass Paths

OR conditions (`||`) in spending logic can create unintended spending paths. An attacker may satisfy one branch of an OR condition that the contract designer did not intend to be independently spendable.

**Mitigation:** Audit each branch of every OR condition independently. Ensure no branch provides an unintended escape route.

### 4. Missing Signature Requirements

Contracts that do not properly gate spending with signature verification can be spent by anyone.

**Mitigation:** Use `sigmaProp(proveDlog(...))` or `atLeast(n, Coll(...))` patterns. Verify signature requirements on all spending paths.

### 5. Point-at-Infinity / Sigma-Protocol Edge Cases

The point at infinity in elliptic curve cryptography can create edge cases in Sigma protocol operations. A `GroupElement` that is the identity element can make `proveDlog` trivially satisfiable.

**Mitigation:** Validate `GroupElement` values stored in registers. Be cautious with cryptographic operations on untrusted inputs.

### 6. Missing Commit-Reveal (Front-Running)

If a contract reveals sensitive information (e.g., a secret value or decision) in the spending transaction itself, miners or observers can front-run the transaction by seeing it in the mempool.

**Mitigation:** Use the CommitReveal pattern — hash the commitment in stage 1, reveal in stage 2 in a separate transaction.

### 7. Incorrect HEIGHT Comparisons

Block HEIGHT logic is susceptible to off-by-one errors and mempool timing issues. Ergo's `CleanupWorker` re-validates mempool transactions against the new HEIGHT when a block arrives, which can cause HEIGHT-dependent scripts to fail if the tolerance window is too tight.

**Mitigation:** Use tolerance windows (e.g., `±10` blocks rather than `±1`) for HEIGHT comparisons. See the Plasma-AVL Phase 2.4-2.6 patterns for a detailed case study.

### 8. Cyclic Script Hash Dependencies

If contract A's ErgoTree references contract B's hash, and contract B references contract A's hash, neither can be deployed — a chicken-and-egg problem.

**Mitigation:** Use singleton NFTs for identity rather than script hash comparisons. Or use a factory pattern where one contract is deployed first and its hash is embedded in the second.

### 9. Scripts Too Complex Hitting Cost Limit

ErgoScript evaluation has a JIT cost budget. Complex scripts with deep nesting, large `fold` operations, or extensive collection manipulation can exceed the cost limit and fail to execute.

**Mitigation:** Keep scripts efficient. Profile JIT costs during testing. Break complex logic across multiple contract stages if needed.

---

## Secure Design Patterns

| Pattern | Description |
|---------|-------------|
| **CommitReveal** | Hash commitment in stage 1, reveal in stage 2 |
| **PerpetualToken** | Enforce token preservation via `OUTPUTS.exists(...)` + script hash match |
| **MultiStage Workflow** | Validate next state via `OUTPUT.propositionBytes.blake2b256 == expected_hash` |
| **Multisig** | Use `sigmaProp(pkA && pkB)` or `atLeast(n, keys)` |
| **EmergencyRefund** | Use `HEIGHT > timeout && ownerKey` for stuck-fund recovery |
| **StateContinuation** | Require next box to preserve registers and tokens |
| **OracleAuth** | Require oracle NFT or expected box ID for price/data feeds |
