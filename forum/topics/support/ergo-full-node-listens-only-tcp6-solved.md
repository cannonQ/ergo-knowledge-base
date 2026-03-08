---
title: Ergo full node listens only tcp6 [solved]
description: 'ErgoForum discussion: Ergo full node listens only tcp6 [solved]'
tags:
- ergoforum
- ergoscript
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/ergo-full-node-listens-only-tcp6-solved/727
created: '2021-02-26'
last_activity: '2021-02-26'
posts_count: 2
views: 491
likes: 0
glossary_hits:
- ErgoScript
- Full node
---

# Ergo full node listens only tcp6 [solved]

> **Forum thread:** [https://ergoforum.org/t/ergo-full-node-listens-only-tcp6-solved/727](https://ergoforum.org/t/ergo-full-node-listens-only-tcp6-solved/727)
> **Category:** Support | **Created:** 2021-02-26 | **Posts:** 2 | **Views:** 491

**Related concepts:** ErgoScript, Full node

---

### Post #1 — @laplasz (2021-02-26)

Hi There!

just started to full node and tries to access <http://127.0.0.1:9053/panel>  
but I realized that node only listens on tcp6:

```ergoscript
~/ergo$ netstat -ltna | grep 9053
tcp6       0      0 :::9053                 :::*                    LISTEN
```

so how can I force the node to listen on tcp4 as well?

Thanks, Balazs

---

### Post #2 — @laplasz (2021-02-26)

false alarm - it listens on everywhere just had a VPN on the client machine that is why I could not reach it.  
Great work - thanks!
