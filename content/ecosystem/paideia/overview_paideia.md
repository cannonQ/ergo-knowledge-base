---
title: paideiadao/paideia-offchain — Overview
description: Paideia off-chain logic — transaction assembly, bot operations in Python
tags: [paideiadao, paideia-offchain, dao, python]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/paideiadao/paideia-offchain"
project: paideiadao-paideia-offchain
group: dao
priority: medium
languages: [python]
contract_count: 0
pattern_match_count: 0
---
# Paideia Off-Chain Developer Overview

## Overview

**paideia-offchain** is the off-chain Python library and bot framework powering the Paideia DAO platform on Ergo. It handles all transaction assembly, signing coordination, and automated bot operations required to interact with the Paideia suite of on-chain multi-stage contracts. Rather than embedding business logic inside wallets or front-end applications, this project implements the headless dApp pattern — separating transaction-building concerns from user-interface concerns so that the same logic can serve bots, backend services, and SDK consumers equally.

Within the Ergo ecosystem, Paideia is a full-featured DAO toolkit that relies heavily on the eUTXO model's ability to encode governance state directly in Boxes and Registers. The off-chain layer is responsible for locating the relevant eUTXOs from the chain, constructing well-formed transactions that satisfy the on-chain ErgoScript guards, and submitting or relaying those transactions. This includes governance actions such as proposal creation, voting, treasury management, and staking, each of which requires careful construction of multi-input transactions with precise Register assignments and token flows.

The project sits at the intersection of Python tooling and the Ergo blockchain's extended UTXO model, making it a reference implementation for teams building DAO infrastructure on Ergo. It demonstrates how to programmatically drive complex multi-stage contracts from Python without requiring a browser wallet, making it suitable for both automated bot workflows and server-side transaction services.

---

## Architecture

The codebase is organized around distinct functional layers that mirror the lifecycle of a transaction on Ergo:

### Chain Interaction Layer
- **Node / Explorer API clients** — thin wrappers around the Ergo Node REST API and/or Ergo Explorer API. These are responsible for fetching unspent Boxes by address or token ID, retrieving current blockchain height, mempool state, and broadcasting signed transactions.
- **Box scanning** — periodic polling or event-driven scanning that identifies Boxes relevant to Paideia contracts (keyed by the Singleton / State NFT Token IDs that uniquely identify each DAO instance or proposal).

### Transaction Assembly Layer
- **Transaction builders** per action type (e.g., `CreateProposal`, `CastVote`, `ExecuteProposal`, `Stake`, `Unstake`, `AddStake`, `CompoundStake`, `TreasuryWithdrawal`). Each builder:
  1. Fetches required input Boxes and optional Data inputs.
  2. Constructs output Boxes with correct value, tokens, and Register layout (`R4`–`R9`).
  3. Attaches Context extension fields where required by the ErgoScript context.
  4. Computes the Minimum box value for each output and enforces the Minimum transaction fee.
  5. Returns an unsigned transaction object ready for signing.

### Signing & Submission Layer
- Supports both **hot wallet signing** (using a loaded mnemonic or secret key) and **EIP-12 connector** delegation (where the assembled transaction is handed off to an external wallet for user signing).
- Signed transactions are broadcast via the Node API.

### Bot Operations Layer
- Long-running Python processes that watch chain state and trigger transactions automatically — for example, compounding staking rewards, executing passed proposals after a timelock, or expiring failed proposals and returning funds.

### Data Flow

```
Chain State (Node/Explorer)
        │
        ▼
Box Scanner ──── identifies relevant UTXOs by State NFT Token ID
        │
        ▼
Transaction Builder ──── assembles inputs, data inputs, outputs, registers
        │
        ▼
Signer (hot wallet or EIP-12 connector delegation)
        │
        ▼
Node Broadcast ──── transaction enters mempool → confirmed block
        │
        ▼
Updated Chain State (new UTXOs consumed/created, state machine advanced)
```

---

## Smart Contracts

Paideia's on-chain logic is written in **ErgoScript** and follows the multi-stage contracts and state machine patterns native to the Ergo eUTXO model. The off-chain code is tightly coupled to the Register layouts and token invariants enforced by these contracts. Key contract categories include:

### DAO Config Contract
A singleton contract identified by a **State NFT**. Holds global DAO configuration (quorum thresholds, vote duration, treasury parameters) encoded in Registers `R4`–`R9`. The off-chain layer reads this Box as a **Data input** in most governance transactions so its contents are available to the ErgoScript context without consuming it.

### Proposal Contracts
Each governance proposal is a Box guarded by a proposal ErgoScript. The contract enforces:
- Voting windows (checked against `CONTEXT.preHeader.height`).
- Vote tallying stored in Registers.
- Execution conditions: a passed proposal can only be "executed" when quorum and approval thresholds encoded in the DAO Config are met.
- The Invariant that the proposal's identifying Token ID is preserved through state transitions.

The off-chain builder must correctly populate `R4` (vote counts), `R5` (end height), `R6` (proposal options), etc., and include the DAO Config Box as a Data input so the ErgoScript context can read configuration without spending it.

### Staking Contracts
Staking uses a **multi-stage contract** pattern:
- A global **Stake State Box** (singleton, identified by State NFT) tracks aggregate staked amounts in Registers.
- Individual **Stake Key Boxes** represent a user's stake position; they carry a **Native token** (stake key NFT) as proof of ownership.
- The ErgoScript enforces that staking/unstaking/compounding transitions preserve the total supply invariant across the Stake State Box's registers.

The off-chain staking bot periodically constructs compounding transactions that update the Stake State Box and distribute accumulated rewards, consuming and re-creating Stake Key Boxes while satisfying all ErgoScript guards.

### Treasury Contract
A guarded treasury Box that can only be spent when a valid executed proposal Box is present as an input, enforcing on-chain that all treasury withdrawals are governance-approved. The off-chain builder assembles the combined transaction including both the proposal and treasury inputs.

### ErgoTree & Constant Segregation
Contract addresses are derived from **ErgoTree** serializations. The off-chain layer uses **constant segregation** where appropriate — substituting DAO-specific parameters (Token IDs, public keys) into template ErgoTrees at deployment time rather than hardcoding them, enabling the same contract logic to serve multiple DAO instances.

---

## Integration Guide

### Prerequisites
- Python 3.8+
- Access to an Ergo Node (local or remote) with the Node REST API enabled, or access to the Ergo Explorer API.
- Relevant Token IDs for the target DAO instance (State NFT, Stake State NFT, Governance Token ID, etc.).

### Installation
```bash
git clone https://github.com/paideiadao/paideia-offchain.git
cd paideia-offchain
pip install -r requirements.txt
```

### Configuration
Provide node endpoint, API key, network type, and DAO-specific Token IDs via environment variables or a config file:
```python
config = {
    "node_url": "http://localhost:9053",
    "api_key": "YOUR_API_KEY",
    "network_type": "mainnet",   # or "testnet"
    "dao_key_nft": "TOKEN_ID_OF_DAO_CONFIG_NFT",
    "governance_token_id": "TOKEN_ID_OF_GOV_TOKEN",
    "stake_state_nft": "TOKEN_ID_OF_STAKE_STATE_NFT",
}
```

### Assembling a Transaction (Example Pattern)
```python
from paideia_offchain.transactions import CreateProposalTx

# Fetch current DAO Config Box (will be used as Data input)
dao_config_box = node_client.get_box_by_token(config["dao_key_nft"])

# Build unsigned transaction
unsigned_tx = CreateProposalTx(
    dao_config_box=dao_config_box,
    proposer_address="9f...",
    proposal_name="Increase Treasury Allocation",
    vote_options=["Yes", "No", "Abstain"],
    end_height=current_height + 720,   # ~1 day at 2-min blocks
    input_