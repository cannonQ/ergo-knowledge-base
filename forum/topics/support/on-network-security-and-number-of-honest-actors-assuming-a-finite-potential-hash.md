---
title: On Network Security and Number of Honest Actors Assuming a Finite Potential
  Hashrate
description: 'ErgoForum discussion: On Network Security and Number of Honest Actors
  Assuming a Finite Potential Hashrate'
tags:
- addresses
- autolykos
- collateral
- eip
- ergoforum
- full-node
- native-tokens
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/on-network-security-and-number-of-honest-actors-assuming-a-finite-potential-hashrate/4014
created: '2022-10-07'
last_activity: '2022-10-13'
posts_count: 5
views: 407
likes: 4
glossary_hits:
- Addresses
- Autolykos
- Collateral
- EIP
- Full node
- Native tokens
- Transaction
---

# On Network Security and Number of Honest Actors Assuming a Finite Potential Hashrate

> **Forum thread:** [https://ergoforum.org/t/on-network-security-and-number-of-honest-actors-assuming-a-finite-potential-hashrate/4014](https://ergoforum.org/t/on-network-security-and-number-of-honest-actors-assuming-a-finite-potential-hashrate/4014)
> **Category:** Support | **Created:** 2022-10-07 | **Posts:** 5 | **Views:** 407

**Related concepts:** Addresses, Autolykos, Collateral, EIP, Full node, Native tokens, Transaction

---

### Post #1 — @WilfordGrimley (2022-10-07)

I have a question that will help me with my research regarding EIP 38 for the Hackathon.

Lets assume network A is secured by X honest actors with Y collective hashrate.

Let’s assume network B is secured by 2X honest actors and Y/2 collective hashrate, etc for networks C, D…

Is the network at an increasingly higher risk to a 51% attack the more actors are involved assuming honest actors and finite hashrate between networks A…D?

I recognise that as we get further down the chain, B,C,D that the threat of sybil attack increases, my concern is of a 51% attack:

Sybil threat aside does a pool splitting itself into two (or more pools) with the same total hashrate provide weaker security to the network?

If the answer is yes, then the fork solution is preferable for EIP 38. If the answer is no, and the network is at no greater threat of a 51% attack (or 25/33% as it may be) then the solution that does not require forking may be preferable.

---

### Post #2 — @WilfordGrimley (2022-10-07)

I found an answer in the [Bypassing Non-Outsourceable Proof-of-Work Schemes Using Collateralized Smart Contracts](https://storage.googleapis.com/ergo-cms-media/2020_044_a8548e2a30/2020_044_a8548e2a30.pdf) paper.

> The primary issue with pools is that they increase the potential of transaction  
> censorship and 51 percent attacks. One way to address this issue is to disallow  
> pools entirely. This is what non-outsourceable puzzles aim to achieve, and Ergo  
> is the first practical implementation of such puzzles [[5](https://storage.googleapis.com/ergo-cms-media/docs/whitepaper.pdf)].

But I think it answers the opposite and obvious: That allowing pooled mining increases the risk that any of the pools themselves should grow to represent 51% of the network.  
The specific issue I am worries about is if pools should systematically split their hash power into smaller pools, is the network less secure?

Rereading the above paper, the Autolykos 2 paper, and the original Bitcoin paper, I am realising that the scratch off nature of PoW means that the **actual total network hash is the larger risk for 51% attacks.**

The true risk to enabling miners to split into smaller subpools with their own puzzles to solve, while maintaining their original central pool operators, is the threat of Sybil attacks. If central pool operators are willing to host such systems, the sybil attack risk is lower than in a fully decentralized solution as they will *hopefully* be transparent about the nodes that they control for the sake of transparency to their miners.

Systems B…D…etc. as defined above are also at greater risk of having their votes censored than if they where in System A, as while the networks themselves are just as secure, the odds of actors in systems B…D… mining a block and having their vote counted decrease. The rewards miners see in these b-d networks can be smoothed using subpooling methods within smartpools, but their decrease in vote power over the network can not be retrieved.

This leads me to conclude for now that the solution for EIP 38 that requires a fork is preferable. While the network itself is no less secure in a fork avoiding scheme, the decreased likelihood that pools in networks with a greater number of smaller hashrate actors will mine a block (and be able to vote at all during the voting period) outweighs the benefits of leaving the network unforked.

---

### Post #3 — @TypoDaPsycho (2022-10-11)

![](https://avatars.discourse-cdn.com/v4/letter/w/779978/48.png) WilfordGrimley:

> Lets assume network A is secured by X honest actors with Y collective hashrate.
>
> Let’s assume network B is secured by 2X honest actors and Y/2 collective hashrate, etc for networks C, D…
>
> Is the network at an increasingly higher risk to a 51% attack the more actors are involved assuming honest actors and finite hashrate between networks A…D?

No actually the opposite, if I’m understanding the question correctly.

More actors = less risk of 51% attack. That’s why Ethereum has never been hit with a 51% attack, but Eth Classic has multiple times.

I would say a pool splitting itself into 2 or more would help protect against 51%, but in reality, this would require each part of pool to be running its own node for big effect.

I often see miners post pics of their rigs with captions like-“helping increase network security ![:sunglasses:](https://emoji.discourse-cdn.com/twitter/sunglasses.png?v=12 ":sunglasses:")”. But then, occasionally, there’s the person who points out that if they’re mining to a pool (not their own personal node) they are NOT actually helping secure the network like they think they are. And they are right.

---

### Post #4 — @USCMigs (2022-10-13)

Agree full-heartedly on this one… More hash rate regardless of the source increases security as long as the hash rate comes from a variety of sources. From a game theory perspective, you’d approach that all hash rate is coming from rational actors and as long as there is a fair distribution of participants, then that is the best outcome that you can shoot for. Defining the behavior of an actor gets down a subjective rabbit hole that is hard to define and ultimately has more variables to factor in making the problem unattainable to model. Hashrate for PoW chains is typical directly related to the profitability and emissions of a project and as mentioned, Ethereum never had a problem, because the competition to earn was so great that it was highly unlikely/improbable that someone could attain enough hash rate to 51% attack the chain.

I personally feel that miner considerations seem to be a major “theme” since the Merge and the system constraints that feed into emissions, block times, and incentives should be aligned with stability and growing Ergo and not focus on attracting miners. Building a strong ecosystem that is robust, vibrant, and welcoming to new participants drives usage, which drives token usage, which drives prices of the coin up and ultimately feeds into miner profitability that secures the network. I think a lot of people are looking at the problem backwards and tend to feel that if there is a strong enough miner presence that this will cause a price increase and grow the project, but that opposite to how it would work.

I know I digress from the original question, but as long as hashrate is distributed then in theory it makes it harder for generating that 51% attack. Much smaller PoW projects have a tough time with distributing hash rate as usually 1-2 pools become the dominate ones… Not to long ago on Nanopool this was an issue for Ergo. Utilizing smart contracts like something on GetBlok is a unique twist, but they are still struggling to establish themselves as one of the larger pools in Ergo.

---

### Post #5 — @Grayman (2022-10-13)

![](https://yyz2.discourse-cdn.com/flex030/user_avatar/www.ergoforum.org/uscmigs/48/1422_2.png) USCMigs:

> Building a strong ecosystem that is robust, vibrant, and welcoming to new participants drives usage, which drives token usage, which drives prices of the coin up and ultimately feeds into miner profitability that secures the network. I think a lot of people are looking at the problem backwards and tend to feel that if there is a strong enough miner presence that this will cause a price increase and grow the project, but that opposite to how it would work.

I agree. Usage should be the goal.

Folks are evidently satisfied to specmine at 50 TH, the block times are stable, the network is secure and stable.

The price is still falling, and to me that indicates that the ones who claimed they would turn off the rigs and buy ERG with the savings are unworthy of any further attention.

Now is the time to fill bags and focus on what is coming from the dev side. We miners have had our say.

ETA: I also do not intend to derail OP’s discussion, nor am I against developing EIP 38.

I just think that when it comes to protocol security assurance, a conservative approach should be applied. If your concern is that small miners are disenfranchised by pooling and that this leads to dominance by certain pools in voting, then perhaps we should consider a governance solution that is separate from hashrate.

Maybe it should work like this:

Anyone can propose changes to the platform in the form of a provisional EIP (pEIP), here in this forum.

After a period of discussion, the terms of such an EIP could be put to a vote among the users of the blockchain. Users that wish to spend their governance tokes on the pEIP may do so, and vote for or against the pEIP.

If the pEIP reaches a certain threshold of upvotes, then the concerned parties should develop an EIP, work with the core devs to implement it, and then the miners vote on implementation as always.

The governance tokens would get distributed via a pseudo-randomized weighting of the volume of transactions between various wallets, with some anti-spam tactics. I also think such governance tokens should expire after a time.

ETA 2: This is being discussed in another thread:[EIP: Democratic Governance - Users, Devs & Miners](https://www.ergoforum.org/t/eip-democratic-governance-users-devs-miners/4019/1)
