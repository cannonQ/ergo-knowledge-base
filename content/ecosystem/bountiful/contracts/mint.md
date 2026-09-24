---
title: StabilityNexus/Bountiful-BountyPlatform-Ergo — mint.es
description: "ErgoScript contract analysis: contracts/mint.es"
tags: [stabilitynexus, bountiful-bountyplatform-ergo, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-09-24
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Bountiful-BountyPlatform-Ergo"
contract_file: contracts/mint.es
project: stabilitynexus-bountiful-bountyplatform-ergo
---
# ErgoScript Contract Analysis: `mint.es`
## StabilityNexus/Bountiful-BountyPlatform-Ergo

---

## Purpose

This contract serves as a **minting/initialization validator** for the Bountiful Bounty Platform. It ensures that when a new bounty is created, the Bounty ID Token (IDT) is correctly transferred from the minting box to a newly instantiated bounty contract, and that the contract's ErgoTree matches the expected specification.

---

## Inputs / Outputs

### Inputs
- **SELF** (Minting Box)
  - Contains the Bounty ID Token (IDT) as the first native token
  - Amount and ID immaterial; only presence and transfer verified

### Outputs
- **OUTPUTS(0)** (Bounty Contract Box)
  - Receives the same Bounty ID Token from SELF
  - Must have a propositionBytes (ErgoTree) matching the contract specification hash
  - Becomes the new state box for the bounty

---

## Key Logic

The contract enforces two invariant conditions via **Sigma protocol AND composition**:

1. **Token Spend Invariant** (`correctSpend`):
   - Verifies the Bounty ID Token's ID in SELF matches the token ID in OUTPUTS(0)
   - Confirms the entire token quantity from SELF is transferred (no splitting/burning)
   - Ensures atomic token movement with no loss or duplication

2. **Contract Verification Invariant** (`correctContract`):
   - Hashes the propositionBytes (complete ErgoTree) of OUTPUTS(0) using **blake2b256**
   - Compares result against the expected `${contract_bytes_hash}` constant (injected at compile-time)
   - Prevents contract template substitution attacks by validating exact bytecode match

**Validation Result:**
- Both conditions must hold (SigmaUSD-style AND composition via `sigmaProp(allOf(...))`)
- Transaction succeeds only if the output box is the intended bounty contract with the IDT correctly transferred
- Prevents creation of malicious contract variants or token loss

---

## Registers Used

**None explicitly read or written.**

- **Implicit Context Access**: Uses `SELF` and `OUTPUTS(0)` from the ErgoScript context
- Registers R0–R9 are not referenced in this contract
- All state initialization likely handled in the bounty contract itself (not this minting contract)

---

## Tokens

### Native Tokens

- **Bounty ID Token (IDT)**
  - **Role**: State singleton / authentication token
  - **Location**: `SELF.tokens(0)` → `OUTPUTS(0).tokens(0)`
  - **Invariant**: Token ID (`_1`) and quantity (`_2`) must match exactly
  - **Purpose**: Uniquely identifies and gates state mutations on the active bounty box
  - **Pattern**: Standard Ergo singleton pattern using NFT-like native token

---

## Integration Pattern

### Off-Chain Requirements

The off-chain minting bot (or headless dApp) must:

1. **Obtain the IDT**
   - Possess a UTXO holding the Bounty ID Token with known ID and quantity

2. **Construct the Bounty Contract**
   - Instantiate the bounty contract ErgoTree with all initialization parameters
   - Compile to propositionBytes using Sigma compiler (e.g., via ergoscala or ergo-appkit)
   - Hash result with blake2b256

3. **Verify Contract Hash**
   - Ensure the computed hash matches the minting contract constant `${contract_bytes_hash}`
   - If mismatch, minting box will reject the transaction (validation fails)

4. **Build and Sign Transaction**
   - Input: Minting box (SELF) with IDT
   - Output: Bounty contract box with same IDT, correct propositionBytes, and initial state registers
   - Sign with sufficient sigma proofs to satisfy both minting and bounty contract guards
   - Broadcast; miners validate the Sigma proposition and blake2b256 hash

### Data Flow
```
Off-Chain Bot
    ↓
Compile Bounty Contract → blake2b256 hash
    ↓
Construct TX: minting box + bounty contract box (with IDT + hash match)
    ↓
Sign & Submit
    ↓
Minting.es validates: IDT spend + contract hash
    ↓
Bounty contract box created; IDT locked in new state box
```

---

## Related Contracts

**Likely Composition:**

1. **Bounty Contract** (`bounty.es` or similar, inferred)
   - The contract whose ErgoTree is hashed and verified by `mint.es`
   - Handles bounty state transitions, claim submissions, funding, and payouts
   - Must be deterministically compiled to match the hash constant

2. **Governance / Minting Controller** (if present)
   - May guard the minting box itself (separate guard)
   - Controls which bounties are created and at what parameters

3. **Claim / Submission Contract** (inferred)
   - Child contract that processes bounty claims
   - Likely references the bounty IDT for authorization
   - Composed via multi-stage contract pattern with state NFT ownership

**Reference via Token ID:**
- The minting contract does **not** hardcode bounty contract address; instead, it uses the IDT as the state singleton anchor
- All downstream contracts (claim handlers, payout validators) lock the same IDT, creating a state machine family

---

## Security Considerations

| Aspect | Analysis |
|--------|----------|
| **Script Injection** | ✓ Protected by blake2b256 constant; exact bytecode match required |
| **Token Loss** | ✓ Enforced: `_2 == contractBox.tokens(0)._2` ensures no quantity loss |
| **Duplication** | ✓ IDT is first token (`tokens(0)`); only one instance can exist per tx output |
| **Minting Authority** | ⚠ Not enforced in this contract; guard assumed on minting box input |
| **State NFT Persistence** | ✓ IDT transfer ensures subsequent transactions can identify the bounty |

---

## Code Annotations

```ergoscript
{
```

*Listing truncated at generation time; the closing lines are missing. Consult the source repository for the complete file.*
