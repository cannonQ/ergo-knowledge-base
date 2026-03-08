---
title: Issues with KuCoin
description: 'ErgoForum discussion: Issues with KuCoin'
tags:
- addresses
- eip
- emission-schedule
- ergoforum
- ergoscript-context
- full-node
- mempool
- nautilus
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/issues-with-kucoin/3704
created: '2022-06-25'
last_activity: '2022-07-03'
posts_count: 7
views: 1141
likes: 11
glossary_hits:
- Addresses
- EIP
- Emission schedule
- ErgoScript context
- Full node
- Mempool
- Nautilus
- Transaction
---

# Issues with KuCoin

> **Forum thread:** [https://ergoforum.org/t/issues-with-kucoin/3704](https://ergoforum.org/t/issues-with-kucoin/3704)
> **Category:** Support | **Created:** 2022-06-25 | **Posts:** 7 | **Views:** 1141

**Related concepts:** Addresses, EIP, Emission schedule, ErgoScript context, Full node, Mempool, Nautilus, Transaction

---

### Post #1 — @jp215 (2022-06-25)

FYI to everyone and question.  
I purchased ERGO on KuCoin June 23rd like I have previously. I tried to send the ERGO to my Nautilus wallet.  
In KuCoin it says it the transaction completed, the address is correct but the Tx Hash has never posted and when I click the link it says, ‘Transaction with this ID was not found, or it has not entered Mempool yet’  
I opened a ticket with KuCoin after 36 hours. I heard back 2 hours later that they’re experiencing a higher volume of tickets and responses are delayed.

FYI as a warning.  
Question if anyone else has had this issue?

---

### Post #2 — @kushti (2022-06-25)

Enigma pool made incorrect non-EIP27 compliant payout transaction. Such transaction can not get into blocks, but nodes not checking EIP-27 rules (so all non-mining nodes atm) do accept such transactions into their mempool. So did the KuCoin node, and as couple of outputs were exchange deposits, it is started to build transactions on top of the unconfirmed pool transaction.

So transactions are in mempools of some nodes but can not get into the blocks. HotBit affected also. Some Enigma miners also withdrawing to [gate.io](http://gate.io), but gate is not affected as it is collecting deposits in another (and likely more secure) way.

Informed the pool and the exchanges. After switching to EIP-27 rules validation everything should be ok for exchanges.

---

### Post #3 — @jp215 (2022-06-25)

Thanks for the response, I’ll continue to wait.

---

### Post #4 — @jp215 (2022-06-26)

Not much help from KuCoin.

See their response below.  
I am happy to help you. Please kindly note that the withdrawal has been completed at our end. Please kindly check it with the receiving platform.

We hope this information guides you to the right direction. If you have any questions or concerns regarding to this process, please don’t hesitate to let us know.

---

### Post #5 — @kushti (2022-06-27)

Deposits and withdrawals are resumed on KuCoin. HotBit is good as well.

---

### Post #6 — @jp215 (2022-06-27)

It did come through thank you!

---

### Post #7 — @Nico2126 (2022-07-03)

I have the same problem. I tried to send my ERGO to my Nautilus wallet but didnt arrive. In KuCoin it says transaction completed but when I click the link it says ‘Transaction with this ID was not found, or it has not entered Mempool yet’. I opened a ticket with Kucoin… I don’t know, I’ll wait
