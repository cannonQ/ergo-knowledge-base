---
title: "Oracle Pool v2 — Oracle Contract"
description: "Owner-signed data point posting, reward token accumulation, and oracle token transfer"
category: ecosystem
difficulty: advanced
tags: [oracle-pool, eip-0023, ergoscript, oracle-box, proveDlog]
source: ergo-eips
source_url: "https://github.com/ergoplatform/eips/tree/cae50b72/eip-0023/contracts/oracle_contract.es"
project: ergoplatform-oracle-core
updated: 2026-03-15
---

# Oracle Contract (EIP-0023)

Guards each oracle box. Supports three operations: owner-initiated actions (publish data, extract rewards, transfer token) and collection (during refresh, pool adds reward tokens).

## Box Layout

- **tokens(0):** Oracle token (one per oracle)
- **tokens(1):** Reward tokens (accumulated during refresh cycles)
- **R4:** Owner's public key (GroupElement)
- **R5:** Epoch counter at post time (Int)
- **R6:** Published data point / rate (Long)

## ErgoScript

```ergoscript
{ // This box (oracle box)
  //   R4 public key (GroupElement)
  //   R5 epoch counter of current epoch (Int)
  //   R6 data point (Long) or empty
  //
  //   tokens(0) oracle token (one)
  //   tokens(1) reward tokens collected (one or more)
  //
  //   When publishing a datapoint, there must be at least one reward token at index 1
  //
  //   Connected to pool NFT in input #0 (not refresh NFT in input #1)
  //   This way, the same box works after updating the pool

  val poolNFT = fromBase64("...") // replace with actual

  val otherTokenId = INPUTS(0).tokens(0)._1

  val minStorageRent = 10000000L
  val selfPubKey = SELF.R4[GroupElement].get
  val outIndex = getVar[Int](0).get
  val output = OUTPUTS(outIndex)

  val isSimpleCopy = output.tokens(0) == SELF.tokens(0)                && // oracle token preserved
                     output.propositionBytes == SELF.propositionBytes  && // script preserved
                     output.R4[GroupElement].isDefined                 && // must have a public key
                     output.value >= minStorageRent                       // prevent garbage collection

  val collection = otherTokenId == poolNFT                    && // first input must be pool box
                   output.tokens(1)._1 == SELF.tokens(1)._1   && // reward tokenId preserved
                   output.tokens(1)._2 > SELF.tokens(1)._2    && // at least one reward token added
                   output.R4[GroupElement].get == selfPubKey  && // preserve public key during collection
                   output.value >= SELF.value                 && // nanoErgs preserved
                   ! (output.R5[Any].isDefined)                  // no registers beyond R4; prevents reuse as valid data-point

  val owner = proveDlog(selfPubKey)

  // owner can transfer to another public key by setting different value in R4
  isSimpleCopy && (owner || collection)
}
```

## Key Design Patterns

- **`getVar[Int](0)` for output index** — The oracle's output position is passed as a context variable, enabling flexible transaction construction where oracles appear at varying indices.
- **`isSimpleCopy && (owner || collection)`** — Two spending paths: owner signs (publish/transfer/extract), or pool box is present as input 0 (collection during refresh).
- **`! (output.R5[Any].isDefined)`** during collection — Clears R5/R6 to prevent a collected oracle box from being counted as a fresh data point in the same epoch.
- **`output.tokens(1)._2 > SELF.tokens(1)._2`** — Enforces that at least one reward token is added during collection. The refresh contract controls the exact amount.
- **Connected to pool NFT, not refresh NFT** — Deliberate design choice: the oracle box checks `INPUTS(0)` for pool-NFT. This means the same oracle box works after a pool update (new refresh-NFT) without needing to be recreated.

## Security Notes

- `minStorageRent = 10000000L` (0.01 ERG) prevents oracle boxes from being garbage-collected by storage rent.
- Owner can change R4 (public key transfer) but the script itself is preserved — no path to change the contract.
- During collection, the public key is explicitly preserved (`output.R4[GroupElement].get == selfPubKey`), preventing oracle theft during refresh.
