---
title: "Oracle Pool v2 — Refresh Contract"
description: "Epoch validation, data point sorting/averaging, deviation filtering, and reward token emission"
category: ecosystem
difficulty: advanced
tags: [oracle-pool, eip-0023, ergoscript, refresh, data-aggregation]
source: ergo-eips
source_url: "https://github.com/ergoplatform/eips/tree/cae50b72/eip-0023/contracts/refresh_contract.es"
project: ergoplatform-oracle-core
updated: 2026-03-15
---

# Refresh Contract (EIP-0023)

The refresh contract contains the core oracle pool logic. It guards the refresh box and enforces all rules for updating the pool rate: epoch expiry, minimum data points, sorted ordering, deviation bounds, correct averaging, and reward token accounting.

## Box Layout

- **tokens(0):** Refresh-NFT (singleton)

## ErgoScript

```ergoscript
{ // This box (refresh box)
  //   tokens(0) refresh token (NFT)

  val oracleTokenId = fromBase64("...") // replace with actual
  val poolNFT = fromBase64("...")        // replace with actual
  val epochLength = 30
  val minDataPoints = 4
  val buffer = 4
  val maxDeviationPercent = 5 // percent

  val minStartHeight = HEIGHT - epochLength
  val spenderIndex = getVar[Int](0).get // index of spender's data-point box

  val poolIn = INPUTS(0)
  val poolOut = OUTPUTS(0)
  val selfOut = OUTPUTS(1)

  def isValidDataPoint(b: Box) = if (b.R6[Long].isDefined) {
    b.creationInfo._1    >= minStartHeight &&  // data point must not be too old
    b.tokens(0)._1       == oracleTokenId  &&  // first token id must be oracle token
    b.R5[Int].get        == poolIn.R5[Int].get // must correspond to this epoch
  } else false

  val dataPoints = INPUTS.filter(isValidDataPoint)
  val pubKey = dataPoints(spenderIndex).R4[GroupElement].get

  val enoughDataPoints = dataPoints.size >= minDataPoints
  val rewardEmitted = dataPoints.size * 2 // one extra token per box as collector reward
  val epochOver = poolIn.creationInfo._1 < minStartHeight

  val startData = 1L // we don't allow 0 data points
  val startSum = 0L
  // data-points expected sorted in INCREASING order

  val lastSortedSum = dataPoints.fold((startData, (true, startSum)), {
        (t: (Long, (Boolean, Long)), b: Box) =>
           val currData = b.R6[Long].get
           val prevData = t._1
           val wasSorted = t._2._1
           val oldSum = t._2._2
           val newSum = oldSum + currData

           val isSorted = wasSorted && prevData <= currData

           (currData, (isSorted, newSum))
    }
  )

  val lastData = lastSortedSum._1
  val isSorted = lastSortedSum._2._1
  val sum = lastSortedSum._2._2
  val average = sum / dataPoints.size

  val maxDelta = lastData * maxDeviationPercent / 100
  val firstData = dataPoints(0).R6[Long].get

  proveDlog(pubKey)                                               &&
  epochOver                                                       &&
  enoughDataPoints                                                &&
  isSorted                                                        &&
  lastData - firstData     <= maxDelta                            &&
  poolIn.tokens(0)._1      == poolNFT                             &&
  poolOut.tokens(0)        == poolIn.tokens(0)                    && // preserve pool NFT
  poolOut.tokens(1)._1     == poolIn.tokens(1)._1                 && // reward token id preserved
  poolOut.tokens(1)._2     >= poolIn.tokens(1)._2 - rewardEmitted && // reward amount correctly reduced
  poolOut.tokens.size      == poolIn.tokens.size                  && // cannot inject more tokens
  poolOut.R4[Long].get     == average                             && // rate = average
  poolOut.R5[Int].get      == poolIn.R5[Int].get + 1              && // counter incremented
  poolOut.propositionBytes == poolIn.propositionBytes             && // preserve pool script
  poolOut.value            >= poolIn.value                        &&
  poolOut.creationInfo._1  >= HEIGHT - buffer                     && // correct start epoch height
  selfOut.tokens           == SELF.tokens                         && // refresh NFT preserved
  selfOut.propositionBytes == SELF.propositionBytes               && // script preserved
  selfOut.value            >= SELF.value
}
```

## Key Design Patterns

- **`INPUTS.filter(isValidDataPoint)`** — Filters oracle boxes from all inputs using token ID and epoch counter checks. Classic eUTXO pattern for multi-box validation.
- **`.fold()` for sort verification + summation** — Single pass computes both sorted-order check and running sum. Avoids needing a separate sort operation.
- **`proveDlog(pubKey)`** — The refresh transaction must be signed by one of the participating oracles (the "collector"), identified by context variable `getVar[Int](0)`.
- **`rewardEmitted = dataPoints.size * 2`** — Each valid oracle gets 1 reward token; the collector gets an extra `n+1` tokens. Incentivizes including maximum oracles.
- **Deviation check** — `lastData - firstData <= maxDelta` on sorted data ensures outliers are rejected. The 5% default prevents manipulation.

## Security Notes

- `startData = 1L` prevents zero-value data points from passing validation.
- `poolOut.tokens.size == poolIn.tokens.size` prevents token injection attacks.
- `poolOut.propositionBytes == poolIn.propositionBytes` ensures the pool script cannot be changed via refresh (only via update).
- Epoch counter in R5 prevents replay of old data points — oracles must match the current epoch.
