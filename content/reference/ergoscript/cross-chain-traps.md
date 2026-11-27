---
title: "Proposed Cross-Chain Traps (X1–X8)"
description: "Proposed audit traps for contracts that trust another chain's headers or state proofs. Not from real losses. Injected by the audit tools when the contract deserializes a Header or Box or checks proof of work."
category: reference
difficulty: advanced
tags: [ergoscript, audit, traps, cross-chain, relay, peg, bridge, header, proposed]
sdk: [none]
author: CannonQ
source: original
license: AGPL-3.0
updated: 2026-11-26
index: false
---
# Proposed cross-chain traps

**Status: proposed. None of these comes from a real loss.** The pre-named traps T1 to T21 each name a real finding as their origin. These eight do not. They come from writing and testing one two-way peg draft (a header relay, a vault and a pool) in November 2026, and they stay marked as proposed until a real engagement confirms or removes them. Do not cite them as precedent, and do not raise a finding's severity because it matches one.

They apply when a contract trusts another chain's headers or proves another chain's state: it deserializes a `Header` or a `Box`, checks proof of work, or reads a relay box that does. Return a verdict for each with the same vocabulary as the T traps (PRESENT, ABSENT with the closing line cited, N/A, PARTIAL), and label each verdict "proposed trap".

| ID | Class | Check |
|---|---|---|
| X1 | Header trusted on its own stated difficulty | Is the difficulty of each new header bounded against its parent's, by the source chain's own adjustment rule? Without that, a minority miner wins with one lucky block that states a high difficulty. |
| X2 | Confirmations counted in blocks | Is depth counted in work, at the proven header's own difficulty? If it is counted in blocks, a run of cheap low-difficulty blocks stands in for depth. |
| X3 | Wrong proof-of-work rule for the chain being read | `Header.checkPow` applies Ergo's rule. A header from a chain with another rule (YOLO feeds height / 4) needs `Global.powHit` with that chain's inputs. Check the height input, the table size N and the direction of the comparison against the target. |
| X4 | Start state the script cannot check | A relay's first header, or a registry that is not empty at creation, is taken on trust by every later spend. Is there a published start procedure and a check anyone can run against the creation box? |
| X5 | Cap window that can be backdated across idle periods | After N idle windows, can the window start be set in the past so that the cap is taken N times in one block? Close relative of T10 and T14. |
| X6 | Record larger than the cap | Can a user create a claim that no window can ever pay? Then the funds behind it are locked for good. |
| X7 | Proof of a box that must still exist | Does a claim depend on one specific box staying unspent until it is proven? A record in a tree that only grows avoids the race. |
| X8 | One side weaker than the other | In a two-way peg, the direction that reads the smaller chain is the cheap one to attack. Is the loss bounded in both directions, and can it be stopped? |

Origin of all eight: one peg draft and its test harness, YOLO project, November 2026. No engagement, no deployed contract, no loss.
