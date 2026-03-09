---
title: "Cookbook: Time-Locked Box with Refund"
description: "Lock ERG until a block height deadline with a refund path for the sender"
tags: [cookbook, fleet-sdk, timelock, height, refund, ergoscript]
category: cookbook
difficulty: intermediate
sdk: [fleet-sdk]
updated: 2026-03-09
source: original
author: "EKB"
---

# Time-Locked Box with Refund

Lock funds until a future block height. The recipient can claim after the
deadline; the sender can reclaim (refund) before it. This is the building
block for escrows, vesting, and payment channels.

## ErgoScript Guard

```ergoscript
{
  val recipient = PK("9fRAWhdxEsTcdb8PhGNrZfwqa65zfkuYHAMmkQLcic1gdLSV5vA")
  val sender    = PK("9hHDQb9eGKWWfwMRB1UYSoQomf5rkCUAsBCmM8iqAYhospGk3wu")
  val deadline  = 1_200_000   // block height

  // Path 1: recipient claims after deadline
  val claim  = recipient && sigmaProp(HEIGHT >= deadline)

  // Path 2: sender refunds before deadline
  val refund = sender && sigmaProp(HEIGHT < deadline)

  claim || refund
}
```

### Variant: Parameterized via Registers

Avoid recompiling for every lock by reading the deadline and recipient
from registers:

```ergoscript
{
  val recipient  = SELF.R4[SigmaProp].get   // stored at lock time
  val deadline   = SELF.R5[Int].get
  val sender     = PK("9hHDQb9e...")        // compiled-in

  val claim  = recipient && sigmaProp(HEIGHT >= deadline)
  val refund = sender    && sigmaProp(HEIGHT < deadline)

  claim || refund
}
```

## Off-Chain: Fleet SDK (TypeScript)

### 1. Compile & Lock

```typescript
import { compile } from "@fleet-sdk/compiler";
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";
import { SInt, SSigmaProp, SParse } from "@fleet-sdk/serializer";

const timelockScript = `{
  val recipient = SELF.R4[SigmaProp].get
  val deadline  = SELF.R5[Int].get
  val sender    = PK("9hHDQb9eGKWWfwMRB1UYSoQomf5rkCUAsBCmM8iqAYhospGk3wu")
  val claim  = recipient && sigmaProp(HEIGHT >= deadline)
  val refund = sender    && sigmaProp(HEIGHT < deadline)
  claim || refund
}`;

const ergoTree = compile(timelockScript);
const DEADLINE = 1_200_000;

async function lockFunds(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  recipientPK: string,       // SigmaProp hex of recipient
  lockAmount: bigint,
  currentHeight: number
) {
  return new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .to(
      new OutputBuilder(lockAmount, ergoTree)
        .setAdditionalRegisters({
          R4: recipientPK,                 // SigmaProp (proveDlog)
          R5: SInt(DEADLINE).toHex(),      // deadline height
        })
    )
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();
}
```

### 2. Claim (After Deadline)

```typescript
async function claimTimelocked(
  timelockBox: Box<Amount>,
  recipientBoxes: Box<Amount>[],
  recipientAddress: string,
  currentHeight: number       // must be >= deadline
) {
  return new TransactionBuilder(currentHeight)
    .from([timelockBox, ...recipientBoxes])
    .to(
      new OutputBuilder(timelockBox.value, recipientAddress)
    )
    .sendChangeTo(recipientAddress)
    .payMinFee()
    .build();
}

// Sign with recipient's wallet
const signed = await ergoRecipient.sign_tx(unsignedClaim);
const txId   = await ergoRecipient.submit_tx(signed);
```

### 3. Refund (Before Deadline)

```typescript
async function refundTimelocked(
  timelockBox: Box<Amount>,
  senderBoxes: Box<Amount>[],
  senderAddress: string,
  currentHeight: number       // must be < deadline
) {
  return new TransactionBuilder(currentHeight)
    .from([timelockBox, ...senderBoxes])
    .to(
      new OutputBuilder(timelockBox.value, senderAddress)
    )
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();
}
```

## How It Works

1. **Locking** — ERG is sent to a P2S address. R4 holds the
   recipient's SigmaProp; R5 holds the deadline height.
2. **Claim path** — After `HEIGHT >= deadline`, the recipient signs
   a transaction spending the box. The guard's `claim` branch is
   satisfied.
3. **Refund path** — Before the deadline, the sender can reclaim by
   satisfying the `refund` branch.
4. **Mutual exclusion** — `HEIGHT` is consensus-level and
   monotonically increasing, so exactly one path is valid at any
   given block height.

## Common Pitfalls

| Pitfall | Explanation |
|---------|-------------|
| **Off-by-one on HEIGHT** | `HEIGHT` is the *inclusion block* height, not the mempool height. Use `>=` for claim and `<` for refund so there is no gap and no overlap. |
| **Deadline in the past** | If you set a deadline below the current height, the recipient can claim immediately and the refund path is dead. Always validate `deadline > currentHeight` off-chain before locking. |
| **Missing fee funding** | The timelock box alone may not cover the claim/refund fee. Include extra user UTXOs in the inputs. |
| **Register type mismatch** | R4 must be `SigmaProp`, not `GroupElement` or `Coll[Byte]`. A type mismatch makes the box unspendable. |
| **Block-time estimation** | Ergo targets ~2 min/block but actual times vary. For user-facing deadlines, convert wall-clock time to approximate block height and add a buffer. |
| **Storage rent** | If the deadline is very far out (>4 years), the box may be subject to miner rent collection. Ensure the box value exceeds the minimum to survive rent cycles. |

## See Also

- [Context Variables guide](../../guides/ergodocs-tutorials/ergoscript/context-variables.md)
- [Sigma Protocols concept](../../concepts/sigma-protocols.md)
- [Simple Send recipe](simple-send.md)
