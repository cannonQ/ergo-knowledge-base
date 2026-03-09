---
title: EIP-12 dApp Connector
description: EIP-12 dApp Connector — connection API, context API, multi-wallet detection, TypeScript types
tags: [eip12-dapp-connector, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repos: [nautls/nautilus-wallet, ThierryM1212/SAFEW, fleet-sdk/fleet]
---
# EIP-12 dApp Connector — Developer Guide

## Overview

EIP-12 defines a standard browser-based communication protocol between Ergo decentralized applications (dApps) and wallet extensions. It is the Ergo ecosystem's answer to Ethereum's EIP-1193 provider API, adapted for the eUTXO model where Boxes, Registers, Data inputs, and multi-stage contracts require a richer context than account-based chains provide.

**Why it exists:** Without a standard connector interface, every dApp would need bespoke integrations for each wallet. EIP-12 gives dApps a single surface to program against—`window.ergoConnector` for authentication and `window.ergo` (the context object) for chain interaction—while wallet implementations (Nautilus, SAFEW, Ergopay-compatible wallets) compete on UX and security without breaking dApp compatibility.

**When to use it:**
- You are building a browser-based dApp that needs to read UTXOs, construct transactions, or sign them using a user's wallet
- You need to support multiple wallets without writing wallet-specific code paths
- You are building a wallet extension and need to expose a standards-compliant API surface
- You need access to user addresses, change address derivation, or UTXOs filtered by Native token Token ID

**What it is NOT for:**
- Server-side signing (use `ergo-lib` / `sigma-rust` directly)
- Cold wallet or hardware wallet signing flows outside the browser
- Node-level access to the Ergo blockchain (use the Ergo Node REST API or Explorer API)

---

## How It Works

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser Tab (dApp)                                              │
│                                                                  │
│  1. Detect wallets via window.ergoConnector                      │
│  2. Request connection via ergoConnector.<wallet>.connect()      │
│  3. User approves in wallet extension popup                      │
│  4. Receive context object (window.ergo or getContext())         │
│  5. Call context API: get_utxos, get_balance, sign_tx, etc.      │
└───────────────────┬──────────────────────────────────────────────┘
                    │  postMessage / chrome.runtime.sendMessage
┌───────────────────▼──────────────────────────────────────────────┐
│  Wallet Extension (background.js + content script)               │
│                                                                  │
│  6. Background script resolves API calls against wallet state    │
│  7. For sign_tx: validates transaction, shows UI, user confirms  │
│  8. Prover signs each input: wallet.sign_tx_input(index, ctx...) │
│  9. Returns signed inputs with spendingProof back to dApp        │
└──────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Protocol

**Step 1 — Script Injection**

The wallet extension's content script injects two JavaScript objects into every page at `document_start`:

- `window.ergoConnector` — the authentication API, one key per wallet (e.g., `nautilus`, `safew`)
- `window.ergo` — the context API, populated after connection is granted

**Step 2 — Wallet Detection**

The dApp inspects `window.ergoConnector` to discover which wallets are installed. Each key is a frozen auth API object.

**Step 3 — Connection Request**

The dApp calls `ergoConnector.<wallet>.connect()`. This triggers a permission popup in the extension. The method returns a `Promise<boolean>`.

**Step 4 — Context Acquisition**

After a successful `connect()`, the dApp either reads `window.ergo` directly (Nautilus injects it) or calls `ergoConnector.<wallet>.getContext()` (SAFEW pattern) to receive the context object.

**Step 5 — Context API Calls**

The context object exposes the full EIP-12 API surface. Each call is proxied via `postMessage` or `chrome.runtime.sendMessage` to the extension's background script where it is resolved against the actual wallet.

**Step 6 — Transaction Signing**

The dApp builds an unsigned transaction (typically using the fleet-sdk), serializes it, and passes it to `ergo.sign_tx(unsignedTx)`. The wallet extension:
1. Deserializes the transaction
2. Validates Box values, Token IDs, and the Minimum box value constraint
3. Presents a human-readable summary to the user
4. Uses `sigma-rust`'s prover to sign each input via Autolykos-compatible Sigma protocols
5. Returns the fully signed transaction

**Step 7 — Submission**

The dApp submits the signed transaction via `ergo.submit_tx(signedTx)` or directly to the Ergo Node / Explorer API.

---

## Implementation

### 1. TypeScript Type Definitions (EIP-12 surface)

These types cover the full EIP-12 API contract. Add them to a `ergo.d.ts` file in your project.

```typescript
// ergo.d.ts — EIP-12 type declarations

/** 
 * Ergo box value in nanoERG (1 ERG = 1_000_000_000 nanoERG).
 * Minimum box value is context-dependent but typically 0.001 ERG.
 */
type Amount = string; // nanoERG as decimal string to avoid JS BigInt issues

/** Base16-encoded bytes */
type HexString = string;

/** Base58Check-encoded Ergo P2PK or P2S address */
type ErgoAddress = string;

/** 32-byte Blake2b256 hash of Box serialization, base16-encoded */
type BoxId = string;

/** 32-byte identifier for a Native token, base16-encoded */
type TokenId = string;

/** Ergo block height as a 32-bit unsigned integer */
type BlockHeight = number;

/** EIP-12 pagination object */
interface Paginate {
  page: number;
  limit: number;
}

/** 
 * EIP-12 API error codes.
 * InvalidRequest (2): malformed input or unsupported operation (e.g., pagination).
 * InternalError (3): wallet-side failure.
 * Refused (4): user rejected the request.
 */
enum APIErrorCode {
  InvalidRequest = 2,
  InternalError = 3,
  Refused = 4,
}

interface APIError {
  code: APIErrorCode;
  info: string;
}

/** A Native token amount attached to a Box */
interface AssetAmount {
  tokenId: TokenId;
  amount: Amount;
}

/** 
 * An Ergo Box as represented in the EIP-12 context API.
 * Registers R4–R9 are encoded as serialized SigmaType hex strings.
 * The ErgoTree field contains the compiled ErgoScript as base16 bytes.
 */
interface EIP12ErgoBox {
  boxId: BoxId;
  transactionId: HexString;
  index: number;
  ergoTree: HexString;         // compiled ErgoScript (ErgoTree serialization)
  creationHeight: BlockHeight;
  value: Amount;               // nanoERG
  assets: AssetAmount[];
  additionalRegisters: {
    R4?: HexString;            // Serialized SigmaType (e.g., 0e20... for Coll[Byte])
    R5?: HexString;
    R6?: HexString;
    R7?: HexString;
    R8?: HexString;
    R9?: HexString;
  };
}

/** 
 * Unsigned input: references a Box to be spent.
 * extension carries Context extension values for ErgoScript context access.
 */
interface UnsignedInput {
  boxId: BoxId;
  extension: Record<string, HexString>; // Context extension key-value pairs
}

/** 
 * A Data input references a Box for read-only ErgoScript context access.
 * The Box is NOT spent; it provides data to the ErgoScript context.
 * Critical for multi-stage contracts and Singleton / State NFT patterns.
 */
interface DataInput {
  boxId: BoxId;
}

/** Output Box specification for unsigned transactions */
interface EIP12ErgoBoxCandidate {
  ergoTree: HexString;
  creationHeight: BlockHeight;
  value: Amount;
  assets: AssetAmount[];
  additionalRegisters: {
    R4?: HexString;
    R5?: HexString;
    R6?: HexString;
    R7?: HexString;
    R8?: HexString;
    R9?: HexString;
  };
}

/** 
 * An unsigned Ergo transaction.
 * inputs are the Boxes to be spent (must satisfy their ErgoTree / ErgoScript).
 * dataInputs are read-only Box references used only in ErgoScript context.
 * outputs are the new Boxes created.
 */
interface EIP12UnsignedTransaction {
  id?: HexString;
  inputs: UnsignedInput[];
  dataInputs: DataInput[];
  outputs: EIP12ErgoBoxCandidate[];
}

/** A Sigma-protocol spending proof for a signed input */
interface SpendingProof {
  proofBytes: HexString;       // serialized Sigma protocol proof
  extension: Record<string, HexString>;
}

interface SignedInput {
  boxId: BoxId;
  spendingProof: SpendingProof;
}

interface SignedTransaction {
  id: HexString;
  inputs: SignedInput[];
  dataInputs: DataInput[];
  outputs: EIP12ErgoBox[];
}

/** 
 * The EIP-12 Context API — exposed as window.ergo after connection.
 * All methods return Promises and may reject with APIError.
 */
interface EIP12ErgoAPI {
  /** Returns total balance in nanoERG, or token amount for a given Token ID */