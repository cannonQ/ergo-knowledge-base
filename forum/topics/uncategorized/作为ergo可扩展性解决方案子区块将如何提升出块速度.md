---
title: 作为Ergo可扩展性解决方案，子区块将如何提升出块速度？
description: 'ErgoForum discussion: 作为Ergo可扩展性解决方案，子区块将如何提升出块速度？'
tags:
- ergoforum
- uncategorized
category: forum
forum_category: Uncategorized
source: ergoforum
source_url: https://ergoforum.org/t/ergo/4556
created: '2023-11-13'
last_activity: '2023-11-13'
posts_count: 1
views: 240
likes: 1
glossary_hits: []
---

# 作为Ergo可扩展性解决方案，子区块将如何提升出块速度？

> **Forum thread:** [https://ergoforum.org/t/ergo/4556](https://ergoforum.org/t/ergo/4556)
> **Category:** Uncategorized | **Created:** 2023-11-13 | **Posts:** 1 | **Views:** 240

---

### Post #1 — @ergonautgcn (2023-11-13)

[![subblock](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/2X/2/246fdd67fff86edceb2fb7e68ad3c4819074ccf9_2_690x482.jpeg)

subblock1920×1343 226 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/2/246fdd67fff86edceb2fb7e68ad3c4819074ccf9.jpeg "subblock")

每个标准区块有128个子区块，将出块速度加快至1秒产出1个区块

1. Ergo将使用子区块（难度降低的候选区块）。例如，当子区块难度为标准区块难度的1/128时，平均每1秒可以产出1个子区块。
2. 子区块在Ergo网络中发送时，会产生新的交易ID（从前一个子区块算起），且快速进行。这将使网络能够在绝大部分算力对交易进行足够确认后最佳利用带宽，实际上，就需要目前大概20秒才能完成一笔交易的当前网络而言，该交易可被视作已完成子确认（Sub-confirm）。
3. 为了激励子区块报告，子区块可以提交到侧链上，因此，可让快捷侧链成为可能且矿工将因此获得奖励。

来源：[A Scalability Plan for Ergo](https://www.ergoforum.org/t/a-scalability-plan-for-ergo/226)

原文链接：<https://twitter.com/GreasyCex/status/1722003192215691337/photo/1>
