---
title: How to run two ergo nodes in same computer?
description: 'ErgoForum discussion: How to run two ergo nodes in same computer?'
tags:
- ergoforum
- ergoscript
- full-node
- scorex
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/how-to-run-two-ergo-nodes-in-same-computer/2043
created: '2021-08-02'
last_activity: '2021-09-14'
posts_count: 6
views: 637
likes: 2
glossary_hits:
- ErgoScript
- Full node
- Scorex
---

# How to run two ergo nodes in same computer?

> **Forum thread:** [https://ergoforum.org/t/how-to-run-two-ergo-nodes-in-same-computer/2043](https://ergoforum.org/t/how-to-run-two-ergo-nodes-in-same-computer/2043)
> **Category:** Support | **Created:** 2021-08-02 | **Posts:** 6 | **Views:** 637

**Related concepts:** ErgoScript, Full node, Scorex

---

### Post #1 — @randomminer (2021-08-02)

I would need 2 separate wallets, so I assume I need to run 2 instances of ergo node. I need two directories, but how do I configure second node to run on different ports?

---

### Post #2 — @randomminer (2021-08-04)

Ok, one possible solution is to have two separate directories, and just run one instance at the time. Not very elegant, but works?

---

### Post #3 — @kushti (2021-08-18)

You also need to occupy different ports:

e.g. for first node:

```ergoscript
scorex {
  network {
     bindAddress = "0.0.0.0:9030" 
 }
  restApi {
    bindAddress = "0.0.0.0:9053"
 }
}
```

and second one:

```ergoscript
scorex {
  network {
     bindAddress = "0.0.0.0:19030" 
 }
  restApi {
    bindAddress = "0.0.0.0:19053"
 }
}
```

and different folders, yes

---

### Post #4 — @intigo_Jung (2021-08-19)

Run 2 types of mining programs

TRM, nbminer…

---

### Post #5 — @randomminer (2021-08-20)

That does not help, point was to have 2 separate wallets in same machine. This machine is not actually even mining.

---

### Post #6 — @randomminer (2021-09-14)

Yeah, configuring ports works as expected. Now I have my two nodes up!
