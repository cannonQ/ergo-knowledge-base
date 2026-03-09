---
title: "Cookbook: State Machine with Singleton NFT"
description: "Multi-stage contract using a singleton NFT to authenticate state transitions"
tags: [cookbook, fleet-sdk, state-machine, singleton-nft, multi-stage, ergoscript]
category: cookbook
difficulty: advanced
sdk: [fleet-sdk]
updated: 2026-03-09
source: original
author: "EKB"
---

# State Machine with Singleton NFT

Track on-chain state across multiple transactions using a singleton
(unique, amount-1) NFT as an authentication token. The NFT guarantees
that exactly one "live" state box exists at any time — the core pattern
behind SigmaUSD, oracle pools, Rosen Bridge, and most Ergo dApps.

## ErgoScript Guard

A counter contract: anyone can increment a counter stored in R4, but
only the contract owner can withdraw. The singleton NFT prevents
forgery.

```ergoscript
{
  // ---- constants (compiled in) ----
  val owner    = PK("9hHDQb9eGKWWfwMRB1UYSoQomf5rkCUAsBCmM8iqAYhospGk3wu")
  val nftId    = SELF.tokens(0)._1    // singleton token ID

  // ---- successor box (state continuity) ----
  val successor       = OUTPUTS(0)
  val nftPreserved    = successor.tokens(0)._1 == nftId &&
                        successor.tokens(0)._2 == 1L
  val scriptPreserved = successor.propositionBytes == SELF.propositionBytes
  val valuePreserved  = successor.value >= SELF.value

  // ---- state transition: increment ----
  val oldCount = SELF.R4[Long].get
  val newCount = successor.R4[Long].get
  val validIncrement = newCount == oldCount + 1L

  val incrementPath = sigmaProp(
    nftPreserved && scriptPreserved && valuePreserved && validIncrement
  )

  // ---- withdrawal: owner drains, NFT returned ----
  val withdrawPath = owner

  incrementPath || withdrawPath
}
```

## Off-Chain: Fleet SDK (TypeScript)

### 1. Bootstrap — Mint the Singleton

The first input's box ID becomes the NFT token ID.

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";
import { compile } from "@fleet-sdk/compiler";
import { SLong } from "@fleet-sdk/serializer";

const contractSrc = `{ /* ... ErgoScript above ... */ }`;
const ergoTree = compile(contractSrc);

async function bootstrap(
  inputBoxes: Box<Amount>[],
  ownerAddress: string,
  currentHeight: number
) {
  const nftId = inputBoxes[0].boxId; // becomes the Token ID

  return new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, ergoTree)
        .mintToken({
          tokenId: nftId,
          amount: 1n,
        }, {
          name: "CounterNFT",
          description: "Singleton state token",
          decimals: 0,
        })
        .setAdditionalRegisters({
          R4: SLong(0n).toHex(),   // initial counter = 0
        })
    )
    .sendChangeTo(ownerAddress)
    .payMinFee()
    .build();
}
```

### 2. Increment — State Transition

Locate the live state box by its NFT, then recreate it with an
updated register.

```typescript
async function increment(
  stateBox: Box<Amount>,       // fetched by NFT token ID
  funderBoxes: Box<Amount>[],
  funderAddress: string,
  currentHeight: number
) {
  const oldCount = BigInt(stateBox.additionalRegisters.R4); // decode
  const nft = stateBox.assets[0];

  return new TransactionBuilder(currentHeight)
    .from([stateBox, ...funderBoxes])
    .to(
      new OutputBuilder(stateBox.value, ergoTree)
        .addTokens({ tokenId: nft.tokenId, amount: 1n })
        .setAdditionalRegisters({
          R4: SLong(oldCount + 1n).toHex(),
        })
    )
    .sendChangeTo(funderAddress)
    .payMinFee()
    .build();
}
```

### 3. Locate the Live State Box

```typescript
// Explorer API or node endpoint
const res = await fetch(
  `https://api.ergoplatform.com/api/v1/boxes/unspent/byTokenId/${nftId}`
);
const { items } = await res.json();
const stateBox = items[0]; // exactly one result
```

### 4. Withdraw (Owner Only)

```typescript
async function withdraw(
  stateBox: Box<Amount>,
  ownerBoxes: Box<Amount>[],
  ownerAddress: string,
  currentHeight: number
) {
  const nft = stateBox.assets[0];

  return new TransactionBuilder(currentHeight)
    .from([stateBox, ...ownerBoxes])
    .to(
      // Return ERG to owner
      new OutputBuilder(stateBox.value, ownerAddress)
    )
    .burnTokens({ tokenId: nft.tokenId, amount: 1n })
    .sendChangeTo(ownerAddress)
    .payMinFee()
    .build();
}
```

## How It Works

1. **Bootstrap** — A unique NFT is minted (token ID = first input's
   box ID). It is placed inside the contract box with initial state
   in R4.
2. **State transition** — Anyone spends the state box and recreates
   it at OUTPUTS(0) with the same NFT, same script, preserved value,
   and a valid state change. The NFT acts as a "passport" — no other
   box can carry this token.
3. **Invariant** — `nftPreserved && scriptPreserved && valuePreserved`
   ensures the contract cannot be hijacked or drained during normal
   transitions.
4. **Withdrawal** — The owner can spend via the `withdrawPath` sigma
   proof, bypassing the state-transition checks.

## Common Pitfalls

| Pitfall | Explanation |
|---------|-------------|
| **Forgetting `scriptPreserved`** | Without checking `propositionBytes`, an attacker can redirect the NFT to a trivial script and steal it on the next spend. |
| **NFT amount != 1** | If you mint amount > 1, multiple state boxes can coexist, breaking the singleton invariant. Always mint exactly 1. |
| **Value leakage** | Each transition must preserve `>= SELF.value`. Otherwise, miners or callers can slowly drain the box via fees. |
| **Register packing gaps** | If your state uses R4 and R6 but not R5, the transaction is consensus-invalid. Pack registers contiguously from R4 upward. |
| **Hard-coding OUTPUTS index** | Using `OUTPUTS(0)` is conventional but fragile if transaction structure changes. Some contracts use `OUTPUTS.filter` with the NFT for flexibility, at the cost of higher script complexity. |
| **Storage rent on long-lived boxes** | A state box that sits idle for ~4 years is subject to miner rent. Ensure enough ERG or build a top-up mechanism. |

## See Also

- [Singleton / State NFT pattern](../../patterns/singleton-state-nft.md)
- [Boxes and Registers concept](../../concepts/boxes-and-registers.md)
- [Transaction Building pattern](../../patterns/transaction-building.md)
- [Timelock recipe](timelock.md)
