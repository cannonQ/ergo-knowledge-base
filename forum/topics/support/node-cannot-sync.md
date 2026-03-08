---
title: Node cannot sync
description: 'ErgoForum discussion: Node cannot sync'
tags:
- ergo-explorer
- ergoforum
- ergoscript-context
- full-node
- scorex
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/node-cannot-sync/2258
created: '2021-08-24'
last_activity: '2021-09-01'
posts_count: 5
views: 1114
likes: 0
glossary_hits:
- Ergo Explorer
- ErgoScript context
- Full node
- Scorex
---

# Node cannot sync

> **Forum thread:** [https://ergoforum.org/t/node-cannot-sync/2258](https://ergoforum.org/t/node-cannot-sync/2258)
> **Category:** Support | **Created:** 2021-08-24 | **Posts:** 5 | **Views:** 1114

**Related concepts:** Ergo Explorer, ErgoScript context, Full node, Scorex

---

### Post #1 — @fatlover (2021-08-24)

Hi there,

Yesterday i configured and started my node + wallet.

I tried to follow some posts already existing, but im affraid i was not able to fix it.

![](https://yyz2.discourse-cdn.com/flex030/user_avatar/www.ergoforum.org/sdcvoltaic/48/663_2.png)
[Ergo wallet stuck in synchronization](https://www.ergoforum.org/t/ergo-wallet-stuck-in-synchronization/1819) [Support](/c/support/8)

> Wallet is stuck on synchronization, Id rather not recopy and retrieve wallet if I don’t have to
> "Please specify when reporting:
> what are you running (jar or docker image)
> how (launch command)
> config
> "
> ergo-4.0.12.jar
> cd I:\Users\REDACTED\Downloads\ergo\_folder
> start java -jar ergo-4.0.12.jar --mainnet -c ergo.conf
> start firefox <http://127.0.0.1:9053/panel/wallet>
> ergo {
> node {
> mining = true
> }
> }
> scorex {
> restApi {
> # Hex-encoded Blake2b256 hash of an API key.
> # Should be 64-chars lon…

Currently i have my node and wallet running in a different machine from where im going to mine on a centOS machine.( on my first try i had at same machine, on windows 10)

Node version: 4.0.13  
Using jar/docker: jar  
java version: openjdk version “11.0.12” 2021-07-20 LTS  
OpenJDK Runtime Environment 18.9 (build 11.0.12+7-LTS)  
OpenJDK 64-Bit Server VM 18.9 (build 11.0.12+7-LTS, mixed mode, sharing)

command used: java -jar ergo-4.0.13.jar --mainnet -c ergo.conf  
ergo.conf :

ergo {  
node {  
mining = true  
}  
}

scorex {  
restApi {  
# Hex-encoded Blake2b256 hash of an API key.  
# Should be 64-chars long Base16 string.  
# below is the hash of the string ‘hello’  
# replace with your actual hash  
apiKeyHash = “MYHASHKEY GOT FROM SWAGGER”  
}  
}

Perhaps, im also missing some basic info like:

* How much time normally it takes to fully sync?
* Do i need to set node mining = true only after fully synced?

Thanks!

BR,  
Joao

---

### Post #2 — @fatlover (2021-08-24)

Also noticed that node shutdown by himself somewhere between height 48000 and 49000

---

### Post #3 — @fatlover (2021-08-24)

Ok now i have everything fully sync. I have no ideia what i have done, just restart java process and let it run for 3/4 hours.

What is the average time for this?

---

### Post #4 — @randomminer (2021-08-26)

For me starting with empty, I have to kill java maybe after 8 hours because it started to hog too much memory/cpu (don’t remember which). I think full sync was ~ 24 hours, but sure it may depend on you computer and network?

---

### Post #5 — @miran (2021-09-01)

My Solution:  
I had exactly the same problem. I was using ergo-4.0.13.jar and the wallet never showed my balance after I recovered it using the keys even though it show balance in the ergo explorer.  
What I did:

1. Used an older version (4.0.5)
2. delete content under ./ergo/wallet (I don’t know if it was necessary honestly)
3. run java -jar ergo-4.0.5.jar --mainnet -c ergo.conf (set mining to true in ergo.config, I don’t know if this helped)
4. Let it run and be patient until completely synch.  
   \*\* I still experienced the constant exiting the synch in terminal and had to keep running the whole java -jar ergo-4.0.5…conf line every 2 or 4 hours, but this did not happen anymore once the whole blocks have been synchronized and now finally I am able to see my wallet balance and move ergos out of it
