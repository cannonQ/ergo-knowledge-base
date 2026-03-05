---
title: EIP-12 dApp Connector
description: EIP-12 dApp Connector — connection API, context API, multi-wallet detection, TypeScript types
tags: [eip12-dapp-connector, pattern, integration]
category: reference
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: auto-generated
source_repos: [nautls/nautilus-wallet, ThierryM1212/SAFEW, fleet-sdk/fleet]
---
# EIP-12 dApp Connector — Developer Integration Guide

## Overview

EIP-12 (Ergo Improvement Proposal 12) defines the standard interface between browser-based dApps and Ergo wallet extensions. It is the Ergo ecosystem's answer to Ethereum's EIP-1193 (MetaMask provider API), adapted for Ergo's eUTXO model, where the fundamental unit of state is a **Box** rather than an account balance.

### Why It Exists

Ergo's eUTXO model introduces unique challenges for dApp connectivity that account-based connector APIs cannot address:

- **Box selection**: dApps need access to unspent Boxes (UTXOs), not just a balance figure
- **Data inputs**: Ergo transactions support read-only Box references (Data inputs) that don't get consumed, enabling multi-stage contracts and oracle consumption without spending
- **Registers**: Boxes carry up to six additional data Registers (R4–R9) beyond the standard value/ErgoTree/tokens fields, which dApps must be able to inspect
- **Native tokens**: Every Box can carry multiple tokens identified by a Token ID (the ID of the minting Box), requiring richer balance APIs than a single-asset model
- **Context extension**: ErgoScript evaluation can be extended with custom key-value pairs injected at signing time
- **Sigma protocols**: Spending proofs are Sigma-protocol proofs (Schnorr, ring signatures, threshold), not raw ECDSA signatures

Without a standard, every wallet would expose a different API surface, fragmenting the dApp ecosystem.

### When to Use It

Use EIP-12 when:

- Building a browser-based dApp that must connect to user wallets (Nautilus, SAFEW, Eternl, etc.)
- You need to read user UTXOs, balances, or addresses without requiring private key access
- You need the wallet to sign a transaction you've constructed (e.g., using Fleet SDK)
- You need multi-wallet support and must enumerate which wallets are installed
- You need to submit signed transactions to the Ergo network through the wallet's node connection

Do **not** use EIP-12 when building server-side signers, CLI tools, or non-browser environments — use `ergo-lib` (Rust/JS/Python bindings) directly in those cases.

---

## How It Works

EIP-12 defines a two-phase API split across two distinct objects: an **Auth API** (`ergoConnector.<wallet>`) for connection negotiation, and a **Context API** (`ergo`) for all subsequent wallet operations.

### Phase 1 — Discovery and Connection

```
Browser Window
│
├── window.ergoConnector          ← injected by each wallet extension
│   ├── .nautilus  (NautilusAuthApi)
│   ├── .safew     (SafewAuthApi)
│   └── .eternl    (EternlAuthApi)   ← any EIP-12 compliant wallet
│
└── window.ergo                   ← populated after successful connect()
    └── (NautilusErgoApi / SafewErgoApi / ...)
```

1. **Injection**: When the browser loads a page, each installed wallet extension injects its Auth API object into `window.ergoConnector` under its own key. Multiple wallets can coexist because they each claim a separate namespace key.

2. **Detection**: The dApp iterates `window.ergoConnector` to find available wallets.

3. **Authorization request**: The dApp calls `window.ergoConnector.<wallet>.connect()` (or the legacy `window.ergo_request_read_access()`). The wallet shows a permission dialog to the user.

4. **Context retrieval**: On approval, the dApp calls `window.ergoConnector.<wallet>.getContext()` which resolves to the Context API object (also available as `window.ergo`).

### Phase 2 — Context API Operations

Once the Context API object is obtained, the dApp can call:

```
Context API (window.ergo)
│
├── get_balance(token_id?)          ← ERG or specific Token ID balance
├── get_utxos(amount?, token_id?)   ← Box selection for transaction building
├── get_used_addresses()            ← addresses that have appeared on-chain
├── get_unused_addresses()          ← fresh derived addresses
├── get_change_address()            ← canonical change address
├── sign_tx(tx)                     ← wallet signs an unsigned ErgoTx
├── sign_tx_input(index, tx)        ← sign a single input (partial signing)
├── sign_data(addr, data)           ← sign arbitrary data (EIP-28 extension)
└── submit_tx(tx)                   ← broadcast signed tx via wallet's node
```

### Phase 3 — Transaction Signing Flow

```
dApp                          Wallet Extension              Ergo Node
 │                                   │                          │
 │─── get_utxos() ──────────────────►│                          │
 │◄── [Box, Box, Box] ───────────────│                          │
 │                                   │                          │
 │  (build UnsignedTransaction        │                          │
 │   using Fleet SDK / ergo-lib)      │                          │
 │                                   │                          │
 │─── sign_tx(unsignedTx) ──────────►│                          │
 │                     (user confirms)│                          │
 │◄── SignedTransaction ─────────────│                          │
 │                                   │                          │
 │─── submit_tx(signedTx) ──────────►│                          │
 │                                   │─── broadcast ───────────►│
 │◄── txId ─────────────────────────│◄── txId ─────────────────│
```

The signing step is where Ergo diverges most from Ethereum: the wallet must construct a full **ErgoScript context** (current height, extension variables, self box reference, etc.) to evaluate ErgoScript guards and produce valid Sigma-protocol proofs.

---

## Implementation

### TypeScript Type Definitions

Define the full EIP-12 surface before writing any integration code. These types precisely mirror the standard:

```typescript
// eip12.types.ts

/**
 * Hex-encoded bytes. Used for serialized Box content, ErgoTree, etc.
 */
type HexString = string;

/**
 * A Box ID is the Blake2b-256 hash of the Box's serialized content.
 */
type BoxId = HexString;

/**
 * Token ID is the Box ID of the transaction that first minted the token.
 * This is the "Token ID rule" — token identity is derived from the minting box.
 */
type TokenId = HexString;

/** ERG amounts are in nanoERG (1 ERG = 1_000_000_000 nanoERG) */
type NanoErg = string; // BigInt-safe string representation

/**
 * A Register value is CBOR-encoded and then hex-encoded.
 * R0 = value (nanoERG), R1 = ErgoTree, R2 = creationInfo, R3 = tokens
 * R4–R9 are available for contract/dApp use.
 */
interface BoxRegisters {
  R4?: HexString;
  R5?: HexString;
  R6?: HexString;
  R7?: HexString;
  R8?: HexString;
  R9?: HexString;
}

interface AssetAmount {
  tokenId: TokenId;
  amount: NanoErg;
}

/**
 * An Ergo Box as returned by the EIP-12 Context API.
 * Represents an unspent eUTXO in the user's wallet.
 */
interface ErgoBox {
  boxId: BoxId;
  /** nanoERG value locked in this box */
  value: NanoErg;
  /** Serialized ErgoTree (the locking script, compiled from ErgoScript) */
  ergoTree: HexString;
  /** Block height at which this box was created — used for Storage rent calculation */
  creationHeight: number;
  /** Native tokens carried by this box */
  assets: AssetAmount[];
  /** Additional data registers R4–R9 */
  additionalRegisters: BoxRegisters;
  /** Transaction that created this box */
  transactionId: HexString;
  /** Output index within that transaction */
  index: number;
}

/**
 * Context extension: key-value pairs injected into the ErgoScript context
 * during transaction signing. Keys are register indices (as strings),
 * values are CBOR-encoded hex. Used to pass runtime data to scripts
 * without modifying the ErgoTree itself.
 */
interface ContextExtension {
  [key: string]: HexString;
}

interface UnsignedInput {
  boxId: BoxId;
  /** The Box being spent — required so the prover can construct context */
  extension: ContextExtension;
}

interface UnsignedTransaction {
  id?: HexString;
  inputs: UnsignedInput[];
  /** Data inputs are read-only box references — not consumed, not signed */
  dataInputs: Array<{ boxId: BoxId }>;
  outputs: Array<Omit<ErgoBox, 'boxId' | 'transactionId' | 'index'>>;
}

interface SpendingProof {
  proofBytes: HexString;
  extension: ContextExtension;
}

interface SignedInput {
  boxId: BoxId;
  spendingProof: SpendingProof;
}

interface SignedTransaction {
  id: HexString;
  inputs: SignedInput[];
  dataInputs: Array<{ boxId: BoxId }>;
  outputs: ErgoBox[];
}

/** Pagination for address/UTXO queries */
interface Paginate {
  page: number;
  limit: number;
}

/** Standard EIP-12 error codes */
enum APIErrorCode {
  InvalidRequest = -1,
  InternalError = -2,
  Refused = -3,
  AccountChange = -4,
}

interface APIError {
  code: APIErrorCode