---
title: Wallet stuck on synchronization?
description: 'ErgoForum discussion: Wallet stuck on synchronization?'
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
source_url: https://ergoforum.org/t/wallet-stuck-on-synchronization/1236
created: '2021-05-17'
last_activity: '2023-10-15'
posts_count: 19
views: 4408
likes: 22
glossary_hits:
- Addresses
- ErgoScript context
- Full node
- Scorex
---

# Wallet stuck on synchronization?

> **Forum thread:** [https://ergoforum.org/t/wallet-stuck-on-synchronization/1236](https://ergoforum.org/t/wallet-stuck-on-synchronization/1236)
> **Category:** Support | **Created:** 2021-05-17 | **Posts:** 19 | **Views:** 4408

**Related concepts:** Addresses, ErgoScript context, Full node, Scorex

---

### Post #1 — @Captain_Crazy (2021-05-17)

Hello!

I’ve been mining for some time now and after a power outage I restarted my node but it seems like the wallet is “stuck” on active synchronization…

I have received 2 coins from mining which isn’t showing in my wallet.

Any advice on how to fix this or advice on how to sync the wallet?

Thanks!

---

### Post #2 — @peternord71 (2021-05-18)

I have the same problem. 8 days with Active synchronization

---

### Post #3 — @Captain_Crazy (2021-05-18)

8 days ?! ![:astonished:](https://emoji.discourse-cdn.com/twitter/astonished.png?v=9 ":astonished:")

Wow I really hope that we can get support on this issue, I have decided to rather mine to a new wallet but I still have some ergo that’s missing…

---

### Post #4 — @Coinage_Diggers (2021-05-18)

Same here! Over 3 days with Active synchronization. Only node was synchonize but not wallet. When we can get support on this issue?!

---

### Post #5 — @peternord71 (2021-05-18)

I set up the node and it was synchronized. I got a wallet address with swagger. But I think I forgot to sync the wallet. Then I fiddled with settings on gpus etc. When I starten mining I started the node and the miner but i did not start the API. I mined for a few weeks when I thought I should check the wallet. When I started The API The wallet balance was zero and both node and wallet says active synchronization and have done so the last week. When I click on the wallet address link it shows the right amount I have been mining.

Is my mistake that I have not run the API while mining?

Will the node and wallet synchronize after a few weeks or have I done something wrong?

---

### Post #6 — @Freeman (2021-05-19)

[![изображение_2021-05-19_064949](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/c55a2e8608f4b7e7548f8b491c064ff7ff595005_2_690x388.png)

изображение\_2021-05-19\_064949988×557 31.1 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/c55a2e8608f4b7e7548f8b491c064ff7ff595005.png "изображение_2021-05-19_064949")

  
Hi! I have already reinstalled the wallet 3 times, the node is syncing, the wallet is not syncing.

---

### Post #7 — @Captain_Crazy (2021-05-19)

So I have sent a mail to the official ergo platform… no reply…

I then tried the Ergo Platform on telegram but that community seems to be nothing short of cancer.

I then joined an Ergo mining group on telegram and the consensus there was to cut my losses and mine directly to a Yoroi wallet instead.

---

### Post #8 — @scalahub (2021-05-19)

Discord is the right place to ask such questions.

---

### Post #9 — @kushti (2021-05-19)

In this case node is not synced also, height is not corresponding to the current best height in the network.

To understand what’s going on, please provide following data:

* how do you run the node (jar/docker, OS)
* config
* is anything wrong in the logs? “cat ergo.log | grep ERR”

---

### Post #10 — @Freeman (2021-05-20)

The problem is solved!

1. Install the wallet, run it with the ergo.conf configuration file, and wait for the node to sync.  
   java -jar ergo-.jar --mainnet -c ergo.conf

> ergo {  
> directory = “c:/ergo”  
> node {  
> mining = false  
> }  
> wallet.secretStorage.secretDir = “c:/ergo”  
> }

2. Copy the api key to swagger, close PowerShell, and edit ergo.conf

> ergo {  
> directory = “c:/ergo”  
> node {  
> mining = false  
> }  
> wallet.secretStorage.secretDir = “c:/ergo”  
> }
>
> scorex {  
> restApi {  
> # Hex-encoded Blake2b256 hash of an API key.  
> # Should be 64-chars long Base16 string.  
> # below is the hash of the string ‘hello’  
> # replace with your actual hash  
> apiKeyHash = “324dcf027dd4a30a932c441f365a25e86b173defa4b8e58948253471b81b72cf”  
> }  
> }

3. Launch the wallet, create a wallet, and wait for the synchronization to complete.

p. s.  
Create a wallet only after syncing with the node.  
With this configuration, the wallet does not work:

> ergo {  
> directory = “c:/ergo”  
> node {  
> mining = false  
> }  
> wallet.secretStorage.secretDir = “d:/ergo”  
> }

---

### Post #11 — @Captain_Crazy (2021-05-20)

Does this method restore wallet with missing coins?

---

### Post #12 — @peternord71 (2021-05-20)

I realized that my node was not ever synced. Node syncing was stuck at “best block” and never went to “height count”. Huge ergo.txt file 27Gb in ergo folder. Started a new sync yesterday evening and hoping it is synced when I am home from work today. Then I can test freemans options.

---

### Post #13 — @Freeman (2021-05-20)

![](https://avatars.discourse-cdn.com/v4/letter/c/dbc845/48.png) Captain\_Crazy:

> Does this method restore wallet with missing coins?

Yes, I believe so.

1. Install the wallet and sync the node.
2. Close the wallet (Stop PowerShell) and enter the api key in the configuration file.
3. Launch the wallet and wait for the wallet to sync.

Good luck

---

### Post #14 — @peternord71 (2021-05-20)

Solved it ![:grinning:](https://emoji.discourse-cdn.com/twitter/grinning.png?v=9 ":grinning:").

1. Started a new session yesterday (created a new folder not to trash anything in the old one) and restored wallet. New address, zero balance.
2. When the node was synced (about 24h) I stopped it. Edited conf-file, removed APIkey section. Copied old wallet folder (with the ERG in its address) to the new node folder. This is probably unnecessary.
3. Restarted node and waited it to sync again (a few minuters).
4. Opened swagger ui and made a APIkey with the same secret as in my first wallet.
5. Stopped the node. Edited The conf file with the apikey.
6. Started node. Set apikey. Waited for wallet to sync (about an hour). When synced, all of the ERG was there.  
   Good luck

The reason for my slightly different approach to Freemans was that I already restored the wallet when I started the sync of the node and did not felt like to start over. That’s why I copied the old wallet folder to the new .ergo folder

---

### Post #15 — @Captain_Crazy (2021-05-21)

[@Freeman](/u/freeman) [@peternord71](/u/peternord71)

Thank you so much for all the help and advice, I will try your methods later today and report back.

Thanks again! ![:clap:](https://emoji.discourse-cdn.com/twitter/clap.png?v=9 ":clap:") ![:clap:](https://emoji.discourse-cdn.com/twitter/clap.png?v=9 ":clap:") ![:clap:](https://emoji.discourse-cdn.com/twitter/clap.png?v=9 ":clap:")

---

### Post #16 — @kushti (2021-05-31)

It is hard to give any advice when not much info given. Please specify when reporting:

* what are you running (jar or docker image)
* how (launch command)
* config

then usually it is clear how a problem could be solved

---

### Post #17 — @Captain_Crazy (2021-06-01)

Apologies for the late response. [@Freeman](/u/freeman) resolved this issue. Thanks

---

### Post #18 — @mcfishblesk (2021-08-20)

Hi, i had similar problem. I followed “absolete” insctruction, which are on main page. I was able to manage the settings somehow and I went through the swagger to set up the validation node and I skip waiting on sync node and went straigt to the wallet set up, because someone wanted mining so badly ![:smiley:](https://emoji.discourse-cdn.com/twitter/smiley.png?v=10 ":smiley:") . So at the beginning both wallet and node was syncing and worker mined and there was a finally first payout and nothing came to the wallet. Ofcourse I manytimes cancelled syncing during minig and i started to ask myself WTF. So i came here and started to prepare myself to do some repairs…, BUT! During the investigating I let the node and wallet syncing at the same time and now finally the end of syncing is sucssesfully done and with this came every payouts aswell. Sorry for my english and be patient! ![:smiley:](https://emoji.discourse-cdn.com/twitter/smiley.png?v=10 ":smiley:")

---

### Post #19 — @Ccgarant (2023-10-15)

I restored the wrong wallet, here’s what worked for me:

* cd .ergo
* rm -rf wallet
* go back to ergo node interface, refresh, set API key
* you should see blank “Initialize Wallet” again
