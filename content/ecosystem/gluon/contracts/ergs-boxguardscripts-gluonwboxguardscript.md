---
title: StabilityNexus/Gluon-Ergo-Contracts — GluonWBoxGuardScript.es
description: "ErgoScript contract analysis: modules/gluonw-base/src/main/resources/ErgoContracts/GluonW/Ergs/BoxGuardScripts/GluonWBoxGuardScript.es"
tags: [stabilitynexus, gluon-ergo-contracts, ergoscript, contract]
category: ecosystem
difficulty: advanced
sdk: [none]
updated: 2026-03-09
source: auto-generated
source_repo: "https://github.com/StabilityNexus/Gluon-Ergo-Contracts"
contract_file: modules/gluonw-base/src/main/resources/ErgoContracts/GluonW/Ergs/BoxGuardScripts/GluonWBoxGuardScript.es
project: stabilitynexus-gluon-ergo-contracts
---
# GluonW Box Guard Script Analysis

## Purpose

This contract serves as the **guard script** for the central reactor box in the GluonW protocol—a stablecoin system that manages two synthetic assets (Neutrons and Protons) backed by ERG collateral. It validates five transaction types (Fission, Fusion, Beta Decay ±, and Treasury updates) by enforcing invariants on token balances, ERG reserves, and state registers while requiring oracle price feeds for certain operations.

---

## Inputs / Outputs

### Input Boxes
- **GluonWBox (SELF)**: The reactor singleton box containing:
  - Token 0: GluonWNFT (1 qty) — Singleton identifier
  - Token 1: Neutrons (variable qty)
  - Token 2: Protons (variable qty)
  - ERG value (reserve collateral)
  - Registers: R4–R9 (see below)

- **UserPk** (Fission/Fusion/Beta Decay): User's spending box (implicit in outputs)
- **MultisigUtxo** (Treasury Update, INPUTS(1)): Treasury multisig authorization box

### Data Inputs
- **OracleBox**: Gold price oracle (CONTEXT.dataInputs(0)) — read-only, used for price validation in Fission/Fusion (enforcement incomplete in provided code)

### Output Boxes
- **OUT_GLUONW_BOX (OUTPUTS(0))**: Updated reactor box with modified token quantities and/or registers
- **UserPk output**: User receives tokens or ERGs

---

## Key Logic

The contract identifies transaction type by comparing token and ERG value changes between input and output reactor box:

### **1. Fission Transaction**
```
Neutrons decrease ∧ Protons decrease ∧ ERG value increases
```
- User sends ERGs → receives Neutrons + Protons
- Both synthetic assets removed from circulation (stored in reactor)
- Enforces: R5 (Treasury multisig), R4 (total supplies), and dev fee cap (R6)

### **2. Fusion Transaction**
```
Neutrons increase ∧ Protons increase ∧ ERG value decreases
```
- User sends Neutrons + Protons → receives ERGs
- Both synthetic assets returned to circulation
- Dev fees (if configured) applied to user output, tracked in R6

### **3. Beta Decay Plus (β⁺)**
```
Neutrons decrease ∧ Protons increase ∧ ERG value constant
```
- User transmutes Protons → Neutrons
- Protons removed from circulation, Neutrons added
- Fee-neutral (Erg value preserved)

### **4. Beta Decay Minus (β⁻)**
```
Neutrons increase ∧ Protons decrease ∧ ERG value constant
```
- User transmutes Neutrons → Protons
- Neutrons removed from circulation, Protons added
- Fee-neutral (Erg value preserved)

### **5. Update Treasury Multisig**
```
INPUTS(1).propositionBytes == TREASURY_MULTISIG.propBytes
```
- Current treasury multisig (from R5) authorizes an update
- New multisig stored in output R5
- All other box properties (NFT, tokens, supplies) immutable

### **Invariants Enforced**
- **GluonWNFT persistence**: Token ID in R4 immutable (singleton constraint)
- **Neutron/Proton token IDs** immutable across transaction
- **Contract script (propositionBytes)** unchanged
- **Total supply (R4)** unchanged
- **Max dev fee threshold (R6._2)** unchanged
- **Dev fees (R6._1)** non-decreasing (accumulation-only)
- **Volume buckets (R7, R8)** and last block (R9) updated per transaction type

---

## Registers Used

| Register | Type | Purpose | Mutable |
|----------|------|---------|---------|
| **R4** | `(Long, Long)` | Total Neutrons supply, Total Protons supply | ✗ No |
| **R5** | `SigmaProp` | Treasury multisig address (authorization) | ✓ Yes (Treasury update only) |
| **R6** | `(Long, Long)` | (Dev fees accumulated, Max dev fee cap) | ✓ Yes (Fission/Fusion increment R6._1) |
| **R7** | `Coll[Long]` | Beta Decay Plus volume history (14 buckets × 720 blocks each ≈ 14 days) | ✓ Yes |
| **R8** | `Coll[Long]` | Beta Decay Minus volume history (14 buckets × 720 blocks each ≈ 14 days) | ✓ Yes |
| **R9** | `Long` | Last bucket update block height | ✓ Yes |

---

## Tokens

### Native Tokens in Reactor Box

| Position | Token | Quantity | Purpose |
|----------|-------|----------|---------|
| **0** | **GluonWNFT** | 1 | Singleton identifier; ensures only one authorized reactor box exists |
| **1** | **Neutrons** | Variable | Synthetic asset representing long exposure; minted/burned by Fission/Fusion |
| **2** | **Protons** | Variable | Synthetic asset representing short exposure; minted/burned by Fission/Fusion |

### Token ID Rule
All three token IDs are **hard-coded** during contract initialization; any transaction attempting to swap token IDs fails the `__gluonWBoxPersistedValueCheck` invariant.

### Circulation Model
```
TokensInCirculation = TotalSupply(R4) - TokensInReactorBox
```
- **Fission**: Tokens moved from circulation → reactor (balance increases)
- **Fusion**: Tokens moved from reactor → circulation (balance decreases)

---

## Integration Pattern

### Off-Chain Bot / Headless dApp Responsibilities

1. **Transaction Construction**
   - Identify transaction type (Fission/Fusion/Beta Decay 