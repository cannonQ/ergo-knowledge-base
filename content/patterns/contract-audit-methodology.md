---
title: "Two-Pass Contract Audit Methodology"
category: pattern
difficulty: advanced
tags: [ergoscript, audit, security, llm, two-pass]
author: CannonQ
source: original
license: AGPL-3.0
updated: 2026-03-09
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
│  • Security rating (1-10)                            │
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
│  • Final consolidated security rating                │
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

## Pass 1: Initial Comprehensive Audit

The first pass performs a standard security audit with pre-calibration:

1. **Explain** what the contract does in simple terms
2. **List vulnerabilities** found (with severity: CRITICAL, HIGH, MEDIUM, LOW)
3. **Identify logic errors** or potential bugs
4. **Check against secure patterns** (CommitReveal, PerpetualToken, MultiStage, etc.)
5. **Verify against all known issues** (9 categories — see Known ErgoScript Security Issues)
6. **Provide specific recommendations** with code fixes
7. **Rate overall security** (1-10)

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
6. **Produce final consolidated report** with adjusted security rating

---

## The Contract Description Field

The optional description field ("what the contract should do") enables **intent-based auditing**:

- Without description: the LLM can only check for generic security issues
- With description: the LLM can verify that the code actually implements the intended behavior, catching **logic bugs** where the code is secure but does the wrong thing

---

## Integration with EKB

When implementing this pattern as an MCP tool, the audit context should be dynamically assembled:

1. **Static context:** Known issues, secure patterns, LLM pitfalls (always included)
2. **Dynamic context:** Semantic search results from the EKB matching patterns found in the contract code (e.g., if the contract uses `HEIGHT`, pull timelock patterns; if it uses oracle data inputs, pull oracle authentication patterns)

This gives the auditing LLM both the calibration data and specific relevant reference material for the contract being audited.

---

## References

- Known ErgoScript Security Issues — `content/reference/ergoscript/known-issues.md`
- ErgoScript Audit Context (LLM Pitfalls) — `content/reference/ergoscript/audit-context.md`
- Ergo Labs implementation — `ergolabs.degens.world/contract-audit`
