---
title: Node wallet, after new jar I initialized it instead of restoring it, and now
  address is different and empty
description: 'ErgoForum discussion: Node wallet, after new jar I initialized it instead
  of restoring it, and now address is different and empty'
tags:
- addresses
- ergo-explorer
- ergoforum
- full-node
- satergo
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/node-wallet-after-new-jar-i-initialized-it-instead-of-restoring-it-and-now-address-is-different-and-empty/4496
created: '2023-09-24'
last_activity: '2023-11-26'
posts_count: 6
views: 376
likes: 1
glossary_hits:
- Addresses
- Ergo Explorer
- Full node
- Satergo
---

# Node wallet, after new jar I initialized it instead of restoring it, and now address is different and empty

> **Forum thread:** [https://ergoforum.org/t/node-wallet-after-new-jar-i-initialized-it-instead-of-restoring-it-and-now-address-is-different-and-empty/4496](https://ergoforum.org/t/node-wallet-after-new-jar-i-initialized-it-instead-of-restoring-it-and-now-address-is-different-and-empty/4496)
> **Category:** Support | **Created:** 2023-09-24 | **Posts:** 6 | **Views:** 376

**Related concepts:** Addresses, Ergo Explorer, Full node, Satergo

---

### Post #1 — @dino (2023-09-24)

Hi Support,

I downloaded “ergo-5.0.14.jar”. After setting the API key I Initialized the wallet ( instead of restoring it, with the wallet password only) and that generated a new address which is empty.

I stopped the node and launched it again on a different PC. This time I restored the wallet (using the mnemonic, wallet password **and** mnemonic password), yet the new address still shows up!

Ergo Explorer shows the new address is empty. While the old address still has a correct balance.

Is this a bug? Is there any other way to recover the funds from a Node wallet (by sending them to a mobile wallet for example), than running the node and succeeding in restoring the correct wallet address?

---

### Post #2 — @glasgowm (2023-09-25)

You can use your mnemonic in any wallet. If you’ve set an additional mnemonic password - you can try it in Satergo I believe.

You can also rescan in swagger, and try deriving additional addresses.

---

### Post #3 — @dino (2023-09-25)

Thanks Glasgowm,

The mnemonic restores to the new address in the official Ergo wallet, and is empty.

I may have stored the wrong mnemonic then… ![:roll_eyes:](https://emoji.discourse-cdn.com/twitter/roll_eyes.png?v=12 ":roll_eyes:")

---

### Post #4 — @glasgowm (2023-09-26)

Did you set a mnemonic password when creating the wallet?

In the Ergo Wallet app, click into the wallet, and try deriving additional addresses to see if your funds appear in them.

---

### Post #5 — @dino (2023-11-26)

Hi Glasgown,

I did set a mnemonic password, which I wasn’t asked for in the Ergo wallet app.  
I derived 100 addresses, but they’re all empty

Thanks

---

### Post #6 — @RealisticClock (2023-11-26)

Have you tried satergo wallet?
