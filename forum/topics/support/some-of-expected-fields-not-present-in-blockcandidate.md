---
title: Some of expected fields not present in /block/candidate
description: 'ErgoForum discussion: Some of expected fields not present in /block/candidate'
tags:
- autolykos
- ergoforum
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/some-of-expected-fields-not-present-in-block-candidate/855
created: '2021-03-19'
last_activity: '2021-05-31'
posts_count: 4
views: 489
likes: 1
glossary_hits:
- Autolykos
- Full node
---

# Some of expected fields not present in /block/candidate

> **Forum thread:** [https://ergoforum.org/t/some-of-expected-fields-not-present-in-block-candidate/855](https://ergoforum.org/t/some-of-expected-fields-not-present-in-block-candidate/855)
> **Category:** Support | **Created:** 2021-03-19 | **Posts:** 4 | **Views:** 489

**Related concepts:** Autolykos, Full node

---

### Post #1 — @merovingio (2021-03-19)

2021-03-18 21:57:38,330 ERROR [main thread] Some of expected fields not present in /block/candidate  
2021-03-18 21:57:38,330 ERROR [main thread] Block data: {  
“MSG” : “5C9FF2EA1CB757A36F4826C66695D1A54979A335178592D841F5F12B56F9D7DE”,  
“B” : 309258817417071668746753866741071288812706062512703436998535338,  
“H” : 447956,  
“PK” : “0280B553664FF2FE2B4A7EDA51C28BF61940936C651B2DDF2B9943467A04A85936”

Hi  
some solution for that,  
thank you

---

### Post #2 — @Patates (2021-05-18)

I’m having the same issue and have been unable to find a solution.

2021-05-18 18:41:55,156 INFO [main thread] Waiting for block data to be published by node…  
2021-05-18 18:41:55,166 ERROR [main thread] Some of expected fields not present in /block/candidate  
2021-05-18 18:41:55,167 ERROR [main thread] Block data: {  
“MSG” : “D96589A5FBC6DF0FC2CDC100F38BB7ACDF4A32EABBFCE0017C3D92F0D7CBD45D”,  
“B” : 70640869773064813112257931620287884840314802398040694104998104,  
“H” : 492664,  
“PK” : “03D45320C684E0C65EE78589B5E7382A07191ADA6430C6C0A0AFD0A163B4CD4D4C”  
}

Is there anyone who can shed some light on this issue and offer some guidance as to how to resolve the matter?

Any help would be greatly appreciated!

Thank you.

---

### Post #3 — @scalahub (2021-05-19)

Can you supply more details:

1. Which document are you following?
2. What are the steps to reproduce the error?

---

### Post #4 — @kushti (2021-05-31)

Seems you are using miner for Autolykos v1
