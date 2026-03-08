---
title: Ergo wallet stuck in synchronization
description: 'ErgoForum discussion: Ergo wallet stuck in synchronization'
tags:
- ergoforum
- ergoscript
- full-node
- scorex
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/ergo-wallet-stuck-in-synchronization/1819
created: '2021-06-19'
last_activity: '2021-06-27'
posts_count: 3
views: 1368
likes: 2
glossary_hits:
- ErgoScript
- Full node
- Scorex
---

# Ergo wallet stuck in synchronization

> **Forum thread:** [https://ergoforum.org/t/ergo-wallet-stuck-in-synchronization/1819](https://ergoforum.org/t/ergo-wallet-stuck-in-synchronization/1819)
> **Category:** Support | **Created:** 2021-06-19 | **Posts:** 3 | **Views:** 1368

**Related concepts:** ErgoScript, Full node, Scorex

---

### Post #1 — @sdcvoltaic (2021-06-19)

Wallet is stuck on synchronization, Id rather not recopy and retrieve wallet if I don’t have to

"Please specify when reporting:

```ergoscript
what are you running (jar or docker image)
how (launch command)
config
```

"  
ergo-4.0.12.jar

cd I:\Users\REDACTED\Downloads\ergo\_folder  
start java -jar ergo-4.0.12.jar --mainnet -c ergo.conf  
start firefox <http://127.0.0.1:9053/panel/wallet>

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
apiKeyHash = “REDACTED”  
}  
}

---

### Post #2 — @Captain_Crazy (2021-06-21)

Hello, I had the same issue - please follow this thread -

![](https://avatars.discourse-cdn.com/v4/letter/c/dbc845/48.png)
[Wallet stuck on synchronization?](https://www.ergoforum.org/t/wallet-stuck-on-synchronization/1236) [Support](/c/support/8)

> Hello!
> I’ve been mining for some time now and after a power outage I restarted my node but it seems like the wallet is “stuck” on active synchronization…
> I have received 2 coins from mining which isn’t showing in my wallet.
> Any advice on how to fix this or advice on how to sync the wallet?
> Thanks!

---

### Post #3 — @sdcvoltaic (2021-06-27)

Thanks I didn’t want to have to resort to that method if I didn’t need to but looks like there’s no other way
