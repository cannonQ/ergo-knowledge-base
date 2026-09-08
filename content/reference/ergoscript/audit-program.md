---
title: "ErgoScript Audit Program — Procedures, Traps, and Severity Matrix"
description: "Compact audit program injected into every audit_contract and audit_verify call: the debit-side procedure checklist, the pre-named trap register (T1–T19, each from a real finding), and the severity matrix. The full engagement method is the contract-audit-engagement skill."
category: reference
difficulty: advanced
tags: [ergoscript, audit, security, severity, traps, debit-side, procedures]
sdk: [none]
author: CannonQ
source: original
license: AGPL-3.0
updated: 2026-09-08
---
# ErgoScript Audit Program

This is the working checklist for a contract audit. It is injected into both audit
passes so that Pass 1 and Pass 2 test the same population, answer the same traps, and
rate on the same matrix. The full engagement method (phases, workpapers, dual-pass
adjudication, delivery, retest) is the `contract-audit-engagement` skill.

## The principle: audit the debit side

Value under a contract leaves only when a guarded box is spent, and the script is the
sole approval control over that spend. So the audit population is every (box, spend
path) pair. For each one, answer the five questions an auditor asks of a cheque:

| Cheque question | eUTXO question |
|---|---|
| Who approved it? | Who can build a valid spending tx: signature, or permissionless with conditions? |
| Who is the payee? | Is every value-carrying output's script pinned, or is the recipient builder-chosen? |
| Is the amount right? | Rounding, overflow, integer division, unit mismatch, sum conservation? |
| Does it reconcile? | Inputs minus script-pinned outputs = residual. Who gets the residual? |
| Recorded so it can't be paid twice? | Is the state update (AVL remove, register advance, successor box) enforced on *this* path? |

Paths that create a claim (deposit, register, mint) are the credit side: confirm the
matching value actually arrived and the claim is bounded by it. Everything else is
presentation.

## Procedures

Run every debit-side procedure on every spend path of every fund-holding box. Record
each as **done** (line cite), **exception** (finding), or **N/A** (reason).

### Debit side (per spend path)

| # | Procedure | Assertion |
|---|---|---|
| D-1 | **Authorization.** Who can build a valid spending tx? If permissionless, list the conditions and confirm they are not trivially satisfiable. | Rights & Obligations |
| D-2 | **Self-identification.** Does the script pin its own input (`SELF.id == INPUTS(i).id`, `selfBoxIndex`)? If it assumes `INPUTS(0)` is itself, can a builder place a decoy there? | Existence |
| D-3 | **Counterparty identification.** Every input and data input read: pinned by NFT, by script hash, or only by position? | Existence |
| D-4 | **Payee pinning.** Every output carrying value out: script constrained? Recipient from trusted state, or from a builder-supplied context var? | Completeness |
| D-5 | **Amount.** Rounding direction, integer division, overflow reliance, unit mismatch, output sum tied to input? | Accuracy |
| D-6 | **Reconciliation.** Inputs minus pinned outputs = residual. Bounded? Who receives it? An unbounded residual to the builder is a finding. | Completeness, Accuracy |
| D-7 | **State update.** What must change so the same claim cannot be paid again, and is it enforced on *this* path, not just a sibling? | Completeness |
| D-8 | **Path selection.** Can the builder force a different branch: op byte unread, threshold flipped by an inflated sum? | Classification |
| D-9 | **Cutoff.** Every `HEIGHT` or time condition: can the window be shortened, moved, or backdated? Register bounded on both sides? | Cutoff |
| D-10 | **Duplicates.** Every collection from a context var or register: distinctness required? `getMany` returns a repeated key repeatedly. | Existence |
| D-11 | **Liveness dependence.** Does safety require someone to act within a window? Name who and the window. Floor MEDIUM. | Cutoff |
| D-12 | **Termination and lock.** Can the box reach a state with no valid spend? Refund or eviction path for stuck value? | Completeness |
| D-13 | **Front-running.** If permissionless, can a mempool observer replace an honest tx spending the same box with a hostile variant? | Existence |

### Credit side (per claim-creating path)

| # | Procedure |
|---|---|
| C-1 | Does the value the claim represents actually arrive in a guarded box in the same tx, and is that checked? |
| C-2 | Is the claim size bounded by the value that arrived? |
| C-3 | Can a claim be created with zero or recycled value (same box counted twice, decoy deposit)? |

### Source level (per contract)

| # | Procedure |
|---|---|
| S-1 | **Header vs enforced logic.** List every claim the header makes; verify each against code. Read the comment *after* the code. |
| S-2 | **Fix diffusion.** Every check one contract does right, every finding, every trap: search every sibling. Asymmetry is the signal. |
| S-3 | **Static test audit.** Read tests as evidence of intended tx layouts even if they cannot be run. A test placing an unconstrained box at an unrestricted position is evidence *for* a finding. |
| S-4 | **Instance parity.** Every deployed instance of the contract set at equal rigour, ranked by value held, not by which is the flagship. |

### Entity level (once)

| # | Procedure |
|---|---|
| E-1 | **Key inventory.** Every admin PK, whitelist, config box: single signer or multisig, mainnet variant present, what it can change. Single signer on mainnet is KEY-RISK. |
| E-2 | **Upgrade paths.** What can change, by whom, with what delay. |
| E-3 | **Off-chain coupling.** What breaks if the keeper or parameter is wrong or absent. |
| E-4 | **Build and hash pinning.** Repo builds; hash-pinning tests green *in this run*; re-pin procedure documented. |
| E-5 | **Traps.** Every trap below has an explicit verdict per contract with a line cite either way. |

## Pre-named traps

Every one comes from a real finding. Return PRESENT / ABSENT / PARTIAL / N/A per
contract with `file:line` either way. ABSENT without a cited line is not a verdict.

| ID | Class | Check | Origin |
|---|---|---|---|
| T1 | Decoy input / positional index | Script reads `INPUTS(n)` / `OUTPUTS(n)` / `dataInputs(n)` without pinning the slot by NFT, script hash, or `== SELF`. | Dexy LP drain, 2026-09-07 (~288k ERG), `main.es`/`swap.es` |
| T2 | Guard + logic context-var execution | What is hashed vs executed, byte for byte; any path where guard runs without logic; absent ctx var fails closed? | Lithos 2026-09 |
| T3 | Singleton NFT conservation | Every spend path forces the NFT into a successor at the same script, pinned by propositionBytes or hash. | Lithos 2026-09 |
| T4 | AVL proofs | Digest pinned into successor; lookup proof for a different key; insert twice; flags/keyLength preserved. | Lithos 2026-09 |
| T5 | Bond / value accounting | Trace every arithmetic step across the lifecycle; any exit without a matching decrement. | Lithos 2026-09 |
| T6 | Permissionless spend driven by another box | Driver pinned by NFT not script; driver's logic constrains where the gated value goes. | Lithos 2026-09 |
| T7 | Testnet artifacts reaching mainnet | PK-gated whitelists/configs, dead testnet contracts; is there a mainnet variant at all. | Lithos K-1/K-2 |
| T8 | Terminal path lacks the sibling's state update | Non-terminal branch removes; terminal branch does not and enforces no sum conservation; ctx-var collection without distinctness. | Lithos H-1 `Payout.ergo` path 3 |
| T9 | Op byte unread on the co-spent side | A box that may only leave in counterparty op *k* never reads the counterparty's op var; escapes inside any other op. | Lithos H-2 `MinerData_Logic` |
| T10 | Late honest action backdates a window | Period boundary set from `HEIGHT` at transform; late transform collapses a protective window. | Lithos M-1 `Holding_Logic:190` |
| T11 | Unpinned value swept as residual | Extra admitted input with no pinned output, or withdrawal pins payees but not the remaining reserve; builder pockets it. | Lithos M-2; Dexy F-9 `hodlcoin.es` |
| T12 | Capacity exhaustion with no eviction | Bounded set fillable by entries that never progress; no removal path; permanent halt. | Lithos M-3 `Collateral_Mainnet` |
| T13 | Shared credential token across targets | One NFT id in N units authorises N boxes; any unit at `INPUTS(0)` satisfies every target; update tx admits extra inputs. | Dexy F-2 `bank.es:82`, `update.es:56` |
| T14 | Register bounded one way on a permissionless path | `>=` but no `<=`; spender sets far future; height-gated path frozen, no recovery. | Dexy F-3 `payout.es:70` |
| T15 | Script-preservation compare that skips bytes | `propositionBytes.slice(1, size)` leaves the header byte free; successor unspendable. Compare full bytes or hash. | Dexy F-4 `emission.es:24` |
| T16 | One branch lacks the script pin its siblings have | Siblings check successor `propositionBytes` + value floor; one branch checks tokens only. Diff successor checks across branches. | Dexy F-5 `buyback.es:54` |
| T17 | Token-weighted quorum with concentrated supply | Quorum sums token amounts; if one address holds a quorum, governance is that address. KEY-RISK. | Dexy F-6 `update.es:52` |
| T18 | Proportional redeem with no liquidity floor | Ratio-invariant fee lets a dominant holder drain to dust; supply 0 bricks mint; pool price resets for downstream consumers. | Dexy F-7 `redeem.es:35` |
| T19 | Stale trigger reads as sustained | Trigger records first height; reset needs an actor; consumers gate on `trigger < HEIGHT - T`; nobody resets. | Dexy F-8 `tracking.es:111` |

## Severity matrix

Set before fieldwork. A finding's severity is the cell it lands in. Deviations are
logged rulings, not arguments.

**Magnitude.** M-Total: all protocol-held value or a pool any user's funds sit in.
M-Pooled: bounded value belonging to someone other than the actor (other users, or a
protocol-owned box). M-Integrity: no direct value path, but a mechanism protecting
others' value is defeated. M-Lock: value or function permanently unusable. M-Own: only
the actor's own funds. M-None: no value path.

**Likelihood.** L-Open: anyone, ~fee cost, no precondition. L-Conditional: permissionless
with a realistic precondition. L-Costly: large cost, liveness failure by honest parties,
or a victim error first. L-Escalated: a credential does more than the design issued it
for (one unit bypasses a quorum; key for A reaches B). L-Privileged: a key the design
trusts, for the action it grants.

| | L-Open | L-Conditional | L-Costly | L-Escalated | L-Privileged |
|---|---|---|---|---|---|
| **M-Total** | CRITICAL | HIGH | MEDIUM | HIGH | KEY-RISK |
| **M-Pooled** | HIGH | HIGH | MEDIUM | HIGH | KEY-RISK |
| **M-Integrity** | HIGH | MEDIUM | MEDIUM | MEDIUM | KEY-RISK |
| **M-Lock** | HIGH | MEDIUM | MEDIUM | MEDIUM | LOW |
| **M-Own** | LOW | LOW | LOW | LOW | INFO |
| **M-None** | INFO | INFO | INFO | INFO | INFO |

Multiple paths: classify each, take the higher. **Modifiers:** front-runnable (note, no
change); liveness-dependent safety (floor MEDIUM); full on-chain shield verified this
audit (drop one level, floor LOW); partial shield (no change); latent, enabling state
not yet on-chain (no change). **Deployment status is a column, not a cell:** live,
latent, patched on-chain, not deployed. Never rate down because the code is not
deployed. **KEY-RISK** is the segregation-of-duties column, reported separately from
defects; launch-blocking if a single hot key on mainnet. **LOW vs INFO:** fail-closed
correctness with a one-line fix is LOW; hygiene with no behavioural effect is INFO.

## Finding format

Every finding carries: assertion violated (Existence, Completeness, Accuracy, Cutoff,
Rights & Obligations, Classification, Presentation); procedure that surfaced it;
`file:line`; magnitude class, likelihood class, cell, modifiers; a numbered scenario
with magnitudes; who can do it and the precondition; for value findings the
reconciliation (value in, pinned out, residual, residual goes to); the smallest fix
that closes every variant; and confirmation the honest path still passes under the fix.
A finding without a constructed transaction is a hypothesis and is listed separately.
