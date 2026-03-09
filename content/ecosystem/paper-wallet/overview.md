---
title: arobsn/ergo-paper-wallet — Overview
description: Ergo paper wallet — offline cold storage wallet generator for secure ERG storage
tags: [arobsn, ergo-paper-wallet, infrastructure, typescript]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-08
source: auto-generated
source_repo: "https://github.com/arobsn/ergo-paper-wallet"
project: arobsn-ergo-paper-wallet
group: infrastructure
priority: low
languages: [typescript]
contract_count: 0
pattern_match_count: 0
---
# Developer Overview: arobsn/ergo-paper-wallet

---

## Overview

`ergo-paper-wallet` is an offline cold storage wallet generator for the Ergo Platform, enabling users to produce tamper-resistant, foldable paper wallets entirely without network connectivity. The tool generates mnemonic seeds and derives the associated Ergo addresses and Extended Public Keys (xPub) in an air-gapped environment, ensuring that private key material never touches an internet-connected process. The final output is a printable, foldable document designed for long-term secure ERG storage.

Within the Ergo ecosystem, this project occupies the **infrastructure** layer as a self-sovereign key management tool. Because Ergo uses the eUTXO model, a paper wallet effectively represents ownership of one or more Boxes on-chain — each Box identified by an ErgoTree derived from the wallet's public key. The paper wallet's Extended Public Key allows a watch-only interface to enumerate and monitor all derived addresses and their associated Boxes without exposing the spending key.

The project is deliberately minimal and auditable. It is distributed as a single `standalone.html` file that can be opened in any browser without a build step, making the security surface area small and the code review burden low. This offline-first design is especially meaningful in the context of Ergo's Storage Rent mechanism: long-lived paper wallets need periodic attention to avoid Box expiry, making the xPub export feature strategically important for monitoring without signing authority.

---

## Architecture

The project is a TypeScript/Vue single-page application compiled to a self-contained `standalone.html` bundle via webpack or Vue CLI. All cryptographic operations execute client-side in the browser; no backend server or RPC node is involved at runtime.

### Key Components

| Component | Responsibility |
|---|---|
| **Mnemonic Generator** | Produces BIP-39 compatible mnemonic phrases using cryptographically secure entropy from the browser's `window.crypto` API |
| **Key Derivation Module** | Derives the Ergo HD wallet hierarchy (BIP-32/EIP-3) from the mnemonic, producing root secret key, Extended Public Key (xPub), and child address key pairs |
| **Address Encoder** | Encodes the derived public key into an Ergo P2PK address using the network-specific prefix and Base58Check encoding, producing the ErgoTree `0x0008cd<public_key>` pattern |
| **xPub Exporter** | Serialises the Extended Public Key for watch-only use, allowing balance monitoring across all derived addresses without exposing the secret key |
| **Print/Render Layer** | Vue templates + CSS that render the wallet into the foldable paper layout, styled for physical cutting, folding, and sealing |
| **Standalone Bundle** | The entire application inlined into a single `standalone.html` file for offline distribution |

### Data Flow

```
Browser entropy (window.crypto.getRandomValues)
        │
        ▼
BIP-39 Mnemonic (12/15/24 words)
        │
        ▼
BIP-32 Root Key  ──────────────────────────────────┐
        │                                           │
        ▼ (EIP-3 derivation path: m/44'/429'/0'/0/i) │
Child Private Key                              Extended Public Key (xPub)
        │                                           │
        ▼                                           ▼
P2PK ErgoTree                              Watch-only address monitoring
(0x0008cd || compressed_pubkey)
        │
        ▼
Base58Check Ergo Address (printed on wallet)
```

All steps occur in-browser memory. No data is transmitted over a network. The mnemonic, private key, and address are rendered into the DOM only at print time, and the browser tab should be closed and the system kept offline throughout.

---

## Smart Contracts

This project does **not** deploy or interact with any ErgoScript smart contracts. The generated paper wallet produces standard **Pay-to-Public-Key (P2PK)** addresses, which correspond to the simplest possible ErgoTree:

```scala
// ErgoTree for a P2PK address
proveDlog(group_element)
```

This ErgoTree encodes a Sigma protocol proof — specifically, a discrete logarithm proof (`proveDlog`) over the Ergo group element corresponding to the wallet's compressed public key. To spend a Box protected by this ErgoTree, the spender must provide a valid Schnorr signature in the transaction's proof context, demonstrating knowledge of the corresponding private key.

There are no Multi-stage contracts, Singleton/State NFTs, or Context extensions involved. The paper wallet is intentionally contract-free: its security model relies entirely on physical custody of the printed mnemonic and the cryptographic hardness of the discrete logarithm problem underlying Ergo's Sigma protocols.

---

## Integration Guide

### Generating a Wallet (Offline)

1. Download the latest `standalone.html` release from the repository.
2. Disconnect from the internet (or boot a live OS for maximum security).
3. Open `standalone.html` in a browser — all dependencies are inlined, no CDN calls are made.
4. Generate the wallet and print the resulting page.
5. Note the **Extended Public Key (xPub)** separately for watch-only monitoring.

### Watch-Only Balance Monitoring (Off-chain)

The xPub exported by the paper wallet follows the EIP-3 HD wallet standard. Any compatible Ergo wallet or library can import it for read-only address derivation:

```typescript
import { ExtendedPublicKey, Network } from "@fleet-sdk/core";

// Import xPub from the paper wallet
const xpub = ExtendedPublicKey.fromBytes(xpubBytes);

// Derive child addresses (m/44'/429'/0'/0/i) for watch-only monitoring
for (let i = 0; i < 20; i++) {
  const childKey = xpub.deriveChild(i);
  const address = childKey.toAddress(Network.Mainnet);
  console.log(`Address ${i}: ${address.encode()}`);
}
```

### Querying Box State via Ergo Explorer API

To check the balance of a paper wallet address without spending authority:

```typescript
const address = "9f..."; // derived from xPub
const response = await fetch(
  `https://api.ergoplatform.com/api/v1/addresses/${address}/balance/confirmed`
);
const balance = await response.json();
// balance.nanoErgs: ERG balance in nanoERG units
// balance.tokens: array of Native tokens held in Boxes at this address
```

### Spending from a Paper Wallet

To spend from a paper wallet, the private key must be imported into an Ergo wallet (e.g., Nautilus, SAFEW, or via fleet-sdk) that can construct and sign a Transaction. The general off-chain flow:

1. Derive child private key from mnemonic at path `m/44'/429'/0'/0/0`.
2. Collect UTxO Boxes at the address via Explorer or a full node.
3. Construct an unsigned Transaction selecting input Boxes and specifying output Boxes with appropriate Minimum box value and Minimum transaction fee.
4. Sign with the private key using a Sigma protocol prover.
5. Submit the signed transaction to the Ergo node mempool.

**Important — Storage Rent:** Boxes on Ergo are subject to Storage Rent after approximately 4 years. Long-term paper wallet holders should monitor Box age and consolidate funds before the rent cycle triggers involuntary collection. The xPub watch-only feature is the recommended mechanism for this surveillance.

---

## Key Patterns

### Offline-First / Air-Gapped Key Generation
The defining pattern of this project. All entropy generation, key derivation, and address encoding occur in a browser context with no outbound network calls. The `standalone.html` distribution model is a deliberate security pattern ensuring no runtime CDN dependency can inject malicious code.

### HD Wallet Key Derivation (EIP-3)
The project follows Ergo's EIP-3 derivation standard, a profile of BIP-32/BIP-44 using coin type `429'` (Ergo's registered SLIP-44 index). This ensures wallet interoperability: a seed from this paper wallet can be imported into any EIP-3 compliant Ergo wallet.

### Extended Public Key (xPub) Watch-