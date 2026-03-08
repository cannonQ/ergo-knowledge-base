---
title: Stuck on "Running the node for the first time"
description: 'ErgoForum discussion: Stuck on "Running the node for the first time"'
tags:
- ergoforum
- full-node
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/stuck-on-running-the-node-for-the-first-time/1858
created: '2021-06-26'
last_activity: '2021-06-26'
posts_count: 1
views: 807
likes: 0
glossary_hits:
- Full node
---

# Stuck on "Running the node for the first time"

> **Forum thread:** [https://ergoforum.org/t/stuck-on-running-the-node-for-the-first-time/1858](https://ergoforum.org/t/stuck-on-running-the-node-for-the-first-time/1858)
> **Category:** Support | **Created:** 2021-06-26 | **Posts:** 1 | **Views:** 807

**Related concepts:** Full node

---

### Post #1 — @nozbo (2021-06-26)

I’ve followed the steps directly from:

this video

[![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/0811a03223aaedb83b63687f3196fe2f11fcafaa.jpeg "How to set up and configure a full Ergo node on Windows")](https://www.youtube.com/watch?v=fpEDJ1CM6ns)

and  
this link  
<https://ergoplatform.org/en/blog/2019_12_02_how_to_setup/>

I’m not sure how to proceed after issuing the power shell command and I get the response:

PS C:\ergo> java -jar ergo-4.0.12.jar --mainnet -c ergo.conf  
14:11:35.597 INFO [main] org.ergoplatform.ErgoApp - Running with args: Args(Some(ergo.conf),Some(MainNet))  
14:11:35.620 INFO [main] o.e.settings.ErgoSettings$ - Running in mainnet network mode  
14:11:35.621 WARN [main] o.e.settings.ErgoSettings$ - NO CONFIGURATION FILE WAS PROVIDED. STARTING WITH DEFAULT SETTINGS!  
Exception in thread “main” com.typesafe.config.ConfigException$Missing: C:\Users\Ryan\AppData\Local\Temp\mainnet.conf: 1: No configuration setting found for key ‘ergo.directory’  
at com.typesafe.config.impl.SimpleConfig.findKeyOrNull(SimpleConfig.java:156)  
at com.typesafe.config.impl.SimpleConfig.findOrNull(SimpleConfig.java:174)  
at com.typesafe.config.impl.SimpleConfig.findOrNull(SimpleConfig.java:180)  
at com.typesafe.config.impl.SimpleConfig.find(SimpleConfig.java:188)  
at com.typesafe.config.impl.SimpleConfig.find(SimpleConfig.java:193)  
at com.typesafe.config.impl.SimpleConfig.getString(SimpleConfig.java:250)  
at net.ceedubs.ficus.readers.StringReader$$anon$1.read(StringReader.scala:7)  
at net.ceedubs.ficus.readers.StringReader$$anon$1.read(StringReader.scala:6)  
at net.ceedubs.ficus.FicusConfig.as(FicusConfig.scala:10)  
at net.ceedubs.ficus.FicusConfig.as$(FicusConfig.scala:10)  
at net.ceedubs.ficus.SimpleFicusConfig.as(FicusConfig.scala:21)  
at org.ergoplatform.settings.ErgoSettings$.fromConfig(ErgoSettings.scala:57)  
at org.ergoplatform.settings.ErgoSettings$.read(ErgoSettings.scala:53)  
at org.ergoplatform.ErgoApp.(ErgoApp.scala:36)  
at org.ergoplatform.ErgoApp$.main(ErgoApp.scala:219)  
at org.ergoplatform.ErgoApp.main(ErgoApp.scala)  
PS C:\ergo>

[![Ergo_PowerShell](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/8714ab042b80f91e4183f1f48d06645e3eb495e2_2_690x245.png)

Ergo\_PowerShell3026×1076 359 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/8714ab042b80f91e4183f1f48d06645e3eb495e2.png "Ergo_PowerShell")

I placed the ergo-4.0.12.jar file in my C:\ergo directory.  
My ergo.conf file contains the following:

ergo {  
directory = “C:\ergo”  
node {  
mining = false  
}  
wallet.secretStorage.secretDir = “C:\ergo”  
}

Any help would be appreciated.  
Thanks!
