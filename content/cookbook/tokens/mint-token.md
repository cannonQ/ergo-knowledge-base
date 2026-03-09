---
title: "Mint a Token (EIP-4)"
description: "Mint fungible tokens and NFTs on Ergo using Fleet SDK and the EIP-4 standard"
category: cookbook
difficulty: beginner
tags: [tokens, minting, eip-4, nft, fleet-sdk, typescript]
sdk: fleet-sdk
updated: 2026-03-09
---

# Mint a Token (EIP-4)

Ergo tokens are minted by including a `mintToken` directive in a transaction output. The new token's ID is always equal to the first input box's ID, and EIP-4 metadata (name, description, decimals) is encoded into registers R4–R6.

## Prerequisites

```bash
npm install @fleet-sdk/core
```

You need UTXOs owned by the minting address and the current blockchain height.

## Mint a Fungible Token

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

async function mintFungibleToken(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  currentHeight: number
) {
  const unsignedTx = new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, senderAddress, currentHeight)
        .mintToken({
          amount: 1_000_000n,        // total supply
          name: "MyToken",
          decimals: 2,               // 1_000_000 raw = 10,000.00 display
          description: "A fungible EIP-4 token",
        })
    )
    .sendChangeTo(senderAddress)
    .payFee(RECOMMENDED_MIN_FEE_VALUE)
    .build();

  return unsignedTx;
  // Token ID = inputBoxes[0].boxId
}
```

## Mint a Picture NFT

NFTs use `amount: 1n` and set R7–R9 for asset type, content hash, and URL per EIP-4.

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
  SConstant,
  SColl,
  SByte,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

async function mintPictureNFT(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  currentHeight: number,
  contentHash: string,  // 32-byte SHA-256 hex of the image
  imageUrl: string
) {
  const PICTURE_NFT_TYPE = Uint8Array.from([0x01, 0x01]);
  const hashBytes = Uint8Array.from(Buffer.from(contentHash, "hex"));

  const unsignedTx = new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .to(
      new OutputBuilder(SAFE_MIN_BOX_VALUE, senderAddress, currentHeight)
        .mintToken({
          amount: 1n,
          name: "My NFT",
          decimals: 0,
          description: "A picture NFT",
        })
        .setAdditionalRegisters({
          R7: SConstant(SColl(SByte, PICTURE_NFT_TYPE)),
          R8: SConstant(SColl(SByte, hashBytes)),
          R9: SConstant(SColl(SByte, new TextEncoder().encode(imageUrl))),
        })
    )
    .sendChangeTo(senderAddress)
    .payFee(RECOMMENDED_MIN_FEE_VALUE)
    .build();

  return unsignedTx;
}
```

## Signing and Submitting

The unsigned transaction is signed via an EIP-12 wallet connector (browser) or a node wallet, then submitted to the `/transactions` endpoint.

```typescript
// Browser — EIP-12 wallet (e.g. Nautilus)
const signedTx = await ergoConnector.nautilus.getContext()
  .then(ctx => ctx.sign_tx(unsignedTx));
const txId = await ctx.submit_tx(signedTx);
```

## Common Pitfalls

- **Token ID is not a choice.** The minted token's ID is always `inputBoxes[0].boxId`. You cannot specify an arbitrary ID.
- **One mint per transaction.** Ergo consensus allows only one token to be minted per transaction. Attempting multiple `.mintToken()` calls will fail.
- **Register gaps are invalid.** If you set R7 for an NFT, you must also have R4–R6 populated (Fleet handles R4–R6 automatically via `mintToken`). Skipping a register (e.g., setting R7 and R9 but not R8) causes `InvalidRegistersPacking`.
- **Minimum box value.** The output box must carry at least `SAFE_MIN_BOX_VALUE` (0.001 ERG). Boxes with tokens may need more — use `estimateMinBoxValue` for precision.
- **Decimals are display-only.** The `decimals` field does not affect on-chain arithmetic. A token with `decimals: 2` and `amount: 100n` displays as `1.00` but is stored as `100`.

## See Also

- [EIP-4 Asset Standard](../../reference/eips/)
- [Transaction Building Pattern](../../patterns/)
- [Transfer Tokens](./transfer-token.md)
- [Burn Tokens](./burn-token.md)
