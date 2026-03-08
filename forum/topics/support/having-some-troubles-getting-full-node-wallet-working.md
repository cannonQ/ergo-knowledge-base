---
title: Having some troubles getting full node wallet working
description: 'ErgoForum discussion: Having some troubles getting full node wallet
  working'
tags:
- addresses
- ergoforum
- full-node
- native-tokens
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/having-some-troubles-getting-full-node-wallet-working/2895
created: '2021-11-01'
last_activity: '2021-11-23'
posts_count: 2
views: 476
likes: 1
glossary_hits:
- Addresses
- Full node
- Native tokens
---

# Having some troubles getting full node wallet working

> **Forum thread:** [https://ergoforum.org/t/having-some-troubles-getting-full-node-wallet-working/2895](https://ergoforum.org/t/having-some-troubles-getting-full-node-wallet-working/2895)
> **Category:** Support | **Created:** 2021-11-01 | **Posts:** 2 | **Views:** 476

**Related concepts:** Addresses, Full node, Native tokens

---

### Post #1 — @Ergosmergo (2021-11-01)

Having some troubles getting full node wallet working. Since there have been some issues with Yoroi wallet lately I decided to set up a full node. I am using Ubuntu 20.04 focal Kernel: x86\_64 Linux 5.11.0-38-generic with Java Ergo full node software.

I followed the directions on Github to set up the java version of the Ergo full node and everything went smooth the node started syncing and give me a wallet address.

I started to send some funds to that wallet address without letting the full node completely sync. I started to this address right after it was issued by the full node.

After a while I noticed the node was not syncing and the folder for Ergo was remaining the same size.

I then downloaded Ergo mobile wallet and tried to recover the seed. The problem is the seed is recovering a completely different address then what specified in full node wallet.

I then deleted a lot of the files in .Ergo - the wallet folder I backed the wallet folder up.

I leave the node syncing but then my electric went out and I had to start the node again.

[![Screenshot from 2021-11-01 00-43-09](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/d/dd9599b01b6747076418be522a4c49be4f54cd86_2_690x388.png)

Screenshot from 2021-11-01 00-43-091920×1080 94.6 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/d/dd9599b01b6747076418be522a4c49be4f54cd86.png "Screenshot from 2021-11-01 00-43-09")

[![Screenshot from 2021-11-01 00-43-15](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/b/b8288d7a66e648e752df0d682116ab4fded92f94_2_690x388.png)

Screenshot from 2021-11-01 00-43-151920×1080 94.4 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/b/b8288d7a66e648e752df0d682116ab4fded92f94.png "Screenshot from 2021-11-01 00-43-15")

I tried to also recover the wallet in Yoroi and the same wallet is recovered as the mobile wallet but no sign of the original wallet created by the full node wallet.

[![Screenshot from 2021-11-01 00-43-38](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/8/8403c3cf929fb742434d44c0ff2d987dd0f56a30_2_690x388.png)

Screenshot from 2021-11-01 00-43-381920×1080 118 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/8/8403c3cf929fb742434d44c0ff2d987dd0f56a30.png "Screenshot from 2021-11-01 00-43-38")

Its not many tokens I have in this wallet from mining around 2 ERG but I’d like to recover them if possible.

How big should the Ergo folder be after full node has finished syncing? would stopping the ergo java software mid way through and starting it back up effect the syncing process? the folder called history gets to around 400MB before it stops growing.

UPDATE: Problem solved ERG is showing node synced. Peers were being dropped restarted PC and re-synced node. Will try and recover the wallet seed on another machine and see if the wallet shows as with the seed a different address shows in mobile wallet and Yoroi.

---

### Post #2 — @Ergosmergo (2021-11-23)

Problem was solved by recovering wallet in full node by backing up and restoring the wallet folder. I was restoring from seed prior in full-node and was getting a completely different wallet address I think this might just be the way the wallet was linked and was likely caused by myself rushing things to get the full node sync any how issue is solved if anyone else has similar issues try restoring the wallet folder and syncing full node the coins and wallet should then show up.
