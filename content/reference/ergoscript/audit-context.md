---
title: "ErgoScript Audit Context — LLM Pitfalls & Calibration"
category: reference
difficulty: advanced
tags: [ergoscript, audit, llm, security, calibration]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Context/blob/main/context.md"
updated: 2026-03-09
---
# ErgoScript Audit Context — LLM Pitfalls & Calibration

When using LLMs to audit ErgoScript contracts, specific failure patterns emerge consistently. This reference documents observed pitfalls from real audits (including a human-reviewed LLM audit of the GluonW contracts) and provides calibration guidance.

---

## Observed LLM Audit Pitfalls

### 1. Indirect Token ID Checks

LLMs frequently miss that a token ID check exists when the token is referenced indirectly — for example, inside a tuple like `oracleBoxPoolNFT` or via a register lookup. The LLM reports "no token ID verification" when verification is actually present through a different code path.

**Before reporting:** Trace all references to the token through tuples, register lookups, and helper values.

### 2. Over-Recommending Identity Checks

LLMs tend to recommend additional identity checks (e.g., verifying ErgoTree bytes) when a singleton NFT already uniquely identifies the box. In common Ergo patterns, a box containing a specific singleton NFT cannot be faked — the NFT IS the identity.

**Before reporting:** Check if the box is already authenticated by a singleton NFT. If so, additional ErgoTree verification is redundant.

### 3. Missing Contextual Cancellation / Invariants

LLMs produce valid-sounding findings but miss that apparent issues are cancelled out by invariants. Examples:
- `_MinFee` appears on both input and output sides, so it cancels out and is not an attack vector
- A singleton token amount is known to be exactly 1 for a referenced box, so quantity checks are unnecessary

**Before reporting:** Check if the finding is neutralized by a matching constraint on the other side of the transaction.

### 4. Type Constraint Blind Spots

LLMs flag type issues (e.g., `Long` to `Int` downcast) without accounting for ErgoScript's type system constraints. For example, `Coll[]` indexing requires `Int`, making a `Long→Int` downcast unavoidable and expected — not a bug.

**Before reporting:** Verify whether the type conversion is required by ErgoScript's type system.

### 5. False-Flagging Bounded Numerics

LLMs flag theoretical numeric truncation or overflow issues without considering that the values are bounded by fixed constants. For example, flagging overflow on a variable that can only range 0–14 (because `BUCKETS = 14`).

**Before reporting:** Check if the values involved have fixed upper bounds that make overflow impossible.

### 6. Missing Optimization Tradeoffs

LLMs miss that some patterns are intentional design choices:
- `&&` can produce smaller ErgoTree than `allOf()` — this is a valid optimization, not a code smell
- `getVar` is off-chain supplied and may be intentionally flexible to support multiple UIs/backends

**Before reporting:** Consider whether the pattern is an intentional tradeoff rather than a mistake.

---

## How to Use Audit Findings

1. **Treat LLM audit findings as hypotheses** — verify each against the ErgoScript Language Specification (LangSpec) and the actual on-chain constraints.

2. **Test off-chain assumptions** — when a finding depends on off-chain transaction construction, explicitly ask: "Can a different backend construct a transaction that violates this assumption while still satisfying the script?"

3. **Call out uncertainty** — when in doubt, flag findings as "potential" rather than "confirmed." State the conditions under which the finding would be exploitable.

4. **Cross-reference against known issues** — check each finding against the Known ErgoScript Security Issues checklist to ensure completeness.

---

## Agent Behavior Rules for Auditing

When auditing ErgoScript contracts:

1. Verify **all spend paths** — enumerate every branch in the script's boolean logic
2. Check **invariants across state transitions** — verify that state changes maintain protocol rules
3. Verify **token and ERG conservation** — all value must be accounted for in OUTPUTS
4. Validate **signature gating** — ensure proper authentication on all spending paths
5. Ensure **predictable HEIGHT usage** — check for off-by-one errors and mempool tolerance
6. Detect **OR-branch bypasses** — test each OR branch independently for unintended spending
7. Check for **front-running vulnerabilities** — identify where sensitive data is revealed in the spending transaction
8. Verify **data input validation** — ensure data inputs are authenticated, not just assumed
