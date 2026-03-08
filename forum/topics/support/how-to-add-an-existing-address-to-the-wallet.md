---
title: How to add an existing address to the wallet?
description: 'ErgoForum discussion: How to add an existing address to the wallet?'
tags:
- addresses
- ergoforum
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/how-to-add-an-existing-address-to-the-wallet/982
created: '2021-04-11'
last_activity: '2021-09-20'
posts_count: 4
views: 1686
likes: 0
glossary_hits:
- Addresses
- Full node
---

# How to add an existing address to the wallet?

> **Forum thread:** [https://ergoforum.org/t/how-to-add-an-existing-address-to-the-wallet/982](https://ergoforum.org/t/how-to-add-an-existing-address-to-the-wallet/982)
> **Category:** Support | **Created:** 2021-04-11 | **Posts:** 4 | **Views:** 1686

**Related concepts:** Addresses, Full node

---

### Post #1 — @slavakonovalov (2021-04-11)

Hi,  
I’ve just re-setup the node, tried to restore the wallet and it seemed to work, but I noticed the address changed however I’ve seen the message ‘wallet successfully restored’.

So the question is how can I recover the former address and to get access to it?  
Is it possible to add it to the current wallet as an additional address?  
Normally, I have all the requisites, i.e. address, pass, mnemonic sentence.

The node version is 4.0.9.

Thanks.

---

### Post #2 — @Arohbe (2021-06-28)

![](https://avatars.discourse-cdn.com/v4/letter/a/b9bd4f/48.png)
[Help to recover ERG (old wallet key phrase format)](https://www.ergoforum.org/t/help-to-recover-erg-old-wallet-key-phrase-format/544/4) [Support](/c/support/8)

> If you never solved this. Easy way is to delete or move the more recent JSON file found in your .ergo/wallet/keystore folder. Then delete the history folder and restart your node. Re-run it through Swagger and unlock in the node platform and your wallet should be restored to original address.

---

### Post #3 — @kushti (2021-08-18)

What was old node version ?

---

### Post #4 — @04Detroitls (2021-09-20)

I have the same issue (fresh node install used correct mnemonic 0 balance), but I backed up all my Ergo files on to a flash drive, can I just copy pasta from the flash drive to the newly installed node?

I can use the the same mnemonic on Yoroi and it will show the correct balance there. Yoroi asks how many characters are in my mnemonic, while restoring through node doesn’t
