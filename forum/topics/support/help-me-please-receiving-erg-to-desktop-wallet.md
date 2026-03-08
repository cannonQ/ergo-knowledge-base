---
title: HELP ME PLEASE receiving erg to desktop wallet
description: 'ErgoForum discussion: HELP ME PLEASE receiving erg to desktop wallet'
tags:
- addresses
- difficulty-adjustment
- ergoforum
- full-node
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/help-me-please-receiving-erg-to-desktop-wallet/498
created: '2020-12-05'
last_activity: '2021-09-30'
posts_count: 5
views: 1497
likes: 0
glossary_hits:
- Addresses
- Difficulty adjustment
- Full node
- Transaction
---

# HELP ME PLEASE receiving erg to desktop wallet

> **Forum thread:** [https://ergoforum.org/t/help-me-please-receiving-erg-to-desktop-wallet/498](https://ergoforum.org/t/help-me-please-receiving-erg-to-desktop-wallet/498)
> **Category:** Support | **Created:** 2020-12-05 | **Posts:** 5 | **Views:** 1497

**Related concepts:** Addresses, Difficulty adjustment, Full node, Transaction

---

### Post #1 — @Tanner (2020-12-05)

I installed the ergo node wallet, after some minor difficulty I got it to go, the I clicked “my addresses” and I sent my Ergo over to the address listed. Hour later it said transfer was complete on the Exchanges side, when open my wallet and set my api key , it shows a balance of 0 erg, when I click “my addresses” and then select the address it does show that the transaction went though. :"( help me

---

### Post #2 — @kushti (2020-12-06)

Welcome aboard Tanner!

Is your node synced, to start with ?

---

### Post #3 — @sidminer (2021-09-29)

I have recently joined. and am having similar issue.  
I had a payout when my wallet was disconnected  
what happens when connection is lost while transaction is being processing?

---

### Post #4 — @Natewana (2021-09-29)

Hi, Sidminer! This seems to be a bit of a hitch for many folks. I just related my experience as well as the fix that worked for me under the post [Lose Ergo while sending test from local wallet to Kucoin - #8 by Natewana](https://www.ergoforum.org/t/lose-ergo-while-sending-test-from-local-wallet-to-kucoin/2082/8). Here is a copy of the meat of it:  
…  
**Problem:** After a hard node crash, my primary wallet zeroed out, although I could still see the balance reflected in my change wallet. These assets could not be accessed.

**Attempted solutions:** I went so far as to delete everything Ergo related and resync the node and wallet from scratch by reinitializing the wallet in question from the mnemonic, to no avail.

**Eventual solution:** As I became increasingly frustrated, I went through almost every function of Swagger. In doing so, I realized that my change address was not registering unless my wallet was unlocked. I unlocked my wallet and used the wallet rescan function. I could actually watch on my main panel as the appropriate amount of ERG fluctuated and then suddenly dropped to zero. I did this twice. I then realized that when the rescan initialized, it was locking my wallet prior to scanning. Realizing this - in the context of what I had discovered earlier about the state of the change wallet when the primary was locked/unlocked - I started the scan and then unlocked the wallet from the main panel. This resulted in the appropriate amount of ERG being available in my primary address while still being reflected in the change wallet.

---

### Post #5 — @sidminer (2021-09-30)

I have given up. spend over a day to do as instructed but wasnt successful.
