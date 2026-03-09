---
title: "Transfer Tokens"
description: "Send native Ergo tokens to another address using Fleet SDK"
category: cookbook
difficulty: beginner
tags: [tokens, transfer, fleet-sdk, typescript]
sdk: fleet-sdk
updated: 2026-03-09
---

# Transfer Tokens

Transferring tokens on Ergo means consuming input boxes that hold the tokens and creating new output boxes at the recipient address. Fleet SDK's `OutputBuilder.addTokens()` handles the token assignment, while `TransactionBuilder` automatically routes leftover tokens to the change box.

## Prerequisites

```bash
npm install @fleet-sdk/core
```

You need the token ID, the recipient address, and UTXOs that contain enough ERG and the token to transfer.

## Transfer a Single Token

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

const TOKEN_ID =
  "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04";

async function transferToken(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  recipientAddress: string,
  currentHeight: number,
  tokenAmount: bigint
) {
  const unsignedTx = new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, recipientAddress, currentHeight)
        .addTokens({
          tokenId: TOKEN_ID,
          amount: tokenAmount,
        })
    )
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}
```

Any remaining token balance is automatically sent to `senderAddress` in the change box.

## Transfer Multiple Token Types

You can send several different tokens in one output by chaining `.addTokens()` calls or passing an array.

```typescript
async function transferMultipleTokens(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  recipientAddress: string,
  currentHeight: number
) {
  const unsignedTx = new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, recipientAddress, currentHeight)
        .addTokens({ tokenId: TOKEN_A, amount: 100n })
        .addTokens({ tokenId: TOKEN_B, amount: 50n })
    )
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}
```

## Transfer to Multiple Recipients

Create multiple `.to()` outputs — one per recipient.

```typescript
async function transferToMultiple(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  currentHeight: number,
  recipients: { address: string; tokenId: string; amount: bigint }[]
) {
  let builder = new TransactionBuilder(currentHeight).from(inputBoxes);

  for (const r of recipients) {
    builder = builder.to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, r.address, currentHeight)
        .addTokens({ tokenId: r.tokenId, amount: r.amount })
    );
  }

  return builder.sendChangeTo(senderAddress).payMinFee().build();
}
```

## Common Pitfalls

- **Accidental burn protection.** Fleet enforces strict input/output token balance. If your outputs do not account for all input tokens, the remaining tokens go to the change box. If there is no change address set, the build will throw `NotAllowedTokenBurning`. Always call `.sendChangeTo()`.
- **Minimum box value.** Every output box must carry at least `SAFE_MIN_BOX_VALUE` (0.001 ERG / 1,000,000 nanoERG) in addition to any tokens. Tokens cannot exist without ERG.
- **Token amounts are raw integers.** A token with `decimals: 4` displaying as `1.5000` is stored as `15000n`. Always use the raw amount when building transactions.
- **Input box selection.** Fleet's default box selector picks inputs greedily until ERG and token requirements are met. If your UTXOs are spread across many small boxes, you may need to consolidate first.
- **Duplicate token entries.** Fleet sums duplicate token IDs in the same output by default, so `.addTokens({ tokenId: X, amount: 50n })` twice results in 100 units total — not an error.

## See Also

- [Mint Tokens](./mint-token.md)
- [Burn Tokens](./burn-token.md)
- [Transaction Building Pattern](../../patterns/)
