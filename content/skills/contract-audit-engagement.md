---
title: "Contract Audit Engagement — Financial-Audit Method for eUTXO Contracts"
description: "End-to-end method for auditing ErgoScript contract sets the way a financial audit is run: scope memo, value ledger of every spend path, fixed procedure checklist, two independent passes with burden-on-safe adjudication, severity matrix set before fieldwork, workpapers, management letter, retest, sign-off. Calibrated on the Dexy-stable and Lithos-Client engagements."
tags: [ergoscript, audit, security, engagement, methodology, workpapers, severity, dual-pass, debit-side]
category: skill
difficulty: advanced
sdk: [none]
author: CannonQ
source: original
license: AGPL-3.0
updated: 2026-09-08
---
# Contract Audit Engagement

## Context

Most LLM contract audits are a single read of a single file that produces a list.
Coverage is whatever the model happened to look at, severity is whatever it felt like,
and there is no record of what was *not* tested. A financial audit is organised the
opposite way: the population is enumerated before testing, the procedures are fixed
before fieldwork, materiality is set before anyone looks at a number, every conclusion
points at a workpaper, and the engagement is not over until management has responded
and the fixes have been retested.

This skill is that structure applied to eUTXO contracts. It was built from two real
engagements on Ergo in September 2026:

- **Dexy-stable** (18 contracts), during which a live mainnet drain of the LP pools
  (~288k ERG) was found from source, and where two auditors given the same trap on
  the same cluster returned opposite verdicts.
- **Lithos-Client** (28 contracts), a developer-requested pre-launch review that
  produced 2 HIGH, 3 MEDIUM, and 2 KEY-RISK findings.

Across both, all sixteen CRITICAL, HIGH, and MEDIUM findings were caught by the
debit-side or entity-level procedures below. None needed a credit-side procedure.

The compact checklist, trap register, and severity matrix live in the EKB reference
`audit-program` and are injected into every `audit_contract` / `audit_verify` call.
This skill is the engagement around them.

---

## 0. If you are not an auditor

| Audit term | Plain meaning here |
|---|---|
| Assertion | The property a test checks (input genuine, every path covered, amount right, timing not gameable, right key, right branch, docs match code) |
| Population | Everything that must be tested: every (box, spend path) pair |
| Materiality / severity matrix | The severity scale, fixed before anyone reads code so it cannot drift per finding |
| Vouching | Tracing a value movement to the line that authorises it |
| Management representations | What the developer states the protocol assumes: initial state, invariants, who is honest, what is deliberately unchecked |
| Compensating control | When a check is absent, the other thing that stops the bad outcome |
| Workpaper | The evidence file a conclusion points at |
| Concurring review | A second reviewer whose job is to break your finding |
| Fraud risk assessment | Who has an incentive to exploit a hole, not just whether it exists |

## 1. The one idea: audit the debit side

A financial auditor vouches every disbursement and confirms every cash balance,
because that is where value moves. Credits follow if the debits are right.

In eUTXO the debit side is every *spend* of a contract-guarded box. The script is the
only approval control over that spend. So the population under audit is every
(box, spend path) pair, and each one gets the five cheque questions: who approved it,
who is the payee, is the amount right, does it reconcile, was it recorded so it cannot
be paid twice.

**The reconciliation.** ERG is conserved per transaction. For every spend path:

```
value in (all inputs the path admits)
  - value pinned to specific outputs by the script
  = residual  →  goes to whoever builds the transaction
```

An unbounded residual is an unsupported disbursement, whatever the path's intent. Two
of the sixteen serious findings were visible from this column alone.

**Assertion crosswalk.** Every finding names the financial-statement assertion it
violates, so the report and the workpapers share one vocabulary:

| Assertion | eUTXO meaning | Example |
|---|---|---|
| Existence | The input the script relies on is the genuine one; each claim paid corresponds to exactly one real entry | Dexy decoy input; Lithos duplicate keys paid *n* times |
| Completeness | Every spend path enumerated; every output that must be constrained is; every required state update happens | Missing AVL `remove` on a terminal path; unpinned co-input |
| Accuracy | Rounding, overflow, unit mismatch, sum conservation | Overflow reliance |
| Cutoff | Height and time windows cannot be shrunk, moved, or backdated | Late transform backdates a period |
| Rights & Obligations | Who can spend; who can change config | Single-PK whitelist |
| Classification | The builder cannot force a branch other than the one intended | Op byte unread; selector flipped by an inflated sum |
| Presentation | Comments, UI, and off-chain code match what the script enforces | Header claims a check the code lacks |

**Segregation of duties.** One key that can both approve and disburse is the classic
material weakness. Here it is a single PK over a whitelist, config box, or oracle.
Report these as **KEY-RISK**, in their own section, not in the defect table.

**Assumptions and omissions.** Every protocol works under assumptions about initial
state, invariants, actors, and off-chain parties. Some are enforced by a line; some
hold only because the developer expects them to. They are obtained from the developer
before fieldwork (the way an auditor obtains management's representations) and
verified into a register. Fieldwork tests inside them first, which is what separates a
real exploit from one that needs an assumption to fail, and then with each
easy-to-fail row removed. In eUTXO every check a script does *not* make is a decision:
intentional omissions go in the register with the developer's reason, and the reason
is verified against the code.

**Incentives.** Auditors assess fraud risk from pressure, opportunity, and
rationalisation. Code review finds opportunity only. A profitable hole will be used by
rational actors, whose population is everyone; the likelihood axis of the matrix is the
**actor threshold**: how many actors, of what kind, must deviate. One anonymous actor
is the lowest bar. A design whose rational move harms the protocol is a finding on the
same matrix as a code defect.

**The contracts are not the whole system.** A user signs what a builder constructed
and a frontend displayed. Builders and frontend are in scope by default when a UI
exists; scoping them out is a recorded decision.

**Review, not audit — name it honestly.** This method produces a *review* unless every
contract received the full per-contract treatment (the EKB two-pass tool included,
nothing truncated). Title the deliverable a review, head the summary "Summary" not
"Opinion", and give a coverage sentence stating what each contract received and any
tool degradation (a cluster that overflowed an input, a probe that could not settle a
semantics question, a file read only statically). When the claim and the work diverge,
the claim moves down to meet the work.

---

## 2. Engagement lifecycle

```
00 Engagement   scope memo: commit, contracts, instances, recipient, deadline, type;
                developer questionnaire sent; off-chain scope decided
01 Walkthrough  interaction map: boxes, tokens, who spends what
01b Assumptions the developer's representations, verified: initial state, invariants,
                actors, off-chain, intentional omissions; ranked by how easily they fail
02 Value ledger the debit-side register: every box × every spend path
03 Fieldwork    procedure checklist per spend path, from source only, inside the
                assumptions then with each removed; two independent passes on every
                fund-holding contract; incentive (G) and off-chain (B) procedures
04 Adjudicate   every dual-pass disagreement, burden on the side that said safe;
                then an independent falsification pass on every HIGH/MEDIUM
05 Report       management letter to the developer
06 Response     developer replies logged per finding
07 Retest       re-run the specific procedure against the fix commit
08 Sign-off     opinion, open items, subsequent-events caveat
```

Nothing in Phase 3 starts until the memo and the value ledger exist. Nothing is
reported that does not point at a workpaper.

### Phase 0 · Engagement memo

| # | Do |
|---|---|
| 0.1 | Pin the commit. Record hash, branch, upstream relation, and `sha256` of every in-scope file. |
| 0.2 | List in-scope contracts by file. List explicitly what is out (builders, UI, tests, legacy fixtures). |
| 0.3 | Name the report recipient, the deadline, and whether the engagement is developer-requested or independent. |
| 0.4 | Record the engagement **type**: pre-deployment, review of a deployed system, or incident. Only the last two use any chain procedure (E-1b, E-6). |
| 0.5 | List every **instance** of the contract set (DexyGold, USE, …) with its constants source and, if deployed, value held. All in scope at equal rigour unless excluded here. |
| 0.6 | Confirm the severity matrix applies unchanged. Any project-specific adjustment is written here, before fieldwork, with a reason. |
| 0.7 | List the tooling available (EKB audit tools, compiler, MockChain, node). A procedure that needs absent tooling is N/A with that reason, never quietly downgraded. |
| 0.8 | Copy the trap register from `audit-program` and add any traps specific to this engagement. Every fieldwork agent returns a verdict per trap per contract. |
| 0.9 | **Send the developer questionnaire** (below). Answers seed the assumptions register. Do not wait for it to start the walkthrough; do wait, or infer and mark inferred, before fieldwork. |
| 0.10 | **Decide off-chain scope.** Builders and frontend in scope by default when a UI exists; record the decision and the paths. |
| 0.11 | **Write the engagement letter.** One page to the developer, sent with the questionnaire: what is reviewed and at which commit, how, what they will get, what is needed from them (answers, permission to run tests, a contact), what happens after the report, disclosure terms (findings private first; they decide public release), what the review is not, timing. Derived from the memo but never the memo: the memo carries house rules, the tooling table, and the trap register, and stays internal. |

**Developer questionnaire.** (1) Initial state: what must be true of genesis boxes,
supplies, tree parameters, spare-token holders. (2) Invariants: what stays true across
every transaction, and which line enforces each. (3) Actors: who is assumed honest and
in what proportion; what a rational participant does on each path; who is paid to
keep, liquidate, challenge, reset, and how much. (4) Off-chain: what keepers, oracles,
or parameters must keep doing; what happens if they stop. (5) Intentional omissions:
which checks were left out, why, and what closes each instead. (6) Known sharp edges:
what looks like a bug but is not; what looks minor but is dangerous. (7) Deployment:
which instances exist or are planned and which holds the most value.

### Phase 1 · Walkthrough

Inventory every box type (script, identifying NFT, registers), every token (minted,
held, burned where), every cross-contract read (data input) and co-spend (input) with
how the counterparty is identified, the lifecycle of each value-holding box from
creation to terminal spend, every admin key and config box, and every off-chain
assumption the contracts depend on.

The cluster is the interaction lens and it comes first on purpose: a per-contract EKB call cannot see dependencies, trust edges, or a spend of A that only makes sense given B. The map produces, per contract, a short hand-forward list (dependencies, trust edges, cluster-surfaced things to check) carried into that contract's per-contract EKB call and its Phase 3 brief, so the deep pass verifies what the cluster found rather than re-deriving it.

Phase 1 maps. It does not audit. Suspected issues go in a "candidate findings" list
with `file:line` and are proven or dropped in Phase 3.

### Phase 1b · Assumptions register

One row per assumption, five kinds: initial state, invariant, actor, off-chain,
intentional omission. Columns: id, kind, assumption, stated by (`questionnaire` /
`docs (path)` / `header` / `inferred (code)`; docs and header are the developer's
written representations and count as documented intent),
enforced by (`file:line`) or **unenforced**, compensating control, what breaks if it
fails, fails with (one actor / k actors / proportion / honest liveness failure / never
without a code change), dependent findings. Every developer representation and every
trust edge from the walkthrough becomes a row. An unenforced row with no compensating
control is a candidate finding before fieldwork. Each intentional omission's reason is
verified against the code. Rows are ranked by how easily they fail; one-actor rows are
tested first.

### Phase 2 · Value ledger

One row per (box, spend path). If a path is not in the ledger it was not audited.

| Column | Content |
|---|---|
| VL | Row id |
| Box (contract) | |
| Assets held | ERG, tokens, by register or claim |
| Spend path | Branch or op byte; terminal paths are separate rows |
| Trigger | Who can build the tx, at what cost |
| Inputs read, pinned how | NFT / script hash / position only |
| Outputs pinned by script | |
| Residual → who | The reconciliation |
| State update enforced | AVL remove, register advance, successor, destruction, or **none** |
| Assertions at risk | |
| Rank | H = every procedure; M/L = sampled, decision recorded |

Add credit-side rows for every claim-creating path (what value must arrive, which line
checks it, bounded by value?). Reconcile: every box in the walkthrough has a row;
every terminal spend has a row.

### Phase 3 · Fieldwork

**Two standing rules.**

*Fieldwork is source-only.* Agents work from the pinned source and the memo. Every
procedure is source-level; a finding is established from source alone. Most
engagements are pre-deployment, where there is no chain state to consult. On a
deployed system, chain access is used for exactly two entity-level procedures
(E-1b credential concentration, E-6 deployed bytes match source), performed after
fieldwork by the lead, not by the fieldwork agents.

*Dual pass with burden on "safe."* Every H-ranked row, meaning every contract that
holds or moves funds, gets two independent passes on the same brief with no sight of
each other's work, and the two passes are **differently shaped**: a *coverage* pass
that runs the procedures and cites the closing line for each, and a *prosecutor* pass
that presumes every path exploitable, tries to build the extracting transaction, and
concedes only to a cited line it has tried to route around. Run them on different
model tiers where possible. Two identical passes measure reproducibility, not
independence: the first smoke test of this method ran two coverage passes on one brief
and got near-identical returns, while every real disagreement came from
differently-shaped passes (the prosecutor framing, an incentives pass, a blind severity
re-derivation, and the falsifier). Verdicts are recorded side by side. Any
disagreement is a mandatory adjudication in Phase 4, and the burden is on whichever
side said safe: it must cite the line that closes the attack. If it cannot, the
finding stands.

*The brief.* Both passes receive one brief file (commit, files, ledger rows,
assumptions register rows, traps, EKB security context, house rules) identified by
its sha256, never a prompt re-typed twice. If the EKB context carries its own Pass 1
instructions or a 1-to-10 rating request, the brief says the return schema and the
matrix override them. Passes label findings `<ledger row>/<procedure>/<slug>`, never
by ordinal, so the two returns can be merged by underlying fact.

*Origin.* On Dexy, auditor P2-4 (main and swap) composed the LP decoy layout and rated
it HIGH. Auditor P2-5 (mint and redeem), given the same trap, refuted it, arguing that
singleton coupling forced the real pool to input 0. No such line exists. A single pass
assigned to mint and redeem would have declared the pool clean. The pool was already
empty.

*Inside the assumptions, then without them.* Every procedure runs first with the
register taken as true. Then, for each row marked as failing with one actor, the
procedures re-run on the paths it touches. A finding that depends on an assumption
failing carries the row id and its actor threshold as precondition.

**The procedures** are D-1..D-13 (debit side, per spend path), C-1..C-3 (credit side),
S-1..S-4 (source level, per contract), A-1..A-3 (per register row), G-1..G-5
(incentives, once, design level), B-1..B-5 (builders and frontend, when in scope), and
E-1..E-6 (entity level), as listed in `audit-program`. Each ends done (line cite),
exception (finding id), or N/A (reason). Design-level and off-chain findings go through
the same finding record, concurring review, and matrix as code findings.

**Evidence.** Every exception gets a finding record with a constructed scenario. Every
library or chain semantic a result depends on (AVL `getMany` duplicate behaviour,
serialization offsets) is settled by an empirical probe with the output saved verbatim.
Agents return the procedure ids they covered and the ones they could not.

**Reconcile the checklist** at the end of Phase 3: every procedure id against every
H-ranked row, with both passes in each cell (`✓/✓`, `X/X (F-003)`, `X/✓ → ADJ-2`). A
cell with an unresolved `→ ADJ-n` is unfinished work.

### Phase 4 · Adjudication and concurring review

| # | Do |
|---|---|
| 4.−1 | **Cross-group composition check (E-8).** Before adjudicating, consolidate every trust edge from the map and both passes into one table (from-contract, assumption, counterparty, closed-by line or UNVERIFIED, counterparty pin). Give one read-only agent that table, the box/NFT inventory, and the trap register — no source — and ask which unverified or cross-group edges compose into an attack, with the lines to read. Settle each candidate from source; survivors become findings (kind: composition) and go to the falsifier. Per-group passes see only their own end of an edge; this is the cheap way to see both ends without a monolithic whole-protocol pass. |
| 4.0 | **Adjudicate every dual-pass disagreement.** Read the source at the cited lines. The safe side must have named the line that closes the attack; verify that line does what was claimed. If it does not exist or does not close it, the finding stands at the severity the other pass derived. Adjudication is decided from source; a landed transaction is corroboration, never the deciding evidence. Record as `ADJ-n`: both positions, the line cited, what was found there, outcome. A "safe" outcome without a verified line is not permitted. Then **merge by underlying fact**: the coverage pass, the prosecutor, the incentives pass, and the off-chain pass each describe the same defect with their own label and cell; one finding record per fact, with a derivation row listing every pass's cell. |
| 4.1 | Every HIGH and MEDIUM goes to an independent falsification pass with the finding record and the source only. Verdict: CONFIRMED / OVERSTATED / WRONG / STALE-ANCHOR. |
| 4.2 | Every prescribed fix is checked for rejecting legitimate spends. A fix that breaks the honest path is not a fix. |
| 4.3 | Severity is re-derived from the matrix, blind to the original cell, in batches of about ten records. This is a mechanical classification and a check on the lead's cells, so it runs on a cheaper, independent model (Sonnet 5) rather than the Opus fieldwork tier; every disagreement is a ruling (`R-n`) with the matrix cell cited, never a verdict. |
| 4.4 | Anchors re-verified against the pinned commit. |

### Phase 5 · Report

A management letter, in this order. The developer reads the first page carefully and
the rest selectively.

1. **Opinion paragraph.** Three or four sentences: what, at which commit, headline
   counts, the single most important result, positive or negative.
2. **Scope and method.** Commit, contracts, instances, tooling, and **what was not
   done**, stated here rather than buried.
3. **Findings table.** Id, severity, deployment status, kind (code / design /
   off-chain), location, title, fix size.
4. **Assumptions the opinion rests on.** The register rows verified, and the
   unenforced rows with their compensating controls, so a reader who disagrees with a
   row knows which findings move.
5. **KEY-RISK section**, separate from findings: the trust assumptions, whether the
   developer pre-disclosed them, what must change before mainnet.
6. **Per-finding detail** for HIGH and MEDIUM, including design-level and off-chain —
   as four bullets each, never a run-on paragraph: **What** (mechanism, `file:line`),
   **Why it matters** (consequence, who), **Fix** (smallest change, any falsifier
   correction), **Verified** (falsifier verdict; omit if none ran). Across the whole
   developer-facing report, no prose paragraph over ~120 words; longer becomes bullets
   or a table. The reader triages from the bullets and opens the finding records only
   for the derivation. No em dashes anywhere in the report (colon, semicolon, period,
   or parentheses instead; a Unicode minus in a code span is not an em dash). No
   AI-prose flourishes ("worth noting", "delve", "crucial", "robust", "leverage") and
   no anthropomorphic verbs on boxes or rent; say what happens. Empty table cells
   read "none" or "n/a", never a lone dash.
7. **LOW and INFO** as a table plus a launch-readiness checklist.
8. **What was verified sound.** Traps found absent, paths proven leak-free. This is
   what makes the opinion paragraph credible.
9. **Re-pin note.** Every contract fix moves hashes; say what must be re-minted.

### Phase 6 · Response log

One row per finding: developer response (date, source), disposition (Fix / Accept /
Defer / Dispute / No response), fix commit. A dispute triggers a re-run of the
falsification pass with the developer's argument as input; a dispute that survives
stays a finding, one that does not is withdrawn and the withdrawal is logged.

### Phase 7 · Retest

For each finding with disposition Fix, at the fix commit: re-run the *specific
procedure* that surfaced it, not a general re-read; construct the original attack
transaction, which must fail; construct the honest transaction on the same path,
which must pass; confirm the hash re-pin landed. Result: Closed / Partial / Not fixed.

### Phase 8 · Sign-off

The opinion at the retest commit, the open items with disposition and reason, any
checklist lines that ended `?` or N/A as scope limitations, and the subsequent-events
caveat: the opinion covers the retest commit and nothing after it.

---

## 3. Severity

The matrix, magnitude and likelihood classes, modifiers, deployment-status rule, and
KEY-RISK definition are in `audit-program`. The engagement rules around them:

- The matrix is confirmed in the memo before fieldwork. It is not renegotiated per
  finding. A finding that seems to deserve a different cell is a **ruling** (`R-n`):
  from-cell, to-cell, reason, visible in the notes.
- Findings are numbered `F-NNN` in order recorded, with severity as a field. The
  report table sorts by severity. This keeps ids stable when the concurring review
  moves a finding.
- A hypothesis without a constructed transaction or probe result is not a finding.
  It goes under "open questions."
- A KEY-RISK the developer already flagged in source is still reported, with a note
  that it was pre-disclosed.

**Calibration.** Across the two engagements the matrix reproduces 13 of 16 CRITICAL /
HIGH / MEDIUM / KEY-RISK rulings that were made ad hoc at the time. The three
divergences were all cases where the matrix answer was more defensible: a
token-weighted quorum held by one address is KEY-RISK rather than MEDIUM; an
unprivileged full-reserve drain in an undeployed contract is CRITICAL with status
"not deployed" rather than MEDIUM.

---

## 4. Workpapers

Someone who was not there must be able to follow what was done, see the evidence, and
reach the same conclusion. In practice that someone is the next session after a
context reset.

```
AUDITS/                        never committed
  00-ENGAGEMENT.md             scope memo
  00-source-hashes.txt         sha256 per in-scope file at the pinned commit
  01-INTERACTION-MAP.md        walkthrough
  01-ASSUMPTIONS.md            developer representations, verified
  02-VALUE-LEDGER.md           debit-side register
  02-PROGRAM-CHECKLIST.md      procedure × row reconciliation, both passes
  03-WORKPAPERS/WS-*.md        one per contract group; both passes side by side
  04-CONCURRING.md             adjudications and falsifier verdicts
  05-REPORT.md                 management letter
  06-RESPONSE-LOG.md
  07-RETEST.md
  08-SIGNOFF.md
  findings/F-NNN.md            one per finding, fixed schema
  evidence/                    probe-*.txt verbatim; agent-*-a.md / -b.md unedited
  notes.md                     rulings R-n, adjudications ADJ-n, decisions, open questions, dead ends
```

**Reference codes.** `WS-A §3.2`, `VL-12`, `F-007`, `EV/probe-avl-getmany.txt`, `D-7`,
`R-3`, `ADJ-2`. A finding cites the ledger row, the procedure, the workpaper section,
and the evidence. Nothing in the report is unsupported by something in the folder.

**Tickmarks.** `✓` verified to source · `P` probe-confirmed · `F` falsifier-confirmed ·
`X` exception (finding id) · `–` N/A (reason) · `?` open. A `?` that survives to the
report is disclosed as a scope limitation.

**Workpaper header.**

```
# WS-A · <group>
Pass A by:            Pass B by:            Date:
Commit:               Adjudicated by:
Ledger rows covered:  VL-1, VL-2, VL-5
Procedures performed: D-1..D-13 on VL-1, VL-2 (both passes); D-1..D-8 on VL-5 (sampled, DEC-2)
Exceptions:           F-001, F-004
Open questions:       Q-3
```

**Finding record** (`findings/F-NNN.md`), fixed fields:

| Field | Content |
|---|---|
| Severity | Magnitude class · likelihood class · cell · modifiers · final |
| Derivation | Each pass's cell for this fact (coverage / prosecutor / incentives / blind re-derivation / falsifier) |
| Fix reviewed by | Falsifier (HIGH/MEDIUM) or blank = unreviewed |
| Actor threshold | One anonymous actor / one with state precondition / k-of-n / proportion / honest liveness failure; profitable (rational) or griefing-only |
| Depends on assumption | none / A-n and its "fails with" |
| Kind | code / design (incentive) / off-chain (builder, frontend) |
| Deployment status | live / latent / patched on-chain / not deployed / pre-deployment, **with a cite** (evidence file and height) for any on-chain state claim |
| Assertion | One of the seven |
| Procedure | The D- / C- / S- / E- line |
| Location | `file:line` at the pinned commit · ledger row |
| Claim | One paragraph: the transaction that should not be valid, is |
| Scenario | Numbered steps with magnitudes |
| Who and precondition | |
| Reconciliation | Value in · pinned out · residual · residual goes to |
| Evidence | Workpaper section · probe file · agent report |
| Concurring | Falsifier verdict and date, or pending |
| Fix | Smallest change closing every variant · honest path still passes · regression test · re-pin consequence |
| Response | Filled in Phase 6 |
| Retest | Filled in Phase 7 |

**Evidence rules.** Probe output is saved verbatim including the command; an edited
probe is not evidence. Agent reports are saved unedited; the two passes are saved
separately and never merged except through an `ADJ-n`. Never claim a test is green
unless it was run in this engagement; a committed green artifact is not evidence.

---

## 5. Running it with the EKB tools

`audit_contract` (Pass 1) and `audit_verify` (Pass 2) inject `audit-program` into
their context, so both passes carry the same procedures, traps, and matrix. The
engagement wraps them:

1. **Phase 3, coverage and prosecutor.** Call `audit_contract` **once per contract**,
   not once per cluster: it is a per-contract tool whose matched-docs are a semantic
   search on that contract's patterns, and concatenating a cluster dilutes the match
   and overflows the input. Put the security-context and matched-docs sections for a
   group's contracts into that group's brief file. Then run two separate contexts on
   that brief: a coverage pass (procedures, closing lines) and a prosecutor pass
   (presume exploitable, build the transaction, concede only to a line you tried to
   route around), on different model tiers if you can. In Claude Code that is two
   subagents dispatched in parallel with the same brief path and hash. Neither sees
   the other. Save both returns unedited.
2. **Phase 4.0, adjudicate.** Diff the two verdict sets. For each disagreement, read
   the cited lines yourself and rule with the burden on safe.
3. **Phase 4.1, concurring.** Run a dedicated falsification agent on each HIGH and
   MEDIUM record with the source and that record only. Then call `audit_verify` with
   the merged findings: **it returns a Pass-2 prompt, not an opinion.** Give that
   prompt to one more independent context as a missed-issues sweep, ignore its
   1-to-10 rating, and route anything new back through adjudication. The
   falsifier's "attack the recommended fix" step is the only review a prescribed fix
   gets; say in the report that LOW and INFO fixes are unreviewed.
4. **Phases 5–8** are documents and a retest; the tools are not involved.

The tools cannot enforce that the two Pass 1 runs were independent. That is the
caller's orchestration, and it is the single most important thing this skill adds to
the two-tool audit.

---

## 6. Templates

Minimal fill-in versions. Copy into `AUDITS/` at the start of an engagement.

**ENGAGEMENT-LETTER.md** (one page, to the developer)

```
To / From / Date
What we are reviewing: <N> contracts under <path> at commit <hash>, plus builders<, frontend>
How: map every box and spend path; assumptions from your docs and answers; fixed checklist;
     two independent review passes reading every contract; adversarial check on serious findings; severity
     scale fixed in advance; source-only, no tx built or broadcast, tests read unless you permit a run
What you get: opinion; findings table; trust assumptions separate from defects; assumptions the
     opinion rests on; launch checklist; what was tested and found sound; file:line on everything
What we need: questionnaire answers by <date>; may we run <test cmd>; a follow-up contact
After the report: response log per finding; retest at your fix commit; sign-off naming the commit
Disclosure: findings to you privately first; you decide public release
What this is not: a certified audit or a warranty; limitations stated in the report
Timing: <deadline and why>
```

**00-ENGAGEMENT.md** (internal, never sent)

```
Project:            Repo / path:
Commit:             (branch:   upstream:   )   Source hashes: 00-source-hashes.txt
Date opened:        Requested by:              Recipient and channel:
Engagement type:    pre-deployment / deployed review / incident
Deadline and why:

In scope:   | Group | Files | Lines | Notes |
Instances:  | Instance | Constants source | Value held (height) or "planned" | In scope |
Credentials:| Credential | Recognised by (file:line) | Units | Intended holders | Actual (deployed only) |
Out of scope (explicit):
Severity matrix applies unchanged: yes / no  — adjustments, with reason:
Tooling available:   | Tool | Available | Procedures N/A if absent |
Pre-named traps:     T1.. plus engagement-specific
House rules: cite file:line for every claim; "checked here" vs "assumed elsewhere" is a
  named trust edge; never edit source, sign, or touch a node during review; AUDITS/ never committed.
```

**01-ASSUMPTIONS.md**

```
| A | Kind | Assumption | Stated by | Enforced by (file:line) / UNENFORCED | Compensating control | What breaks if it fails | Fails with | Dependent findings |
Omissions verified: | A | Developer's reason | Holds? | Evidence (redundancy line or cost) |
```

**02-VALUE-LEDGER.md**

```
| VL | Box | Assets | Spend path | Trigger | Inputs read / pinned how | Outputs pinned | Residual → | State update | Assertions | Rank | WP |
| VL-C1 | Box | Claim created | Value that must arrive | Check (file:line) | Bounded? | Rank | WP |
Reconciliation: every walkthrough box has a row · every terminal spend has a row
```

**notes.md — adjudications**

```
| ADJ | Contract / trap | Pass A said | Pass B said | Line cited by safe side | Found at that line | Outcome |
```

**07-RETEST.md**

```
Fix commit:            Source hashes second column updated: yes / no
| Finding | Procedure re-run | Attack tx vs fix | Honest tx | Re-pin | Closed / Partial / Not fixed |
Accepted / deferred (no procedure run): | Finding | Disposition | Developer's reason |
```

**08-SIGNOFF.md**

```
Opinion: At commit <retest hash>, the contracts listed in 00-ENGAGEMENT.md were reviewed
under this program. All HIGH and MEDIUM findings are Closed except those listed below.
Open items: | Finding | Severity | Disposition | Reason |
Scope limitations: checklist lines that ended ? or N/A for tooling reasons
Subsequent events: this opinion covers the retest commit only.
Signed: session / date
```

---

## 7. Adding to the trap register

At sign-off, each HIGH or MEDIUM that was not already a listed class gets a row in
`audit-program`: class name, the procedure(s) that should have caught it, origin
engagement and finding, the one-paragraph check. The origin column is the audit trail
for why the trap exists. That file is how one engagement's fieldwork compounds into
the next engagement's program, for everyone who calls the audit tools.

---

## References

- `audit-program` — procedures, traps, severity matrix (injected into both audit tools)
- `known-issues` — the nine general vulnerability categories
- `audit-context` — LLM pitfall calibration
- `contract-audit-methodology` pattern — the two-pass tool design
