---
title: "ErgoScript Audit Context — LLM Pitfalls & Calibration"
category: reference
difficulty: advanced
tags: [ergoscript, audit, llm, security, calibration, semantics, probes]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Context/blob/main/context.md"
updated: 2026-10-01
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
- `getVar` being builder-supplied is by design and not a finding in itself

`getVar` IS a finding when the value feeds a payee, an amount, a branch choice, or a collection used for a sum, count or payout (see Known Issues #13), because that value is chosen by whoever builds the transaction.

**Before reporting:** Consider whether the pattern is an intentional tradeoff rather than a mistake. For `getVar`, check what the value feeds before dismissing it.

---

## Settled Semantics (empirical, do not re-derive)

Settled on a fleet-sdk MockChain harness (fleet-sdk 0.12.0, sigmastate-js 0.4.6) during audit
engagements in September and October 2026. These are probe results, not inferences, and
each has already flipped at least one real finding's verdict.

**Arithmetic and indexing fail closed, they do not fail open.**

- An out-of-range `Coll` index (`box.tokens(i)` where `i >= tokens.size`) THROWS whenever it is
  evaluated, and the whole script fails. A `tokens.size >= n` guard makes the same script pass.
  `getOrElse` returns the default. Whether a read inside a branch that is not taken is evaluated
  at all is covered in the next section.
- `Long * Int` and `Long * Long` overflow THROW ("long overflow"). The same product taken
  `.toBigInt` first does not overflow.
- `BigInt` division by zero THROWS ("BigInteger divide by zero").

Consequence: a finding whose impact depends on one of these silently producing a wrong value
is wrong as written. The transaction does not exist. Rate the denial of service, not the theft.

**`getOrElse` on a register rescues only the ABSENT register.**

`box.R4[Int].getOrElse(0)` against a box whose R4 is present but of another type THROWS
("Cannot getReg[Int](4): invalid type of value ... at id=4"). The default is supplied for
`None` only.

- A "fails open to the default" finding against a wrong-typed register is therefore usually
  WRONG: the read fails closed instead.
- A box whose own script reads `R4[Int]` unconditionally is UNSPENDABLE BY ANYONE if its R4 is
  wrong-typed. That is a full shield and it is worth crediting before rating a dependent
  contract's register read.
- A refund arm's reachability must be argued from who controls the box layout, not from the
  read being throw-safe.

**The interpreter runs the compiled tree, not the source: branches that are not taken are not evaluated, hoisted definitions always are.**

A failing read fails the script only if the tree evaluates it. An out-of-range `Coll` index and a wrongly typed register read behave the same way in every case below. An earlier version of this page said that an untaken `if` arm throws. That was wrong.

1. Not evaluated unless reached: the arms of an `if`, the right-hand side of `&&` and `||`, and the body of a function (`def` or lambda). A failing read there does not fail the script when the branch is not taken. This holds whether the condition is a run-time value or a constant, and with constant segregation on or off.
2. Always evaluated: a definition the compiler places at the top of the script. It runs on every spend, whether or not any use of it is reached. What the compiler places there:
   - a `val` declared outside the branches and used in two or more places that are not reached together (two `if` arms; an `if` arm and a `||` right-hand side; the two sides of an `&&` inside one arm) is hoisted and always runs;
   - a `val` used once is moved into its use, so it runs only if that branch does;
   - a `val` declared inside an arm stays in the arm;
   - a `val` that is never used is dropped from the tree;
   - the same read written inline in each arm (no shared `val`) stays in each arm.
3. Only the hoisted part runs. With `val o = box.R4[Int]` hoisted, a wrongly typed R4 throws and an absent R4 does not (the `.get` stays in the arm). With `val r = box.R4[Int].get` hoisted, both throw.
4. `anyOf(Coll(...))` and `allOf(Coll(...))` evaluate every element. They do not short-circuit; `||` and `&&` do.
5. To settle a real contract, read its compiled tree or probe it. The source alone does not say where a multi-use `val` lands. One observed exception: a `val` declared outside and used on both sides of an `&&` inside one arm, each time through the same sub-expression, stayed in the arm.

What it changes for audit work:

- "The transaction cannot exist because a read in another arm throws" is not a valid reason to close an attack. "This path is dead because another arm's read throws" is not a valid liveness finding. Both need the read to be shown to sit in a top-level definition of the compiled tree.
- The real hazard runs the other way: a multi-use `val` over an output or data-input read makes every path depend on that box's shape, including refund and owner paths that never use the value.
- `anyOf` and `allOf` over a `Coll` give no guard ordering.

Limits: MockChain only; fleet-sdk 0.12.0, sigmastate-js 0.4.6; tree versions 0 and 1. A deployed tree may come from another compiler version, so read the compiled tree or probe it.

**`getMany` returns a repeated key repeatedly.** A collection taken from a context variable
and passed to `getMany` without a distinctness check yields duplicate entries, so a per-entry
sum or payout can be satisfied more than once by one real entry. This is the origin of trap T8.

**Two harness caveats, so a clean probe is not mistaken for a safe contract.**

- A MockChain PASS does not prove node validity on value. MockChain does not enforce the node's
  min-value-per-byte rule: an output of 59,999 nanoERG executes there although a token-free
  P2PK box needs about 60,000. Confirm with the node's `POST /transactions/check`, or compute
  the minimum from the serialized size.
- `TransactionBuilder.from([...])` runs an input selector that SILENTLY DROPS listed inputs the
  outputs do not need, so a script box may never be spent and every script appears to pass,
  including `sigmaProp(false)`. Pass `{ ensureInclusion: true }` and assert `tx.inputs.length`
  before trusting any probe result.

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
9. Check **output exclusivity** — for every output a spend path checks, ask what binds it to this input alone, and which other script, version or product pays the same address (Known Issues #10)
