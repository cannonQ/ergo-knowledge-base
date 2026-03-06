---
title: "ErgoScript Fundamentals: Off-Chain Transactions with AppKit"
description: "Build and sign Ergo transactions in Scala using Ergo AppKit — from ErgoClient setup through input retrieval, output construction, context variables, signing, and submission. Adapted from DeCo Education's ErgoScript Developer Course."
tags: [appkit, transactions, off-chain, scala, tutorial, deco-education]
category: guide
difficulty: intermediate
sdk: [appkit]
updated: 2026-03-06
source: adapted
original_source: "https://github.com/DeCo-Education/ErgoScript-Developer-Course"
original_author: "DeCo Education (lgd, kii)"
license: MIT
---

# ErgoScript Fundamentals: Off-Chain Transactions with AppKit

> **Attribution:** This guide is adapted from [DeCo Education's ErgoScript Developer Course](https://github.com/DeCo-Education/ErgoScript-Developer-Course) (Week 3), originally created by lgd and kii under the MIT License.

## Prerequisites

- [Boxes, Registers & Blockchain Context](01-boxes-registers-context.md) — ErgoScript syntax basics
- [Guard Script Framework](02-guard-script-framework.md) — Contract design methodology
- Basic Scala knowledge (vals, types, method calls)
- An Ergo node or public API endpoint

## What Is AppKit?

[Ergo AppKit](https://github.com/ergoplatform/ergo-appkit) is the official Scala/Java SDK for building Ergo transactions off-chain. While ErgoScript defines the *on-chain* spending conditions (guard scripts), AppKit handles everything *off-chain*:

- Connecting to the Ergo network
- Fetching unspent boxes from the blockchain
- Constructing transaction inputs and outputs
- Attaching context variables
- Signing and submitting transactions

Think of it this way: ErgoScript is the **lock**, AppKit is the **key-maker and locksmith**.

## The 10-Step Transaction Recipe

Every AppKit transaction follows the same structure:

1. Create the ErgoClient (network connection)
2. Open a BlockchainContext (session)
3. Retrieve input boxes from the chain
4. Calculate amounts (fees, taxes, change)
5. Create context variables if needed
6. Create the transaction builder
7. Build output boxes
8. Create the prover (wallet/signer)
9. Build the unsigned transaction
10. Sign and submit

## Walkthrough: Alcohol Sale Transaction

We'll implement the off-chain code for the Alcohol Sale Proxy Contract from the [Guard Script Framework](02-guard-script-framework.md) guide. This contract handles a purchase where:

- A buyer's proxy boxes provide funds
- A license box proves the buyer's identity
- Outputs go to: store, provincial tax, federal tax, buyer change
- The buyer can also request a full refund

### Assumptions

For this tutorial, we assume we know:
1. The buyer's public key and mnemonic
2. The proxy contract address
3. The license box address
4. The store's public key
5. Government tax collection public keys

> **In production**, these would be resolved through wallet integration (ErgoPay), dApp connectors, or digital identity systems. See the [Real-World Considerations](#real-world-considerations) section.

### Step 1: Create the ErgoClient

```scala
import org.ergoplatform.appkit._

val ergoClient: ErgoClient = RestApiErgoClient.create(
  nodeApiUrl,    // e.g., "http://213.239.193.208:9053/"
  networkType,   // NetworkType.MAINNET or NetworkType.TESTNET
  nodeApiKey,    // API key for protected node methods (empty string for public)
  explorerURL    // e.g., "https://api.ergoplatform.com/"
)
```

The `ErgoClient` manages the network connection. You can point it at your own node or a public API.

### Step 2: Open BlockchainContext

All transaction building happens inside a `BlockchainContext` — a session that provides access to the current chain state:

```scala
val txId: String = ergoClient.execute { (ctx: BlockchainContext) =>
  // All transaction logic goes here
  // ctx provides methods to query boxes, build transactions, etc.
}
```

### Step 3: Retrieve Input Boxes

Convert address strings to `Address` objects, then fetch unspent boxes:

```scala
// Convert addresses
val buyerPKAddress: Address           = Address.create(BuyerPKAddressString)
val proxyAddress: Address             = Address.create(SaleProxyContractAddressString)
val licenseAddress: Address           = Address.create(LicenseAddressString)
val storePKAddress: Address           = Address.create(StorePKAddressString)
val provincialTaxAddress: Address     = Address.create(ProvincialSalesTaxPKString)
val federalTaxAddress: Address        = Address.create(FederalSalesTaxPKString)

// Fetch the license box (first unspent box at the license address)
val licenseBox: InputBox = ctx.getUnspentBoxesFor(licenseAddress, 0, 1)
  .get(0)

// Fetch proxy boxes (the buyer's funded boxes)
val proxyBoxes: java.util.List[InputBox] = ctx.getUnspentBoxesFor(proxyAddress, 0, 5)
```

### Step 4: Calculate Amounts

```scala
import scala.collection.JavaConverters._

val buyerAmount: Long = proxyBoxes.asScala.foldLeft(0L) {
  (acc, box) => acc + box.getValue
}

val provincialTaxAmount: Long =
  ProvincialSalesTaxNum * AlcoholSaleAmount / ProvincialSalesTaxDenom
val federalTaxAmount: Long =
  FederalSalesTaxNum * AlcoholSaleAmount / FederalSalesTaxDenom
```

### Step 5: Create Context Variables

Context variables are off-chain data that gets attached to input boxes. The on-chain contract accesses them via `getVar[T](index)`.

```scala
// The proxy contract needs the license template bytes as context variable 0
val licenseErgoTreeBytes: ErgoValue[_] =
  ErgoValue.of(licenseBox.getErgoTree.bytes)

val cVar0: ContextVar = ContextVar.of(0.toByte, licenseErgoTreeBytes)

// Attach context variables to each proxy box
val extendedProxyBoxes: java.util.List[InputBox] =
  proxyBoxes.asScala.map(_.withContextVars(cVar0)).asJava
```

**Why context variables?** The proxy contract uses `getVar[Coll[Byte]](0).get` to receive the license template bytes. These bytes are needed to verify the license box's script via `substConstants`. Since the template bytes are the same regardless of which specific buyer is transacting, they're passed as a context variable rather than being hardcoded.

### Step 6: Create the Transaction Builder

```scala
val txBuilder: UnsignedTransactionBuilder = ctx.newTxBuilder()
```

### Step 7: Build Output Boxes

Each output box needs a value and a contract (script):

```scala
// Store receives the sale amount
val storeBox: OutBox = txBuilder.outBoxBuilder()
  .value(AlcoholSaleAmount)
  .contract(ctx.newContract(storePKAddress.getErgoAddress.script))
  .build()

// Provincial government receives their tax
val provincialTaxBox: OutBox = txBuilder.outBoxBuilder()
  .value(provincialTaxAmount)
  .contract(ctx.newContract(provincialTaxAddress.getErgoAddress.script))
  .build()

// Federal government receives their tax
val federalTaxBox: OutBox = txBuilder.outBoxBuilder()
  .value(federalTaxAmount)
  .contract(ctx.newContract(federalTaxAddress.getErgoAddress.script))
  .build()
```

For boxes with tokens or register data, chain additional builder methods:

```scala
// Example: output box with tokens and register data
val boxWithData: OutBox = txBuilder.outBoxBuilder()
  .value(minBoxValue)
  .tokens(new ErgoToken(tokenId, amount))
  .registers(
    ErgoValue.of(42L),                          // R4
    ErgoValue.of("hello".getBytes("UTF-8"))     // R5
  )
  .contract(someContract)
  .build()
```

### Step 8: Create the Prover

The prover holds the signing keys. For a mnemonic-based wallet:

```scala
val prover: ErgoProver = ctx.newProverBuilder()
  .withMnemonic(
    SecretString.create(BuyerMnemonic),
    SecretString.empty()  // No passphrase
  )
  .build()
```

### Step 9: Build the Unsigned Transaction

Assemble inputs, outputs, fee, and change address:

```scala
val unsignedTx: UnsignedTransaction = txBuilder
  .boxesToSpend(extendedProxyBoxes)
  .outputs(storeBox, provincialTaxBox, federalTaxBox)
  .fee(MinerFee)
  .sendChangeTo(buyerPKAddress.getErgoAddress)
  .build()
```

Key points:
- **`boxesToSpend`** — The input boxes (with context variables attached)
- **`outputs`** — The output boxes you explicitly create
- **`fee`** — Miner fee (typically 0.001 ERG = 1,000,000 nanoERGs)
- **`sendChangeTo`** — Where leftover ERG goes (buyer gets their change back)

### Step 10: Sign and Submit

```scala
val signedTx: SignedTransaction = prover.sign(unsignedTx)
val txId: String = ctx.sendTransaction(signedTx)
```

If the on-chain guard script evaluates to `true` for the constructed transaction, signing succeeds and the transaction is broadcast to the network.

## Putting It All Together

```scala
import org.ergoplatform.appkit._
import scala.collection.JavaConverters._

val ergoClient = RestApiErgoClient.create(nodeApiUrl, networkType, nodeApiKey, explorerURL)

val alcoholSaleTxId: String = ergoClient.execute { (ctx: BlockchainContext) =>

  // Addresses
  val buyerPKAddress       = Address.create(BuyerPKAddressString)
  val proxyAddress         = Address.create(SaleProxyContractAddressString)
  val licenseAddress       = Address.create(LicenseAddressString)
  val storePKAddress       = Address.create(StorePKAddressString)
  val provincialTaxAddress = Address.create(ProvincialSalesTaxPKString)
  val federalTaxAddress    = Address.create(FederalSalesTaxPKString)

  // Inputs
  val licenseBox = ctx.getUnspentBoxesFor(licenseAddress, 0, 1).get(0)
  val proxyBoxes = ctx.getUnspentBoxesFor(proxyAddress, 0, 5)
  val buyerAmount = proxyBoxes.asScala.foldLeft(0L)(_ + _.getValue)

  // Tax calculation
  val provincialTax = ProvincialSalesTaxNum * AlcoholSaleAmount / ProvincialSalesTaxDenom
  val federalTax = FederalSalesTaxNum * AlcoholSaleAmount / FederalSalesTaxDenom

  // Context variables
  val licenseTreeBytes = ErgoValue.of(licenseBox.getErgoTree.bytes)
  val cVar0 = ContextVar.of(0.toByte, licenseTreeBytes)
  val extendedInputs = proxyBoxes.asScala.map(_.withContextVars(cVar0)).asJava

  // Transaction builder
  val txBuilder = ctx.newTxBuilder()

  // Outputs
  val storeBox = txBuilder.outBoxBuilder()
    .value(AlcoholSaleAmount)
    .contract(ctx.newContract(storePKAddress.getErgoAddress.script))
    .build()

  val provincialTaxBox = txBuilder.outBoxBuilder()
    .value(provincialTax)
    .contract(ctx.newContract(provincialTaxAddress.getErgoAddress.script))
    .build()

  val federalTaxBox = txBuilder.outBoxBuilder()
    .value(federalTax)
    .contract(ctx.newContract(federalTaxAddress.getErgoAddress.script))
    .build()

  // Prover
  val prover = ctx.newProverBuilder()
    .withMnemonic(SecretString.create(BuyerMnemonic), SecretString.empty())
    .build()

  // Build, sign, submit
  val unsignedTx = txBuilder
    .boxesToSpend(extendedInputs)
    .outputs(storeBox, provincialTaxBox, federalTaxBox)
    .fee(MinerFee)
    .sendChangeTo(buyerPKAddress.getErgoAddress)
    .build()

  val signedTx = prover.sign(unsignedTx)
  ctx.sendTransaction(signedTx)
}
```

## The Refund Transaction

The proxy contract also allows refunds. The refund transaction is simpler:

- **Input**: The proxy boxes (same as sale)
- **Output**: A single box returning funds to the buyer's PK
- **Change address**: Also the buyer's PK

The on-chain contract's `validRefund` branch checks that `OUTPUTS(0).propositionBytes == buyerPK.propBytes` and `OUTPUTS(0).value >= buyerAmount - MinerFee`. The off-chain code just needs to construct a transaction that satisfies these conditions.

## Key Concepts

### On-Chain vs Off-Chain

| Concern | On-Chain (ErgoScript) | Off-Chain (AppKit) |
|---------|----------------------|-------------------|
| **Defines** | Spending conditions | Transaction construction |
| **Runs** | During validation by miners | Before submission by the dApp |
| **Accesses** | SELF, INPUTS, OUTPUTS, CONTEXT | Blockchain state, wallet keys |
| **Produces** | SigmaProp (true/false) | Signed transaction bytes |

The on-chain contract cannot construct transactions — it can only validate them. AppKit does the construction; the contract validates the result.

### Context Variables Bridge the Gap

Context variables are the primary mechanism for passing off-chain information to on-chain contracts. Common uses:

- Template contract bytes (for `substConstants` verification)
- Merkle proofs (for AVL tree/Plasma operations)
- Signature data (for multi-party protocols)
- Configuration parameters that vary per transaction

### Input Box Selection

In production, you often need to select specific boxes from the chain. AppKit provides several methods:

```scala
// By address (returns all unspent boxes)
ctx.getUnspentBoxesFor(address, offset, limit)

// By box ID (when you know the exact box)
ctx.getBoxesById(boxId1, boxId2)

// Using the box selection utility for covering a target amount
BoxOperations.createForSender(address).withAmountToSpend(amount)
```

## Real-World Considerations

The assumptions in this tutorial (knowing PKs, mnemonics, addresses) are simplified for learning. In production:

1. **ErgoPay** — Create unsigned transactions as QR codes. The user's wallet scans, reviews, and signs. No mnemonic ever leaves the wallet.

2. **dApp Connector (EIP-12)** — Browser wallets (Nautilus) inject a JavaScript API. Your dApp requests the wallet to sign transactions directly.

3. **Digital Identity** — Instead of passing license addresses, future protocols may use zero-knowledge proofs to verify identity without revealing specific box locations.

4. **Proxy Contract Alternatives** — With ErgoPay or dApp connectors, you can skip proxy contracts entirely and place the logic in your backend, requesting the user's wallet to sign directly.

## What's Next

- Explore [Ergo AppKit on GitHub](https://github.com/ergoplatform/ergo-appkit) for the full API
- See [Fleet SDK](../../content/ecosystem/fleet-sdk/) for TypeScript/JavaScript transaction building
- Study the [Auction House source](https://github.com/anon-real/ErgoAuctionHouse) for a production AppKit application
- Read about [ErgoPay (EIP-20)](https://github.com/ergoplatform/eips/blob/master/eip-0020.md) for wallet integration

---

*Adapted from [DeCo Education ErgoScript Developer Course](https://github.com/DeCo-Education/ErgoScript-Developer-Course) (MIT License) by lgd and kii. The original course includes Scala source files with runnable playground examples.*
