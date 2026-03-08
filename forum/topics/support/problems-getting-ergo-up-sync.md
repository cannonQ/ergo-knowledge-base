---
title: Problems getting ergo up & sync
description: 'ErgoForum discussion: Problems getting ergo up & sync'
tags:
- ergoforum
- ergoscript-context
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/problems-getting-ergo-up-sync/1714
created: '2021-06-11'
last_activity: '2021-06-11'
posts_count: 6
views: 465
likes: 1
glossary_hits:
- ErgoScript context
- Full node
---

# Problems getting ergo up & sync

> **Forum thread:** [https://ergoforum.org/t/problems-getting-ergo-up-sync/1714](https://ergoforum.org/t/problems-getting-ergo-up-sync/1714)
> **Category:** Support | **Created:** 2021-06-11 | **Posts:** 6 | **Views:** 465

**Related concepts:** ErgoScript context, Full node

---

### Post #1 — @randomminer (2021-06-11)

I installed ergo for getting wallet, but I am not anymore sure if it was right decision. I am running it from jar-file in linux.

* It logs huge amounts, 2 MB/minute.
* Seems to use CPU pretty much

Once had to stop it for removing logs, and start again. Another shut down for thunder storm before sync is done. I have some mining profits paid, but cannot see them in my wallet.

I suppose sync is working because ‘height’ number is growing. From where I can see what is current height? No, don’t give me number, but tell how to see it so that other people also can check.

Is there some way to cut logging? Is it possible to limit number cores ergo can hog? Is there some other way to access my wallet?

---

### Post #2 — @randomminer (2021-06-11)

Ok, core limiting is easy, -XX:ActiveProcessorCount=2 for java

---

### Post #3 — @kushti (2021-06-11)

and for limiting log, -Dlogback.stdout.level=WARN

---

### Post #4 — @kushti (2021-06-11)

check heights at 127.0.0.1:9053/info or 127.0.0.1:9053/panel

---

### Post #5 — @randomminer (2021-06-11)

That tells height I have synced, but not height it is aiming. Idea was to get idea to get how far my node is from beeing synced.

---

### Post #6 — @randomminer (2021-06-11)

Got my node in sync. Current height 508897 but for next newbie place where to check height would be good.
