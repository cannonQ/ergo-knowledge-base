---
title: REST API doesn't work with scorex configuration at 4.0.12 version
description: 'ErgoForum discussion: REST API doesn''t work with scorex configuration
  at 4.0.12 version'
tags:
- addresses
- ergoforum
- ergoscript
- full-node
- scorex
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/rest-api-doesnt-work-with-scorex-configuration-at-4-0-12-version/1981
created: '2021-07-20'
last_activity: '2021-07-20'
posts_count: 1
views: 435
likes: 0
glossary_hits:
- Addresses
- ErgoScript
- Full node
- Scorex
---

# REST API doesn't work with scorex configuration at 4.0.12 version

> **Forum thread:** [https://ergoforum.org/t/rest-api-doesnt-work-with-scorex-configuration-at-4-0-12-version/1981](https://ergoforum.org/t/rest-api-doesnt-work-with-scorex-configuration-at-4-0-12-version/1981)
> **Category:** Support | **Created:** 2021-07-20 | **Posts:** 1 | **Views:** 435

**Related concepts:** Addresses, ErgoScript, Full node, Scorex

---

### Post #1 — @lurang (2021-07-20)

I was runnig ergo node with ergo.json config file below and rest api was enabled at 4.0.11.  
After I upgrade ergo node 4.0.12, there is no established api address.

```ergoscript
{ 
    "ergo": {
        "directory": "/my/ergo/directory"
    },
    "scorex": {
        "network": {
            "bindAddress": "0.0.0.0:4445"
        },
        "restApi": {
            "bindAddress": "0.0.0.0:3000"
        }
    }
}
```

[github.com/ergoplatform/ergo](https://github.com/ergoplatform/ergo/issues/1399)

#### [REST API doesn't work with scorex configuration at 4.0.12 version](https://github.com/ergoplatform/ergo/issues/1399)

opened 12:07AM - 29 Jun 21 UTC

[![0stein](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/7072dffc49b71b1fbb2bc9e482998cb48dda1452.png)
0stein](https://github.com/0stein)

I was runnig ergo node with ergo.json config file below and rest api was enabled… at 4.0.11.
After I upgrade ergo node 4.0.12, there is no established api address.
`
{
"ergo": {
"directory": "/my/ergo/directory"
},
"scorex": {
"network": {
"bindAddress": "0.0.0.0:4445"
}
"restApi": {
"bindAddress": "0.0.0.0:3000"
}
}
}
`
4.0.11 version
![image](https://user-images.githubusercontent.com/69712107/123718146-5fa30280-d8b9-11eb-96f1-5e6a14e37778.png)
4.0.12 version
![image](https://user-images.githubusercontent.com/69712107/123718171-70ec0f00-d8b9-11eb-91b4-6fcec7654918.png)
