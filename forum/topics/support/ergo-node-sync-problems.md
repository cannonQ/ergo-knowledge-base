---
title: Ergo node sync problems
description: 'ErgoForum discussion: Ergo node sync problems'
tags:
- addresses
- ergoforum
- ergoscript-context
- full-node
- scorex
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/ergo-node-sync-problems/2644
created: '2021-09-27'
last_activity: '2021-09-27'
posts_count: 2
views: 776
likes: 0
glossary_hits:
- Addresses
- ErgoScript context
- Full node
- Scorex
---

# Ergo node sync problems

> **Forum thread:** [https://ergoforum.org/t/ergo-node-sync-problems/2644](https://ergoforum.org/t/ergo-node-sync-problems/2644)
> **Category:** Support | **Created:** 2021-09-27 | **Posts:** 2 | **Views:** 776

**Related concepts:** Addresses, ErgoScript context, Full node, Scorex

---

### Post #1 — @kil0pro (2021-09-27)

Hi, I looked through the support forums, and I couldn’t really nail down a wait time on synchronization. I noticed people reporting between 2 and 24 hours, but I really want to make sure I have done things correctly.

I have already installed ergo and initialized a wallet according to the instructional video on the ergo wallet webpage (about a week ago). I was able to generate a wallet address and I went ahead and started sending my mining rewards to that address. I just booted up my ergo node, but it is has been on active synchronization for over an hour and my ergo wallet folder is over 5gb in size…

Q1) I also notice my height is contact increasing, is that correct behavior?  
Q2) Should I be waiting several hours to sync?  
Q3) Is my jar file running correctly? My setting are below:

1. I am running windows 10
2. ergo-4.0.13.jar
3. my script: java -jar ergo-4.0.13.jar --mainnet -c ergo.conf
4. my conf file:  
   ergo {  
   directory = “c:/ergo”  
   node {  
   mining = false  
   }  
   wallet.secretStorage.secretDir = “c:/ergo”  
   }

scorex {  
restApi {  
# Hex-encoded Blake2b256 hash of an API key.  
# Should be 64-chars long Base16 string.  
# below is the hash of the string ‘hello’  
# replace with your actual hash  
apiKeyHash = “my\_hash\_key\_is\_here”  
}  
}

5. snippet of the jar output:  

   [![image](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/112e99eb5dd9e77f7524a984289753cd38eb24c1.png)

   image1449×346 32.7 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/112e99eb5dd9e77f7524a984289753cd38eb24c1.png "image")

Thanks for any help! It is much appreciated

---

### Post #2 — @kil0pro (2021-09-27)

pic of my ergo node:  

[![image](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/f431af32cdb03f163b6374b14d0a2386a9fd58ed_2_690x302.png)

image1079×473 28.4 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/f431af32cdb03f163b6374b14d0a2386a9fd58ed.png "image")
