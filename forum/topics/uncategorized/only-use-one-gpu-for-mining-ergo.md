---
title: Only use One GPU for mining ERGO
description: 'ErgoForum discussion: Only use One GPU for mining ERGO'
tags:
- ergoforum
- uncategorized
category: forum
forum_category: Uncategorized
source: ergoforum
source_url: https://ergoforum.org/t/only-use-one-gpu-for-mining-ergo/1756
created: '2021-06-12'
last_activity: '2021-06-13'
posts_count: 3
views: 1739
likes: 1
glossary_hits: []
---

# Only use One GPU for mining ERGO

> **Forum thread:** [https://ergoforum.org/t/only-use-one-gpu-for-mining-ergo/1756](https://ergoforum.org/t/only-use-one-gpu-for-mining-ergo/1756)
> **Category:** Uncategorized | **Created:** 2021-06-12 | **Posts:** 3 | **Views:** 1739

---

### Post #1 — @Kaladin (2021-06-12)

Hi everyone,  
I am very new to mining and would greatly appreciate some help ![:slight_smile:](https://emoji.discourse-cdn.com/twitter/slight_smile.png?v=12 ":slight_smile:")

I currently have a 1070 and will be getting a 3070Ti in the mail soon.

I have a few more weeks to get a payout for the 1070 using cudaminer for Eth and I want to keep the 1070 mining Eth at least until that payout.

Using NBminer, How do I set it up so it ONLY uses the 3070ti to mine Ergo?

Thanks for the help!

---

### Post #2 — @VooDoo (2021-06-13)

When you start the ergo.bat file, probably it should have the option to enable/disable the desired gpu…

---

### Post #3 — @Kcteby (2021-06-13)

* -d, --devices Specify GPU list to use. Format: “-d 0,1,2,3” to use first 4 GPU.

-d 0 or -d 1
