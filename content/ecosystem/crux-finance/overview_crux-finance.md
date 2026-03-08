---
title: cruxfinance/ergo-node-zmqpub — Overview
description: CruxFinance ZMQ publisher — picks up ergo node events and publishes via ZeroMQ
tags: [cruxfinance, ergo-node-zmqpub, analytics, scala]
category: ecosystem
difficulty: intermediate
sdk: [none]
updated: 2026-03-04
source: auto-generated
source_repo: "https://github.com/cruxfinance/ergo-node-zmqpub"
project: cruxfinance-ergo-node-zmqpub
group: analytics
priority: low
languages: [scala]
contract_count: 0
pattern_match_count: 2
---
# ergo-node-zmqpub — Developer Overview

---

## Overview

**ergo-node-zmqpub** is a lightweight event-bridge service developed by CruxFinance that connects directly to a running Ergo full node and re-publishes node-level events over a ZeroMQ (ZMQ) publish/subscribe socket. Its primary role is to act as a real-time event fan-out layer, allowing multiple downstream analytics consumers, off-chain bots, and indexing services to subscribe to Ergo blockchain events without each independently polling or connecting to the node's REST API. This decouples event production from event consumption in a clean, low-latency pub/sub model.

Within the Ergo ecosystem, where eUTXO-based state transitions are expressed through Box creation and spending, the ability to react to on-chain events in near real-time is critical for off-chain bots, dApp backends, and analytics pipelines. Rather than relying solely on periodic REST polling of endpoints like `/blocks/lastHeaders` or `/transactions/unconfirmed`, this service establishes a persistent peer-level connection to the Ergo node using the **Ergonnection** library, enabling it to receive raw node events (such as new blocks and transactions) as they propagate through the P2P layer.

The project is intentionally narrow in scope — it does not index, store, or interpret blockchain data. Instead it acts as a transparent, stateless relay: any event received from the Ergo node is immediately serialized and forwarded to all connected ZMQ subscribers. This makes it a foundational infrastructure component in the CruxFinance analytics group, sitting at the boundary between the Ergo P2P network and internal data processing pipelines.

---

## Architecture

The system is composed of two primary logical layers connected by an internal event pipeline:

```
[ Ergo Full Node ]
       │  P2P (port 9030)
       ▼
[ Ergonnection Listener ]   ← JDK 17+ P2P client (Scala)
       │  Internal event stream
       ▼
[ EventPublish.scala ]      ← Event serialization & dispatch
       │  ZMQ PUB socket
       ▼
[ ZeroMQ Subscribers ]      ← Analytics consumers, off-chain bots, indexers
```

**Key Components:**

- **Ergonnection Library** (`nodePeersPort: 9030`): A Scala/JVM library that implements Ergo's P2P handshake and message protocol, allowing the service to join the node's peer network and receive raw messages such as `InvData`, `ModifiersData`, and transaction/block announcements. This is distinct from the REST API layer and provides lower-latency event delivery.

- **`EventPublish.scala`**: The central event-handling component. It receives decoded node events from the Ergonnection listener and publishes them onto the ZMQ PUB socket. Each published message is framed with a topic prefix (enabling subscribers to filter by event type) and a serialized payload. This is where the translation from Ergo P2P wire format to ZMQ message envelope occurs.

- **`Config.scala`**: Typed configuration model that resolves runtime parameters — `nodeURL`, `nodePeersPort`, `zmqIP`, and `zmqPort` — typically from a configuration file or environment. The separation of configuration into a dedicated type reflects standard Scala application hygiene and makes deployment-environment overrides straightforward.

- **ZMQ PUB Socket** (default `0.0.0.0:9060`): A ZeroMQ publisher socket that any number of downstream subscribers can connect to. The pub/sub pattern means the publisher is entirely unaware of subscribers; adding or removing consumers has zero impact on the publisher's operation.

**Data Flow:**

1. The service initiates a P2P connection to the configured Ergo node (`nodeURL`, `nodePeersPort`).
2. The Ergonnection library handles the Ergo handshake and begins receiving node messages.
3. `EventPublish` intercepts each message, wraps it in a ZMQ envelope, and calls `socket.send(topic, message)`.
4. Any process subscribed to `zmqIP:zmqPort` on the relevant topic receives the event in real time.

---

## Smart Contracts

This project contains **no ErgoScript contracts, ErgoTrees, or on-chain components**. It is a pure infrastructure/middleware service operating entirely off-chain. It does not construct, sign, or submit Transactions; it does not interact with Boxes, Registers, or Sigma protocols directly. There are no Multi-stage contracts, Singleton/State NFTs, or AVL tree operations involved.

If downstream consumers of the ZMQ feed use this service to trigger contract interactions (e.g., an off-chain bot watching for specific Box creation events), those contract concerns are entirely the responsibility of the consuming application.

---

## Integration Guide

### Subscribing to the ZMQ Feed

Any ZeroMQ-compatible client (Python, JavaScript, Go, Rust, Java, etc.) can subscribe to the feed. The socket type is **PUB/SUB**, so consumers must create a `SUB` socket and connect to the publisher's endpoint.

**Python example (pyzmq):**
```python
import zmq

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:9060")
socket.setsockopt_string(zmq.SUBSCRIBE, "")  # subscribe to all topics

while True:
    topic, payload = socket.recv_multipart()
    print(f"Topic: {topic}, Payload: {payload.hex()}")
```

**Scala/JVM example (jeromq):**
```scala
val ctx = ZContext()
val sub = ctx.createSocket(SocketType.SUB)
sub.connect("tcp://localhost:9060")
sub.subscribe(ZMQ.SUBSCRIPTION_ALL)

while (true) {
  val topic = sub.recvStr()
  val payload = sub.recv()
  println(s"Event: $topic -> ${payload.length} bytes")
}
```

### Configuration

Edit the application configuration file (typically `application.conf` for Scala/Typesafe Config projects) or supply environment overrides:

| Key | Description | Default |
|---|---|---|
| `nodeURL` | REST URL of the Ergo full node | `http://213.239.193.208:9053` |
| `nodePeersPort` | P2P port of the Ergo node | `9030` |
| `zmqIP` | Bind address for the ZMQ socket | `0.0.0.0` |
| `zmqPort` | Bind port for the ZMQ socket | `9060` |

Point `nodeURL` and `nodePeersPort` at any accessible Ergo full node (local or remote). For production deployments, a local node is strongly recommended to minimize latency and avoid dependency on third-party infrastructure.

### Deployment

```bash
# Linux
./run.sh

# Windows
run.bat

# Docker (recommended for production)
docker compose up -d
```

> **Requirement:** JDK 17 or higher is mandatory due to the Ergonnection library's use of modern JVM features.

### Payload Interpretation

Payloads received over ZMQ correspond to Ergo P2P protocol messages. Consumers should use an Ergo SDK (e.g., **Appkit**, **sigma-rust** bindings, or **ergo-lib**) to deserialize Block headers, Block sections, and Transaction objects from their binary wire format. Key fields of interest for most consumers include:
- **Block header** — height, `parentId`, difficulty, Autolykos proof
- **Transaction** — input Box IDs being spent, output Boxes with Registers and Native tokens, Token IDs

---

## Key Patterns

### Off-Chain Event Bridge
The dominant pattern here is an **off-chain infrastructure bridge** — the service has no on-chain footprint and exists solely to make on-chain events accessible to off-chain systems more efficiently. This is a prerequisite pattern for building responsive **off-chain bots** that must react to eUTXO state changes (e.g., detecting when a specific Box is spent, or when a new Box matching a particular ErgoTree appears in a block).

### P2P-Level Observation (vs. REST Polling)
Rather than the common pattern of polling the node's REST API (`/blocks/lastHeaders`, `/transactions/un