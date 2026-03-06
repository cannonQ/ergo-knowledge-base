---
title: "Sigma Protocols"
description: "Ergo's cryptographic proof system: SigmaProp, Schnorr signatures, Diffie-Hellman tuples, composable AND/OR/threshold operations, zero-knowledge proofs, ring signatures, and how they differ from account-based access control."
tags: [sigma-protocols, sigmaprop, zero-knowledge, schnorr, diffie-hellman, ring-signatures, privacy, concepts]
category: concept
difficulty: intermediate
sdk: [none]
updated: 2026-03-05
source: original
---

# Sigma Protocols

## What Are Sigma Protocols?

Sigma protocols (denoted as Sigma, or the Greek letter Sigma) are a family of cryptographic proof systems that let someone prove they know a secret **without revealing the secret itself**. This is the foundation of zero-knowledge proofs.

In Ergo, every contract returns a **SigmaProp** — a sigma proposition. This isn't just a true/false value. It's a cryptographic statement that can be proven through an interactive protocol (made non-interactive via the Fiat-Shamir transformation for blockchain use).

Why does this matter? Because Ergo contracts can express spending conditions like "prove you know the private key for this public key" or "prove you're one of these five people, without revealing which one" — things that are impossible in Bitcoin Script and impractical in Solidity.

## SigmaProp: The Core Type

Every ErgoScript contract must ultimately return a `SigmaProp`. There are two ways to create one:

### From a Boolean

Wrap any boolean expression with `sigmaProp()`:

```ergoscript
{
  val enoughErg = SELF.value > 1000000000L  // More than 1 ERG
  val correctHeight = HEIGHT > 500000
  sigmaProp(enoughErg && correctHeight)
}
```

This creates a "trivial" sigma proposition — it's either true or false, with no cryptographic proof needed. Anyone can spend this box if the conditions are met.

### From a Public Key

Public keys are inherently SigmaProp values:

```ergoscript
{
  val owner = PK("9fRAWhdxEsTcdb8PhGNrZfwqa65zfkuYHAMmkQLcic1gdLSV5vA")
  owner  // Only the holder of this private key can spend
}
```

This requires a cryptographic proof — the spender must demonstrate knowledge of the private key corresponding to this public key, without revealing the private key. This is a Schnorr signature under the hood.

## The Two Elementary Protocols

Ergo implements two foundational sigma protocols from which all others are composed:

### Schnorr Signature (proveDlog)

Proves knowledge of the discrete logarithm of a group element. In plain terms: "I know the private key for this public key."

```ergoscript
{
  // These are equivalent:
  PK("9fRAWhdxEsTcdb8PhGNrZfwqa65zfkuYHAMmkQLcic1gdLSV5vA")

  // Lower-level form:
  proveDlog(groupElement)  // Prove you know x such that g^x = groupElement
}
```

This is what every standard "send to address" transaction uses. The address encodes a public key, and spending requires proving knowledge of the corresponding private key via a Schnorr signature.

### Diffie-Hellman Tuple (proveDHTuple)

Proves that two values share identical discrete logarithms across different generators. In plain terms: "I know a secret that links these four curve points together."

```ergoscript
{
  proveDHTuple(g, h, u, v)
  // Proves: there exists x such that u = g^x AND v = h^x
}
```

This is the building block for more advanced protocols: ring signatures, shared secrets, and multi-party computation. ErgoMixer uses Diffie-Hellman tuples to enable non-interactive mixing (ZeroJoin protocol).

## Composability: AND, OR, Threshold

The real power of sigma protocols is **composability**. You can combine propositions using logical operators, and the resulting proof remains zero-knowledge:

### AND (both must prove)

```ergoscript
{
  val alice = PK("9fRAWhdx...")
  val bob = PK("9hHDQb9e...")
  alice && bob  // Both Alice AND Bob must sign
}
```

### OR (either can prove)

```ergoscript
{
  val alice = PK("9fRAWhdx...")
  val bob = PK("9hHDQb9e...")
  alice || bob  // Either Alice OR Bob can sign
}
```

The crucial property: in an OR proof, the verifier cannot tell **which** party actually provided the proof. If Alice spends the box, an observer cannot distinguish whether Alice or Bob signed. This is the basis of privacy-preserving protocols.

### Threshold (k-of-n)

```ergoscript
{
  val keys = Coll(
    PK("9fRAWhdx..."),  // Alice
    PK("9hHDQb9e..."),  // Bob
    PK("9iHkyh3k..."),  // Carol
    PK("9gWDz4ar..."),  // Dave
    PK("9eYSjGtm...")   // Eve
  )
  atLeast(3, keys)  // Any 3 of 5 can authorize
}
```

`atLeast(k, propositions)` creates a threshold sigma proposition. Any `k` of the `n` provided propositions must be proven. Like OR, the verifier cannot determine which specific `k` participants signed.

This is more powerful than Ethereum's multisig contracts: there's no on-chain record of which signers participated. The proof reveals only that the threshold was met.

### Mixing Boolean and Cryptographic Conditions

You can freely combine boolean-based and key-based sigma propositions:

```ergoscript
{
  val owner = PK("9fRAWhdx...")
  val timelock = sigmaProp(HEIGHT > 100000)

  // Owner can spend anytime, OR anyone can spend after block 100000
  owner || timelock
}
```

This pattern creates multiple "spending paths" — different ways the box can be spent under different circumstances.

## Zero-Knowledge Proofs in Practice

### Ring Signatures

A ring signature lets one member of a group sign a message such that any member could have been the signer. This is how ErgoMixer achieves privacy:

```
Alice, Bob, Carol, Dave, Eve form a "ring"
Alice signs a transaction
An observer sees: "someone in {Alice, Bob, Carol, Dave, Eve} signed"
The observer cannot determine it was Alice
```

In Ergo, ring signatures are constructed using OR-composition of Diffie-Hellman tuples. The prover constructs simulated proofs for all non-signing members and a real proof for themselves. The verifier sees valid proofs for all members but cannot distinguish real from simulated.

### ZKProof Scope

ErgoScript provides a `ZKProof` block for explicit zero-knowledge scoping:

```ergoscript
{
  ZKProof {
    // Everything inside is evaluated with zero-knowledge guarantees
    // Only SigmaProp operations allowed (no boolean ops)
    proveDlog(someGroupElement)
  }
}
```

## How Verification Works

The prover-verifier flow for sigma protocols:

1. **Reduction**: The ErgoTree interpreter evaluates the contract, reducing it to a `SigmaBoolean` — a tree of AND/OR/threshold nodes with `proveDlog` and `proveDHTuple` leaves.

2. **Proving**: The spender's wallet traverses the `SigmaBoolean` tree and generates cryptographic proofs for each leaf it can satisfy. For OR branches, it simulates proofs for the branches it doesn't need to prove. This uses the **Fiat-Shamir transformation** to make the interactive protocol non-interactive.

3. **Verification**: Miners verify the proof against the `SigmaBoolean`. The verification checks that the proof is valid without learning which specific secrets were used.

## vs. Ethereum's Access Control

The difference is fundamental:

**Ethereum (Solidity)**:
```solidity
require(msg.sender == owner);  // Simple address check
```
The blockchain records exactly who sent the transaction. There's no cryptographic privacy. Multisig requires an on-chain contract that tracks and reveals each signer.

**Ergo (ErgoScript)**:
```ergoscript
atLeast(2, Coll(PK(alice), PK(bob), PK(carol)))
```
The blockchain records only that 2-of-3 signed. It does not reveal which two. No multisig contract needed — the protocol itself provides threshold authorization with zero-knowledge.

This isn't just a privacy feature — it's a fundamentally different security model. Ergo contracts prove that authorization conditions are met through cryptographic proof, rather than checking revealed identities against a list.

## Applications in the Ecosystem

| Application | Sigma Protocol Used | Purpose |
|-------------|-------------------|---------|
| **Standard transactions** | Schnorr (proveDlog) | Prove ownership of address |
| **ErgoMixer** | Diffie-Hellman tuples + OR composition | Non-interactive mixing, ring signatures |
| **Stealth addresses** (EIP-41) | Diffie-Hellman key exchange | Receiving funds without revealing recipient address |
| **Multi-party contracts** | Threshold (atLeast) | DAO voting, multisig wallets |
| **Covert addresses** | proveDHTuple | Generate one-time receiving addresses |
| **Oracle pools** | Threshold signatures | k-of-n oracle data posting |

## Learn More

- [eUTXO Model](eutxo-model.md) — How SigmaProp fits into the transaction validation model
- [Boxes and Registers](boxes-and-registers.md) — The data structures that sigma protocols protect
- [ErgoScript Fundamentals: Boxes, Registers & Context](../guides/ergoscript-fundamentals/01-boxes-registers-context.md) — Hands-on SigmaProp tutorial, adapted from [DeCo Education](https://github.com/DeCo-Education/ErgoScript-Developer-Course)
