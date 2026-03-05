---
title: LiliumErgo/scala-api — StateContract.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/StateContract.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/StateContract.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: StateContract.es

## Purpose

This contract manages NFT minting and sales through a **State Machine** pattern, maintaining a singleton state box that tracks metadata issuance via an AVL tree. It validates each NFT sale transaction, enforcing metadata integrity, payment routing, and collection supply constraints while supporting multiple payment methods (ERG, whitelist tokens, premint tokens, custom payment tokens).

---

## Inputs / Outputs

### Inputs
| Index | Description |
|-------|-------------|
| 0 | **SELF** – State box (singleton, holds AVL tree of metadata) |
| 1 | **Buyer Proxy Box** – Input from buyer; must match `_proxyContractBytes` |
| 2 | **Optional** – Context box (checked for fee payment flag in R5) |

### Outputs
| Index | Description |
|-------|-------------|
| 0 | **Issuer Box** – New NFT box with minted collection token and metadata |
| 1 | **State Box (recreated)** – Updated singleton with new AVL tree state and incremented index |
| 2 | **User/Artist Box** – Receives artist's share of payment |
| 3 | **Lilium Fee Box** – Receives protocol fee |
| 4 | **Optional Sale LP Box** – Liquidity pool box (if `usePool` is true) |

---

## Key Logic

### Sale Eligibility
```
✓ Sale is valid if:
  - hasSaleStarted (R7._1 ≤ current timestamp) OR
  - premintAccepted (early access token holders) OR
  - whitelistBypass (whitelist bypass flag enabled)
  
  AND
  
  - !hasSaleEnded (R7._2 > current timestamp) OR
  - isInfiniteSale (R7._2 == -1L, no end date)
```

### Metadata Validation
1. **AVL Tree Lookup**: Retrieves serialized NFT metadata from the issuer box's AVL tree (R5) using the current index
2. **Blake2b256 Hash Match**: Reconstructs metadata bytes from issuer box output registers (R5–R8) and verifies hash matches AVL data
3. **Metadata Structure**:
   - **Traits** – Key-value pairs (trait name, trait value)
   - **Levels** – Attributes with min/max ranges
   - **Stats** – Numeric attributes with min/max ranges
   - **Royalty** – Artist payment addresses and percentages
   - **Explicit Flag** – Binary indicator (first byte of additionalInfo)

### Token & Payment Flow
- **Collection Token**: Decremented in state box; 1 unit transferred to issuer box
- **Singleton Token**: Preserved in recreated state box
- **Payment Validation**: Verifies correct amount routed based on payment method:
  - ERG direct payment
  - Whitelist token (whitelistTokenId from R9(0))
  - Premint token (premintTokenId from R9(1))
  - Custom payment token (paymentTokenId from R9(2))
- **Lilium Fee**: `(_liliumFeeNum * _priceOfNFT) / _liliumFeeDenom` routed to `_liliumSigmaProp`

### Supply Cap Enforcement
```
validSupplyCap: index + 1 ≤ nftSupplyCap
isLastSale: index + 1 == nftSupplyCap (triggers state box destruction)
```

### Liquidity Pool Integration
```
isValidSaleLP(buyerIsPayingFee):
  if buyerIsPayingFee OR INPUTS(2).R5 == 1L:
    return true
  else:
    return OUTPUTS(4).tokens(0)._1 == singleton token ID
```

---

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `AvlTree` | Issuance Box AVL tree (currently unused in shown logic) |
| **R5** | `AvlTree` | **Issuer Box AVL tree** – Maps metadata index → serialized NFT attributes |
| **R6** | `Long` | **Current NFT Index** – Position in minting sequence (starts at 1L, not 0) |
| **R7** | `(Long, Long)` | **Sale Window** – (saleStartTimestamp, saleEndTimestamp); -1L = infinite |
| **R8** | `Coll[Boolean]` | **Feature Flags** – `[isReturn, whitelistAccepted, whitelistBypass, premintAccepted, paymentTokenAccepted, usePool, ergAccepted]` |
| **R9** | `Coll[Coll[Byte]]` | **Token IDs** – `[whitelistTokenId, premintTokenId, paymentTokenId]` |

---

## Tokens

### State Box Tokens
| Position | Token | Amount | Purpose |
|----------|-------|--------|---------|
| 0 | **Singleton Token** (`_singletonToken`) | 1 | Authenticates state box; ensures only one active instance |
| 1 | **Collection Token** (`_collectionToken`) | Variable | Supply tracker; decremented on each sale; transferred to issuer box |

### Related Token IDs (in R9)
- **Whitelist Token ID** – Guards early access purchases
- **Premint Token ID** – Guards premint phase purchases
- **Payment Token ID** – Alternative payment method (if `paymentTokenAccepted`)

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Metadata Preparation**
   - Construct metadata structures (traits, levels, stats, royalty)
   - Serialize into bytes with delimiter `0x7f000fbaf55fab7e`
   - Compute Blake2b256 hash and insert into AVL tree at index position

2. **AVL Tree Construction**
   - Build **AVL tree insertion proof** for current index
   - Pass proof via **Context Extension** variable 0: `getVar[Coll[Byte]](0)`