---
title: "Known ErgoScript Security Issues"
category: reference
difficulty: intermediate
tags: [ergoscript, security, audit, vulnerabilities]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Context/blob/main/context.md"
updated: 2026-10-01
---
# Known ErgoScript Security Issues

A checklist of known vulnerability categories for ErgoScript smart contracts. Use this when designing or auditing contracts to verify all logic against historical and theoretical flaws.

---

## Vulnerability Categories

### 1. Unvalidated Data Inputs

Data inputs are read-only references consumed without being spent. If the contract does not verify the authenticity of a data input (e.g., checking for a specific NFT or known box ID), an attacker can substitute a malicious box with crafted register values.

A script-hash (ErgoTree) match on a data input proves which script guards the box. It does not prove who created the box or who wrote its registers: anyone can send a hand-built box with arbitrary registers to any script address. This narrows the Audit Program's D-3 and T1, which accept a script-hash pin: for a box whose registers are read, a script hash closes the slot for the script only, not for the register values.

**Mitigation:** Authenticate a data input whose registers you read by a protocol-controlled singleton NFT, or by a known box ID. A script-hash pin alone is a finding when the registers feed a price, an amount, a payee or a branch choice.

### 2. Token Loss / Unpreserved Tokens

Tokens must be explicitly accounted for in all OUTPUTS. If a contract spends a box containing tokens but does not enforce their presence in outputs, tokens can be permanently lost or stolen.

**Mitigation:** Put the tokens in an output whose script, token ID and amount are all checked, and bind that output to this input. Pinning the output by index does not bind it: two boxes of the same script that both check `OUTPUTS(0)` are both satisfied by one output, and the builder keeps the second box's tokens. `OUTPUTS.exists(...)` has the same gap. Use a binding from #10 (write `SELF.id` into the output and check it, pin `SELF` to an input index, or sum over all inputs that share the script). A true one-unit singleton cannot sit in two inputs, so for it the index pin alone is enough.

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

A height that the transaction builder writes (a deadline or start height in a register, or a box's creation height) is only as tight as the bounds the script puts on it. A one-sided bound lets the builder backdate a window or push a deadline far into the future. Bound it on both sides relative to `HEIGHT` (for example `unlock >= HEIGHT + n && unlock <= HEIGHT + n + slack`).

### 8. Cyclic Script Hash Dependencies

If contract A's ErgoTree references contract B's hash, and contract B references contract A's hash, neither can be deployed — a chicken-and-egg problem.

**Mitigation:** Use singleton NFTs for identity rather than script hash comparisons. Or use a factory pattern where one contract is deployed first and its hash is embedded in the second.

### 9. Scripts Too Complex Hitting Cost Limit

ErgoScript evaluation has a JIT cost budget. Complex scripts with deep nesting, large `fold` operations, or extensive collection manipulation can exceed the cost limit and fail to execute.

**Mitigation:** Keep scripts efficient. Profile JIT costs during testing. Break complex logic across multiple contract stages if needed.

### 10. One Output Satisfying Several Inputs (Shared Output / Shared Payee)

Every input's script is evaluated on its own. If a spend path identifies its payout only by who is paid plus `>=` its own amount, or by output position, or by `OUTPUTS.exists`, then one output satisfies every input that makes the same check. The builder co-spends several boxes in one transaction, pays the largest claim once, and keeps the rest.

Example: two boxes both require "an output to address P with value >= `SELF.value`".

| Slot | Content |
|------|---------|
| Input 0 | box A, 100 ERG |
| Input 1 | box B, 80 ERG |
| Output 0 | P, 100 ERG |
| Output 1 | builder, 80 ERG |

Box A passes (100 >= 100). Box B passes (100 >= 80). With N boxes the builder keeps everything except the largest.

Shapes to check:

- The same script in several boxes.
- Several branches of one script reading the same output.
- Two different scripts that accept the same output (for example a refund and a repayment that pay the same user).
- Another script's branch that accepts this box as a co-input.
- A fixed new version co-spent beside a still-live older version that pays the same address.
- A "singleton" NFT minted in more than one unit, so two boxes can both be "the" box.

The shared payee is the attack surface, not the single contract. Review every script, version and product that pays the same address together.

**Mitigation:** In order of strength:

1. Write `SELF.id` into the payout output (for example in R4) and check it. Each input bound this way needs its own output, so several boxes can still be spent in one transaction. It holds between all scripts that use the same binding in the same register.
2. Pin the input index (`SELF.id == INPUTS(0).id`). Only one such box fits in a transaction. It holds between scripts that pin the same index.
3. Sum over all inputs that share the script and require the output to cover the sum. This covers the same script only.
4. Give each version or product its own payee address. This is operational, and it removes only the cross-version and cross-product cases.

None of 1 to 3 protects a script that has no binding. A box whose script only checks the payee and `>=` its own amount can still be spent beside a bound box and be satisfied by that box's output, and its value goes to the builder. For boxes already deployed without a binding, no new script protects them: option 4 keeps new outputs from paying them off, but two old boxes that pay the same address can still be swept together. Spending the old boxes is the only full protection.

The question an auditor must answer: which other script, in any version or protocol, pays this same address, and what stops one output from satisfying both?

### 11. Positional Trust (Decoy Input or Output)

A script that treats `INPUTS(i)`, `OUTPUTS(i)` or a data input at a fixed index as "the pool box" or "the bank box" without checking its identity lets the builder put a different box in that position. The decoy carries whatever values make the arithmetic pass, with or without the real box elsewhere in the transaction.

**Mitigation:** Check the singleton NFT of every box read by position, and where a specific script is expected, check the script too. Do this in every script that reads the box. Do not rely on another contract's check unless that contract's box is itself proven to be in the transaction.

### 12. Unpinned Residual Goes to the Builder

A script constrains only the outputs it names. Any value or token in the inputs that no checked output is required to hold goes wherever the transaction builder sends it. Checks written as `>=` on one output, or that pin some outputs but not the total, leave a residual.

**Mitigation:** For every spend path write the reconciliation: inputs minus pinned outputs equals the residual, and state who receives it. A residual from the protocol's inputs that goes to an arbitrary builder is a finding unless it is bounded and intended (a stated keeper reward, the miner fee).

### 13. Context-Variable Collections Without Distinctness

A collection supplied by the builder through `getVar` (keys, indexes, box IDs) is attacker-chosen. Passing it to `getMany` returns a repeated key repeatedly, so a per-entry sum, count or payout can be satisfied several times by one real entry.

**Mitigation:** Require the collection to be distinct (for example strictly increasing) before using it for a sum, a count or a payout.

---

## Secure Design Patterns

| Pattern | Description |
|---------|-------------|
| **CommitReveal** | Hash commitment in stage 1, reveal in stage 2 |
| **PerpetualToken** | Enforce token preservation in an output with script match and exact token ID and amount, bound to this input (see #10). An output-index pin or `OUTPUTS.exists(...)` without a binding is the vulnerable form, unless the token is a one-unit singleton |
| **MultiStage Workflow** | Validate next state via `OUTPUT.propositionBytes.blake2b256 == expected_hash` |
| **Multisig** | Use `sigmaProp(pkA && pkB)` or `atLeast(n, keys)` |
| **EmergencyRefund** | Use `HEIGHT > timeout && ownerKey` for stuck-fund recovery |
| **StateContinuation** | Require next box to preserve registers and tokens |
| **OracleAuth** | Require oracle NFT or expected box ID for price/data feeds |
| **ExclusiveOutput** | Write `SELF.id` into the payout output and check it, so each input needs its own output (see #10) |
