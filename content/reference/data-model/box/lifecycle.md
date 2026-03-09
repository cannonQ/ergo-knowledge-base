---
title: "Box Lifecycle"
category: reference
difficulty: intermediate
tags: [ergo]
source: ergodocs
source_url: "https://docs.ergoplatform.com/dev/data-model/box/lifecycle/"
updated: 2026-03-08
---

# Box Lifecycle

This page describes the journey of a box from creation to spending and destruction in the Ergo blockchain.

## Stages of a Box

1. **Creation**: A box is generated as an output of a transaction
2. **Existence**: The box remains in the UTXO set, available to be spent
3. **Spending**: The box is used as an input in a new transaction
4. **Destruction**: The box is removed from the UTXO set after being spent

## Key Characteristics

- Immutability
- Unique Identification
- Programmable Conditions
