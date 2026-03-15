---
title: "Oracle Pool v2 — Pool Contract"
description: "Minimal pool box guard requiring refresh-NFT or update-NFT in second input"
category: ecosystem
difficulty: advanced
tags: [oracle-pool, eip-0023, ergoscript, pool-box, singleton-nft]
source: ergo-eips
source_url: "https://github.com/ergoplatform/eips/tree/cae50b72/eip-0023/contracts/pool_contract.es"
project: ergoplatform-oracle-core
updated: 2026-03-15
---

# Pool Contract (EIP-0023)

The pool contract is deliberately minimal — it only checks that the second input contains either the refresh-NFT or the update-NFT. All validation logic is delegated to those contracts, keeping the pool box compact for use as a data-input in consumer dApps (SigmaUSD, Dexy, etc.).

## Box Layout

- **tokens(0):** Pool-NFT (singleton identifying this as the canonical pool box)
- **tokens(1):** Reward tokens (emitted to oracles during refresh)
- **R4:** Current data point / rate (Long)
- **R5:** Current epoch counter (Int)

## ErgoScript

```ergoscript
{
  // This box (pool box)
  //   epoch start height is stored in creation Height (R3)
  //   R4 Current data point (Long)
  //   R5 Current epoch counter (Int)
  //
  //   tokens(0) pool token (NFT)
  //   tokens(1) reward tokens
  //   When initializing the box, there must be one reward token.
  //   When claiming reward, one token must be left unclaimed

  val otherTokenId = INPUTS(1).tokens(0)._1
  val refreshNFT = fromBase64("...") // replace with actual token id
  val updateNFT = fromBase64("...")  // replace with actual token id

  sigmaProp(otherTokenId == refreshNFT || otherTokenId == updateNFT)
}
```

## Security Notes

- The pool box can **only** be spent when the refresh box or update box is the second input. This is enforced by checking `INPUTS(1).tokens(0)._1`.
- All rate validation, reward accounting, and epoch checks are in the [refresh contract](refresh-contract.md), not here.
- Consumer dApps reference the pool box as a **data-input** (read-only), so the pool box is never spent by external protocols.
