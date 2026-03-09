---
title: "Cookbook: Multi-Signature Guard (Threshold)"
description: "Lock a box with a k-of-n threshold SigmaProp so any k signers can spend"
tags: [cookbook, fleet-sdk, multi-sig, sigma-protocols, threshold, ergoscript]
category: cookbook
difficulty: intermediate
sdk: [fleet-sdk]
updated: 2026-03-09
source: original
author: "EKB"
---

# Multi-Signature Guard (Threshold)

Lock ERG (or tokens) behind a k-of-n threshold — any `k` of `n` key
holders can authorize spending. Unlike Ethereum multi-sig contracts,
Ergo's sigma-protocol proofs hide *which* signers participated.

## ErgoScript Guard

### 2-of-3 Threshold

```ergoscript
{
  val alice = PK("9fRAWhdxEsTcdb8PhGNrZfwqa65zfkuYHAMmkQLcic1gdLSV5vA")
  val bob   = PK("9hHDQb9eGKWWfwMRB1UYSoQomf5rkCUAsBCmM8iqAYhospGk3wu")
  val carol = PK("9iHkyh3kfXPjz7gBo8BFPh2x1wPBZFhBe3PW5JMCHJRKVEm37Nb")

  atLeast(2, Coll(alice, bob, carol))
}
```

`atLeast(k, props)` is a native sigma-protocol operation. The prover
generates a threshold Schnorr proof — the verifier confirms the
threshold is met but cannot tell which `k` keys signed.

### Generalized k-of-n

```ergoscript
{
  // Store n public keys; change k to any desired threshold
  val keys = Coll(
    PK("9f..."), PK("9h..."), PK("9i..."),
    PK("9g..."), PK("9e...")
  )
  atLeast(3, keys)   // 3-of-5
}
```

## Off-Chain: Fleet SDK (TypeScript)

### 1. Compile the Contract

```typescript
import { compile } from "@fleet-sdk/compiler";
import {
  TransactionBuilder,
  OutputBuilder,
  SAFE_MIN_BOX_VALUE,
} from "@fleet-sdk/core";

const script = `{
  val alice = PK("9fRAWhdxEsTcdb8PhGNrZfwqa65zfkuYHAMmkQLcic1gdLSV5vA")
  val bob   = PK("9hHDQb9eGKWWfwMRB1UYSoQomf5rkCUAsBCmM8iqAYhospGk3wu")
  val carol = PK("9iHkyh3kfXPjz7gBo8BFPh2x1wPBZFhBe3PW5JMCHJRKVEm37Nb")
  atLeast(2, Coll(alice, bob, carol))
}`;

const ergoTree = compile(script);
```

### 2. Lock Funds to the Multi-Sig Address

```typescript
async function lockToMultiSig(
  inputBoxes: Box<Amount>[],
  senderAddress: string,
  lockAmount: bigint,
  currentHeight: number
) {
  return new TransactionBuilder(currentHeight)
    .from(inputBoxes)
    .to(
      new OutputBuilder(lockAmount, ergoTree)
    )
    .sendChangeTo(senderAddress)
    .payMinFee()
    .build();
}
```

### 3. Spend from the Multi-Sig Box

Spending requires a threshold signature. In a browser workflow each
signer connects their wallet and contributes a partial proof.

```typescript
async function spendMultiSig(
  multiSigBox: Box<Amount>,
  fundingBoxes: Box<Amount>[],
  recipientAddress: string,
  signerAddress: string,
  currentHeight: number
) {
  const unsignedTx = new TransactionBuilder(currentHeight)
    .from([multiSigBox, ...fundingBoxes])
    .to(
      new OutputBuilder(multiSigBox.value, recipientAddress)
    )
    .sendChangeTo(signerAddress)
    .payMinFee()
    .build();

  return unsignedTx;
}

// Each participating signer signs and the wallet combines proofs:
// Signer 1 (e.g. Alice)
const partial1 = await ergoAlice.sign_tx(unsignedTx);
// Signer 2 (e.g. Bob)
const partial2 = await ergoBob.sign_tx(unsignedTx);
```

> **Note:** Nautilus and SAFEW handle threshold proof aggregation
> internally when the wallet holds one of the required keys. For
> multi-device signing, use a coordination layer (e.g. Mosaik) to
> collect partial signatures and combine them before submission.

### 4. Submit

```typescript
const txId = await ergo.submit_tx(signedTx);
```

## How It Works

1. **Locking** — Funds are sent to a P2S address whose ErgoTree
   encodes the `atLeast(k, ...)` proposition.
2. **Proving** — When spending, each signer produces a Schnorr proof
   for their key. The prover assembles a threshold proof that satisfies
   `k` leaves of the sigma-tree.
3. **Privacy** — The on-chain proof reveals only that `k` valid
   signatures exist — not which `k` of the `n` keys participated.

## Common Pitfalls

| Pitfall | Explanation |
|---------|-------------|
| **Confusing `atLeast` with boolean AND/OR** | `alice && bob` requires *both*; `alice \|\| bob` requires *either*. `atLeast(k, ...)` is a true threshold — exactly k proofs suffice. |
| **Hardcoded keys in script** | Changing signers requires a new contract address. For dynamic membership, store keys in a register and iterate with `forall`/`exists`. |
| **Partial-signature coordination** | Two wallets cannot independently submit — proofs must be combined into one transaction. Use a shared signing service or Mosaik for multi-device flows. |
| **Under-funded spending TX** | The multi-sig box might not cover the fee. Include extra funding boxes in the inputs. |
| **Exceeding script complexity** | Very large `n` (>15–20) can push ErgoTree size or verification cost past limits. For large committees, consider a Merkle-tree approach with register-stored keys. |

## See Also

- [Sigma Protocols concept](../../concepts/sigma-protocols.md)
- [Transaction Building pattern](../../patterns/transaction-building.md)
- [Simple Send recipe](simple-send.md)
