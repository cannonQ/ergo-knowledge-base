---
title: Help to recover ERG (old wallet key phrase format)
description: 'ErgoForum discussion: Help to recover ERG (old wallet key phrase format)'
tags:
- addresses
- ergoforum
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/help-to-recover-erg-old-wallet-key-phrase-format/544
created: '2021-01-09'
last_activity: '2022-05-29'
posts_count: 5
views: 2882
likes: 0
glossary_hits:
- Addresses
- Full node
---

# Help to recover ERG (old wallet key phrase format)

> **Forum thread:** [https://ergoforum.org/t/help-to-recover-erg-old-wallet-key-phrase-format/544](https://ergoforum.org/t/help-to-recover-erg-old-wallet-key-phrase-format/544)
> **Category:** Support | **Created:** 2021-01-09 | **Posts:** 5 | **Views:** 2882

**Related concepts:** Addresses, Full node

---

### Post #1 — @Nick_OLEUM_Stakepool (2021-01-09)

I have the keyphrase 15 words from an ERG wallet I used in August 2020.  
It was a full node wallet, the only option I had back then apart from 3rd party stuff  
Is there a wallet I can restore this into?  
I was pointed to the mixer software, but its not abundantly clear what to do. I just want my ERG in Yoroi!

Please help if you can but remember help is only help when the daft bugger (me) trying to understand it can actually understand it.  
The easiest option would be if Yoroi supported this format. I can’t see why that would be difficult? The current 15 word key there is not the same. I waited a few months to ask again as I was told it was a known issue back when Yoroi launched.  
Thanks for any help.

---

### Post #2 — @deadit (2021-01-12)

Hello, Nick! You need to install 3.3.3 version of ergo-node - [Release Ergo Platform Reference Client 3.3.3 · ergoplatform/ergo · GitHub](https://github.com/ergoplatform/ergo/releases/tag/v3.3.3) at v3.3.4 ergo switch standart mnemonic phrase.  
If you have any question you can ask it to me at telegram @eilemust or in discord [@deadit](/u/deadit), I will help you!

---

### Post #3 — @NickOLEUM (2021-01-12)

Awesome (but not so awesome) I don’t want to run a full node just to restore my ERG but if that’s the only way then I guess I have to.  
Ill get back to you , thanks

---

### Post #4 — @Arohbe (2021-06-28)

If you never solved this. Easy way is to delete or move the more recent JSON file found in your .ergo/wallet/keystore folder. Then delete the history folder and restart your node. Re-run it through Swagger and unlock in the node platform and your wallet should be restored to original address.

---

### Post #5 — @test (2022-05-29)

Tell me how to correctly specify the commands in ergo.conf to restore the wallet using a phrase of 15 words
