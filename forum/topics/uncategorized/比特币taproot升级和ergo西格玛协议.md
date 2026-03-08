---
title: 比特币Taproot升级和Ergo西格玛协议
description: 'ErgoForum discussion: 比特币Taproot升级和Ergo西格玛协议'
tags:
- ergoforum
- uncategorized
category: forum
forum_category: Uncategorized
source: ergoforum
source_url: https://ergoforum.org/t/taproot-ergo/4248
created: '2023-03-09'
last_activity: '2023-03-11'
posts_count: 3
views: 265
likes: 7
glossary_hits: []
---

# 比特币Taproot升级和Ergo西格玛协议

> **Forum thread:** [https://ergoforum.org/t/taproot-ergo/4248](https://ergoforum.org/t/taproot-ergo/4248)
> **Category:** Uncategorized | **Created:** 2023-03-09 | **Posts:** 3 | **Views:** 265

---

### Post #1 — @ergonautgcn (2023-03-09)

## 比特币Taproot升级和Ergo西格玛协议

来源：金色财经  
发布日期：2022/02/14  
<https://m.jinse.com/news/blockchain/1055325.html>

[![bnTCjoUSObNb81zYs1HQ5IhVT9JBtVOSk3B3Ge9N.png](//cdck-file-uploads-canada1.s3.dualstack.ca-central-1.amazonaws.com/flex030/uploads/ergoforum/original/2X/5/53f20d2f6d506a44ee2296f200c124788fabe153.jpeg)

bnTCjoUSObNb81zYs1HQ5IhVT9JBtVOSk3B3Ge9N.png600×338 68.3 KB](//cdck-file-uploads-canada1.s3.dualstack.ca-central-1.amazonaws.com/flex030/uploads/ergoforum/original/2X/5/53f20d2f6d506a44ee2296f200c124788fabe153.jpeg "bnTCjoUSObNb81zYs1HQ5IhVT9JBtVOSk3B3Ge9N.png")

最近比特币Taproot升级包括了许多变化，引起了广泛的讨论。Taproot升级由三个比特币改进提案（BIP）组成：Schnorr签名（BIP340）、默克尔化抽象语法树（MAST-BIP341）和Tapscript（BIP342）。通过此次升级，比特币将允许更高的可扩展性、隐私性和灵活的智能合约设计。

Ergo的设计也是基于西格玛（Sigma）协议，即众所周知的广义Schnorr证明。Ergo自启动时就有可扩展性和隐私性设计，例如类似比特币设想的NIPoPoW（工作量证明之非交互式证明）。此外，Ergo还享有扩展UTXO模型的强大功能和工作量证明的长期安全性。

BIP340带来了Schnorr签名机制，该机制自2018年以来一直在比特币开发者当中争论不休。Schnorr签名被认为具有高层级的安全性，同时保持快速的验证过程。Schnorr签名使复杂的交易看起来像常规交易，从而使各种交易难以区分。

BIP341实现了默克尔化抽象语法树（MAST），它允许在单个哈希下编译一组哈希。这种结构允许花费者选择一些条件来满足，而其他条件不会被披露。MAST允许更简单的验证过程，在不削弱安全性的情况下增加表达性和隐私性。

比特币之前的支付到脚本哈希（P2SH）设计受限于智能合约隐私。使用多重签名合约时，合约脚本在交易后显示。这将透露关于用户的信息，同时加剧了区块链的膨胀。新实现的MAST设计允许隐藏嵌入在合约中的这些额外信息。使用Schnorr证明，Taproot甚至可以隐藏MAST结构存在过的证据。

BIP342 Tapscript更新了比特币脚本，实现了前面提到的Schnorr和MAST升级。Tapscript还消除了10000字节的脚本规模和操作码数量限制，从而改进了签名哈希并启用了更具表现力的脚本。

为比特币添加BIP340和零知识证明可实现Ergo和比特币之间的互操作性，允许隐私跨链原子交换和未来可能的侧链。

虽然Ergo不是一条专门的隐私链（译注：Ergo是一条底层公链），但它的西格玛协议允许零知识隐私应用程序使用Schnorr签名提供验证。这让Layer2应用程序成为可能，例如NIPoPoW和侧链在Ergo上匿名运行。

Ergo的语言ErgoScript已经包含了为比特币设想的东西——它采用了类似的结构，但运用了不同的技术，通过实现具有UTXO和PoW元素且更具表达性的智能合约语言，Ergo旨在成为一个面向安全、复杂、可扩展、隐私性的去中心化金融应用的平台。比特币可以通过其可互操作的DeFi功能来利用Ergo的安全性。

作者：Ergo平台

原文发布日期：2021年11月17日

---

### Post #2 — @Grayman (2023-03-09)



---

### Post #3 — @bigoogawoogla (2023-03-11)

Looks like someone went through a whole lot of effort to understand Ergo. I wonder if this is the start of a “red wave” of Chinese coming in. Wouldn’t be surprised, given that mining may be the only way for them to get crypto.

Nice song.
