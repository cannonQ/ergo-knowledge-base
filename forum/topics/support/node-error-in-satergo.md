---
title: Node error in Satergo
description: 'ErgoForum discussion: Node error in Satergo'
tags:
- addresses
- ergoforum
- ergoscript-context
- full-node
- satergo
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/node-error-in-satergo/4437
created: '2023-08-12'
last_activity: '2023-08-14'
posts_count: 3
views: 323
likes: 2
glossary_hits:
- Addresses
- ErgoScript context
- Full node
- Satergo
---

# Node error in Satergo

> **Forum thread:** [https://ergoforum.org/t/node-error-in-satergo/4437](https://ergoforum.org/t/node-error-in-satergo/4437)
> **Category:** Support | **Created:** 2023-08-12 | **Posts:** 3 | **Views:** 323

**Related concepts:** Addresses, ErgoScript context, Full node, Satergo

---

### Post #1 — @Yikes (2023-08-12)

Hi, just set up a node with Satergo a few days ago.  
I added port forwarding on port 9030 and 9053 as well as adding my public IP to settings in the wallet. But after rebooting the node I’m getting this error message:

ERROR [ctor.default-dispatcher-4] s.c.n.NetworkController - Declared address validation failed:  
/My nodes public IP:9030 not match any of the listening address: Set(/127.0.0.1:9030, /My nodes local IP:9030, /Some other IP:9030)

(I obviously replaced my IP’s above with text)

Does anyone know what this means? It almost looks like it doesn’t find my private node under my public IP?

I let it run for a day but it still shows the error, as well as showing unreachable on [ergonodes.com](http://ergonodes.com).

---

### Post #2 — @Yikes (2023-08-13)

Figured it out in the end. I have 2 routers, my ISP and another. I thought I had set my ISP router to bridge mode but it turns out I hadn’t done that so it had a firewall that blocked the 9030 and 9053 ports.

---

### Post #3 — @Grayman (2023-08-14)

Thank you for reporting back.  
Well done with the self service!
