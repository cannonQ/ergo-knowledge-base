---
title: "Cookbook: Simple ERG Transfer (P2PK)"
description: "Send ERG to a P2PK address using Fleet SDK — the minimal Ergo transaction"
tags: [cookbook, fleet-sdk, p2pk, transaction-building, beginner]
category: cookbook
difficulty: beginner
sdk: [fleet-sdk]
updated: 2026-03-09
source: original
author: "EKB"
---

# Simple ERG Transfer (P2PK)

Send nanoERGs from one wallet to a Pay-to-Public-Key address — the most
fundamental Ergo transaction.

## ErgoScript Guard

A P2PK box has no custom script. The default guard is a Schnorr proof
(`proveDlog`) embedded in the address itself:

```ergoscript
// Implicitly encoded in every P2PK address:
proveDlog(ownerPublicKey)
```

The spender proves knowledge of the private key without revealing it.
No contract compilation is needed for simple sends.

## Off-Chain: Fleet SDK (TypeScript)

### 1. Install Dependencies

```bash
npm i @fleet-sdk/core @fleet-sdk/common
```

### 2. Build the Transaction

```typescript
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
  RECOMMENDED_MIN_FEE_VALUE,
} from "@fleet-sdk/core";
import type { Box, Amount } from "@fleet-sdk/common";

const NANOERG = 1_000_000_000n; // 1 ERG

async function buildSendTx(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  recipientAddress: string,
  amountNanoErg: bigint,
  currentHeight: number
) {
  return new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .to(
      new OutputBuilder(amountNanoErg, recipientAddress)
    )
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();
}
```

### 3. Sign & Submit via EIP-12 Wallet (Browser)

```typescript
// Connect to Nautilus / SAFEW
const connected = await ergoConnector.nautilus.connect();
const ergo = await ergoConnector.nautilus.getContext();

// Fetch UTXOs owned by the wallet
const utxos = await ergo.get_utxos();
const height = await ergo.get_current_height();

const unsignedTx = await buildSendTx(
  utxos,
  await ergo.get_change_address(),
  "9f4QF8AD1nQ3nJahQVkM...",   // recipient
  1n * NANOERG,                  // 1 ERG
  height
);

const signedTx = await ergo.sign_tx(unsignedTx);
const txId = await ergo.submit_tx(signedTx);
console.log("Submitted:", txId);
```

### 4. Sign Headless (Node.js with ergo-lib-wasm)

```typescript
import { Wallet } from "ergo-lib-wasm-nodejs";

const wallet = Wallet.from_mnemonic("your mnemonic ...", "");
const signedTx = wallet.sign_transaction(
  /* ergoStateContext */ ctx,
  /* unsignedTx */      unsignedTx,
  /* boxesToSpend */    inputBoxes,
  /* dataInputs */      []
);
```

## How It Works

1. **Box selection** — Fleet greedily picks UTXOs from `inputBoxes` until
   their total value covers `amount + fee`.
2. **Fee box** — `payMinFee()` appends an output paying 0.0011 ERG to
   the miners' fee address.
3. **Change box** — any leftover nanoERGs (and tokens) go to
   `sendChangeTo`.
4. **Signing** — the wallet produces a Schnorr proof for each consumed
   input, proving private-key knowledge.

## Common Pitfalls

| Pitfall | Explanation |
|---------|-------------|
| **Insufficient box value** | Every output must carry ≥ `SAFE_MIN_BOX_VALUE` (0.001 ERG). Sending less causes a build-time error. |
| **Forgetting `sendChangeTo`** | Without it, leftover ERG/tokens are implicitly burned — Fleet will throw `NotAllowedTokenBurning` if tokens remain. |
| **Stale UTXOs** | If another transaction spends an input before yours confirms, yours is rejected. Re-fetch UTXOs and rebuild. |
| **Wrong network prefix** | Mainnet addresses start with `9`, testnet with `3`. Mixing them produces an invalid transaction. |
| **Not accounting for fee** | The sender needs `amount + 0.0011 ERG` in their UTXOs. Under-funded builds throw an insufficient-inputs error. |

## See Also

- [Transaction Building pattern](../../patterns/transaction-building.md)
- [EIP-12 dApp Connector pattern](../../patterns/eip12-dapp-connector.md)
- [Sigma Protocols concept](../../concepts/sigma-protocols.md)
