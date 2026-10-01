---
title: "Two-Pass Contract Audit Methodology"
category: pattern
difficulty: advanced
tags: [ergoscript, audit, security, llm, two-pass, dual-pass, adjudication, severity]
author: CannonQ
source: original
license: AGPL-3.0
updated: 2026-10-01
---
# Two-Pass Contract Audit Methodology

A structured approach to auditing ErgoScript contracts using LLMs, developed through production audits on the Ergo Labs platform. The two-pass pattern significantly reduces false positives and catches issues that single-pass audits miss.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User Input                        │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ Contract          │  │ Description (optional)   │ │
│  │ Description       │  │ "What the contract       │ │
│  │                   │  │  should do"              │ │
│  └──────────────────┘  └──────────────────────────┘ │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              PASS 1: Initial Audit                   │
│                                                      │
│  System prompt includes:                             │
│  • ErgoScript context (known issues, patterns)       │
│  • LLM pitfall warnings (pre-calibration)            │
│                                                      │
│  Output:                                             │
│  • Contract explanation                              │
│  • Vulnerabilities (CRITICAL/HIGH/MEDIUM/LOW)        │
│  • Logic errors                                      │
│  • Best practice violations                          │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│           PASS 2: Verification Audit                 │
│                                                      │
│  Input: Original code + FULL Pass 1 output           │
│                                                      │
│  System prompt includes:                             │
│  • Same ErgoScript context                           │
│  • Instructions to verify Pass 1 findings            │
│  • Cross-reference against all checklists            │
│                                                      │
│  Output:                                             │
│  • Confirmed vulnerabilities                         │
│  • NEW issues found ("SECOND PASS FINDING")          │
│  • Removed false positives (with explanations)       │
│  • Rating from worst open finding, plus if-fixed     │
└─────────────────────────────────────────────────────┘
```

---

## Why Two Passes?

Single-pass LLM audits suffer from:
1. **False positives** — the LLM reports issues that don't exist (see LLM Pitfalls in the audit context reference)
2. **Missed issues** — the LLM focuses on obvious patterns and misses subtle vulnerabilities
3. **Inconsistent ratings** — severity assessments vary without cross-referencing

The second pass addresses all three by reviewing the first pass output against the contract code, known issues checklist, and LLM pitfall calibration data.

---

## Why Two *Independent* Pass 1 Runs on Fund-Holding Contracts

Pass 2 verifies Pass 1. It cannot recover a false negative that Pass 1 never raised. For any contract that holds or moves funds, run Pass 1 **twice, in two separate contexts, with the same pre-named traps and no sight of each other's output**, and only then run Pass 2 on the merged findings.

**What happened without it.** In the Dexy-stable engagement (September 2026), two auditors were given the same trap on the same LP cluster: can a non-LP box at input 0 with a genuine swap box satisfy `swap.es` and yield a gain? The auditor on `main.es`/`swap.es` composed the decoy layout and rated it HIGH. The auditor on `mint.es`/`redeem.es` **refuted the same trap**, arguing that singleton coupling forced the real pool to input 0. No such line exists in the source. The contradiction is what forced a manual read; the pool had already been drained on mainnet. A single Pass 1 assigned to mint and redeem would have declared the cluster clean, and Pass 2 would have verified that.

**Adjudication rule.** Any disagreement between the two runs is a mandatory adjudication, and the burden of proof is on whichever side said *safe*: it must cite the specific line that closes the attack, and the adjudicator verifies that line does what was claimed. If the line does not exist or does not close it, the finding stands at the severity the other run derived. An adjudication resolved as safe without a verified line is not permitted. Adjudication is decided from source; a landed transaction is corroboration, not the deciding evidence.

**In Claude Code** this is two subagents dispatched in parallel with the same prompt. **With any client**, it is two separate conversations. The tools cannot enforce independence; the caller's orchestration is what provides it. The full engagement structure around this (scope memo, value ledger, procedure checklist, workpapers, retest, sign-off) is the `contract-audit-engagement` skill.

---

## Pass 1: Initial Comprehensive Audit

The first pass performs a standard security audit with pre-calibration:

1. **Explain** what the contract does in simple terms
2. **Enumerate every spend path** of every value-holding box and run the debit-side procedures D-1..D-13 on each (see the Audit Program reference); state the reconciliation (inputs minus pinned outputs = residual, and who receives it)
3. **Return a verdict per pre-named trap** (T1..T19) with `file:line` either way; ABSENT without a cited line is not a verdict
4. **List findings** with severity derived from the matrix: magnitude class × likelihood class → cell, plus modifiers; deployment status as a separate field
5. **Identify logic errors** or potential bugs
6. **Check against secure patterns** (CommitReveal, PerpetualToken, MultiStage, etc.)
7. **Verify against all known issues** (13 categories — see Known ErgoScript Security Issues)
8. **Provide specific recommendations** with code fixes, and confirm the honest path still passes under each fix

Pass 1 gives no overall rating. The rating is produced once, at the end of Pass 2.

**Key:** The system prompt includes the LLM pitfall warnings BEFORE the first pass runs. This pre-calibration reduces (but does not eliminate) false positives in Pass 1 itself.

---

## Pass 2: Verification & Consolidation

The second pass receives both the original contract AND the complete Pass 1 output:

1. **Review Pass 1 findings** for accuracy
2. **Check for missed issues** — look for vulnerabilities Pass 1 didn't catch
3. **Cross-reference every finding** against:
   - eUTXO model principles
   - Secure patterns index
   - Known issues categories
   - LLM pitfall list
4. **Remove false positives** — explain WHY each was removed
5. **Look for subtle issues** specifically:
   - Hidden OR-branch bypasses
   - Subtle token preservation failures
   - Edge cases in HEIGHT comparisons
   - Data input manipulation vectors
   - Front-running opportunities
6. **Re-derive severity from the matrix** for every finding without reference to Pass 1's cell; log any difference as a ruling with the cell cited
7. **Produce final consolidated report** with the findings table (id, severity, deployment status, location, title, fix size), the KEY-RISK section separate from defects, and a "verified sound" section listing the traps found absent. The last line of the report is the rating line, `Rating: N/10. If fixed: should go to X-Y. Key risks: <ids or none>. Pending: <ids or none>.` The band is set by the worst open finding (rule in the tool's Pass 2 instructions)

---

## The Contract Description Field

The optional description field ("what the contract should do") enables **intent-based auditing**:

- Without description: the LLM can only check for generic security issues
- With description: the LLM can verify that the code actually implements the intended behavior, catching **logic bugs** where the code is secure but does the wrong thing

---

## Integration with EKB

When implementing this pattern as an MCP tool, the audit context should be dynamically assembled:

1. **Static context:** Known issues, secure patterns, LLM pitfalls, and the Audit Program (debit-side procedures, trap register, severity matrix) — always included in both passes so they test the same population and rate on the same scale
2. **Dynamic context:** Semantic search results from the EKB matching patterns found in the contract code (e.g., if the contract uses `HEIGHT`, pull timelock patterns; if it uses oracle data inputs, pull oracle authentication patterns)

This gives the auditing LLM both the calibration data and specific relevant reference material for the contract being audited.

---

## References

- Audit Program (procedures, traps, severity matrix) — `content/reference/ergoscript/audit-program.md`
- Contract Audit Engagement skill — `content/skills/contract-audit-engagement.md`
- Known ErgoScript Security Issues — `content/reference/ergoscript/known-issues.md`
- ErgoScript Audit Context (LLM Pitfalls) — `content/reference/ergoscript/audit-context.md`
- Ergo Labs implementation — `ergolabs.degens.world/contract-audit`
