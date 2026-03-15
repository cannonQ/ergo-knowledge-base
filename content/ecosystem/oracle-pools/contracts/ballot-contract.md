---
title: "Oracle Pool v2 — Ballot Contract"
description: "Owner-signed voting for pool governance updates and ballot token transfer"
category: ecosystem
difficulty: advanced
tags: [oracle-pool, eip-0023, ergoscript, governance, voting]
source: ergo-eips
source_url: "https://github.com/ergoplatform/eips/tree/cae50b72/eip-0023/contracts/ballot_contract.es"
project: ergoplatform-oracle-core
updated: 2026-03-15
---

# Ballot Contract (EIP-0023)

Guards each ballot box used in the oracle pool governance mechanism. Ballot token holders vote for pool updates (new script, reward token changes) by setting registers on their ballot box. A threshold of votes triggers the update via the [update contract](update-contract.md).

## Box Layout

- **tokens(0):** Ballot token
- **R4:** Owner's public key (GroupElement)
- **R5:** Creation height of the update box being voted on (Int)
- **R6:** Hash of the new pool box script (Coll[Byte])
- **R7:** New reward token ID (Coll[Byte])
- **R8:** New reward token amount (Long)

## ErgoScript

```ergoscript
{ // This box (ballot box):
  // R4 the group element of the owner of the ballot token [GroupElement]
  // R5 the creation height of the update box [Int]
  // R6 the value voted for [Coll[Byte]]
  // R7 the reward token id [Coll[Byte]]
  // R8 the reward token amount [Long]

  val updateNFT = fromBase64("...") // replace with actual

  val minStorageRent = 10000000L

  val selfPubKey = SELF.R4[GroupElement].get

  val outIndex = getVar[Int](0).get
  val output = OUTPUTS(outIndex)

  val isSimpleCopy = output.R4[GroupElement].isDefined                && // ballot boxes are transferable
                     output.propositionBytes == SELF.propositionBytes &&
                     output.tokens == SELF.tokens                     &&
                     output.value >= minStorageRent

  val update = INPUTS.size > 1                           &&
               INPUTS(1).tokens.size > 0                 &&
               INPUTS(1).tokens(0)._1 == updateNFT       && // can only update when update box is 2nd input
               output.R4[GroupElement].get == selfPubKey && // public key preserved
               output.value >= SELF.value                && // value preserved or increased
               ! (output.R5[Any].isDefined)                 // no more registers; prevents reuse as valid vote

  val owner = proveDlog(selfPubKey)

  // unlike in collection, spender need not be a ballot token holder
  isSimpleCopy && (owner || update)
}
```

## Key Design Patterns

- **`isSimpleCopy && (owner || update)`** — Two spending paths: owner signs (vote/transfer), or update box is present as input 1.
- **`! (output.R5[Any].isDefined)`** during update — Clears all registers beyond R4 after the update executes. Prevents a ballot from being counted twice in the same update cycle.
- **`INPUTS(1).tokens(0)._1 == updateNFT`** — The ballot can only be consumed during an update when the update box is specifically at input index 1.
- **Transferable by design** — `output.R4[GroupElement].isDefined` (not `.get == selfPubKey`) allows the owner to set a different public key, transferring ballot ownership.

## Voting Flow

1. Owner sets R5 = update box creation height, R6 = hash of proposed new pool script, R7 = reward token ID, R8 = reward token amount
2. Multiple ballot holders do the same (must all agree on the same values)
3. When `minVotes` (default 6) ballots match, the [update contract](update-contract.md) can execute
4. After update, ballot registers are cleared (R5+ emptied)
