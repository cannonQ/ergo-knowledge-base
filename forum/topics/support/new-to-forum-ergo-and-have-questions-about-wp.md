---
title: New to forum, Ergo, and have questions about WP
description: 'ErgoForum discussion: New to forum, Ergo, and have questions about WP'
tags:
- box
- ergoforum
- registers
- storage-rent
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/new-to-forum-ergo-and-have-questions-about-wp/561
created: '2021-01-24'
last_activity: '2021-01-26'
posts_count: 4
views: 739
likes: 7
glossary_hits:
- Box
- Registers
- Storage rent
- Transaction
---

# New to forum, Ergo, and have questions about WP

> **Forum thread:** [https://ergoforum.org/t/new-to-forum-ergo-and-have-questions-about-wp/561](https://ergoforum.org/t/new-to-forum-ergo-and-have-questions-about-wp/561)
> **Category:** Support | **Created:** 2021-01-24 | **Posts:** 4 | **Views:** 739

**Related concepts:** Box, Registers, Storage rent, Transaction

---

### Post #1 — @Ergosum (2021-01-24)

Hi everyone,  
I’m new to Ergo and working my way through the white paper. I hope that this is the appropriate place to ask questions. I am for the most-part a non-technical newbie, so patience (and plain language!) will be appreciated!

I’m sure I will have more but for the moment:

1)Can someone please explain how the storage-rent fee component will work? If I am a miner, and need to contend with large state size, I understand that I can charge a small fee. I’m a bit confused as to where the fee comes from. Who pays for it? Is the fee debited from the outdated account deemed outdated? Is it inactivity that makes an account outdated?

2)I am wrapping my head around the idea of the Ergo Box. Is a Box created for each block? For each transaction? Is it correct to understand the registers as an array of sorts? If an Ergo Box is created for each block (and assuming that blocks include multiple transactions), who gets to include the user-defined data in the block?

Thank you in advance for help

---

### Post #2 — @scalahub (2021-01-25)

In order to understand both answers, you need to have some idea of UTXOs.

A box is an acronym for UTXO in Ergo. So they are one and the same thing.

1. If a box has remained unspent for 4 years or more, the miners can spend that box, removing a fraction of the Ergs and creating an identical box with the reduced Ergs. The difference is taken by miners as storage rent. The rationale behind this is explained in [this paper](https://fc18.ifca.ai/bitcoin/papers/bitcoin18-final18.pdf) and [this post](https://www.ergoforum.org/t/storage-rent-details/256)
2. As explained earlier, a box is a UTXO, so each transaction spends (destroys) some boxes and creates new boxes

The hierarchy of data structures is:

* A box contains up to 10 registers
* A transaction contains many boxes
* A block contains many transactions

User defined data is stored in the box (in one of the 10 registers)

---

### Post #3 — @Ergosum (2021-01-26)

Thanks very much for your reply, I truly appreciate it. I need to study UTXO vs. the ETH account system before I ask more questions. I’m also curious to read the paper to which you linked.

Thanks again – and I hope that I’ll have more substantive questions next time!

---

### Post #5 — @scalahub (2021-01-26)

No worries… I think your questions are great. I’m pretty sure such questions (and their answers) are needed for outsiders to understand Ergo. Feel free to ask more.

About UTXOs and accounts, kind of a separate topic in itself and lot of info on this topic online already
