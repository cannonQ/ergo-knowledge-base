---
title: First timer ergo node
description: 'ErgoForum discussion: First timer ergo node'
tags:
- box
- ergoforum
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/first-timer-ergo-node/690
created: '2021-02-18'
last_activity: '2021-02-26'
posts_count: 6
views: 3249
likes: 6
glossary_hits:
- Box
- Full node
---

# First timer ergo node

> **Forum thread:** [https://ergoforum.org/t/first-timer-ergo-node/690](https://ergoforum.org/t/first-timer-ergo-node/690)
> **Category:** Support | **Created:** 2021-02-18 | **Posts:** 6 | **Views:** 3249

**Related concepts:** Box, Full node

---

### Post #1 — @naaman (2021-02-18)

hello  
so out of interest i installed a node on my remote server  
its running for about 3 days and still hasnt finish to sync  
the folder size is about 3.5gb now  
and synchronization state shows yellow active synchronization and keeps running  
its connected to 25 peers and the terminal is very busy in the background  
no mining  
on a 100mb connection  
is it normal? how long should it take?  
it seems like the network is very slow to get the blocksdata for some reason  
how big should the block folder be?

---

### Post #2 — @Martin-mx (2021-02-18)

Folder size is about 4gb now. This version should resolve issue with bad config at least [Ergo Mainnet 4.0.5 Release](https://www.ergoforum.org/t/ergo-mainnet-4-0-5-release/689) Latest tutorial [Guide for setting up an Ergo node on windows 10 by ADA North Pool](https://www.ergoforum.org/t/guide-for-setting-up-an-ergo-node-on-windows-10-by-ada-north-pool/570)

---

### Post #3 — @naaman (2021-02-18)

ok will be running the 4.0.5 ver see if that will run faster  
i run it by the instructions on the post , its seems ok , except for the download speed

what effects the speed of blocks download? is it physical connection to other nodes or is it a factor of network calculations and block generating that effects the build of a new node data?

---

### Post #4 — @teknishun (2021-02-19)

I installed the node on my PC recently and I was kinda surprised by the CPU usage while it was sync. PC is usually quite as a mouse but my 5600X was definitely working while it was doing the initial sync. If your remote box hasn’t got decent processing power, that’s why it’s probably a bit slow.

It took about 5 hours to sync on mine.

---

### Post #5 — @kushti (2021-02-23)

I guess it also depends on HDD vs SSD.

4.0.8 should have significantly faster bootstrap, under 2 hours on my old laptop with weak HDD.

---

### Post #6 — @naaman (2021-02-26)

for the info  
my problem was in the config file , i had it pointing to the actual folder path  
instead of ${user.dir}"/…" , after setting it correctly it actually downloaded after few hours.

but now i have another problem , its actually crushes after few hours with a scala error code ,  
i think its java version , updated and will see.
