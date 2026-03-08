---
title: ThierryM1212/SAFEW — Overview
description: SAFEW — alternative EIP-12 browser wallet, ErgoMixer integration
tags: [thierrym1212, safew, infrastructure, javascript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ThierryM1212/SAFEW"
project: thierrym1212-safew
group: infrastructure
priority: medium
languages: [javascript]
contract_count: 0
pattern_match_count: 7
---
# SAFEW — Developer-Focused Overview

---

## Overview

SAFEW (Simple And Fast Ergo Wallet) is a browser extension wallet for the Ergo blockchain, designed as a lightweight, developer-friendly alternative to Yoroi and Nautilus. Its primary role is to expose a fully EIP-12–compliant dApp connector, allowing web-based dApps to request wallet access, enumerate Boxes, and submit signed Transactions without managing private key material themselves. SAFEW injects the `ergoConnector` API into page contexts, mirroring the Yoroi connector interface (`ergo_request_read_access`, `ergo_check_read_access`) to maintain backward compatibility with existing dApps built against that standard.

Beyond the EIP-12 connector surface, SAFEW integrates directly with ErgoMixer, enabling users to initiate and manage mix Transactions from within the wallet UI. This tightens the feedback loop between coin-joining privacy workflows and the wallet layer, reducing friction for privacy-conscious users. The wallet supports mnemonic-based, ErgoPay (read-only/remote-signing), and Ledger hardware wallet modes, each representing a different trade-off between custody model and signing locality.

SAFEW was developed during ErgoHack III and has since grown into a production-grade wallet available on the Chrome Web Store and Firefox Add-ons. Its configurable Explorer and Node endpoints, BIP-44 address discovery, chained Transaction support, and expert-mode Transaction Builder make it a practical reference implementation for anyone building wallet infrastructure or EIP-12–compatible dApps on Ergo.

---

## Architecture

SAFEW follows the standard Chrome/Firefox Manifest V3 extension architecture, which separates execution into three isolated JavaScript contexts that communicate via the browser's messaging layer:

```
┌─────────────────────────────────────────────────────────────┐
│  Web Page Context                                           │
│  inject1.js  ──► ergoConnector API (EIP-12 surface)        │
│  inject2.js  ──► sign_tx relay                             │
└────────────────────────┬────────────────────────────────────┘
                         │  window.postMessage / chrome.runtime.sendMessage
┌────────────────────────▼────────────────────────────────────┐
│  Content Script (bridge)                                    │
│  Forwards page requests → background; responses → page      │
└────────────────────────┬────────────────────────────────────┘
                         │  chrome.runtime.sendMessage
┌────────────────────────▼────────────────────────────────────┐
│  Background Service Worker  (background/background.js)      │
│  - Connection state machine (per-origin permission store)   │
│  - sign_tx orchestration                                    │
│  - Node / Explorer HTTP clients                             │
│  - chrome.storage read/write (replaces localStorage in MV3) │
└────────────────────────┬────────────────────────────────────┘
                         │  chrome.windows.create / chrome.tabs
┌────────────────────────▼────────────────────────────────────┐
│  Extension UI (React SPA — src/)                            │
│  App.js, SignPopup.js, Mixer.js, CovertAddress.js, …       │
│  - Wallet management (mnemonic AES-256 encrypted at rest)  │
│  - Transaction Builder (JSON-level Box manipulation)        │
│  - ErgoMixer UI (mix listings, covert addresses)           │
│  - NFT display / mint / burn flows                         │
└─────────────────────────────────────────────────────────────┘
```

**Data flow for a dApp-initiated transaction:**

1. The dApp calls `ergoConnector.safew.connect()` via `inject1.js`.
2. `inject1.js` posts a message to the content script, which relays it to the background service worker.
3. The background opens a permission popup (the React UI's `SignPopup` component).
4. On approval, the background grants access and stores origin permissions in `chrome.storage`.
5. Subsequent `ergo.sign_tx(unsignedTx)` calls route through the same message chain; the background invokes `ergo-lib-wasm-browser` to produce the signed Transaction, prompting the user for their spending password if a mnemonic wallet is active.
6. For ErgoPay wallets, the unsigned Transaction is encoded as a QR code for out-of-band signing on a mobile device.
7. The signed Transaction is returned to the dApp and may be submitted directly to the configured Node endpoint.

**Box and balance resolution** is handled entirely against the configured Ergo Node (since v0.7.1, explorer dependency was removed for wallet content fetching). UTxO sets are fetched per address, unconfirmed Boxes are tracked separately, and the Transaction balance displayed at signing time is derived from the unsigned Transaction object itself—not from UI-level inputs—improving reliability.

---

## Smart Contracts

SAFEW does not deploy or own ErgoScript contracts of its own. Its role is purely as a wallet and connector layer. However, it interacts with existing on-chain contract constructs in the following ways:

- **ErgoMixer contracts**: SAFEW calls the ErgoMixer service API to fetch available mixes and covert address state, then constructs and signs the resulting mix Transactions. The ErgoScript contracts governing the mixing protocol (half-mix and full-mix Boxes) are owned by the ErgoMixer project; SAFEW is a client of those contracts.
- **Token minting**: The Transaction Builder supports minting Native tokens by constructing the correct first-input Box reference (exploiting the Token ID rule, where a Token ID equals the Box ID of the first input). No ErgoScript guard is required beyond `sigmaProp(true)` for simple mints, but the tool allows arbitrary ErgoTree expressions to be set on output Boxes.
- **Token burning**: Burn Transactions are built by omitting tokens from outputs; the Transaction Builder validates that the resulting Token balance delta is intentional.
- **Registers**: The Transaction Builder exposes Registers (R4–R9) as editable JSON fields, allowing developers to construct outputs with arbitrary Register contents for multi-stage contract interactions.
- **Minimum box value / Storage rent**: As of v0.7.2, SAFEW displays the estimated time until Storage rent is due per Box, surfacing this eUTXO-specific cost model directly in the wallet UI.

Developers should note that `sign_tx_input` (for signing individual inputs in multi-party protocols such as Atomic swaps or Sigma protocol collaborative signing) is not yet implemented in the EIP-12 surface.

---

## Integration Guide

### Connecting as a dApp (EIP-12)

SAFEW injects `window.ergoConnector.safew` into every page context. The standard EIP-12 connection flow applies:

```javascript
// 1. Request access
if (typeof ergoConnector !== 'undefined' && ergoConnector.safew) {
  const connected = await ergoConnector.safew.connect();
  // connected === true on approval
}

// 2. Check existing access
const isConnected = await ergoConnector.safew.isConnected();

// 3. Use the ergo API object
const balance = await ergo.get_balance('ERG'); // returns nanoERG as string

// 4. Enumerate UTxOs (Boxes)
const utxos = await ergo.get_utxos();
// Returns array of Box JSON objects with boxId, value, ergoTree,
// assets (Native tokens), additionalRegisters (Registers R4-R9),
// creationHeight, transactionId, index

// 5. Get change address
const changeAddress = await ergo.get_change_address();

// 6. Sign a Transaction
const signedTx = await ergo.sign_tx(unsignedTxJson);

// 7. Submit
const txId = await ergo.submit_tx(signedTx);
```

SAFEW also exposes the legacy Yoroi-compatible methods for backward compatibility:

```javascript
await ergo_request_read_access();   // legacy connect
await ergo_check_read_access();     // legacy isConnected
```

### Chained Transactions

SAFEW supports chained Transactions