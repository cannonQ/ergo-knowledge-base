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

---

## 2. Engagement lifecycle

```
00 Engagement   scope memo: commit, contracts, instances, recipient, deadline, type
01 Walkthrough  interaction map: boxes, tokens, who spends what
02 Value ledger the debit-side register: every box × every spend path
03 Fieldwork    procedure checklist per spend path, from source only;
                two independent passes on every fund-holding contract
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

### Phase 1 · Walkthrough

Inventory every box type (script, identifying NFT, registers), every token (minted,
held, burned where), every cross-contract read (data input) and co-spend (input) with
how the counterparty is identified, the lifecycle of each value-holding box from
creation to terminal spend, every admin key and config box, and every off-chain
assumption the contracts depend on.

Phase 1 maps. It does not audit. Suspected issues go in a "candidate findings" list
with `file:line` and are proven or dropped in Phase 3.

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
holds or moves funds, gets two independent passes by two separate agents with the same
traps and no sight of each other's work. Their per-trap and per-procedure verdicts are
recorded side by side. Any disagreement is a mandatory adjudication in Phase 4, and the
burden is on whichever side said safe: it must cite the line that closes the attack.
If it cannot, the finding stands.

*Origin.* On Dexy, auditor P2-4 (main and swap) composed the LP decoy layout and rated
it HIGH. Auditor P2-5 (mint and redeem), given the same trap, refuted it, arguing that
singleton coupling forced the real pool to input 0. No such line exists. A single pass
assigned to mint and redeem would have declared the pool clean. The pool was already
empty.

**The procedures** are D-1..D-13 (debit side, per spend path), C-1..C-3 (credit side),
S-1..S-4 (source level, per contract), and E-1..E-6 (entity level), as listed in
`audit-program`. Each ends done (line cite), exception (finding id), or N/A (reason).

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
| 4.0 | **Adjudicate every dual-pass disagreement.** Read the source at the cited lines. The safe side must have named the line that closes the attack; verify that line does what was claimed. If it does not exist or does not close it, the finding stands at the severity the other pass derived. Adjudication is decided from source; a landed transaction is corroboration, never the deciding evidence. Record as `ADJ-n`: both positions, the line cited, what was found there, outcome. A "safe" outcome without a verified line is not permitted. |
| 4.1 | Every HIGH and MEDIUM goes to an independent falsification pass with the finding record and the source only. Verdict: CONFIRMED / OVERSTATED / WRONG / STALE-ANCHOR. |
| 4.2 | Every prescribed fix is checked for rejecting legitimate spends. A fix that breaks the honest path is not a fix. |
| 4.3 | Severity is re-derived from the matrix by the reviewer without seeing the original cell. Disagreements are rulings (`R-n`) with the matrix cell cited. |
| 4.4 | Anchors re-verified against the pinned commit. |

### Phase 5 · Report

A management letter, in this order. The developer reads the first page carefully and
the rest selectively.

1. **Opinion paragraph.** Three or four sentences: what, at which commit, headline
   counts, the single most important result, positive or negative.
2. **Scope and method.** Commit, contracts, instances, tooling, and **what was not
   done**, stated here rather than buried.
3. **Findings table.** Id, severity, deployment status, location, title, fix size.
4. **KEY-RISK section**, separate from findings: the trust assumptions, whether the
   developer pre-disclosed them, what must change before mainnet.
5. **Per-finding detail** for HIGH and MEDIUM.
6. **LOW and INFO** as a table plus a launch-readiness checklist.
7. **What was verified sound.** Traps found absent, paths proven leak-free. This is
   what makes the opinion paragraph credible.
8. **Re-pin note.** Every contract fix moves hashes; say what must be re-minted.

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
| Deployment status | live / latent / patched on-chain / not deployed / pre-deployment |
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

1. **Phase 3, pass A and pass B.** For each H-ranked contract group, run
   `audit_contract` twice in two separate contexts. In Claude Code that is two
   subagents dispatched in parallel with the same prompt: the contract source, the
   memo, the traps, and the instruction to return per-trap verdicts with line cites
   and per-procedure results. Neither sees the other. Save both reports unedited.
2. **Phase 4.0, adjudicate.** Diff the two verdict sets. For each disagreement, read
   the cited lines yourself and rule with the burden on safe.
3. **Phase 4.1, concurring.** Run `audit_verify` (or a dedicated falsification agent)
   on the merged findings, with the source and the finding records only. This is the
   "another auditor produced these; assume they made mistakes" pass.
4. **Phases 5–8** are documents and a retest; the tools are not involved.

The tools cannot enforce that the two Pass 1 runs were independent. That is the
caller's orchestration, and it is the single most important thing this skill adds to
the two-tool audit.

---

## 6. Templates

Minimal fill-in versions. Copy into `AUDITS/` at the start of an engagement.

**00-ENGAGEMENT.md**

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
