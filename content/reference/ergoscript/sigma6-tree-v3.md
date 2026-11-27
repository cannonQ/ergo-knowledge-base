---
title: "Settled Semantics at Tree Version 3 (Sigma 6.0)"
description: "Probe results for ErgoScript contracts compiled to version 3 trees and for Sigma 6.0 methods: evaluation order and hoisting, fail-closed reads, Header.checkPow, Global.decodeNbits, Global.deserializeTo. Injected by the audit tools when the contract uses a 6.0 method or the chain is yolo."
category: reference
difficulty: advanced
tags: [ergoscript, sigma-6, tree-version-3, audit, semantics, probes, header, deserializeTo]
sdk: [none]
author: CannonQ
source: original
license: AGPL-3.0
updated: 2026-11-26
ergo_version: "6.0"
index: false
---
# Settled semantics at tree version 3 (Sigma 6.0)

Use this section when the contract is compiled to a version 3 tree or calls a Sigma 6.0 method (`Global.deserializeTo`, `Header.checkPow`, `Global.powHit`, `Global.decodeNbits`, `UnsignedBigInt` and others). On Ergo these need the 6.0 soft fork to be active. On YOLO SigmaChain they are available from block 1.

Every statement below is marked with where it comes from. A **probe** is a result this page's own harness produced. A **harness result** was produced by the peg-draft harness of the YOLO project and read from its source and its result files; it was not re-run for this page.

## 1. The evaluation-order rules hold at version 3 (probe)

The "Settled Semantics" section of the audit context was established at tree versions 0 and 1 on a fleet-sdk MockChain. The same rules were probed again at tree version 3. All 30 cases gave the result the version 0/1 rules give.

**Harness.** `sigma-state` 6.0.7 (Scala 2.12.18): scripts compiled with its `SigmaCompiler`, placed in a version 3 tree without constant segregation, and reduced with its `ErgoLikeInterpreter.fullReduction` at activated script version 3. Each case was also run at activated version 2 with a version 0 tree as a control, with the same result. Probe and output: `examples/probes/sigma6-tree-v3/` in the EKB repository, run on 26 November 2026.

What was observed at version 3:

| Case | Result |
|---|---|
| A failing read in an `if` arm that is not taken (run-time condition, and constant condition) | not evaluated |
| A failing read on the right of `&&` when the left is false, and on the right of `\|\|` when the left is true | not evaluated |
| A failing read in the body of a `def` or a lambda that this path does not call | not evaluated |
| A `val` declared outside and used in two `if` arms, neither taken | evaluated: the script throws |
| A `val` declared outside and used in an `if` arm and on a `\|\|` right-hand side | evaluated: the script throws |
| A `val` declared outside and used on both sides of an `&&` inside one arm | evaluated: the script throws |
| The same, where both uses go through the same sub-expression (`b.value` twice, `val b` a box) | not evaluated |
| A `val` declared outside and used once, in an arm not taken | not evaluated |
| A `val` declared inside an arm and used twice there | not evaluated |
| A `val` that is never used | not evaluated |
| The same read written inline in two arms, neither taken | not evaluated |
| Hoisted `val o = SELF.R5[Int]`: R5 absent | no throw |
| Hoisted `val o = SELF.R5[Int]`: R5 holds a `Long` | throws |
| Hoisted `val r = SELF.R5[Int].get`: R5 absent, and R5 holds a `Long` | throws in both |
| `anyOf(Coll(true, failing read))`, `allOf(Coll(false, failing read))` | every element evaluated: throws |
| `key \|\| sigmaProp(failing read)` | evaluated: throws, so the key path fails too |
| `key \|\| sigmaProp(if (not taken) failing read else true)` | not evaluated |
| `Coll` index out of range | throws; passes behind a `size` guard |
| `Long * Long` overflow | throws; the same product taken `.toBigInt` first does not |
| `BigInt` division by zero | throws |
| `R5[Int].getOrElse(0)`: R5 absent | returns the default |
| `R5[Int].getOrElse(0)`: R5 holds a `Long` | throws |

So the consequences listed in the audit context ("What it changes for audit work") apply to a version 3 contract as written.

**Limits of this probe.**

- One compiler, one interpreter: `sigma-state` 6.0.7. Where a `val` lands is decided by the compiler. A tree built by another compiler or another version (sigma-rust, sigmastate-js, an older Scala release) can place it differently. To settle a real contract, read its compiled tree or probe it.
- Trees were built without constant segregation. The version 0/1 results held with it on and off; that was not repeated at version 3.
- Library-level evaluation of one input with no data inputs and one output. No node, no mempool, no block validation.
- The failing read in the hoisting cases was `CONTEXT.dataInputs(0)` with no data inputs, plus the register and arithmetic cases in the table. Other failing operations were not tried at version 3.
- Whether fleet-sdk MockChain or sigmastate-js can evaluate a version 3 tree was not checked. The version 0/1 harness caveats (MockChain minimum value, the fleet-sdk input selector) are about that harness and say nothing about this one.

One further observation agrees with the table: the peg project reports that a path whose `val` was declared inside an `if` arm ran with no data inputs present although another arm reads a data input (one case, reported in that project's handoff; not re-run here).

## 2. Sigma 6.0 methods

| Fact | Basis |
|---|---|
| A script that calls a 6.0 method does not compile at activated version 2 for a version 0 tree (`MethodNotFound` on `Global.decodeNbits`). What a node without 6.0 does with a version 3 tree it receives was not probed. | Probe |
| `Global.decodeNbits(nBits)` returns the **difficulty**, not the target. For `nBits` 104330148 it returned 61519568044032, the value of `NBitsUtils.decodeCompactBits`. The target is the group order divided by the difficulty. | Probe |
| `Global.deserializeTo[Header](bytes)` parses serialized header bytes, and `blake2b256(bytes)` equals both the header's stated id and the parsed header's `.id`. | Probe: 8 real Ergo mainnet headers (heights 1,924,816 to 1,924,821, two of them orphans) and 1 header from a YOLO private test chain (height 3,988) |
| `Header.checkPow` returns **true** for a real Ergo mainnet header. | Probe: the same 8 Ergo headers |
| `Header.checkPow` returns **false** for a valid YOLO header. It applies Ergo's rule, which feeds the block height into the proof of work; YOLO feeds height / 4. A contract that checks YOLO headers must compute the hit with `Global.powHit` at height / 4 with the table size N for that value. | Probe: 1 YOLO test-chain header. The YOLO developer guide states the same. The peg project reports the same for four YOLO headers; that run was not repeated here |
| A header with one bit of the nonce or of the timestamp changed fails a contract that requires `hdr.id == id && hdr.checkPow`. | Harness result (relay contract, 2 cases) |
| `Global.deserializeTo[Box](bytes)` accepts the bytes a node stores for a box in its UTXO state tree, and the `.id` of the parsed box is that tree's key. So `header.stateRoot.get(box.id, proof)` proves that the box existed in the state after that block. | Harness result: 4 real boxes from a YOLO test node with that node's own proofs, each accepted; a box's bytes with another box's proof, bytes with the amount changed, and a header with a different state root each rejected |
| The node endpoint `POST /utxo/getBoxesBinaryProof` proves a box against the node's current tip only. | Stated in the handoff from the peg project as read in the node source. Not checked for this page |

**What it changes for audit work.**

- A relay or light-client contract on Ergo that reads YOLO headers and calls `checkPow` accepts nothing: fail-closed, a liveness defect. The opposite mistake is the dangerous one: a contract that skips the work check because `checkPow` "did not work", or that calls `powHit` with the wrong height input or N, accepts headers nobody mined.
- Any comparison that treats `decodeNbits` as a target is inverted. Check the direction of every inequality against the hit.
- A state proof shows a box existed after one block. It says nothing about whether the box is still unspent. See the proposed cross-chain traps.
- `None.get` on a failed AVL lookup throws, so a missing key rejects the transaction. That is fail-closed, as in the arithmetic rules.

**Limits.** Library-level results on `sigma-state` 6.0.7. The YOLO header and boxes come from private test chains; no public YOLO network exists. Methods not named in this table (`Global.powHit` taken alone, `UnsignedBigInt` arithmetic, `encodeNbits`, the bitwise and shift methods, `getVarFromInput`) have no probe result here: read the language specification and probe them.
