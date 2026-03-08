---
title: AgeUSD protocol
description: 'ErgoForum discussion: AgeUSD protocol'
tags:
- addresses
- eip-12
- ergoforum
- sigmausd
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/ageusd-protocol/1405
created: '2021-05-24'
last_activity: '2021-05-31'
posts_count: 4
views: 366
likes: 5
glossary_hits:
- Addresses
- EIP-12
- SigmaUSD
- Transaction
---

# AgeUSD protocol

> **Forum thread:** [https://ergoforum.org/t/ageusd-protocol/1405](https://ergoforum.org/t/ageusd-protocol/1405)
> **Category:** Support | **Created:** 2021-05-24 | **Posts:** 4 | **Views:** 366

**Related concepts:** Addresses, EIP-12, SigmaUSD, Transaction

---

### Post #1 — @ZeroKnowledge (2021-05-24)

Hey guys, when I try to mint SigRSV or redeem them for ERG my transactions OFTEN fails and I get refunded. After like 3-4 times it works at some point. Anyone knows what’s going wrong? I’m sending the correct amount to the correct address…

---

### Post #2 — @thegeologist (2021-05-24)

I’m not totally sure, but it could be due to attempting to transact during an oracle update or there may be high traffic on the contract. The bearwhale had also been spamming the contract for some time trying to keep SigRSV holders from redeeming in the past.

---

### Post #3 — @ZeroKnowledge (2021-05-25)

I don’t think the oracle update process is the issue. After trying it several times the oracle price ist most often still the same. So this shouldn’t matter. But high traffic could be a very real issue. Maybe the developers can say more about that? [@kushti](/u/kushti)

---

### Post #4 — @kushti (2021-05-31)

Transactions fail because of oracle price change or parallel request. For both cases DApp connector would be useful I guess ( it will reduce %% of failed transactions)
