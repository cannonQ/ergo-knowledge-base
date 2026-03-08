---
title: Bad API key message
description: 'ErgoForum discussion: Bad API key message'
tags:
- ergoforum
- ergoscript
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/bad-api-key-message/622
created: '2021-02-05'
last_activity: '2021-03-26'
posts_count: 6
views: 2476
likes: 1
glossary_hits:
- ErgoScript
- Full node
---

# Bad API key message

> **Forum thread:** [https://ergoforum.org/t/bad-api-key-message/622](https://ergoforum.org/t/bad-api-key-message/622)
> **Category:** Support | **Created:** 2021-02-05 | **Posts:** 6 | **Views:** 2476

**Related concepts:** ErgoScript, Full node

---

### Post #1 — @mar75 (2021-02-05)

Hi,  
After passes steps to set up node and trying to “Set APi key” I have screen message - Bad APi key.  
i’m typing my passwords, config file is as on template - see screens.  
Please help  
M.

[![ergo2](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/99f2c030ebeb429e759cfbcdac3a32f6032cb3d7_2_690x388.jpeg)

ergo22560×1440 82 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/99f2c030ebeb429e759cfbcdac3a32f6032cb3d7.jpeg "ergo2")

---

### Post #2 — @mar75 (2021-02-05)

[![ergo1](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/a3802227ef26ddca32f7547accfca9da02ab4e74_2_690x388.jpeg)

ergo12560×1440 232 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/a3802227ef26ddca32f7547accfca9da02ab4e74.jpeg "ergo1")

---

### Post #3 — @scalahub (2021-02-06)

I’m sure you’ve already tried it but just in case… did you try without quotes?

---

### Post #4 — @kushti (2021-02-06)

Please provide first lines of the log. But I am pretty sure that this is about config file can’t be read. As there are a lot of complaints like that I guess it would make sense to fail immediately during the launch if config parsing fails, made an issue about that [Fail if config can't be parsed · Issue #1284 · ergoplatform/ergo · GitHub](https://github.com/ergoplatform/ergo/issues/1284) .

In your case, you can just remove lines with directories, I guess paths do not corresponding to Windows format. Then the node data sub-folder will be created in a folder you’re running the node launch command from.

---

### Post #5 — @crazzziecanuck (2021-03-25)

I’m experiencing the same.

Host system is running centOS 8.3. Tried multiple keys, with or without quotes.

```ergoscript
19:19:11.536 INFO  [main] org.ergoplatform.ErgoApp - Running with args: Args(Some(/opt/ergo/ergo.conf),Some(MainNet))
19:20:35.872 INFO  [main] org.ergoplatform.ErgoApp - Running with args: Args(Some(/opt/ergo/ergo.conf),Some(MainNet))
19:20:47.803 INFO  [main] org.ergoplatform.ErgoApp - Running with args: Args(Some(ergo.conf),Some(MainNet))
19:21:21.551 INFO  [main] org.ergoplatform.ErgoApp - Running with args: Args(Some(ergo.conf),Some(MainNet))
19:21:56.067 INFO  [main] org.ergoplatform.ErgoApp - Running with args: Args(Some(ergo.conf),Some(MainNet))
19:23:13.608 INFO  [main] org.ergoplatform.ErgoApp - Running with args: Args(Some(ergo.conf),Some(MainNet))
```

I’m not seeing anything out of the ordinary in the startup output.

Update #1:  
I tried to directly access the system via curl using the example to get the API key hash:

curl -X POST <…>

but it would always tell me the port was closed. So, I tried forcing it to use ipv4 with an ‘–ipv4’ option with the curl and that worked.

I’m thinking that I have to deal with an IPv6 issue because if the calls are going through IPv6 they’re being blocked and that may explain the Bad API Key error. Maybe the calls through panel are defaulting to IPv6 and getting blocked would explain things.

Just not entirely sure how to properly remedy this. I made sure I made a rule for port 9053 for my home zone, yet still getting Bad API Key still.

Update 2:  
I swapped out the name drive with another running a brand new Ubuntu 20.04.2 Server. Getting to the same point. Telling me Bad API Key.

I can’t pretty much eliminate the firewall issue because I used a web browser on another networked computer to access the panel (centOS had full GUI setup).

I’ve also tried multiple browsers. I use Safari a lot, so I fired up the development window and I do get a 403 response on any attempt to send the any API key via the popup dialog.

Update #3:  
I rolled back to the 4.0.7 client, and it accepts the API hash … but only on Ubuntu.

Using centOS, either using 4.0.7 or 4.0.8 it still doesn’t accept the key.

---

### Post #6 — @crazzziecanuck (2021-03-26)

So, after all of this, I think the issue might have been that I had “restAPI” when it could have been “restApi” instead.
