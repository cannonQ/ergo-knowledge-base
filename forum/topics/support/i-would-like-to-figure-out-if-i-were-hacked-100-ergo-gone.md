---
title: I would like to figure out if I were hacked - 100+ ergo gone
description: 'ErgoForum discussion: I would like to figure out if I were hacked -
  100+ ergo gone'
tags:
- addresses
- ergo-explorer
- ergoforum
- full-node
- mempool
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/i-would-like-to-figure-out-if-i-were-hacked-100-ergo-gone/3105
created: '2021-12-10'
last_activity: '2021-12-11'
posts_count: 2
views: 572
likes: 2
glossary_hits:
- Addresses
- Ergo Explorer
- Full node
- Mempool
- Transaction
---

# I would like to figure out if I were hacked - 100+ ergo gone

> **Forum thread:** [https://ergoforum.org/t/i-would-like-to-figure-out-if-i-were-hacked-100-ergo-gone/3105](https://ergoforum.org/t/i-would-like-to-figure-out-if-i-were-hacked-100-ergo-gone/3105)
> **Category:** Support | **Created:** 2021-12-10 | **Posts:** 2 | **Views:** 572

**Related concepts:** Addresses, Ergo Explorer, Full node, Mempool, Transaction

---

### Post #1 — @FlaxenFish (2021-12-10)

Hi everyone,

I have worked hard to try to accrue as much ergo I could reasonably afford and I was always concerned with security, because evidently everything can be hacked one way or the other, so i have set up a ergo full node on my secondary machine. Yes, my probable mistake was to put everything on windows …

Recently I have made a few small transactions from the full node wallet to my yoroi wallet. 1 and 2 ergos.  
Within those transactions I saw that there are some additional addresses in there, but checking my ergo node wallet, the numbers didn’t add up.

On the explorer it was clearly stated, that I have 97.1913 ergos, when on the ergo node wallet it was clearly said that I have ~236 so i didn’t think of it.

Yesterday, I decided to create a more secure place for my ergo wallet on a VM, when I decided to move everything, I kept getting an error, I couldn’t even move a single ERG out of the wallet (error was “Transaction with this ID was not found, or it has not entered Mempool yet”.

As I found this strange I decided to investigate, so in the CLI it said “Failed to initialize storage: org.fusesource.leveldbjni.internal.NativeDB$DBException: Corruption: CURRENT file does not end with newline.”

To fix this, I renamed the history and state folders so i can start to completely re-sync. Once the sync was complete, to my horror, it was no longer showing me 236 ERG, but 97.1913.

Once I checked the transactions on the explorer, it was there, clear as day, another address, within my 1-2 ERG transactions, with way higher values.

To date, 130 ERG are missing. I do not know this address, I checked every single exchange that I used, it is not any of them. This address, currently holds what used to be my 130 ergos.

Before posting the addresses, funny thing is, I always TRIPLECHECK every single transaction, to make sure the fields are only populated by the addresses where I want to send, scroll left and right to make sure there is nothing else in the address fields. Yet somehow, if it turns out that this was injected somehow, those transactions were made.

Is it possible at all to validate my claims? I still have 97 ergos in there that i would like to get out, but if every time I do a transaction there is a way to inject another address … its basically gone before I may even have a chance to salvage what is left.

My main wallet address: 9hUVScrWS5MMS9bLxabg8jiuTTuWMtq4Tswo6cyfTiJZkPTsXoX  
My Yoroi: 9gJmMAAQq8PLNskKKF5FSJ3GfauT3KZ27R5AHxvscN1n2txx8oP  
The suspect address: 9efMs56kANdn9udDDnW6xYHjD2U1pscu3q4fYSpybXw6ooXk5rQ

I appreciate any feedback anyone might have.  
This burns my heart to no avail … I tried to be so careful.

Later edit:

Someone replied to this thread on discord (thanks andee and liquid\_phase) saying it may be because I am running an old version and that the new address is the change address.  
It is possible i may have been my own bad actor this whole time by not reading the changelogs and by not updating my node. I updated my .jar and now I’m waiting for a re-sync of the node.

---

### Post #2 — @TypoDaPsycho (2021-12-11)

Please share the final outcome once fully synced. Could be helpful information for others in the future, sounds like the updated version will fix your issue.
