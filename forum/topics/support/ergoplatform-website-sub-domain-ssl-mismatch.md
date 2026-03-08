---
title: Ergoplatform website sub domain SSL MISMATCH
description: 'ErgoForum discussion: Ergoplatform website sub domain SSL MISMATCH'
tags:
- addresses
- box
- ergo-foundation
- ergoforum
- ergoscript
- getblok-plasma
- layer-scaling
- mev
- sigma-chains
- storage-rent
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/ergoplatform-website-sub-domain-ssl-mismatch/3306
created: '2022-01-27'
last_activity: '2022-01-31'
posts_count: 8
views: 442
likes: 10
glossary_hits:
- Addresses
- Box
- Ergo Foundation
- ErgoScript
- GetBlok Plasma
- Layer scaling
- MEV
- Sigma Chains
- Storage rent
- Transaction
---

# Ergoplatform website sub domain SSL MISMATCH

> **Forum thread:** [https://ergoforum.org/t/ergoplatform-website-sub-domain-ssl-mismatch/3306](https://ergoforum.org/t/ergoplatform-website-sub-domain-ssl-mismatch/3306)
> **Category:** Support | **Created:** 2022-01-27 | **Posts:** 8 | **Views:** 442

**Related concepts:** Addresses, Box, Ergo Foundation, ErgoScript, GetBlok Plasma, Layer scaling, MEV, Sigma Chains, Storage rent, Transaction

---

### Post #1 — @Ergosmergo (2022-01-27)

Just a heads up on the SSL certs for sub-domain [docs.ergoplatform.org](http://docs.ergoplatform.org) need to be reinstalled the main domain itself is secured by SSL but the subdomain isn’t

[![Screenshot from 2022-01-27 12-43-45](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/a/a348c9342623d1e0f19ed1018b7c011e8318b888_2_690x388.png)

Screenshot from 2022-01-27 12-43-451920×1080 307 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/a/a348c9342623d1e0f19ed1018b7c011e8318b888.png "Screenshot from 2022-01-27 12-43-45")

The overall score in SSLabs is low because of the certificates being mismatched and untrusted under the subdomain. The worry is that any user reading Docs is essentially browsing without SSL. The SSL certs are issued by Cloudflare I think Cloudflare Full SSL will be best for the website with some workers that will force some rules so that no downgrade attacks can happen in the Ergoplatform website and stop any XSS, Clickjacking attacks by using hardened HTTP headers.

[![image](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/c/c35e193c0d09fa6fde5e0034a976c61b5649ff65_2_690x478.png)

image1083×751 82 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/c/c35e193c0d09fa6fde5e0034a976c61b5649ff65.png "image")

The website also accepts TLS 1.0 TLS 1.1 by using only modern TLS like TLS 1.2 TLS 1.3 will clear up these errors and give a perfect SSL score in SSLabs.

Good job on the website guys and I would love to put some ideas forwards to you based on some of the past web design and security experience.

Here is an example of some [HTTP headers](https://owasp.org/www-project-secure-headers/) we should add. Secure HTTP headers in the website will stop any internal applications from being exposed.

[![image](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/e/e593c3ab6c04d668fdb49f3ad86ddaa621bf66f3_2_690x318.png)

image1340×618 59.7 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/e/e593c3ab6c04d668fdb49f3ad86ddaa621bf66f3.png "image")

---

### Post #2 — @glasgowm (2022-01-27)

new address is

<https://docs.ergoplatform.com/>

---

### Post #3 — @bigoogawoogla (2022-01-27)

I’ve wondered, so the ergo websites are hosted on centralized website servers, right? Including Dapps? Will there be a future in which Dapps are hosted on ergo domains? Or will headless Dapps make this not a potential risk for deplatforming?

---

### Post #5 — @Ergosmergo (2022-01-27)

The Ergo websites are hosted on a typical centralized website server and act as an information post. The dApps are Decentralized apps that work from a Smart Contract on the Ergo blockchain coded in Ergo Script some dApps could have a front-end that would be hosted on a centralized server. I don’t think de-platforming would cause a threat to Ergo if any censorship Ergo would fight it. Data backup is essential to running a website and I would imagine Ergo foundation to be taking many backups. The Ergo website and information on it are in safe hands. I do think a mirror of websites on TOR could fight the problem if anyone was ever to boycott the website.

---

### Post #6 — @bigoogawoogla (2022-01-28)

Oh man having tor access to ergo would be great. Even twitter can be accessed on tor. Would that mean the ergo foundation hosting their own tor server?

Do websites for Dapps essentially just act as a GUI or API for ergo smart contracts? So if a website were to be taken down the essential information is still recorded on chain, making it easy for a new interface to connect to the smart contracts that are the Dapp?

I read somewhere that many dexes are built custom fit to web hosting services (azure, awz, etc). The “Dapp” isn’t really a **decentralized** app, it’s just a normal website that integrates blockchain for its payment channels. In that case if the web hosting service sanctions the Dapp, the Dapp would disappear, and would have to be completely redesigned around a new web hosting service. Could this be true? Do you understand what I’m asking?

Also, how does that work with off chain or L2 solutions? Does L2 work outside the blockchain and just use the blockchain as a book keeper for the most important information? And offchain, does it operate the same way? For example the lightening network. I don’t understand the difference between the lightening network and a central bank network hosting a decentralized currency.

---

### Post #7 — @Ergosmergo (2022-01-29)

The websites themselves are just normal websites accept from they can connect directly with the dApp. Just acting as a graphical interface storing the website directly on-chain would cost too much in storage rent and there wouldn’t be a practical way of accessing DNS settings that are needed for the domain name system. If the website was to be taken down for example there would be no way to interact with the blockchain from the front end but the data would still be on-chain. The website is essentially a frontend user interface and the smart contract code when it runs the smart contract (dApp) then stores the value on the blockchain like open APIs. The backend code is a decentralized peer-to-peer network the front end is not. dApps are often built on top of a base layer of Ergo but the front end of the applications is centralized. Having tor access to the front-end would add an extra layer of security in the event any dApp fron’t end went down as users would still have a tool to interact with the blockchain via the smart contract.

A lot of popular dApps will often keep backup and prepare for any doomsday event a lot of these operators of dApps often have good business logic but it is certainly a worry that a web host could potentially close the webserver off hosting the front end whenever they feel like it. To get past this operators will store the data over multiple centralized servers as to not rely on one but this can become costly.

Many Dex will use a centralized server for their front end and this will often come with some of the challenges of running a centralized front end. With L2 they use Polygon as a second layer so, for example, NFT would be stored on Polygon chain rather than Ethereum the advantage is small fees in L2 chain by storing data on another chain wrapped means the NFT will inherit the good and bad aspects of that chain.

A good example of a website front end becoming inaccessible is [FishBank.io](http://FishBank.io) it was a blockchain-based game on Ethereum. I minted a couple of these Fish when the game was becoming popular. The operators then pulled the rug leaving an unusable front end. Whereas if I was to add in my wallet address into OpenSeas I can still access the fish I bought buy or sell I am just not able to play the game making the NFT assets useless.

This video gives a good explanation of how dApps work using Ethereum as an example and how they can scale with L2 solutions.

[![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/f/fdffb24815b286be38434c48601e95c834be62a6.jpeg "What is a dApp? Decentralized Application on the Blockchain")](https://www.youtube.com/watch?v=F50OrwV6Uk8)

[![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/0/01a6378ce02722f904dad1be29a94696649d74c6.jpeg "Ethereum LAYER 2 SCALING Explained (Rollups, Plasma, Channels, Sidechains)")](https://www.youtube.com/watch?v=BgCgauWVTs0)

---

### Post #8 — @bigoogawoogla (2022-01-29)

Is gas on ethereum different than transaction fees on ergo? My understanding is that ethereum uses gas fees to allow a market to form around transactions, letting people pay more to miners to get their transaction settled. Is this different on ergo?

Why would it cost too much in storage rent to store the website directly on-chain? My understanding was that storage rent is a fixed cost per inactive wallet, not related to the size of data stored on a wallet. So even a large data size website would only have to pay 1 storage rent fee, right?

So if a website front end for a Dapp were to be taken down, anyone could create a new website front end and re-launch the Dapp?

Thank you for your knowledge.

---

### Post #9 — @Ergosmergo (2022-01-31)

Gas on Ethereum is different from Ergo the fees are based on per tx or execution of smart contracts cost a fixed fee of 0.0011 ERG. In Ethereum, miners are able to choose what transactions they include based on Miner extractable value (MEV). Blockchain developers have started to create programs and apps that can programmatically reorg chains by targeting blocks that have some empty transactions this destabilizes consensus.

![](https://ergoplatform.org/favicon.svg)
[ergoplatform.org](https://ergoplatform.org/en/blog/2021_03_26_eth_vs_erg/)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/9/984f75ae8e9dcbcfdf7998f5122a313cd237327a_2_690x330.png)

### [Ergo seeks to fix what Ethereum can’t… Here’s how](https://ergoplatform.org/en/blog/2021_03_26_eth_vs_erg/)

It is no secret that the …

I think that would be correct assuming you could put the front-end on the chain. A website can be many GB and won’t be able to fit all the code in a single block. Adding code like this could cost a lot of Storage-oriented load, Computational load, Network load. Storage fees. Storage rent is a scheduled fee that is based on the continuation of each UTXO created in the blockchain.

Front end of dApp is for render and the back end for data.

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/7/76e1efbaf0bfa5eccf046eba5cefb5cad95f9653.png)
[Quora](https://www.quora.com/Is-the-front-end-for-a-DApp-off-chain-centralized-whereas-the-back-end-for-a-DApp-is-on-chain-decentralized-sitting-on-the-blockchain)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/d/dffd0745fa38cf0ec28ed0a7fcd5b677e9820815_2_690x388.png)

### [Is the front-end for a DApp off-chain/centralized, whereas the back-end for a...](https://www.quora.com/Is-the-front-end-for-a-DApp-off-chain-centralized-whereas-the-back-end-for-a-DApp-is-on-chain-decentralized-sitting-on-the-blockchain)

Answer (1 of 2): Not really. Even large parts of the backend could be run on centralized servers. In the simplest form, the blockchain will just be used as an immutable database. But even if the central servers are compromised, the database and such...

If the front end of a dApp went down then I think anyone could relaunch the code of the smart contract but this would change the owner and make it a new contract. Every smart contract is owned by an address called as owner.

<https://www.geeksforgeeks.org/creating-a-smart-contract-that-returns-address-and-balance-of-owner-using-solidity/>

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/5/5aba942168eb30ae4122068b019df341e54b1515.png)
[Espeo Blockchain – 10 Dec 20](https://espeoblockchain.com/blog/dapp-development "12:00AM - 10 December 2020")

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/c/ca43759d2f5975219a88a046cf79fd7736a339c1_2_690x460.jpeg)

### [DApp development: An easy guide for front-end developers](https://espeoblockchain.com/blog/dapp-development)

DApp development projects only account for a small portion of current projects. Here's a handy guide on how to implement connect a dApp to the blockchain.

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/d/dc87ba08bee9ff76a7becce269337c7c8a391838.png)
[ethereum.org](https://ethereum.org/en/developers/docs/mev/)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/6/64df7aadba254160ba0f1a17231a3df8b0c2d769_2_690x472.jpeg)

### [Miner extractable value (MEV) | ethereum.org](https://ethereum.org/en/developers/docs/mev/)

An introduction to miner extractable value (MEV)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/a70ab5d077374748901898cfcd9c7a09b8a303a9.png)
[reddit](https://www.reddit.com/r/ergonauts/comments/nrxn9f/ergo_transaction_costs/)

### [r/ergonauts - Ergo transaction costs](https://www.reddit.com/r/ergonauts/comments/nrxn9f/ergo_transaction_costs/)

31 votes and 9 comments so far on Reddit

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/a70ab5d077374748901898cfcd9c7a09b8a303a9.png)
[reddit](https://www.reddit.com/r/ergonauts/comments/p1wk3b/what_kind_of_fees_does_ergo_charge_for/)

### [r/ergonauts - What kind of fees does ergo charge for transactions](https://www.reddit.com/r/ergonauts/comments/p1wk3b/what_kind_of_fees_does_ergo_charge_for/)

16 votes and 12 comments so far on Reddit

![](https://ergoplatform.org/favicon.svg)
[ergoplatform.org](https://ergoplatform.org/en/blog/2021-07-09-cryptocurrency-fees-a-solution-to-unreasonable-state-growth/)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/e/ed78d6af47bc03c95987f16645a5fdd4e237b0f4_2_690x320.jpeg)

### [Cryptocurrency Fees: A Solution to Unreasonable State Growth](https://ergoplatform.org/en/blog/2021-07-09-cryptocurrency-fees-a-solution-to-unreasonable-state-growth/)

This article is a continuation …

Guys please correct me if I’m wrong with any of this stuff.
