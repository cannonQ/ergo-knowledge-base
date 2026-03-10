---
title: "Plasma-AVL Phase 2.4-2.6 Race Resolution Patterns"
category: reference
difficulty: advanced
tags: [avl-tree, plasma-toolkit, height-tolerance, mempool, ergoscript]
author: CannonQ
source: original
source_url: ""
license: AGPL-3.0
updated: 2026-03-09
---
# Plasma-AVL Skill Addendum — Phase 2.4/2.5/2.6 Race Resolution

Lessons from the race resolution contract (1223-byte ErgoTree, 3 resolution paths, 10 context vars, CONTEXT.headers block hash pinning) tested on Ergo mainnet across 14 test runs (Feb–Mar 2026, heights 1731997–1732655).

## Additions to Main Skill

### HEIGHT Tolerance — Mempool CleanupWorker Eviction (CRITICAL UPDATE)

**The ±1 tolerance documented in the main skill is insufficient.** Change to ±10.

Ergo's `CleanupWorker` re-validates all mempool TXs when a new block arrives using the **new** HEIGHT. Any HEIGHT-dependent script logic will fail re-validation if the TX sits in the mempool for >1 block.

**Evidence (Run 12):** Node log `#0 => Success((false,1455))` — training contract returned false (not cost-exceeded) at cost 1455. The ±1 window was too tight; HEIGHT drifted by 2+ blocks while the TX waited for inclusion.

```ergoscript
// WRONG — ±1 too tight for mempool survival
val lastActionOk = newLastAction >= hL - 1L && newLastAction <= hL

// CORRECT — ±10 survives ~20 min in mempool
val lastActionOk = if (isBonus) newLastAction == oldLastAction
  else newLastAction >= hL - 10L && newLastAction <= hL

val dayStartOk = if (isBonus) newDayStart == oldDayStart
  else if (dayReset) newDayStart >= hL - 10L && newDayStart <= hL
  else newDayStart == oldDayStart
```

**Security analysis:** 10 blocks (~20 min) vs 180-block cooldown — negligible attack surface.

**Key insight:** `Success((false, N))` in node logs means a LOGIC failure (script returned false), NOT a cost budget issue. Our scripts cost 162–1455, far below the 8,001,091 `maxBlockCost`. The JIT cost analysis about foldLeft with `||` creating O(n²) SigmaProp accumulation applies to different contract patterns (e.g., 64-member ring withdrawal), not single-path validation contracts.

---

### CONTEXT.headers — Direct Indexing vs `exists` (CRITICAL)

**Direct indexing into `CONTEXT.headers` is HEIGHT-dependent and WILL be evicted from the mempool.**

`CONTEXT.headers` is a sliding window of the 10 most recent block headers. `CONTEXT.headers(n)` returns the header at height `HEIGHT - 1 - n`. When HEIGHT changes (new block arrives), the index for a given target height changes too.

```ergoscript
// WRONG — HEIGHT-dependent, breaks in mempool
val headerIndex = (HEIGHT - deadlineHeight - 2L).toInt
val pinnedBlockHash = CONTEXT.headers(headerIndex).id
// When HEIGHT changes, headerIndex changes, points to wrong header

// CORRECT — mempool-resilient, searches all headers
val pinnedBlockHash = getVar[Coll[Byte]](3).get
val targetHeight = (deadlineHeight + 1L).toInt
val hashVerified = CONTEXT.headers.exists { (h: Header) =>
  h.id == pinnedBlockHash && h.height == targetHeight
}
```

**Evidence (Run 13):** Node log `#0 => Success((false,162))` — Path A TX evicted at cost 162. The direct indexing failed almost immediately in script evaluation because the header at the new index didn't match the pinned hash.

**Pattern:** Pass the target block hash as a context variable, then verify it exists in CONTEXT.headers at the expected height. The `exists` lambda searches all 10 headers regardless of their position in the sliding window.

**Cost impact:** `CONTEXT.headers.exists` iterates up to 10 headers. This costs more than direct indexing but is the ONLY mempool-safe approach. Path A uses 0.01 ERG fee (10x MinFee) to absorb this cost.

---

### Contract Fee Tolerance — Match Actual TX Fee (CRITICAL)

When a contract checks `refundOutput.value >= SELF.value - N` where N is a fee deduction tolerance, the tolerance MUST match or exceed the actual miner fee used in the TX builder.

```ergoscript
// WRONG — tolerance (1.2M) < actual fee (2M)
val refundAmount = refundOutput.value >= SELF.value - 1200000L
// buildPathBTx uses fee = 2000000L → refund too low → script fails

// CORRECT — tolerance (2.2M) > actual fee (2M)
val refundAmount = refundOutput.value >= SELF.value - 2200000L
```

**Pattern:** Always set tolerance ≥ actual fee + margin. A `Parameters.MinFee` (1,000,000) TX fee needs at least 1,200,000 tolerance. A 2,000,000 fee needs at least 2,200,000.

---

## New Error → Fix Table Entries

| Error | Cause | Fix |
|---|---|---|
| `Success((false,1455))` CleanupWorker eviction | ±1 HEIGHT tolerance too tight for mempool | Widen to ±10 |
| `Success((false,162))` CleanupWorker eviction | `CONTEXT.headers(index)` shifts with HEIGHT | Use `CONTEXT.headers.exists` with context var |
| Path B "Script reduced to false" at sign time | Fee tolerance < actual miner fee | Widen `SELF.value - N` tolerance to match fee |
| `waitForUtxo` polls forever | TX evicted from mempool, test has no timeout | Add timeout or check mempool status |
| `Double spending attempt` (node 400) | Race box already claimed in prior run | Check UTXO first or catch and skip |

---

## New Measured Results

| Metric | Phase 2.4/2.5/2.6 (Race Resolution) |
|---|---|
| ErgoTree size | 1223 bytes |
| Context vars | 4 (Path A), 2 (Path B/C) |
| DataInputs | 1 (Season Box) |
| Resolution paths | 3 (A=resolution, B=cancel, C=timeout) |
| CONTEXT.headers cost | ~162 at failure point |
| Path A fee | 0.01 ERG (10x MinFee, for CONTEXT.headers.exists) |
| Path B fee | 0.002 ERG |
| Path C fee | 0.002 ERG |
| Mempool survival | Confirmed — Path A TX survived block transitions with exists fix |
| All 3 paths on-chain | ✅ Run 14, blocks 1732644–1732655 |

**Phase 2.7/2.8 JitCost (measured on mainnet, Run 13):** See `SKILL_addendum_2.7_2.8.md` for full staging contract metrics — Path A Payout: 168,695, Path B Fraud Proof: 164,402.

---

## New Debugging Checklist Entries

11. **Mempool eviction?** Check node logs for `Success((false,N))` — it's a logic failure, not cost.
12. **CONTEXT.headers indexed or exists?** Direct indexing breaks in mempool. Always use `exists`.
13. **Fee tolerance >= actual fee?** Contract's deduction tolerance must match TX builder's fee.
14. **Resolution window wide enough?** Path A needs `deadlineHeight + 2` to `+ 10` (8-block window).
15. **Staging box script validated?** The real staging contract (1304 bytes) replaced the `sigmaProp(true)` placeholder in Phase 2.7/2.8 — confirmed on mainnet Run 13.

---

## Updated "What This Skill Covers"

Add to coverage list:
- Race resolution with 3 paths (resolution, cancellation, timeout) — Phase 2.4/2.5/2.6
- `CONTEXT.headers.exists` for mempool-resilient block hash pinning
- CleanupWorker re-validation behavior and HEIGHT drift mitigation
- Multi-path contract design (`if/else if/else` on pathId context var)
- Staging box creation with register preservation (R4–R9)
- Challenge window and resolver bond patterns
- Reclaiming locked ERG from old contract versions

## Reference Files

- `references/phase-2.4-2.6-patterns.md` — Resolution paths A/B/C, CONTEXT.headers patterns, staging box registers, fee tolerance, reclaim utilities
- `references/phase-2.7-2.8-patterns.md` — Staging/fraud proof contract, on-chain scoring, leaderboard AVL, off-chain parity
- `SKILL_addendum_2.7_2.8.md` — Phase 2.7/2.8 skill addendum (staging payout, fraud proof, leaderboard)
