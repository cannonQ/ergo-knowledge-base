---
title: How to recover a Yoroi wallet without Yoroi
description: 'ErgoForum discussion: How to recover a Yoroi wallet without Yoroi'
tags:
- addresses
- ergoforum
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/how-to-recover-a-yoroi-wallet-without-yoroi/2840
created: '2021-10-21'
last_activity: '2021-11-15'
posts_count: 4
views: 481
likes: 2
glossary_hits:
- Addresses
---

# How to recover a Yoroi wallet without Yoroi

> **Forum thread:** [https://ergoforum.org/t/how-to-recover-a-yoroi-wallet-without-yoroi/2840](https://ergoforum.org/t/how-to-recover-a-yoroi-wallet-without-yoroi/2840)
> **Category:** Support | **Created:** 2021-10-21 | **Posts:** 4 | **Views:** 481

**Related concepts:** Addresses

---

### Post #1 — @d1g174l (2021-10-21)

I made the mistake of creating an ERGO wallet using Yoroi browser extension.

After a month or two of use, it crashed and wouldn’t load any more. I had saved my mnemonic seed, so I tried to recover it using Yoroi browser extension, but no matter what OS or browser I try to do this with, it goes to a white screen and crashes.

I tried using Yoroi iOS application to recover my wallet, but it creates a new empty wallet. So even Yoroi it seems can’t open a wallet created with Yoroi.

Is there a command line tool that I can use to extract my private key using the method that Yoroi used to create it in their browser extension version?

---

### Post #2 — @glasgowm (2021-10-22)

ERG is not supported on Yoroi iOS.

There’s an issue with miner dust on Yoroi right now, the dev is working hard trying to fix. He would appreciate error logs.

![](https://telegram.org/favicon.ico?3)
[Telegram](https://t.me/ergosupport)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/5/54af5ef397b8138b19b7a834c427dde69a5193f4.jpeg)

### [Ergo Support](https://t.me/ergosupport)

This group is related to technical question regarding Development, Mining and Wallets only! Please refrain from any other questions. #ERGOPlatform

---

### Post #3 — @Ergosmergo (2021-10-24)

![](https://avatars.discourse-cdn.com/v4/letter/g/9dc877/48.png) glasgowm:

> miner dust

Thanks for the information can you explain a little bit more what miner dust is? dust is the small amount of ERGO that remains in a particular wallet or address because the monetary value is so tiny that it is below the amount of the fee required?

---

### Post #4 — @glasgowm (2021-11-15)

Dust refers to any UTXOs of vanishingly low value, or for UTXOs that are uneconomic to create or spend at a given fee rate. For Ergo this usually manifests as miners gaining lots of UTXOs and clogging up the wallet. Using ‘Send All Assets’ tidies this up.
