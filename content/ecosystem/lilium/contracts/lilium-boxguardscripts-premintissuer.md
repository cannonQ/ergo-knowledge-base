---
title: LiliumErgo/scala-api — PreMintIssuer.es
description: "ErgoScript contract analysis: conf/contracts/Lilium/BoxGuardScripts/PreMintIssuer.es"
tags: [liliumergo, scala-api, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/LiliumErgo/scala-api"
contract_file: conf/contracts/Lilium/BoxGuardScripts/PreMintIssuer.es
project: liliumergo-scala-api
---
# ErgoScript Contract Analysis: PreMint Issuer

## Purpose

This contract guards an issuer box that mints and distributes pre-mint tokens to users. It validates that tokens created from this box are issued in the correct amount and transferred to the intended recipient's address, ensuring atomic and authorized pre-mint token issuance.

## Inputs / Outputs

| Component | Description |
|-----------|-------------|
| **Input (SELF)** | The issuer box itself, containing the pre-mint token amount in R4 and recipient's public key in R5 |
| **Output (OUTPUTS(0))** | The newly created box that receives the minted pre-mint tokens and becomes locked to the user's public key (userPk) |

The contract enforces that exactly one output receives the tokens—OUTPUTS(0)—ensuring deterministic token routing.

## Key Logic

The contract validates a pre-mint token issuance transaction through two core checks:

1. **Token Validation** (`validTokens`):
   - The first output must receive a native token with Token ID equal to `SELF.id` (the issuer box ID itself)
   - The token quantity must exactly match the `preMintTokenAmount` stored in R4
   - This ensures the correct amount is minted in a single atomic operation

2. **Recipient Validation** (`validUser`):
   - The output box's guarding script (`propositionBytes`) must match the `userPk` (user's public key) stored in R5
   - This ensures tokens are locked to the authorized recipient, not an arbitrary address

3. **Authorization** (`_txOperatorPK`):
   - A compile-time constant signature must be provided by `_txOperatorPK`
   - The final proposition combines both conditions: `validPreMintMintingTx && _txOperatorPK` requires both contract logic AND operator authorization via Sigma protocol

## Registers Used

| Register | Type | Purpose |
|----------|------|---------|
| **R4** | `Long` | Stores the `preMintTokenAmount`—the quantity of pre-mint tokens to be minted and transferred |
| **R5** | `SigmaProp` | Stores the `userPk`—the recipient's public key whose proposition bytes must guard the output box |

These registers enable parameterized issuance: each issuer box instance can mint a different quantity to a different user by varying R4 and R5 at box creation time.

## Tokens

- **Native Token**: The issuer box itself (`SELF.id`) serves as the **Token ID** for the minted tokens
  - This follows the Ergo native token **Token ID rule**: a token's ID is the box ID in which it is first created
  - The pre-mint tokens are created in OUTPUTS(0) with quantity `preMintTokenAmount`
  - No NFT singleton pattern is used here; the issuer box acts as a one-time minting authority

## Integration Pattern

**Off-chain Construction** (expected from calling dApp/bot):

1. **Create the Issuer Box**:
   - Fund a new box with sufficient minimum box value (in nERG)
   - Set R4 = desired pre-mint token amount (e.g., `1000000000L` for 1B tokens)
   - Set R5 = recipient user's `SigmaProp` (their public key in Sigma encoding)
   - Guard it with this contract's ErgoTree

2. **Construct the Minting Transaction**:
   - Include the issuer box as an input
   - Create OUTPUTS(0) as the recipient box:
     - Must hold the newly minted token: `(SELF.id, preMintTokenAmount)`
     - Must have guarding script = `userPk.propBytes`
     - Can hold additional value or tokens
   - All other outputs are unrestricted (can add change boxes, etc.)

3. **Sign the Transaction**:
   - Sign with both:
     - The issuer box's script (satisfying `validPreMintMintingTx`)
     - The operator's private key (satisfying `_txOperatorPK`)
   - Return the signed transaction to the blockchain

**Verification**: The contract ensures atomic validation—tokens cannot exist outside the issuer box unless this exact rule is satisfied, preventing token theft or misallocation.

## Related Contracts

From the file path `conf/contracts/Lilium/BoxGuardScripts/`, this contract is part of a **multi-stage contract system** (likely the Lilium protocol):

- **Likely upstream**: A contract that creates issuer boxes (possibly a minting pool or pre-mint manager)
- **Likely downstream**: User-side contracts that receive and stake/lock the minted pre-mint tokens
- **Related sibling**: Other `BoxGuardScripts` in the same directory (e.g., token vesting, staking, or governance contracts) that interact with pre-mint tokens post-issuance

The structure suggests a **State Machine** pattern where the issuer box transitions from an unspent state (holding issuance rules) to a consumed state (tokens distributed), enabling sequential pre-mint operations across multiple users.

---

**Key Ergo Concepts Applied:**
- eUTXO model: State transition via box consumption/creation
- Native Tokens: Token ID rule enforcement
- Sigma Protocols: Multi-signature authorization (`sigmaProp(...) && _txOperatorPK`)
- Register-based Parameterization: R4/R5 customize behavior per box instance