---
title: Teamredminer trouble
description: 'ErgoForum discussion: Teamredminer trouble'
tags:
- ergoforum
- uncategorized
category: forum
forum_category: Uncategorized
source: ergoforum
source_url: https://ergoforum.org/t/teamredminer-trouble/1577
created: '2021-06-01'
last_activity: '2021-06-01'
posts_count: 2
views: 756
likes: 1
glossary_hits: []
---

# Teamredminer trouble

> **Forum thread:** [https://ergoforum.org/t/teamredminer-trouble/1577](https://ergoforum.org/t/teamredminer-trouble/1577)
> **Category:** Uncategorized | **Created:** 2021-06-01 | **Posts:** 2 | **Views:** 756

---

### Post #1 — @peternord71 (2021-06-01)

I got a weird issue with teamredminer.

Have been mining on srbminer on win10 with 2xvega64, 2xvega56 and a rx580. Stock bios, no amdmemtweak, only gpu-boost and gpu-tweak. Getting 550Mh/s average.

Thought I should try teamredminer to get higher hashrate. When I try to start trm I get  
GPU3 Failed to initialize (-31).

Tried one gpu at the time, no problem.  
Tried two gpus in different combinations, no problem.  
Tried three gpus i different combinations, no problem.

But as soon as I try four or five I get the Failed initialize error.

Anyone know the issue and how to fix it?

---

### Post #2 — @peternord71 (2021-06-01)

Solved it.

Had to manually set win10 virtual memory to 36Gb.
