---
title: "Oracle Pool v2 — Update Contract"
description: "Governance threshold check, ballot counting, and pool box script replacement"
category: ecosystem
difficulty: advanced
tags: [oracle-pool, eip-0023, ergoscript, governance, update]
source: ergo-eips
source_url: "https://github.com/ergoplatform/eips/tree/cae50b72/eip-0023/contracts/update_contract.es"
project: ergoplatform-oracle-core
updated: 2026-03-15
---

# Update Contract (EIP-0023)

Guards the update box and enforces the governance threshold for pool updates. Counts valid ballot boxes, verifies they all agree on the proposed change, and ensures the pool box is correctly replaced while preserving tokens, rate, and epoch counter.

## Box Layout

- **tokens(0):** Update-NFT (singleton)
- **Registers:** Empty (stateless)

## ErgoScript

```ergoscript
{ // This box (update box):
  // Registers empty
  //
  // ballot boxes (Inputs)
  // R4 the pub key of voter [GroupElement] (not used here)
  // R5 the creation height of this box [Int]
  // R6 the value voted for [Coll[Byte]] (hash of the new pool box script)
  // R7 the reward token id in new box
  // R8 the number of reward tokens in new box

  val poolNFT = fromBase64("...")      // replace with actual
  val ballotTokenId = fromBase64("...") // replace with actual
  val minVotes = 6

  val poolIn = INPUTS(0)  // pool box is 1st input
  val poolOut = OUTPUTS(0) // copy of pool box is 1st output

  val updateBoxOut = OUTPUTS(1) // copy of this box is 2nd output

  // compute the hash of the pool output box — this should match what ballots voted for
  val poolOutHash = blake2b256(poolOut.propositionBytes)
  val rewardTokenId = poolOut.tokens(1)._1
  val rewardAmt = poolOut.tokens(1)._2

  val validPoolIn = poolIn.tokens(0)._1 == poolNFT

  val validPoolOut = poolIn.tokens(0) == poolOut.tokens(0)                && // NFT preserved
                     poolIn.value == poolOut.value                        && // value preserved
                     poolIn.R4[Long] == poolOut.R4[Long]                  && // rate preserved
                     poolIn.R5[Int] == poolOut.R5[Int]                    && // counter preserved
                     ! (poolOut.R6[Any].isDefined)

  val validUpdateOut = updateBoxOut.tokens == SELF.tokens                     &&
                       updateBoxOut.propositionBytes == SELF.propositionBytes &&
                       updateBoxOut.value >= SELF.value                       &&
                       updateBoxOut.creationInfo._1 > SELF.creationInfo._1    &&
                       ! (updateBoxOut.R4[Any].isDefined)

  def isValidBallot(b:Box) = if (b.tokens.size > 0) {
    b.tokens(0)._1 == ballotTokenId       &&
    b.R5[Int].get == SELF.creationInfo._1 && // vote corresponds to this update box
    b.R6[Coll[Byte]].get == poolOutHash   && // voted for this pool script
    b.R7[Coll[Byte]].get == rewardTokenId && // voted for this reward token
    b.R8[Long].get == rewardAmt              // voted for this reward amount
  } else false

  val ballotBoxes = INPUTS.filter(isValidBallot)

  val votesCount = ballotBoxes.fold(0L, {(accum: Long, b: Box) => accum + b.tokens(0)._2})

  sigmaProp(validPoolIn && validPoolOut && validUpdateOut && votesCount >= minVotes)
}
```

## Key Design Patterns

- **`blake2b256(poolOut.propositionBytes)`** — The update contract hashes the *output* pool box script and compares it against what each ballot voted for (R6). This is a **hash-locked governance** pattern — voters commit to a specific contract hash, not the contract itself.
- **`b.R5[Int].get == SELF.creationInfo._1`** — Each ballot's R5 must match the update box's creation height. This ties votes to a specific update proposal and prevents stale votes from being reused.
- **`updateBoxOut.creationInfo._1 > SELF.creationInfo._1`** — The output update box must have a strictly higher creation height, invalidating all current ballots. This is the "vote reset" mechanism — after any update (successful or not), a new round of voting is required.
- **`ballotBoxes.fold(0L, ... + b.tokens(0)._2)`** — Vote counting sums ballot token quantities, not just box count. If someone holds multiple ballot tokens in one box, each token counts as one vote.
- **`validPoolOut` preserves R4 (rate) and R5 (counter)** — The update can change the pool script but must preserve the current oracle data. This prevents an update from disrupting active data feeds.

## Security Notes

- `! (poolOut.R6[Any].isDefined)` — Ensures no extra registers are injected into the new pool box.
- `! (updateBoxOut.R4[Any].isDefined)` — The output update box has empty registers, preventing it from being misused as a ballot.
- The update box is **stateless** (no meaningful registers) — its only role is to gate the update transaction and provide a creation height for ballot correlation.
- Three things are voted on independently: pool script hash (R6), reward token ID (R7), reward token amount (R8). All must match across all counted ballots.
