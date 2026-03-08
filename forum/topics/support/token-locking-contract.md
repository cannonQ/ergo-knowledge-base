---
title: Token locking contract
description: 'ErgoForum discussion: Token locking contract'
tags:
- ergoforum
- ergoscript
- ergoscript-context
- native-tokens
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/token-locking-contract/3021
created: '2021-11-27'
last_activity: '2021-12-01'
posts_count: 6
views: 376
likes: 3
glossary_hits:
- ErgoScript
- ErgoScript context
- Native tokens
---

# Token locking contract

> **Forum thread:** [https://ergoforum.org/t/token-locking-contract/3021](https://ergoforum.org/t/token-locking-contract/3021)
> **Category:** Support | **Created:** 2021-11-27 | **Posts:** 6 | **Views:** 376

**Related concepts:** ErgoScript, ErgoScript context, Native tokens

---

### Post #1 — @JOFLITO (2021-11-27)

Hello guys, I am José from $COMET (memecoin on ergo <https://thecomettoken.com>) we are trying to give holders some peace of mind by locking our tokens and unlocking them over time, I came up with a contract starting from Luivatra’s self replicating contract ([ergoscript-by-example/selfReplicatingTokenSale.md at main · ergoplatform/ergoscript-by-example · GitHub](https://github.com/ergoplatform/ergoscript-by-example/blob/main/selfReplicatingTokenSale.md))

I think my code is working as intended, but since it is my first ever contact with ergoscript and it might hold some value at some point I would love if you could take a look at it and hopefully break it before a hacker does. Here is the code [Scastie - An interactive playground for Scala.](https://scastie.scala-lang.org/7KDlDXynSh6UxUo2WVM9iQ)

---

### Post #2 — @Ergosmergo (2021-11-29)

I have never really understood meme coins. I could have made so much money investing in them like DOGE/SHIB the thing is I could never bring myself to buy a coin that is created as a joke.

---

### Post #3 — @JOFLITO (2021-11-29)

I understand 100% in fact $COMET was born while talking about memecoins on the trading chat, SHIBA was booming and we were tanking like crazy. We started talking how memecoins are essentially ponzis, but bring people to the ecosystem that will eventually support real projects. My friend even said that as memeCoins they weren’t even really that good and he could create a better one to bring attention to Ergo, so here we are making locking contracts and trying to find a way to make a refundable ICO.  
I completely understand your point of view, and really appreciate you taking the time to leave a comment.

---

### Post #4 — @Ergosmergo (2021-11-30)

I think people like meme coins because they are cheap and have a low entry level. And I think traders like meme coins because they are so low in price and traders are often offered high leverage trades often on these types of tokens at exchanges. COMET sounds like a very interesting project and I wish you the best of luck on the creation of your scripts. By no way am I bashing meme coins or another persons investments but rather giving my thoughts on meme coins because they are clearly in demand but when it comes to meme coins there is a lot of pumps and dumps will there be any mechanisms in place to stop any insiders selling early. Locking mechanism sounds good how does it work?

---

### Post #5 — @JOFLITO (2021-11-30)

please bash meme coins, that’s why we did this one. We were too salty seeing dog coins pumping and Erg dumping lol.

The token locking contract is a real simple contract that has an “IF” to check if the withdrawal of the funds is valid. It pretty much says, if it has passed X amount of time you can withdraw a maximum of Y tokens.

We are trying to avoid pumps and dumps as much as we can. We intend to make a refundable ICO, you buy $COMET with $ERG, and if you didn’t like your coins or maybe they dumped, you can send back your $COMET and you get your initial investment ( -tx fees) back. In order to have this erg available for refund we won’t be touching them, so our “payment” as founders are the tokens locked in the locking contract.

If anybody is interested on taking part of the project I would go the memecreator way (we pay 5k $COMET per meme) or the ICO, buying $COMET in a dex is absolutely nuts and not advisable at all, but who am I to tell you do what to do with your money

---

### Post #6 — @Ergosmergo (2021-12-01)

I will try to make you a funny meme sometime please link me to your Discord or Telegram server. There is a guy I subscribe to on YouTube constantly talking about meme/dog coins lately its ramped up his name is Mineyour.biz hes quite a good You Tuber and quite popular in the mining space. Every time without doubt when he puts another a video about a dog coin I am there to say “Not another pointless meme coin”. He always reply’s very quickly saying “The pointless meme coins will continue to continue until morale improves!”. Half the time I see these creators promoting these dodgy coins for there own gain wouldn’t the morale surely improve if these creators were not promoting those coins to start with.
