---
title: Yorio chrome wont sync
description: 'ErgoForum discussion: Yorio chrome wont sync'
tags:
- addresses
- ergoforum
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/yorio-chrome-wont-sync/3078
created: '2021-12-08'
last_activity: '2021-12-08'
posts_count: 2
views: 386
likes: 0
glossary_hits:
- Addresses
- Transaction
---

# Yorio chrome wont sync

> **Forum thread:** [https://ergoforum.org/t/yorio-chrome-wont-sync/3078](https://ergoforum.org/t/yorio-chrome-wont-sync/3078)
> **Category:** Support | **Created:** 2021-12-08 | **Posts:** 2 | **Views:** 386

**Related concepts:** Addresses, Transaction

---

### Post #1 — @sveinsin (2021-12-08)

I have noy tried for 3-4 weeks to get my wallet sync, but every time it just hang up and restart.  
Tried setting up extention new many times and recover the wallet, but always around tranaction 240-300 it will not sync anymore, and i cant get my coins out of wallet.  
Tried on chrome and edge, but same probleme on both.

Resume im notalone with this probleme, so hope someone can be helpfull.  
Support never answer my ticket/mails, so wounder whats going on with ergo?

---

### Post #2 — @dubster (2021-12-08)

do you have a large amount of adresses ?

If yes, I’m in same case, Anon has fixed it in the new incoming release, you can track progress here.

[github.com/Emurgo/yoroi-frontend](https://github.com/Emurgo/yoroi-frontend/pull/2551)

#### [Fix a syncing issue on wallets with 50+ addresses](https://github.com/Emurgo/yoroi-frontend/pull/2551)

`Emurgo:develop` ← `Emurgo:anon-br/fix-syncing-issue`

opened 11:27PM - 03 Dec 21 UTC

[![anon-br](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/2/2dbbe074c8f55c8f06c954958321f0ddc5959384.png)
anon-br](https://github.com/anon-br)

[+123
-63](https://github.com/Emurgo/yoroi-frontend/pull/2551/files)

This PR fixes a syncing issue that affects wallets which have more addresses tha[…](https://github.com/Emurgo/yoroi-frontend/pull/2551)n `CONFIG.app.addressRequestSize`.
# Background
The `rawUpdateTransactions()` function fetches transaction history in batches of 50 addresses each time, taking the last transaction as a starting point for the next call. The problem is that this function fetches the tx history in chunks but save it to the database at once. Since the second chunk onward usually has newer transactions than the first, this causes a gap between the transactions from the first chunk and the rest, because the 'starting point' to subsequent calls will be the newest one present on db, so the transactions relative to the first chunks of addresses are ignored.
# Implementation
The implementations consists of making the function `rawUpdateTransactions()` to fetch and persist data in blocks of 50 address, using `CONFIG.app.addressRequestSize`, trough the function `rawGetAllTxIdsChunked()`.
# Comments
This issue is a bit hard to explain with my weak English skills, so if isn't clear or do you have any additional question, just ask ;)

Thank again to Anon for his support
