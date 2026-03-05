---
title: kushti/dexy-stable — extract.es
description: "ErgoScript contract analysis: contracts/lp/pool/extract.es"
tags: [kushti, dexy-stable, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/kushti/dexy-stable"
contract_file: contracts/lp/pool/extract.es
project: kushti-dexy-stable
---
# ErgoScript Contract Analysis: `extract.es`

## Purpose

This contract implements **Extract-to-the-Future**, a mechanism in the Dexy stablecoin protocol that allows Dexy tokens to be extracted from the liquidity pool during depeg events (when Dexy trades below peg) and released back when the peg recovers. It manages a state machine with two transitions: **Extract** (when oracle rate < 95% of LP rate) and **Release** (when oracle rate > 101% of LP rate), enforced via time-locked tracking boxes and reserve validation.

---

## Inputs / Outputs

### Inputs
| Index | Description | Required | Notes |
|-------|-------------|----------|-------|
| 0 | LP Box | Yes | Singleton State NFT holding reserves; must be a valid AMM pool |
| 1 | Extract Box (SELF) | Yes | The contract itself; holds extractionNFT + Dexy tokens |
| 2+ | Optional (Update Box) | No | If present with `updateNFT`, bypasses all validation (governance override) |

### Outputs
| Index | Description | Required | Notes |
|-------|-------------|----------|-------|
| 0 | LP Box (updated) | Yes | Same as input LP; reserves adjusted by `deltaDexy` |
| 1 | Extract Box (successor) | Yes | Updated state; NFT, Dexy tokens, and proposition bytes preserved |

### Data Inputs (Read-Only)
| Index | Name | NFT Token | Purpose |
|-------|------|-----------|---------|
| 0 | Oracle Box | `oracleNFT` | Reads R4: nanoErgs per USD (oracle rate) |
| 1 | Tracking Box | `tracking95NFT` or `tracking101NFT` | Reads R7: Height when depeg threshold crossed |
| 2 | Bank Box | `bankNFT` | Verifies bank reserves ≤ 10,000 ERG (bank is "empty") |

---

## Key Logic

### Validation Flow

1. **Governance Override**
   - If INPUTS(0) contains `updateNFT`, skip all logic and return `true`
   - Allows protocol governance to update contract without going through state machine

2. **State Transition Guard**
   ```
   validDelay: lastBurnOrRelease < HEIGHT - T_delay (360 blocks)
   ```
   - Enforces cooldown period between consecutive Extract/Release operations
   - Prevents rapid state cycling

3. **Box Integrity Checks**
   - **Successor Box** (SELF → OUTPUTS(1)):
     - Extraction NFT preserved
     - Dexy token ID preserved
     - Proposition bytes unchanged (no code upgrade mid-transaction)
     - Value ≥ original value (no funds leakage)
     - Creation height within buffer tolerance (prevents timestamp spoofing)
   
   - **LP Box** (INPUTS(0) → OUTPUTS(0)):
     - LP NFT, LP tokens, Dexy token ID all preserved
     - Reserve Y (Dexy) changes by exactly `deltaDexy`
     - Reserve X (ERG) unchanged (AMM invariant for this operation)
     - Proposition bytes unchanged

4. **Extract Action** (deltaDexy > 0)
   ```
   Condition: oracleRate < 95% of LP rate AND bank is empty AND sufficient time has passed
   
   - validTracking95Box: Tracking box holds tracking95NFT
   - (HEIGHT - tracker95Height) > T_extract (720 blocks)
     ↳ At least 720 blocks must pass after rate fell below 95%
   - validBankBox: Bank box has ≤ 10,000 ERG
   - validExtractAmount: 
       0.97 * lpRate < oracleRate < 0.98 * lpRate
     ↳ Oracle rate must be in narrow band (97-98% of LP rate)
       to prevent arbitrage extraction during volatile conditions
   ```

5. **Release Action** (deltaDexy < 0)
   ```
   Condition: oracleRate > 101% of LP rate AND sufficient time has passed
   
   - validTracking101Box: Tracking box holds tracking101NFT
   - (HEIGHT - tracker101Height) > T_release (2 blocks)
     ↳ Quick release once peg recovers
   - validReleaseAmount:
       oracleRate > 1.01 * lpRate
     ↳ Oracle must confirm depeg is healed
   ```

6. **Oracle Rate Calculation**
   ```
   oracleRateXY = oracleBox.R4[Long] / 1,000,000
   (Converts nanoErgs per USD → nanoErgs per Dexy, 1 Dexy = 1 mg gold)
   ```

7. **LP Rate Validation**
   ```
   lpRateXY = reservesXOut / reservesYOut
   (ERG per Dexy token at pool)
   ```

---

## Registers Used

| Register | Type | Read/Write | Purpose |
|----------|------|-----------|---------|
| **R3** | Int (Long) | Read | `creationInfo._1`: Height when Extract box was created; used as timestamp for last burn/release operation |
| **R4** (Oracle) | Long | Read | Oracle rate: nanoErgs per USD |
| **R7** (Tracking) | Int | Read | Height when depeg threshold was crossed (tracking95/tracking101Box) |

**Note:** No R4-R9 writes occur in this contract; it only reads oracle and tracking data inputs.

---

## Tokens

| Token | Index | Purpose | Authentication |
|-------|-------|---------|-----------------|
| **extractionNFT** | tokens(0) | Singleton token identifying this Extract box state | Preserved across all transitions; prevents duplication |
| **Dexy Token** | tokens(1) | The stablecoin being extracted/released | ID verified against LP box; quantity adjusted by `deltaDexy` |
| **lpNFT** | LP box tokens(0) | Identifies the liquidity pool | Verified in `validLpBox` check |
| **tracking95NFT**