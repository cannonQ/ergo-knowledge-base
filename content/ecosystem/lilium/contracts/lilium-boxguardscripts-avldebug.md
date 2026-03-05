---
title: LiliumErgo/scala-api — AVLdebug.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/AVLdebug.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/AVLdebug.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: AVLdebug.es

## Purpose
This contract implements an **AVL tree proof-of-membership verification** mechanism, validating that a value exists in an authenticated AVL tree at a specific index. It serves as a debugging/testing utility for AVL tree operations in the Lilium framework, ensuring that off-chain proofs correctly authenticate data stored in the tree.

## Inputs / Outputs

### Input
- **SELF**: A box containing:
  - **R4**: An `AvlTree` — the authenticated AVL tree root digest
  - **R5**: A `Long` — the index key to query in the tree

### Output
- **OUTPUTS(0)**: An output box expected to contain:
  - **R4**: A `Coll[Byte]` — the value that should match the tree's stored value

### Data Input
- **Context Extension Variable 0**: A `Coll[Byte]` containing the **AVL tree proof** (Merkle proof path) required to authenticate the lookup.

## Key Logic

The contract validates a **stateless AVL tree membership proof** through these steps:

1. **Extract tree state**: Reads the AVL tree root from `SELF.R4` and the lookup index from `SELF.R5`
2. **Hash the key**: Converts the index (`Long`) to bytes, then hashes it with Blake2b256 to create the AVL tree key
3. **Prove membership**: Uses the proof (from context extension) to query the AVL tree at `keyHash`, retrieving the stored value
4. **Verify consistency**: Hashes the value in `OUTPUTS(0).R4` and asserts it equals the value retrieved from the tree
5. **Atomicity**: Succeeds only if the tree proof is valid **AND** the output value matches the authenticated tree value

**Validation outcome**: `sigmaProp( valueFromAvlTree == dummyCheckValue )`

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** (input) | `AvlTree` | Authenticated AVL tree root digest (acts as single source of truth) |
| **R5** (input) | `Long` | Index/key to query in the tree |
| **R4** (output) | `Coll[Byte]` | The claimed value, verified against tree via hash comparison |

## Tokens

**No tokens used.** This contract does not employ NFTs or native tokens. It relies entirely on **Sigma protocol verification** of the AVL tree proof and cryptographic hash commitments (Blake2b256).

## Integration Pattern

### Off-Chain Bot / Headless dApp Workflow

1. **Construct the transaction**:
   - Read an AVL tree from persistent storage (e.g., a State NFT box or database)
   - Select a `SELF` box containing the tree root in R4 and an index in R5
   - Generate a **Merkle proof** by traversing the AVL tree from the queried key to the root

2. **Context Extension Setup**:
   - Serialize the AVL tree proof as a `Coll[Byte]`
   - Attach it to the transaction via **Context Extension variable 0**

3. **Output Construction**:
   - Create `OUTPUTS(0)` with:
     - The value retrieved from the AVL tree (hashed and stored in R4)
     - Any other state or UTxO structure required downstream

4. **Verification**:
   - The ErgoScript contract automatically:
     - Verifies the proof cryptographically
     - Compares hash digests
     - Asserts atomic consistency

### Off-Chain Guarantee
The transaction **fails** if:
- The proof is invalid (AVL tree rejects it)
- `blake2b256(OUTPUTS(0).R4)` ≠ value retrieved from tree
- Context extension variable 0 is missing or malformed

## Related Contracts

**Likely dependencies** (inferred from Lilium framework patterns):

- **State NFT / Singleton Contract**: Likely manages the AVL tree root and guards state mutations
- **AVL Tree Storage Contract**: May hold the full AVL tree across multiple boxes (sharded by key range)
- **Multi-stage Contracts**: This is a validation stage in a larger **state machine** where:
  - Stage 1: Read from AVL tree (this contract)
  - Stage 2: Update state based on verified values
  - Stage 3: Persist changes back to tree storage

---

## Security Considerations

- **AVL Tree Proof Validation**: Relies on Ergo's native AVL tree implementation — proofs are cryptographically binding
- **Hash Commitment**: Blake2b256 makes it infeasible to forge values that hash to expected digests
- **Stateless Design**: No mutable state — validates in isolation (suitable for parallel verification)
- **Debug Utility**: The name "AVLdebug" suggests this is for testing; production use should validate that the proof source is trustworthy