---
title: Mining Ergo for Fun and Profit
description: 'ErgoForum discussion: Mining Ergo for Fun and Profit'
tags:
- autolykos
- emission-schedule
- ergoforum
- ergoscript
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/mining-ergo-for-fun-and-profit/154
created: '2019-12-22'
last_activity: '2021-06-01'
posts_count: 5
views: 20621
likes: 2
glossary_hits:
- Autolykos
- Emission schedule
- ErgoScript
- Full node
---

# Mining Ergo for Fun and Profit

> **Forum thread:** [https://ergoforum.org/t/mining-ergo-for-fun-and-profit/154](https://ergoforum.org/t/mining-ergo-for-fun-and-profit/154)
> **Category:** Support | **Created:** 2019-12-22 | **Posts:** 5 | **Views:** 20621

**Related concepts:** Autolykos, Emission schedule, ErgoScript, Full node

---

### Post #1 — @Martin-mx (2019-12-22)

# Ergo GPU Mining

This article will help you start mining Ergo using a GPU.

Ergo mining is based on [Autolykos](https://docs.ergoplatform.com/ErgoPow.pdf), a Proof-of-Work algorithm designed to be ASIC and pool resistant. Miners have to perform memory-hard computations~(at least 4 GB memory is needed, but the current most efficient implementation utilizes between 8 GB of vRAM) that makes Ergo friendly for GPU mining. In addition, Autolykos requires access to **private** keys, thereby preventing mining pool formation. As soon as a correct solution is found, the miner broadcasts the block along with the solution and is able to collect the block reward after a delay of 720 blocks using the secret he used during mining. The rest of the network verifies the solution using the miner’s **public** key and this verification can be done very efficiently, requiring less than a kilobyte of memory.

## Prerequisites

In order to mine, you need the following setup:

1. A full node with wallet initialized and fully synced.
2. A computer with a GPU that is recognized by your OS.
3. Ergo mining software for your operating system. Ergo supports both AMD and NVidia GPUs.

Ergo mining requires a configured and synchronized Ergo node and at least one GPU for mining. You may use multiple GPUs if you wish (to multiply your hashing power) but you only need one Ergo node.

**Note that Ergo no longer works in Java 8 due to its lack of [strong cryptography](http://mail.openjdk.java.net/pipermail/security-dev/2016-October/014942.html). You must use Java >= 9**

The links for setting up the mining software are:

* [Nvidia Miner](https://github.com/ergoplatform/cuda-miner)
* [AMD Miner](https://ergoplatform.org/en/blog/2019_08_07_amd/)

**!!!WARNING!!! Since Autolykos utilizes private keys, you should never use untrusted mining software. Check that the software is open-source and validated by the community**

## Sync node and Initialize Wallet

Follow the steps of setting up a node as described in [the tutorial](https://github.com/ergoplatform/ergo/wiki/Set-up-a-full-node).

Edit the config file of the node and add the following line.

`ergo.node.mining = true`

Ensure that the wallet is initialized and you are in possession of the correct mnemonic sentence.

Finally, ensure that the node is synced as described [here](https://github.com/ergoplatform/ergo/wiki/Set-up-a-full-node#check-if-the-node-is-synced).

## Configure and run the miner

On the computer where the miner will be running, create a file called `config.json` with the following content

```ergoscript
{
    "seed": "Attention!!! Replace this with your mnemonic sentence and keep it secret or you will get robbed", 
    "node": "http://192.168.1.100:9053",
    "keepPrehash": false
}
```

where:

* **seed** is the mnemonic sentence from your node’s wallet obtained in the previous step.
* **node** is the URL of your node.
* **keepPrehash** is an optimization parameter. If set to `true` , the miner will consume at most 8GB of memory. If set to `false` the miner will consume at most 4GB of memory, but its performance will be for about 25% lower.

Run your miner using the command `./auto.out config.json` (for Linux) or `miner.exe config.json` (for Windows) and enjoy receiving block rewards!

Once you have received any mining rewards, you can view the balance as described [here](https://github.com/ergoplatform/ergo/wiki/Set-up-a-full-node#check-wallet-balance) and then withdraw the funds as described [here](https://github.com/ergoplatform/ergo/wiki/Set-up-a-full-node#sending-funds).

![](https://github.githubassets.com/favicons/favicon.svg)
[GitHub](https://github.com/ergoplatform/ergo/wiki/Mining-Ergo-for-Fun-and-Profit)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/46a3c2d015b23d114fafd4756ea7c173fad09cb2.png)

### [ergoplatform/ergo](https://github.com/ergoplatform/ergo/wiki/Mining-Ergo-for-Fun-and-Profit)

Ergo protocol description & reference client implementation - ergoplatform/ergo

---

### Post #2 — @b8engl (2021-05-29)

[Martin-mx](https://www.ergoforum.org/u/Martin-mx),

Thanks for the tutorial!  
But i don’t know if this is working or not, could you help?

The error:

```ergoscript
2021-05-29 23:54:55,568 INFO [main thread] Unrecognized config option, currently valid options are "node"
2021-05-29 23:54:55,568 INFO [main thread] Unrecognized config option, currently valid options are "node"
2021-05-29 23:54:55,568 INFO [main thread] Unrecognized config option, currently valid options are "node"
```

* My node is sync
* My wallet has password

config.json settings:

```ergoscript
{ "mnemonic" : "my_mnmonic", "mnemonicPass": "my_password", "node" : "https://127.0.0.1:9053", "keepPrehash" : true }
```

Thanks in advance!

---

### Post #3 — @b8engl (2021-05-29)

Although I’m getting the double hashrate when using `"keep rehash" : true`, so I’m really lost here.

---

### Post #4 — @kushti (2021-05-31)

the tutorial is outdated, no mnemonic is needed in config anymore

---

### Post #5 — @b8engl (2021-06-01)

I thought that too… but the information is limited.

Is this the correct way for solo?

* Initiate node, and unlock wallet
* config.json `{ "node" : "http://127.0.0.1:9053", }`
