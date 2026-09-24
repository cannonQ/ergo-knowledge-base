---
title: nautls/nautilus-wallet — Overview
description: Nautilus wallet — EIP-12 dApp connector reference implementation, Ledger integration
tags: [nautls, nautilus-wallet, infrastructure, typescript, vue]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/nautls/nautilus-wallet"
project: nautls-nautilus-wallet
group: infrastructure
priority: high
languages: [typescript, vue]
contract_count: 0
pattern_match_count: 1
---
# Nautilus Wallet — Developer Overview

---

## Overview

Nautilus Wallet is a community-driven, browser-extension wallet for the Ergo platform, serving as the **reference implementation of the EIP-12 dApp connector standard**. It bridges end users and decentralized applications by exposing a well-defined, permission-gated JavaScript API that any Ergo dApp running in a browser context can consume to request wallet access, enumerate Boxes, sign transactions, and submit them to the network. Its role in the Ergo ecosystem is analogous to MetaMask's in Ethereum: it is the canonical connector layer that dApp developers target when building front-end integrations against Ergo's eUTXO model.

Beyond the connector surface, Nautilus provides full Ledger hardware-wallet support, making it one of the few Ergo-native wallets to bring cold-signing to the browser extension context. This integration is architecturally separated from the software-key path, allowing the same EIP-12 API surface to transparently dispatch signing requests to either an in-extension software prover or a connected Ledger device without requiring dApp changes.

The project is built on TypeScript and Vue, targets both Chromium and Firefox extension APIs, and is organized under the `nautls` GitHub organization alongside companion libraries. Because it implements EIP-12, it is a foundational dependency for the entire browser-accessible Ergo dApp ecosystem, including SigmaUSD, Dexy, spectrum DEX, and other protocols that rely on a Headless dApp or front-end dApp pattern to compose and present unsigned transactions to an external signer.

---

## Architecture

### High-Level Component Map

```
┌─────────────────────────────────────────────────────┐
│                 Browser Extension Shell             │
│  ┌────────────┐   ┌───────────────────────────────┐ │
│  │  Popup UI  │   │  Background Service Worker    │ │
│  │  (Vue SPA) │   │  (state, keystore, connector) │ │
│  └─────┬──────┘   └──────────┬────────────────────┘ │
│        │  chrome.runtime     │  chrome.runtime msgs  │
│        └──────────┬──────────┘                       │
└───────────────────┼─────────────────────────────────┘
                    │
         ┌──────────▼──────────┐
         │  Content Script     │  (injected per tab)
         │  EIP-12 Shim        │
         └──────────┬──────────┘
                    │ window.ergoConnector / ergo API
         ┌──────────▼──────────┐
         │   dApp (web page)   │
         └─────────────────────┘
```

### Key Components

| Component | Location (inferred) | Responsibility |
|---|---|---|
| **EIP-12 Content Script / Injected API** | `src/content-scripts/` | Injects `window.ergoConnector` and `window.ergo` into the hosting page; proxies all dApp calls over `chrome.runtime` messaging to the background |
| **Background Service Worker** | `src/background/` | Authoritative state keeper; holds encrypted keystore, wallet list, connected-origin registry, pending signing queue |
| **Popup UI** | `src/ui/` (Vue SPA) | User-facing wallet management, asset display, NFT gallery, connection approval dialogs, signing confirmation screens |
| **Ergo Chain Module** | `src/chains/ergo/` | All Ergo-specific logic: address derivation (BIP-32/44), UTXO selection, transaction building, fee calculation, Box serialization |
| **Transaction Prover** | `src/chains/ergo/transaction/prover.ts` | Dispatches signing to either the software key path or the Ledger transport; produces a fully signed transaction from an unsigned `UnsignedTransaction` |
| **Ledger Transport Layer** | `src/hw/ledger/` | Wraps `@ledgerhq/hw-transport-webusb` / `webHID`; speaks the Ergo Ledger application protocol to produce Sigma-protocol proofs on-device |
| **Store (Pinia/Vuex)** | `src/stores/` | Reactive state shared across popup views; synced to background via messaging |
| **API Server (background-side)** | `src/api/` | Implements the EIP-12 method handlers (`get_utxos`, `get_balance`, `get_addresses`, `sign_tx`, `sign_data`, `submit_tx`); enforces per-origin permission model |

### Data-Flow: dApp Signs a Transaction

```
dApp calls ergo.sign_tx(unsignedTx)
  → content script serializes and posts to background via chrome.runtime.sendMessage
    → background enqueues signing request, opens popup
      → Popup UI renders UnsignedTransaction detail (inputs as Boxes, outputs, fee)
        → User approves → Prover.sign_tx() invoked
          → [software path] decrypt spending key → produce Sigma-protocol proof
          → [Ledger path]   serialize tx for Ledger app → USB/HID round-trip → proof returned
        → Signed transaction returned to background
      → Background resolves the pending promise held by content script
    → content script resolves the dApp's awaited Promise with SignedTransaction
dApp calls ergo.submit_tx(signedTx) → submitted to Ergo node / explorer API
```

Box data flowing through the pipeline conforms to the EIP-12 JSON schema: each Box carries `boxId`, `value` (nanoERG), `ergoTree` (hex-encoded ErgoTree), `assets` (array of `{tokenId, amount}` representing Native tokens), `additionalRegisters` (R4–R9 as hex-encoded serialized values), `creationHeight`, and `transactionId`/`index`.

---

## Smart Contracts

Nautilus Wallet itself does not deploy or own ErgoScript contracts. It is a **pure signing and connector layer**. Its responsibilities stop at producing a valid signed transaction from an unsigned one provided by the dApp or composed internally for simple ERG/token transfers.

However, the wallet correctly handles all eUTXO transaction structures that smart contracts impose:

- **Data inputs** — Boxes referenced read-only (no spending proof required) are passed through the EIP-12 `sign_tx` payload as `dataInputs`; the prover does not attempt to produce proofs for them.
- **Context extension** — The EIP-12 unsigned transaction schema supports per-input `extension` fields (key-value `ContextExtension` maps), which are forwarded verbatim to the prover so that ErgoScript context variables (`getVar[T](id)`) resolve correctly during script evaluation.
- **Registers** — Additional register data (R4–R9) in both spending inputs and outputs is preserved as opaque hex blobs; Nautilus serializes/deserializes them but does not interpret ErgoScript semantics.
- **Multi-stage contract inputs** — Because signing is box-agnostic (any valid ErgoTree can appear as an input so long as the prover can satisfy it with a known key), Nautilus naturally supports multi-stage contract patterns such as Singleton/State NFT state machines where one of the inputs is a P2PK box owned by the wallet.

---

## Integration Guide

### Prerequisites

Install the extension from the Chrome Web Store, Firefox Add-ons, or build locally:

```bash
pnpm i
pnpm run build:mainnet:chrome   # produces dist/ loadable as unpacked extension
```

### Connecting from a dApp (EIP-12)

```typescript
// 1. Detect connector
if (typeof window.ergoConnector === 'undefined') {
  throw new Error('Nautilus not installed');
}

// 2. Request connection (triggers permission popup)
const connected: boolean = await window.ergoConnector.nautilus.connect();

// 3. Obtain the EIP-12 API handle
const ergo = await window.ergoConnector.nautilus.getContext();
// After EIP-12 v2, `window.ergo` may also be populated after connect()

// 4. Read wallet state
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
