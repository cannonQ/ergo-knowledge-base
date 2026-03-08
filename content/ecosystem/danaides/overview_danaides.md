---
title: ergo-pad/danaides — Overview
description: Danaides blockchain indexer — high-performance UTXO indexing, dApp backend patterns
tags: [ergo-pad, danaides, analytics, python]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-03
source: auto-generated
source_repo: "https://github.com/ergo-pad/danaides"
project: ergo-pad-danaides
group: analytics
priority: high
languages: [python]
contract_count: 0
pattern_match_count: 0
---
# Danaides — Developer Overview

---

## Overview

Danaides is a high-performance blockchain indexer purpose-built for the Ergo eUTXO model, developed by the ergo-pad team. Its core responsibility is maintaining a continuously synchronized, queryable snapshot of all **unspent Boxes** on the Ergo blockchain — the live UTXO set. Rather than storing the full transaction history, Danaides focuses exclusively on the unspent state: tracking which Boxes exist at any given chain tip, what **Native tokens** and **Registers** they carry, and what balances and staking/vesting positions can be derived from them. This design philosophy deliberately trades historical completeness for operational performance, making it well-suited as a production backend for dApps that need fast, current state lookups.

Within the Ergo ecosystem, Danaides fills the role of an indexing layer between a running Ergo full node and application-layer services. Raw block data is consumed from a local ergonode, processed sequentially by height, and persisted into a PostgreSQL database with normalized tables and materialized views for assets, balances, tokens, staking, and vesting. Downstream consumers — including the ergo-pad frontend, API clients, and analytics dashboards — query this database rather than burdening the node directly. This separation is especially important given that eUTXO state lookups (e.g., resolving all Boxes holding a specific **Token ID**, or finding the current state Box of a **Singleton / State NFT**) are expensive when performed ad hoc against a live node.

Danaides is not a generic block explorer. It is explicitly architected as a dApp backend: the schemas, views, and API routes are oriented toward the domain objects relevant to ergo-pad products, including ErgoPad staking contracts, vesting schedules, and token metrics. It demonstrates a practical pattern for how teams building on Ergo can maintain their own indexed, queryable UTXO state without relying on shared third-party infrastructure. The project is open-source and serves as a reference implementation for high-throughput eUTXO indexing in Python.

---

## Architecture

Danaides is composed of several loosely coupled services orchestrated via Docker Compose, each with a distinct responsibility:

### Components

| Component | Technology | Role |
|-----------|-----------|------|
| **Indexer (core)** | Python | Sequentially fetches block data from the ergonode, processes Boxes, and writes to PostgreSQL |
| **API service** | Python (FastAPI/similar) | Exposes indexed data as JSON endpoints; also responsible for bootstrapping database schema and triggering materialized view refreshes |
| **PostgreSQL 14** | Postgres w/ `hstore` extension | Primary data store for Box state, token records, audit logs, and all derived views |
| **Celery worker** (optional) | Celery | Offloads heavy materialized view refreshes from the main indexer thread |
| **Alembic** (optional) | SQLAlchemy + Alembic | Schema migration management; runs as a separate Docker profile |
| **Ergo full node** | Ergo reference client | Source of truth for all Box and transaction data; must be local for async/multithreaded fetch performance |

### Data Flow

```
Ergo Node (local)
      │
      │  REST API (block/box queries, async/multithreaded)
      ▼
 Indexer (Python)
      │
      │  Sequential by block height
      ├──► boxes table         (raw unspent Box records, built height by height)
      ├──► tokens table        (token records, sequential by height)
      └──► utxos table         (derived: boxes minus spent; incrementally maintained)
                │
                ▼
     Materialized Views (concurrent refresh)
      ├── assets               (Native token holdings per address)
      ├── balances             (ERG balances per address)
      ├── vesting              (vesting schedule positions)
      └── staking              (staking positions)
                │
                ▼
          API Service
                │
                ▼
        External Consumers
      (frontend, analytics, bots)
```

### Key Database Tables

- **`boxes`**: The canonical record of all currently unspent Boxes. Built sequentially from genesis (or a chosen start height) to chain tip. Each record captures the Box ID, **ErgoTree**, **Registers** (R4–R9), value in nanoERG, and associated **Native tokens**.
- **`utxos`**: A maintained projection of `boxes` where spent Boxes are removed and new unspent Boxes are added with each processed block. This is the primary table queried for current UTXO state.
- **`tokens`**: Token registration records, indexed sequentially by height. The first issuance transaction for any token (governed by the **Token ID rule** — Token ID equals the Box ID of the input Box that minted it) is captured here.
- **`audit_log`**: Simple operational log with a 3-day TTL for debugging and monitoring.

### Schema Management

SQLAlchemy is used for schema definition, with Alembic managing migrations. The API container is responsible for ensuring all database objects exist before the indexer begins processing — it must complete initialization successfully on startup.

The "drop-n-pop" approach is used for some tables during reindexing: tables are dropped and recreated rather than updated in place, which requires that the database user (`pirene` by default) holds `CREATE` on the relevant schemas. The `hstore` PostgreSQL extension is required for flexible key-value storage within Box records.

---

## Smart Contracts

Danaides is an **indexer and backend service**, not a contract deployment or execution layer. It does not define or deploy ErgoScript contracts directly. However, the indexing schema and materialized views are explicitly designed to track the on-chain state of ergo-pad's deployed contracts:

- **Staking contracts**: The `staking` materialized view derives positions from unspent Boxes whose **ErgoTree** matches the known staking contract template. **Registers** (typically R4–R6) encode stake amounts, timestamps, and participant addresses, which Danaides decodes and surfaces via the API.
- **Vesting contracts**: Similarly, the `vesting` view tracks Boxes locked under vesting contract **ErgoTrees**, reading vesting schedule parameters from **Registers**.
- **Token issuance**: The `tokens` table records the minting of **Native tokens** by identifying Box-creation transactions where the **Token ID rule** applies — specifically, where a token's ID equals the `box_id` of the first input Box of its issuance transaction.

A planned integration with [Paideia contracts](https://github.com/ergo-pad/paideia-contracts) is noted in the roadmap, which would extend indexing to governance and DAO-related **Multi-stage contracts** and **Singleton / State NFT** patterns.

For developers extending Danaides to track new contracts: the pattern is to identify the canonical **ErgoTree** (or its Base16/Base58 encoding) for the contract of interest, filter the `utxos` table by that ErgoTree, and decode relevant **Registers** according to the contract's documented register layout.

---

## Integration Guide

### Prerequisites

- A running local Ergo full node with the REST API accessible (set via `NODE_URL` in `.env`).
- PostgreSQL 14 with the `hstore` extension enabled.
- Docker and Docker Compose.

### Quick Start

```bash
git clone https://github.com/ergo-pad/danaides.git
cd danaides

# Copy and configure environment
cp alt.env .env
# Edit .env: set NODE_URL, DANAIDES_PASSWORD, POSTGRES_PASSWORD

docker compose up
```

The API container initializes the database schema on first boot. The indexer then begins processing blocks sequentially from the configured start height. The first full sync (building `boxes` and `utxos` from scratch) is time-intensive; subsequent runs are incremental.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `NODE_URL` | IP/hostname of the local Ergo full node |
| `DANAIDES_PASSWORD` | Password for the `pirene` database user (must match `sql/init.sql`) |
| `POSTGRES_PASSWORD` | PostgreSQL superuser password |
| `POSTGRES_HOST` | Database host (change if using external Postgres) |

### API Endpoints

The API service exposes indexed