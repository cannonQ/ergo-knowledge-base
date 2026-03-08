---
title: Memory consumption goes higher than heap size limit
description: 'ErgoForum discussion: Memory consumption goes higher than heap size
  limit'
tags:
- ergoforum
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/memory-consumption-goes-higher-than-heap-size-limit/3018
created: '2021-11-26'
last_activity: '2021-11-29'
posts_count: 2
views: 339
likes: 1
glossary_hits:
- Full node
---

# Memory consumption goes higher than heap size limit

> **Forum thread:** [https://ergoforum.org/t/memory-consumption-goes-higher-than-heap-size-limit/3018](https://ergoforum.org/t/memory-consumption-goes-higher-than-heap-size-limit/3018)
> **Category:** Support | **Created:** 2021-11-26 | **Posts:** 2 | **Views:** 339

**Related concepts:** Full node

---

### Post #1 — @Ewemek (2021-11-26)

Hello,

We are currently starting to run an ERGO node v4.0.16 using docker.  
The max heap size of java is correctly set as the log tells upon startup:  
`Picked up _JAVA_OPTIONS: -Xmx3g`

However what we experience at some point is:

* peaks of memory consumption reaching 3 GB with logs telling `java.lang.OutOfMemoryError`
* then later, no more `java.lang.OutOfMemoryError` and the memory consumption goes up to 16 GB and even more

As a workaround, we have set a limit of memory consumption using docker itself.  
But we would like to know if this is an identified problem, or if someone did experience that ?

At first glance I’d say it looks like a memory leak, so we definitely cannot use it that way at the moment.

---

### Post #2 — @Ewemek (2021-11-29)

Small update: this week-end everything went fine. We had a misonfiguration in our API key where we used a placeholder with ‘<’ and ‘>’ characters, so it’s a guess but maybe it is related to the memory leak somehow.
