---
title: Lose Ergo while sending test from local wallet to Kucoin
description: 'ErgoForum discussion: Lose Ergo while sending test from local wallet
  to Kucoin'
tags:
- addresses
- box
- ergo-explorer
- ergoforum
- full-node
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/lose-ergo-while-sending-test-from-local-wallet-to-kucoin/2082
created: '2021-08-06'
last_activity: '2021-10-01'
posts_count: 13
views: 1172
likes: 1
glossary_hits:
- Addresses
- Box
- Ergo Explorer
- Full node
- Transaction
---

# Lose Ergo while sending test from local wallet to Kucoin

> **Forum thread:** [https://ergoforum.org/t/lose-ergo-while-sending-test-from-local-wallet-to-kucoin/2082](https://ergoforum.org/t/lose-ergo-while-sending-test-from-local-wallet-to-kucoin/2082)
> **Category:** Support | **Created:** 2021-08-06 | **Posts:** 13 | **Views:** 1172

**Related concepts:** Addresses, Box, Ergo Explorer, Full node, Transaction

---

### Post #1 — @Feoraelan (2021-08-06)

Hi there,

I decided to transfer some Ergo from my local wallet to my kucoin account.  
For this, i made a test with small amount 0.27ERG, but, and i don’t know why, an amount of 10 ERG where sent to another address. I certainly made a mistake but don’t see what exactly.  
Additional information : my node was syncing during my test.

here the transaction link, if it can help to explain to me what happened:

<https://explorer.ergoplatform.com/en/transactions/412af0accfbe29def1bb556dcfb358f92ca0d06248130c108a93b38448f2fce2>

Thanks by advance for you help  
Greetings.

---

### Post #2 — @kushti (2021-08-18)

10 ERG were sent to change address, please check they’re reflected in balance.

---

### Post #3 — @Feoraelan (2021-08-29)

Hi,  
Sorry for the late answer, I was on vacation. I don’t understand what you mean by “reflected in balance”  
( sorry, i’m French ![:wink:](https://emoji.discourse-cdn.com/twitter/wink.png?v=10 ":wink:") ). I synced my node and I see my balance to 0.  
Thanks helping me ![:slight_smile:](https://emoji.discourse-cdn.com/twitter/slight_smile.png?v=10 ":slight_smile:")

---

### Post #4 — @deadit (2021-08-30)

Hey. 9gPeYofyxmv7z6Awxdgnm1bMsCXkcYavCwoEs7ni39BXWAV7cAs - this is also yours address.  
I recommend you delete .ergo/.ergo/wallet folder and resync the node. After you resync it you will see your balance.

---

### Post #5 — @Uberlord (2021-09-19)

Hi, it seems the exact same thing has happened to me, which is a kind of a really unsettling experience I have to say! So far I had a great time with Ergo, but this is really startling, I hope you can understand.

I was moving some mined ERG to another wallet when for no good reason, instead of the intended 5 ERG, 6 were moved in the transaction, 5 correctly where I send them and 1 I guess to this “change address”, whatever this is.

I have tried setting up a new node, recover the wallet in hopes that I would get access to this “change address”, but it didn’t work. My questions:

1. What is a “change address”? I have been trying to find it somewhere in the various Ergo wikis etc. but no luck.
2. How do I get access to it? Should I retry setting up an Ergo node?
3. How can I make sure that no funds are sent to the “change address”?

This is the transaction I am referring to: [Ergo Explorer](https://explorer.ergoplatform.com/en/transactions/ddbe099af62c0cbc352593079d216de1f687843e9522578fa2347fcbaf23baec)

Any help / information is greatly appreciated, thanks in advance.

---

### Post #6 — @Uberlord (2021-09-20)

I was asking the same question in the Ergo Discord channel. Thanks for andee for the help there.

To let others know what I found so far (I have not been able to recover the ERG stored at the change address, yet):

1. A change address is needed when a transaction does not use the total balance of a utxo box. The amount specified in the transaction will be send to its target, just as normal. The remainder of the utxo box will go to the change address. More here: <https://coincentral.com/utxo-beginners-explainer/>
2. I am in progress of getting hold of the change address. Something irregular must have happened, as setting up a new node and restoring the wallet has not given me access to the change address. I will try setting up a transaction “by hand” via Swagger. My best guess is right now that it is a kind of UI problem. Will post here when I find out more.
3. I guess using the total available balance of a wallet will make sure there is no excess which could go to the change address. Or, choosing the utxos manually and apply the same logic should also work. Please correct me if I am wrong.

---

### Post #7 — @Uberlord (2021-09-21)

Got hold of the change address finally. The solution was using the node’s REST API with route /wallet/addBox. Doing this with the three boxes where the change ERG were sent made the node aware of the balances and I could send them via the UI.

A subsequent call of /wallet/rescan seems to have brought back the node in sync.

---

### Post #8 — @Natewana (2021-09-25)

I am so sorry to ask this of you, but I am a simple miner and am only able to keep my operation afloat by copy and pasting even the simplest of operational instructions. Could you please spell out exactly how you accomplished accessing your change wallet, as if you were speaking to a four year old that knows how to use a computer but is seeing everything inside for the very first time? I have ended up with a fair amount of ERG in my change wallet, and it is distressing to see it there with no (functional) idea how to access it. Thank you very much in advance!..and I’m sure there will be many others after me who thank you as well, as this is kind of a tricky aspect of entering the world of Ergo node operation.

---

### Post #9 — @Natewana (2021-09-26)

Uberlord, I appreciate your post, which pointed me in the right direction. It wasn’t the fix for me, but got me on track.

In case anyone else finds themselves in a similar pinch, my fix was thus:

**Problem:** After a hard node crash, my primary wallet zeroed out, although I could still see the balance reflected in my change wallet. These assets could not be accessed.

**Attempted solutions:** I went so far as to delete everything Ergo related and resync the node and wallet from scratch by reinitializing the wallet in question from the mnemonic, to no avail.

**Eventual solution:** As I became increasingly frustrated, I went through almost every function of Swagger. In doing so, I realized that my change address was not registering unless my wallet was unlocked. I unlocked my wallet and used the wallet rescan function. I could actually watch on my main panel as the appropriate amount of ERG fluctuated and then suddenly dropped to zero. I did this twice. I then realized that when the rescan initialized, it was locking my wallet prior to scanning. Realizing this - in the context of what I had discovered earlier about the state of the change wallet when the primary was locked/unlocked - I started the scan and then unlocked the wallet from the main panel. This resulted in the appropriate amount of ERG being available in my primary address while still being reflected in the change wallet.

---

### Post #10 — @Uberlord (2021-09-26)

Hi Natewana,

I am glad my post has supported you in finding a solution. Sorry, I have not had time to write up a more detailed guide, yet. I will try adding this here once I find the time. Good you have access to your ERG again.

In general, I think this is a problem only of the node UI and could probably be fixed without too much effort. Something with the sync of the change address goes wrong when sending ERG.

---

### Post #11 — @kushti (2021-09-30)

Did you guys used some older version than 4.0.13 initially and then upgraded maybe ?

---

### Post #12 — @Uberlord (2021-09-30)

I was using 4.0.10 before and already had the problem with the unrecognized change address on this version. I then tried upgrading to 4.0.13 but it didn’t help either.

One thing coming to mind but not sure how relevant it is: I sometimes switch Java versions during development and it could be that I was running the initial node on Java 8, then eventually switching to Java 13 and 16 (all openjdk).

---

### Post #13 — @Feoraelan (2021-10-01)

I did the transaction with the 4.0.7 version. I tried the latest release but like Uberlord, it didn’t help :\
