---
title: "Burn Tokens"
description: "Permanently destroy Ergo tokens using Fleet SDK's burn safety mechanism"
category: cookbook
difficulty: beginner
tags: [tokens, burning, fleet-sdk, typescript]
sdk: fleet-sdk
updated: 2026-03-09
---

# Burn Tokens

Burning tokens on Ergo means consuming input boxes that hold the tokens without including them in any output. Fleet SDK requires an explicit `.burnTokens()` call as a safety measure — without it, any unaccounted tokens trigger a `NotAllowedTokenBurning` error at build time.

## Prerequisites

```bash
npm install @fleet-sdk/core
```

You need UTXOs containing the tokens to burn and enough ERG to cover the transaction fee.

## Burn a Specific Amount

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

const TOKEN_ID =
  "03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04";

async function burnTokens(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  currentHeight: number,
  burnAmount: bigint
) {
  const unsignedTx = new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .burnTokens({
      tokenId: TOKEN_ID,
      amount: burnAmount,
    })
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}
```

Any remaining token balance (input amount minus burn amount) is returned to `senderAddress` in the change box.

## Burn Multiple Token Types

Pass an array to `.burnTokens()` to destroy several token types in one transaction.

```typescript
async function burnMultipleTokens(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  currentHeight: number
) {
  const unsignedTx = new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .burnTokens([
      { tokenId: TOKEN_A, amount: 100n },
      { tokenId: TOKEN_B, amount: 1n },
    ])
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}
```

## Burn an Entire Token Supply (NFT)

To fully destroy an NFT or a token, burn its total supply. The token ID will still exist in the blockchain history but no spendable boxes will hold it.

```typescript
async function burnNFT(
  nftBox: Box<Amount>,    // the box holding the NFT
  otherBoxes: Box<Amount>[], // ERG for fees
  senderAddress: string,
  currentHeight: number
) {
  const nftTokenId = nftBox.assets[0].tokenId;

  const unsignedTx = new TransactionBuilder(currentHeight)
    .from([nftBox, ...otherBoxes])
    .burnTokens({
      tokenId: nftTokenId,
      amount: 1n,
    })
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}
```

## Common Pitfalls

- **Burns are irreversible.** Once a token is burned and the transaction is confirmed, those tokens are permanently destroyed. There is no undo.
- **Explicit burn required.** Fleet SDK enforces input/output token balance by default. If tokens in the inputs are not accounted for in outputs, the build throws `NotAllowedTokenBurning`. You must call `.burnTokens()` to declare intent.
- **Burn amount must be exact.** If you declare a burn of 50 but the inputs only contain 30 of that token, the build will fail. Verify your input box balances first.
- **Change box still needed.** Even when burning, you need `.sendChangeTo()` to receive leftover ERG and any non-burned tokens.
- **Cannot burn ERG.** Only native tokens can be burned. ERG is conserved in every transaction (inputs = outputs + fee). Any ERG surplus goes to the change box.
- **Token still "exists" on-chain.** Burning removes all circulating supply, but the token's minting transaction and metadata remain in the blockchain history forever.

## See Also

- [Mint Tokens](./mint-token.md)
- [Transfer Tokens](./transfer-token.md)
- [Transaction Building Pattern](../../patterns/)
