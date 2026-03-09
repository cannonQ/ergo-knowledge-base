---
title: "DORT/GORT Buyback Bot — Technical Reference"
category: guide
difficulty: advanced
tags: [dexy, dort, gort, buyback, spectrum-dex, transaction-building, ergo-lib-wasm]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# DORT/GORT Buyback Bot — Technical Reference

**Date:** January 2026
**Protocol:** Dexy USD (USE stablecoin on Ergo blockchain)
**Stack:** Node.js + ergo-lib-wasm-nodejs + Local/Remote Ergo node

---

## Infrastructure

The bot runs on a Windows 10 workstation via Task Scheduler, executing buyback swaps against Spectrum Finance LP pools on Ergo mainnet. It interacts with an Ergo full node for block headers and transaction submission, and the Explorer API for box discovery.

| Component | Detail |
|-----------|--------|
| Runtime | Node.js (ESM modules) |
| Signing library | `ergo-lib-wasm-nodejs` |
| Environment | `dotenv` loading `.env.local` |
| Primary node | `http://<LOCAL_NODE_IP>:9053` (local indexed node) |
| Backup node | `http://<REMOTE_NODE_IP>:9053` (remote) |
| Explorer API | `https://api.ergoplatform.com/api/v1` |
| Scheduling | Windows Task Scheduler (9 AM + 9 PM daily) |
| Notifications | Telegram bot + Windows toast + log file |

---

## What the Bot Does

The buyback bot executes small, automated ERG→Token swaps through the Dexy protocol's buyback contract boxes. These boxes accumulate ERG from protocol fees (every $USE mint/purchase contributes). The bot applies gentle, sustained buy pressure on DORT (and GORT) by swapping 1% of the buyback box's ERG balance per run, twice daily.

The buyback box is a permissionless smart contract — anyone can build and submit a valid swap transaction. The bot operator only pays the miner fee (~0.0011 ERG); the swap ERG comes from the contract box itself.

---

## Token Configuration

| Parameter | DORT | GORT |
|-----------|------|------|
| Token ID | `ae399fcb...3cb2dd` | (separate config) |
| LP Pool NFT | `35bc7189...035f0e` | (separate config) |
| Buyback Contract NFT | `dcce07af...92da4f` | `bf24ed4a...3755c` |
| LP Fee | 990/1000 (1%) | 997/1000 (0.3%) |
| Token Decimals | 0 | 0 |

**GORT Buyback NFT gotcha:** The deployment documentation had a truncated 62-character NFT ID. Ergo token IDs are always 64 hex characters. The missing two characters caused lookup failures until the full ID was sourced from the actual on-chain box.

---

## Transaction Structure

Every buyback swap produces exactly 4 outputs from 3+ inputs:

**Inputs:**
1. LP Box (no context extension — permissionless contract)
2. Buyback Box with `ContextExtension {0: 0x0400}` (action=0 for swap)
3. Fee funding box(es) from operator wallet (P2PK, requires signature)

**Outputs:**
1. LP Box (updated reserves)
2. Buyback Box (less ERG, more token, R4 = input box ID)
3. Change box (fee wallet remainder)
4. Miner fee box (explicit output to the EIP-27 miner fee contract)

**Critical contract requirement (DORT):** The output buyback box must have `R4 = Coll[Byte]` containing the input buyback box's `boxId`. The contract validates `OUTPUTS(1).R4[Coll[Byte]].get == SELF.id`. Omitting R4 causes the contract to fail with `Option.get on None`. This was discovered only after the bot failed on-chain — the GORT contract documentation did not mention this requirement, and initial development was based on GORT examples.

---

## LP Swap Math (Constant Product AMM)

The Spectrum LP uses a constant product formula with a fee deduction on the input side.

**Buy (ERG → Token):**

```
tokenOutput = (tokenReserve × ergInput × feeNum) / (ergReserve × feeDenom + ergInput × feeNum)
```

**Slippage calculation:**

```
spotPrice     = tokenReserve / ergReserve
effectiveRate = tokenOutput / ergInput
slippage      = (spotPrice - effectiveRate) / spotPrice × 100
```

**Fee is stored in the LP box's R4 register.** For DORT, `R4 = 990` means 990/1000 = 99% retained → 1% fee. For GORT, `R4 = 997` means 0.3% fee. The bot reads R4 at runtime rather than hardcoding, though a default is provided as fallback.

**Optimal swap sizing:** A binary search finds the maximum ERG amount that keeps slippage at or below a target (default 2%):

```javascript
function calcOptimalBuyback(ergAvailable, ergReserve, tokenReserve, maxSlippage = 2.0) {
  let low = 100_000_000n;   // 0.1 ERG min
  let high = ergAvailable - 10_000_000n;
  let best = low;
  while (low <= high) {
    const mid = (low + high) / 2n;
    const slippage = calcSlippage(mid, ergReserve, tokenReserve);
    if (slippage <= maxSlippage) {
      best = mid;
      low = mid + 100_000_000n;
    } else {
      high = mid - 100_000_000n;
    }
  }
  return best;
}
```

For a pool with ~146 ERG / 79,881 DORT, 2% slippage caps at ~2.28 ERG per swap. The daily 1% auto-mode typically swaps ~0.84 ERG per run (1% of ~84 ERG balance), well under the 2% slippage ceiling.

---

## The Big Bug: JavaScript Number Precision Loss

This was the single hardest issue in the entire project, consuming multiple debugging sessions before root cause was identified.

### The Problem

Spectrum LP boxes contain an LP token with an amount near `2^63`: `9223372036747791116`. JavaScript's `Number` type can only represent integers accurately up to `2^53` (~9 quadrillion). When `response.json()` parses the Explorer API response, this value silently truncates to `9223372036747791000` — a difference of 116.

This causes a cascade:

1. `ErgoBox.from_json()` receives the truncated amount
2. ergo-lib recalculates the box ID from the (now incorrect) serialized bytes
3. The calculated box ID doesn't match the Explorer-provided box ID
4. Error: `Box id parsed from JSON ... differs from calculated from box serialized bytes ...`

Even when the box parsed successfully, the signed transaction contained the wrong LP token amount. The node correctly rejected it with the misleading error `Amount of Ergs in inputs should be equal to amount of Erg in outputs`, which sent debugging in the wrong direction for hours.

### The Fix (Two Parts)

**Part 1 — Preserve large numbers during JSON parsing:**

```javascript
async function fetchJsonSafe(url) {
  const response = await fetch(url);
  const text = await response.text();
  // Wrap any integer with 12+ digits in quotes before parsing
  const safeText = text.replace(/:(\s*)(\d{12,})(\s*[,\}\]])/g, ':"$2"$3');
  return JSON.parse(safeText);
}
```

**Part 2 — Use binary serialization for transaction submission:**

Even with string-preserved amounts flowing through the build pipeline correctly, `signedTx.to_json()` converts I64 values back to JavaScript Number, re-introducing precision loss. The fix is to bypass JSON entirely for submission:

```javascript
const txBytes = Buffer.from(signedTx.sigma_serialize_bytes()).toString('hex');
const response = await fetch(`${ERGO_NODE}/transactions/bytes`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(txBytes)  // hex string, not a JS object
});
```

The `/transactions/bytes` endpoint accepts a hex-encoded sigma-serialized transaction. This preserves full 64-bit integer precision and is the reason the first successful DORT buyback transaction worked.

### Lesson

Any time an Ergo box contains token amounts exceeding `Number.MAX_SAFE_INTEGER` (9,007,199,254,740,991), standard `JSON.parse()` will silently corrupt the data. Always use a text-first approach with regex number preservation, and always submit transactions via binary serialization.

---

## Box Cleaning for ergo-lib

The Explorer API returns box data with extra fields and nested register objects that ergo-lib cannot parse. A cleaning function strips the response down to the exact fields ergo-lib expects:

```javascript
function cleanBoxForErgoLib(box) {
  const cleaned = {
    boxId: box.boxId,
    value: typeof box.value === 'string' ? box.value : box.value.toString(),
    ergoTree: box.ergoTree,
    creationHeight: box.creationHeight,
    assets: (box.assets || []).map(a => ({
      tokenId: a.tokenId,
      amount: typeof a.amount === 'string' ? a.amount : a.amount.toString()
    })),
    additionalRegisters: {},
    transactionId: box.transactionId,
    index: box.index
  };
  
  if (box.additionalRegisters) {
    for (const [reg, data] of Object.entries(box.additionalRegisters)) {
      if (data) {
        if (typeof data === 'object' && data.serializedValue) {
          cleaned.additionalRegisters[reg] = data.serializedValue;
        } else if (typeof data === 'string') {
          cleaned.additionalRegisters[reg] = data;
        }
      }
    }
  }
  
  return cleaned;
}
```

**Key points:**

- `value` and `amount` must be strings (not numbers) to preserve precision for large values.
- Explorer wraps registers as objects with `serializedValue` and `renderedValue` — ergo-lib needs only the raw hex string.
- `transactionId` and `index` are required for box identity — without them, ergo-lib can't match the box ID.
- Extra Explorer fields like `globalIndex`, `settlementHeight`, `mainChain`, `spentTransactionId`, token `name`, `decimals`, and `type` must be omitted — they cause parsing failures.

---

## Wallet and Signing

### Key Derivation (EIP-3)

The bot uses BIP-44/EIP-3 derivation at path `m/44'/429'/0'/0/0`:

```javascript
const seed = lib.Mnemonic.to_seed(mnemonic, '');
const root = lib.ExtSecretKey.derive_master(seed);
const path = lib.DerivationPath.new(0, new Uint32Array([0]));
const derived = root.derive(path);
const secretKey = lib.SecretKey.dlog_from_bytes(derived.secret_key_bytes());
const address = derived.public_key().to_address().to_base58(lib.NetworkPrefix.Mainnet);
```

**Do not use `Wallet.from_mnemonic()`** — use `Wallet.from_secrets()` with the manually derived key. The manual derivation matches what Nautilus wallet produces.

### ErgoStateContext

Signing requires block headers for script evaluation context:

```javascript
async function createStateContext(lib) {
  const response = await fetch(`${ERGO_NODE}/blocks/lastHeaders/10`);
  const headersData = await response.json();
  
  const blockHeaders = lib.BlockHeaders.from_json(headersData);  // Array directly, NOT JSON string
  const latestHeader = lib.BlockHeader.from_json(JSON.stringify(headersData[0]));
  const preHeader = lib.PreHeader.from_block_header(latestHeader);
  
  if (lib.Parameters?.default) {
    return new lib.ErgoStateContext(preHeader, blockHeaders, lib.Parameters.default());
  }
  return new lib.ErgoStateContext(preHeader, blockHeaders);
}
```

**Critical: `BlockHeaders.from_json()` takes a JavaScript array, not a JSON string.** Passing `JSON.stringify(headersData)` produces `Failed to parse BlockHeader from JSON string: JsValue("{")`. This wasted an entire debugging session.

**Also critical:** ergo-lib 0.28+ requires a third `Parameters` argument to `ErgoStateContext`. Older versions do not. The bot feature-detects `lib.Parameters?.default` to handle both.

### Signing Mechanics

Only the fee-funding input box requires a wallet signature. The LP box and buyback box are smart contracts — ergo-lib generates empty proofs for them:

```
Input 0 (LP):      proof EMPTY (contract)
Input 1 (Buyback): proof EMPTY (contract)
Input 2 (Fee):     proof 112 bytes
```

---

## Context Extension: The action=0 Pattern

The buyback contract uses a context variable at index 0 to determine the action. For a swap, the value is `Int(0)`, serialized as `0x0400` (SInt type tag `04` + ZigZag-encoded `0`).

```javascript
const contextExt = new lib.ContextExtension();
contextExt.set_pair(0, lib.Constant.from_i32(0));
```

In the unsigned transaction JSON, this appears as:

```json
{ "boxId": "...", "extension": { "0": "0400" } }
```

The LP box input has an empty extension (`{}`). The fee funding box also has an empty extension.

---

## Miner Fee as Explicit Output

The miner fee is an explicit 4th output box, not implicit. Using ergo-lib's `UnsignedTransaction` constructor, the fee parameter is set to `MIN_BOX_VALUE` (not the actual fee), and the real fee appears as a dedicated output to the EIP-27 miner fee contract:

```javascript
const minerFeeTree = lib.ErgoTree.from_base16_bytes(MINER_FEE_ERGO_TREE);
const feeOutBuilder = new lib.ErgoBoxCandidateBuilder(
  lib.BoxValue.from_i64(lib.I64.from_str(TX_FEE.toString())),
  lib.Contract.pay_to_address(lib.Address.recreate_from_ergo_tree(minerFeeTree)),
  height
);
```

The balance check is: total input nanoERG = total output nanoERG (all 4 outputs). The difference must be exactly 0. Earlier iterations omitted the miner fee output and relied on the UnsignedTransaction constructor's fee parameter, which produced valid-looking transactions that were silently rejected.

---

## Multiple Buyback Boxes

The GORT buyback NFT exists in multiple UTXO boxes (3 were observed). The bot queries for all unspent boxes containing the buyback NFT and selects the one with the most ERG (`selectRichest` flag). Without this, it would pick the first result, which might have only 1 ERG — enough for exactly 1 swap that buys ~1 token.

```javascript
if (selectRichest && data.items.length > 1) {
  const sorted = data.items.sort((a, b) => {
    const aVal = BigInt(a.value);
    const bVal = BigInt(b.value);
    return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
  });
  return sorted[0];
}
```

---

## Multi-Buyback Mode

For spending a larger portion of the buyback balance efficiently, the bot supports a multi-swap mode. Binary search determines the optimal ERG amount per swap at a target slippage, then executes them sequentially with a 5-second delay between each.

**Example at 2% slippage with ~90 ERG available:**

| Metric | Value |
|--------|-------|
| Swaps | 17 |
| Total ERG spent | 44.90 ERG |
| Total DORT received | 18,732 DORT |
| Avg slippage | 1.90% |
| Total miner fees | 0.019 ERG |
| Effective rate | 417.2 DORT/ERG |

Compared to a single 45 ERG swap which would exceed 25% slippage and be rejected by the contract.

**Slippage efficiency tradeoff:**

| Target Slippage | Swaps | Effective Rate |
|-----------------|-------|----------------|
| 1% | 20 | 494.5 DORT/ERG |
| 2% | 17 | 417.2 DORT/ERG |

Lower slippage per swap yields better effective rates but requires more transactions. For daily automated operation, the 1% auto-mode (1% of balance, ~0.84 ERG per swap) achieves excellent per-swap efficiency.

---

## Race Conditions

Multiple operators may be running buyback bots or manually executing swaps against the same LP and buyback boxes. When two transactions target the same input boxes, one will be mined and the other will fail with a "double spent" error. This is expected behavior, not a bug. The bot should handle this gracefully — log the error and try again on the next scheduled run.

The first live DORT buyback transaction succeeded, but a simultaneous operator was observed submitting their own swap at the same time. Their transaction used a lower miner fee (0.002 ERG vs our 0.0011 ERG).

---

## Notification System

Three notification channels run in parallel after every execution:

**Telegram bot:** Sends HTML-formatted message via the Bot API with the swap summary and a clickable Explorer link. Uses `parse_mode: 'HTML'` and `disable_web_page_preview: false` for the link preview.

**Windows toast:** Uses `node-notifier` for a system notification popup. Installed via `npm install node-notifier`. Fails silently if the package isn't installed.

**Log file:** Appends timestamped entries to `./logs/buyback.log`. The log file revealed a UTF-8 encoding issue where the arrow character `→` rendered as `â†'` in the Windows console log — a cosmetic issue only.

---

## Windows Task Scheduler Setup

Two tasks are configured: DORT AM (9:00 AM) and DORT PM (9:00 PM).

| Field | Value |
|-------|-------|
| Program/script | `node` |
| Add arguments | `buyback-bot.js --token DORT` |
| Start in | `C:\Users\...\DORT+GORT BOT` |

The "Start in" field is critical — without it, the task can't find `.env.local` or the bot script. "Run whether user is logged on or not" must be selected for unattended operation (requires entering the Windows password).

The first scheduled run fired but produced no notification, leading to a manual run for verification. After confirming the Telegram integration worked, subsequent scheduled runs operated correctly.

---

## Node Fallback Pattern

The bot tries the local node first, then falls back to the remote backup:

```javascript
const nodes = [
  'http://<LOCAL_NODE_IP>:9053',   // Local
  'http://<REMOTE_NODE_IP>:9053'   // Remote backup
];
```

Early runs using only a remote node encountered intermittent `fetch failed` errors — likely network timeouts or node restarts. Adding the local node as primary eliminated these. If the local node is down, the bot automatically tries the backup.

The Explorer API (`api.ergoplatform.com`) is used for box discovery (finding LP and buyback boxes by NFT ID, fetching wallet UTXOs) but not for transaction submission. The node API's `/transactions/bytes` endpoint is always used for submission.

---

## Minimum Swap Amounts

Through testing, the following minimum thresholds were established:

| Amount | Result |
|--------|--------|
| 0.1 ERG | ✅ Works (posted live on mainnet) |
| 0.2 ERG | ✅ Works (initially adjusted to 0.3 by floor, then floor lowered) |
| 0.3 ERG | ✅ Works (original minimum) |

The minimum was initially set at 0.3 ERG and later lowered to 0.2 ERG after testing confirmed 0.1 ERG transactions posted successfully. The minimum protects against dust transactions where the token output rounds to 0.

---

## DORT vs GORT Contract Differences

Despite using the same general buyback pattern, the two contracts have a critical difference:

| Feature | DORT Buyback | GORT Buyback |
|---------|-------------|-------------|
| R4 on output | **Required** (input box ID) | Not required |
| LP Fee | 1% (990/1000) | 0.3% (997/1000) |
| Buyback box count | 1 | 3+ (select richest) |
| Typical balance | ~84 ERG | ~1 ERG per box |

This difference was discovered the hard way: the bot was initially built from GORT buyback documentation which didn't mention R4. When deployed against the DORT contract, the transaction failed on-chain with `v4.getReg(4).get == SELF.id → Not found: calling Option.get on None`. Adding R4 as `Coll[Byte]` of the input box ID fixed it.

---

## Evolution Timeline

| Phase | Key Milestone |
|-------|--------------|
| v0.1 | `lp-swap.js` unified CLI — builds and signs TX, but Explorer returns 200 without confirming |
| v0.2 | Diagnosed JSON precision loss in LP token amount |
| v0.3 | Added `fetchJsonSafe` regex for large number preservation |
| v0.4 | Discovered `sigma_serialize_bytes()` for binary submission |
| v0.5 | First successful DORT buyback posted to mainnet via `/transactions/bytes` |
| v1.0 | `dort-buyback-bot.js` — clean single-purpose bot with auto/custom swap modes |
| v1.5 | Multi-buyback mode added (batch sequential swaps with slippage targeting) |
| v2.0 | `buyback-bot.js` — DORT + GORT dual-token support, Telegram/Windows notifications, local node with fallback, Task Scheduler automation |

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `ERGO_SERVER_MNEMONIC` | 15-word BIP39 mnemonic for fee-funding wallet |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Target chat/group ID for notifications |

All stored in `.env.local` (never committed to version control).

---

## Ergo Node API Patterns Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/blocks/lastHeaders/10` | GET | Block headers for ErgoStateContext |
| `/info` | GET | Current blockchain height |
| `/transactions/bytes` | POST | Submit signed TX as hex bytes |

| Explorer Endpoint | Method | Purpose |
|-------------------|--------|---------|
| `/boxes/unspent/byTokenId/{id}` | GET | Find LP box and buyback box by NFT |
| `/boxes/unspent/byAddress/{addr}` | GET | Find fee-funding UTXOs |

---

## Debugging Checklist

When a buyback transaction fails, check in this order:

1. **Has the input box been spent?** Another operator may have beat you (race condition).
2. **Is the LP token amount correct?** Check for Number precision loss — the LP token near `2^63` is the most common failure cause.
3. **Is R4 set on the buyback output?** DORT requires it, GORT does not.
4. **Is the context extension correct?** Must be `{0: 0x0400}` for action=0 swap.
5. **Are all registers preserved on LP output?** Copy R4 (fee numerator) from input.
6. **Is the token order preserved?** LP output tokens must appear in the same order as the input.
7. **Is the balance exactly zero?** Sum of all output nanoERG must equal sum of all input nanoERG.
8. **Are you using binary submission?** JSON submission via `/transactions` will fail due to precision loss.

---

## Prior Art

The signing infrastructure was adapted from `ergo-sign-tx.js` and `ergo-tx_2_.js`, which had been successfully posting transactions to Ergo mainnet for other projects. The key derivation pattern, `Wallet.from_secrets()` approach, and ErgoStateContext construction were proven in that context before being adapted for the more complex multi-input buyback transaction.
