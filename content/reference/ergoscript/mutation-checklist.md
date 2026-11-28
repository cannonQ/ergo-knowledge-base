---
title: "Proposed Mutation Checklist for Pass 2 (MC1–MC20)"
description: "Twenty hostile changes to an honest transaction, asked of every spend path in the second audit pass. Proposed, not from real losses. Adapted from the mutator list of the ergo-redteam-lab fuzzer. Injected by audit_verify."
category: reference
difficulty: advanced
tags: [ergoscript, audit, mutation, checklist, fuzzing, pass-2, proposed]
sdk: [none]
author: CannonQ
source: original
license: AGPL-3.0
updated: 2026-11-28
index: false
---
# Proposed mutation checklist

**Status: proposed.** This list is adapted from the 25 mutators of the `ergo-redteam-lab` fuzzer (https://github.com/a-shannon/ergo-redteam-lab, commit `c31994c`, MIT licence), merged to 20 rows and reworded as questions. The EKB has not run that fuzzer, and no row here names a real loss as its origin. Do not cite a row as precedent, and do not raise a finding's severity because it matches one. Where a row overlaps a pre-named trap, the trap is the authority and the row only points at it.

## How to use it

Take each spend path's honest transaction (the one the builder would make). For each row, picture the one change described and nothing else, and answer with one of:

- **BLOCKED**: cite the line that rejects the changed transaction.
- **ACCEPTED**: the script still passes. This is a lead, not a finding. Say what the change gains or costs anyone. A contract that accepts an extra token or an extra nanoERG is often working as designed.
- **N/A**: the path has nothing for the change to act on (no data input, no successor, no context variable). Say which.

Answer from the code. If a probe harness is available, an ACCEPTED on a row that would move value is reproduced there before it is reported. Apply every row to every checked output and every data input the path reads, not only the first.

Two limits of this kind of test, which apply to any fuzzer that runs scripts and not transactions:

- A change the script accepts can still be an invalid transaction. Node rules (minimum box value, the creation height rule, size and cost limits) are outside the script.
- A change the script rejects says nothing about a different change. The list is a floor.

## The rows

| ID | Change to the honest transaction | Ask | See also |
|---|---|---|---|
| **Value** | | | |
| MC1 | The checked output pays less: 1 nanoERG less, half, the minimum box value | Which line fixes the amount, and is it `==` or `>=` against the right base? | |
| MC2 | The paid output's script is the attacker's | Which line pins the recipient? | |
| MC3 | Two outputs swap positions | Is any box taken by position with nothing else identifying it? | T1 |
| **Tokens** | | | |
| MC4 | The singleton NFT is left out of the successor | Does every path force it into a successor? | T3 |
| MC5 | The singleton NFT goes to a box at another script | Is the successor's script pinned on the same path that pins the NFT? | T3, T16 |
| MC6 | A token amount in a checked output is 1 lower | Exact amount or lower bound, and who keeps the difference? | T11 |
| MC7 | An unrelated token is added to the successor | If accepted: can it block a later path, clash with a register convention, or grow the box toward a size limit? | |
| MC8 | A second box of the same script is spent in the same transaction, with the same outputs | Does one output satisfy both inputs? | Known issue 10 |
| **State** | | | |
| MC9 | The successor's script is replaced by an anyone-can-spend script | Which line compares the successor's full `propositionBytes`? | T15, T16 |
| MC10 | A register the next spend reads is absent from the successor | Does this path check it is present and of the right type, or does the box become unspendable? | Settled semantics on `getOrElse` |
| MC11 | A register in the successor holds a different value | Is each carried register compared, or only the ones this path changes? | T8 |
| MC12 | The successor's AVL tree has the same digest but wider operation flags | Is the whole tree compared, or only the digest? | T4 |
| MC13 | A deadline or height register is set to the largest value | Is it bounded on both sides? | T14 |
| **Time** | | | |
| MC14 | The transaction is made one block before the gate opens, and far before | Is the comparison `>` or `>=`, and against which stored value? | T10 |
| MC15 | The successor's creation height is set far in the past | Does the script read `creationInfo`? If not, what does the node's creation height rule allow, and what does an old creation height do to this box's storage-rent clock? | Known issue 7 |
| **Context variables** | | | |
| MC16 | The context extension is empty | Which paths still evaluate? Does a refund or owner path fail because a variable read is hoisted or sits in a sigma-level OR? | Settled semantics on hoisting |
| MC17 | A witness variable has extra bytes appended, or one bit flipped | A plain hash comparison rejects both. It matters only where the script slices the bytes, checks a prefix, or passes them on. | T2 |
| MC18 | A `GroupElement` variable is the identity point | Does any proof or exponentiation take it unchecked? | Known issue 5 |
| **Data inputs** | | | |
| MC19 | The data input is replaced by a box with the same registers and no NFT | Which line authenticates it, and does that line run on every path that reads it? | T1, T6 |
| MC20 | The data input is left out | Which paths fail, and is a path that never needs the data among them? | Settled semantics on hoisting |

## Reporting

Give one table per spend path with a verdict per row. An ACCEPTED that harms someone becomes a VERIFICATION FINDING with its severity derived from the matrix in the usual way, and it cites the row only as how it was found.
