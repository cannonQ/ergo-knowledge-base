---
title: Mnemonic sentence bugs
description: 'ErgoForum discussion: Mnemonic sentence bugs'
tags:
- addresses
- ergoforum
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/mnemonic-sentence-bugs/762
created: '2021-03-03'
last_activity: '2022-05-03'
posts_count: 10
views: 735
likes: 2
glossary_hits:
- Addresses
- Full node
---

# Mnemonic sentence bugs

> **Forum thread:** [https://ergoforum.org/t/mnemonic-sentence-bugs/762](https://ergoforum.org/t/mnemonic-sentence-bugs/762)
> **Category:** Support | **Created:** 2021-03-03 | **Posts:** 10 | **Views:** 735

**Related concepts:** Addresses, Full node

---

### Post #1 — @Ergomaniac (2021-03-03)

1. Upon creating a new wallet, the window that shows the mnemonic sentence pops up and then disappears very quickly before I have time to copy it.
2. Also, when I try restore a wallet, I tested it with the correct wallet password, but a different mnemonic sentence and it said “Success”, however I got a wallet with a different address, and not the same one

---

### Post #2 — @Maks (2021-03-07)

I have similar problem, after upgrading desktop wallet to new version and entering mnemonic phrase my balance is 0 and I have new address. Any solution?

---

### Post #3 — @Juxtor88 (2021-03-07)

Hello I have the same problem I create my wallet on the 3.2.7 node and yesterday I update the node to 4.0.7 and restore my wallet with the 15 word and he give me a new public key so my balance come to 0

And in addition I try to restore in 3.2.7 node but the sync is block so I can’t do a transfer on my new Waller key.

---

### Post #4 — @miran (2021-08-19)

Hi, did you figure it out?

---

### Post #5 — @scalahub (2021-08-20)

I think the later versions have solved the issue. If it still persists please mention the version

---

### Post #6 — @dfvdf (2022-04-29)

me too  
！！！！！！！！！！！！！！！  
I lost my wallet

---

### Post #7 — @Ergosmergo (2022-04-30)

Guys don’t panic it will only cause further frustrations rest assured your funds will likely be safe on-chain and this is most probably just a small hiccup in the version of the node you are using. this reminds me of a similar issue I had. in the past do you have the wallet data backed up by any chance? You should be able to transfer the wallet data to the new node software and restore the wallet that way. [@glasgowm](/u/glasgowm) any similar reports on any of the social media platforms for Ergo that you have come across recently? [@kushti](/u/kushti) Any ideas on what may be causing this issue for these users?

---

### Post #9 — @kushti (2022-05-03)

![](https://avatars.discourse-cdn.com/v4/letter/e/a88e57/48.png) Ergomaniac:

> * Upon creating a new wallet, the window that shows the mnemonic sentence pops up and then disappears very quickly before I have time to copy it.
> * Also, when I try restore a wallet, I tested it with the correct wallet password, but a different mnemonic sentence and it said “Success”, however I got a wallet with a different address, and not the same one

Please provide details, such as node version, and browser (where the window disappears quickly).

Restore is restoring wallet from a mnemonic, wallet password is used to encrypt a file with a secret key derived from mnemonic. So if you are using different sentence, address would be different indeed.

---

### Post #10 — @kushti (2022-05-03)

![](https://avatars.discourse-cdn.com/v4/letter/m/96bed5/48.png) Maks:

> I have similar problem, after upgrading desktop wallet to new version and entering mnemonic phrase my balance is 0 and I have new address. Any solution?

Please try to rescan, by removing wallet/registry subfolder in your Ergo data folder, or by calling wallet/rescan method in Swagger API.

---

### Post #11 — @kushti (2022-05-03)

![](https://avatars.discourse-cdn.com/v4/letter/j/4af34b/48.png) Juxtor88:

> Hello I have the same problem I create my wallet on the 3.2.7 node and yesterday I update the node to 4.0.7 and restore my wallet with the 15 word and he give me a new public key so my balance come to 0
>
> And in addition I try to restore in 3.2.7 node but the sync is block so I can’t do a transfer on my new Waller key.

Please set ergo.wallet.usePreEip3Derivation = true as described in 3.3.4 release notes: [Release Ergo Protocol Reference Client 3.3.4 · ergoplatform/ergo · GitHub](https://github.com/ergoplatform/ergo/releases/tag/v3.3.4)
