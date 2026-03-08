---
title: '[SOLVED] Ergo Node Wallet Balance Not the Same as Explorer'
description: 'ErgoForum discussion: [SOLVED] Ergo Node Wallet Balance Not the Same
  as Explorer'
tags:
- addresses
- eip
- ergo-explorer
- ergoforum
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/solved-ergo-node-wallet-balance-not-the-same-as-explorer/4108
created: '2022-12-21'
last_activity: '2022-12-21'
posts_count: 1
views: 282
likes: 0
glossary_hits:
- Addresses
- EIP
- Ergo Explorer
- Full node
---

# [SOLVED] Ergo Node Wallet Balance Not the Same as Explorer

> **Forum thread:** [https://ergoforum.org/t/solved-ergo-node-wallet-balance-not-the-same-as-explorer/4108](https://ergoforum.org/t/solved-ergo-node-wallet-balance-not-the-same-as-explorer/4108)
> **Category:** Support | **Created:** 2022-12-21 | **Posts:** 1 | **Views:** 282

**Related concepts:** Addresses, EIP, Ergo Explorer, Full node

---

### Post #1 — @matty_19 (2022-12-21)

Having issues with my node wallet I think. I have a local node and a stratum server. Set up to mine to it. Looks like I hit a block showing a mining reward but my mobile wallet that should be the same address shows 0 and so does explorer. If I try to transfer funds I get the following error.  
![image](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/d/d771dee2b6928c31971b75a2c9b9abbd2229c276.png)

Not sure whats going on. I tried a wallet rescan. Funds showed up again but still not on anything else.

Update  
Had to fix .conf file. Added check eip argument to node config. Rescan wallet from before the block then send a transfer to myself. Was unable to send the full amount but as soon as I sent a chunk it all populated.
