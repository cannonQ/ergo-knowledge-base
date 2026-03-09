---
title: "Ergo Register Encoding & Decoding Reference"
category: reference
difficulty: advanced
tags: [registers, decoding, hex, zigzag, sigma-types, data-model]
author: CannonQ
license: AGPL-3.0
source: original
updated: 2026-03-09
---
# Ergo Register Encoding & Decoding Reference

---

## Overview

Ergo box registers (R4-R9) store typed data in a compact binary encoding. The raw hex values returned by Explorer, GQL, and node APIs must be decoded to extract meaningful data. This document covers every encoding we encountered across marketplace sales extraction, LP pool analysis, and oracle pool queries.

**This is essential knowledge.** Every on-chain data extraction project we did — MewMart sales, SkyHarbor sales, LP pool reserves, oracle datapoints — required register decoding.

---

## Type Prefix Table

| Hex Prefix | Sigma Type | Description | Decoding Method |
|------------|-----------|-------------|-----------------|
| `04` | SInt | 32-bit signed integer | Zigzag + VLQ |
| `05` | SLong | 64-bit signed integer (variant 1) | Zigzag + VLQ |
| `06` | SLong/BigInt | 64-bit signed or arbitrary precision | Zigzag + VLQ, or length-prefixed big-endian |
| `08` | SigmaProp | Cryptographic proposition | `08cd` + 33-byte compressed public key |
| `0e` | Coll[Byte] | Byte array | VLQ length + raw bytes |

---

## Zigzag + VLQ Encoding (SInt / SLong)

Used for R4 prices, R6 royalty basis points, R9 fee values.

### Zigzag Encoding
Converts signed integers to unsigned for efficient VLQ encoding:
```
encode: zigzag(n) = (n << 1) ^ (n >> 63)
decode: original(z) = (z >> 1) ^ -(z & 1)

Examples:
   0 → 0
   1 → 2
  -1 → 1
  88 → 176
  92 → 184
  95 → 190
```

### VLQ (Variable Length Quantity)
Encodes unsigned integers in 7-bit chunks, high bit = continuation:
```
0-127:    single byte (high bit 0)
128+:     multiple bytes (high bit 1 on all but last)

Examples:
  0   → 0x00
  2   → 0x02
  176 → 0xB0 0x01  (176 = 0b10110000 → split: 0110000 | 0000001)
  190 → 0xBE 0x01
```

### Quick Reference (Common Values)

| Value | Zigzag | VLQ Hex | Full Register |
|-------|--------|---------|---------------|
| 0 | 0 | `00` | `0500` |
| 1 | 2 | `02` | `0502` |
| 2 | 4 | `04` | `0504` |
| 87 | 174 | `ae01` | `05ae01` |
| 88 | 176 | `b001` | `05b001` or `060158` |
| 92 | 184 | `b801` | `05b801` |
| 95 | 190 | `be01` | `05be01` |
| 997 | 1994 | `ca0f` | `05ca0f` |

**Note:** Some encoders use prefix `05`, others use `06`. Both decode the same way for SLong values.

---

## Coll[Byte] Encoding

Used for R7 payment token IDs, R8 labels, R9 JSON metadata.

**Format:** `0e` + VLQ(length) + raw bytes

### Examples

| String | Full Hex |
|--------|----------|
| `"0"` | `0e0130` |
| `"Hello"` | `0e0548656c6c6f` |
| `"MewMart,Cyberverse,Sell"` | `0e174d65774d6172742c437962657276657273652c53656c6c` |

### Decoding Steps
1. Skip `0e` prefix
2. Read VLQ-encoded length
3. Read that many bytes
4. Decode as UTF-8 (or keep as hex for token IDs)

---

## BigInt Encoding

Used for large prices (nanoERG values in marketplace contracts).

**Format:** `06` + VLQ(byte_length) + big-endian bytes

### Example
```
R4: 060510ca174780
  06     = BigInt type
  05     = 5 bytes follow
  10ca174780 = big-endian value
```

### Decoding
```python
def decode_bigint(hex_str):
    if hex_str.startswith("06"):
        hex_str = hex_str[2:]
    data = bytes.fromhex(hex_str)
    # VLQ decode length
    length, idx = decode_vlq(data)
    # Read big-endian bytes
    value_bytes = data[idx:idx + length]
    return int.from_bytes(value_bytes, 'big', signed=True)
```

---

## SigmaProp Encoding

Used for R5 seller public keys in marketplace contracts.

**Format:** `08cd` + 33-byte compressed EC point (ProveDlog)

### Example
```
08cd02b30612080af7f82aba4a21095b2f515c923c7dcd545ff3a554aa7ba602375f01
  08   = SigmaProp type
  cd   = ProveDlog marker
  02b30612... = 33-byte compressed public key
```

### Converting to Address
The 33-byte public key (`02...` or `03...`) is a compressed secp256k1 point. To get the Ergo address, you need `ergo-lib` or equivalent — there's no simple hex→address conversion.

---

## Marketplace Register Conventions

### MewMart Listing Box Registers
| Register | Type | Content |
|----------|------|---------|
| R4 | SLong or BigInt | Price in nanoERG (or token smallest unit) |
| R5 | SigmaProp | Seller's proposition bytes (public key) |
| R6 | SLong | Royalty basis points |
| R7 | Coll[Byte] | Payment token ID (empty hex = ERG payment) |
| R8 | Coll[Byte] | Label string (e.g., `"MewMart,Cyberverse,Sell"`) |
| R9 | SLong | Fee basis points |

### SkyHarbor Listing Box Registers
| Register | Type | Content |
|----------|------|---------|
| R4 | SLong | Price in nanoERG |
| R5 | Coll[Byte] | Seller proposition bytes |
| R6 | Coll[Byte] | Embedded box data (fee/royalty info) |
| R7 | GroupElement | Seller's public key |

### Spectrum Pool Box Registers
| Register | Type | Content |
|----------|------|---------|
| R4 | SInt | Fee numerator (e.g., 997 = 0.3% fee) |

---

## Python Decoder (Complete)

```python
def decode_vlq(data: bytes):
    """Returns (value, bytes_consumed)"""
    result = 0
    shift = 0
    for i, byte in enumerate(data):
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, i + 1
        shift += 7
    return result, len(data)

def zigzag_decode(n):
    return (n >> 1) ^ -(n & 1)

def decode_slong(hex_str):
    if hex_str.startswith(("05", "06")):
        hex_str = hex_str[2:]
    data = bytes.fromhex(hex_str)
    value, _ = decode_vlq(data)
    return zigzag_decode(value)

def decode_bigint(hex_str):
    if hex_str.startswith("06"):
        hex_str = hex_str[2:]
    data = bytes.fromhex(hex_str)
    length, idx = decode_vlq(data)
    if length <= 0:
        return 0
    return int.from_bytes(data[idx:idx+length], 'big', signed=True)

def decode_coll_byte(hex_str):
    if hex_str.startswith("0e"):
        hex_str = hex_str[2:]
    data = bytes.fromhex(hex_str)
    length, idx = decode_vlq(data)
    content = data[idx:idx+length]
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        return content.hex()

def decode_sigmaprop(hex_str):
    if hex_str.startswith("08"):
        hex_str = hex_str[2:]
    if hex_str.startswith("cd"):
        return hex_str[2:2+66]  # 33-byte compressed pubkey
    return hex_str

def decode_register(hex_str):
    """Auto-detect type and decode."""
    if not hex_str:
        return None
    prefix = hex_str[:2]
    if prefix == "04":
        return decode_slong(hex_str)  # SInt uses same VLQ
    elif prefix in ("05", "06"):
        if prefix == "06" and len(hex_str) > 6:
            try:
                return decode_bigint(hex_str)
            except:
                pass
        return decode_slong(hex_str)
    elif prefix == "0e":
        return decode_coll_byte(hex_str)
    elif prefix == "08":
        return decode_sigmaprop(hex_str)
    return hex_str

def encode_slong(value):
    """Encode integer as SLong hex (for building register filters)."""
    zigzag = value * 2 if value >= 0 else (-value * 2) - 1
    vlq = []
    while zigzag >= 0x80:
        vlq.append((zigzag & 0x7F) | 0x80)
        zigzag >>= 7
    vlq.append(zigzag & 0x7F)
    return "05" + bytes(vlq).hex()
```

---

## JavaScript Decoder

```javascript
function decodeVLQ(bytes) {
    let result = 0, shift = 0, consumed = 0;
    for (const byte of bytes) {
        consumed++;
        result |= (byte & 0x7F) << shift;
        if (!(byte & 0x80)) break;
        shift += 7;
    }
    return [result, consumed];
}

function zigzagDecode(n) {
    return (n >> 1) ^ -(n & 1);
}

function decodeSLong(hex) {
    if (hex.startsWith("05") || hex.startsWith("06")) hex = hex.slice(2);
    const bytes = Buffer.from(hex, 'hex');
    const [val] = decodeVLQ(bytes);
    return zigzagDecode(val);
}
```

---

## Common Gotchas

1. **`05` vs `06` prefix ambiguity** — both can encode SLong. `06` is also used for BigInt. If the hex after `06` decodes to a suspiciously small "length" value followed by reasonable bytes, it's BigInt. Otherwise treat as SLong.

2. **Price type varies by marketplace** — MewMart uses both SLong (`05`) and BigInt (`06`) for R4 prices. Always try both decoders.

3. **Empty R7 = ERG payment** — in MewMart, if R7 decodes to an empty hex string, the listing is priced in ERG. A non-empty R7 is the payment token ID.

4. **R4 `060158`** — this decodes to SLong value 88 (not BigInt). The `06` prefix with a small value following is SLong, not BigInt. Context matters.

5. **Explorer API returns rendered values** — if using `api.ergoplatform.com`, the `additionalRegisters` include `renderedValue` and `sigmaType` fields that are pre-decoded. GQL only returns raw hex.
