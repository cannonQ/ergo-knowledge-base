---
title: How to set up and configure a full Ergo node
description: 'ErgoForum discussion: How to set up and configure a full Ergo node'
tags:
- addresses
- box
- context-extension
- ergoforum
- ergoscript
- ergoscript-context
- full-node
- native-tokens
- node-modes
- registers
- scorex
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/how-to-set-up-and-configure-a-full-ergo-node/142
created: '2019-12-04'
last_activity: '2020-12-31'
posts_count: 5
views: 7053
likes: 5
glossary_hits:
- Addresses
- Box
- Context extension
- ErgoScript
- ErgoScript context
- Full node
- Native tokens
- Node modes
- Registers
- Scorex
- Transaction
---

# How to set up and configure a full Ergo node

> **Forum thread:** [https://ergoforum.org/t/how-to-set-up-and-configure-a-full-ergo-node/142](https://ergoforum.org/t/how-to-set-up-and-configure-a-full-ergo-node/142)
> **Category:** Support | **Created:** 2019-12-04 | **Posts:** 5 | **Views:** 7053

**Related concepts:** Addresses, Box, Context extension, ErgoScript, ErgoScript context, Full node, Native tokens, Node modes, Registers, Scorex, Transaction

---

### Post #1 — @Martin-mx (2019-12-04)

# How to set up and configure a full Ergo node

This tutorial explains how to install and run a full Ergo node. It does not cover mining.

# Node security

There are a few important aspects of node usage that your wallet and money’s safety depends on:

* An Ergo node requires storing security-critical parameters in the configuration file. You should never make this file public.
* An Ergo node provides a REST API for interacting with the built-in wallet. Sensitive API methods require a security token, which should never be sent over untrusted channels.
* Access to the Ergo REST API must be restricted to known hosts. In particular, the API must not be accessible from the Internet.

# Prerequisites

To run an Ergo node you need a **JDK/JRE version >= 9** installed on your system. We recommend either version 9 or 11. One way to do this is to install [Oracle Java SE](https://www.oracle.com/technetwork/java/javase/overview/index.html).

**Note that Oracle JDK/JRE <= 8 is no longer supported** .

The next step is to download the latest [Ergo client release](https://github.com/ergoplatform/ergo/releases/) jar file and create a node configuration file.

Note that instead of downloading the precompiled Ergo jar, you can clone the repository and compile the jar from the source using [SBT](https://www.scala-sbt.org/) by issuing the `sbt assembly` command.

Create a dedicated folder (such as `~/ergo` ) for running the node. Denote by **ergo\_folder** the folder where the jar is kept.

# Running the node for the first time

Create a configuration file `ergo.conf` with the following text in **ergo\_folder** .

```ergoscript
ergo {
  directory = ${ergo.directory}"/.ergo"
  node {
    mining = false
  }
  wallet.secretStorage.secretDir = ${ergo.directory}"/wallet/keystore"
}
```

The parameter `${ergo.directory}` points to the directory where the jar will be run from. Open a command prompt and `cd` to **ergo\_folder** . Then issue the following command to run the node for the first time:

```ergoscript
 java -jar ergo-<release>.jar --mainnet -c ergo.conf
```

The node will start syncing immediately after this. Wait for a few minutes for the API to start and go to the next step.

**Note:** You can use any name for the file instead of `ergo.conf` . All configuration parameters are to be passed through this file and you only need to rewrite parameters that you want to change from the default values. The above config file actually has the default values.

# Compute the hash of your secret

First, select a secret to protect your API. Then go to <http://127.0.0.1:9053/swagger#/utils/hashBlake2b> and call the API to compute the hash of your secret. Refer to the image below.

[![Compute Hash of secret](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/136f5666abbf41713b49769f4fe1db0d816febb2.png)

Compute Hash of secret698×384 16 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/136f5666abbf41713b49769f4fe1db0d816febb2.png "Compute Hash of secret")

Copy the response containing the hash for use in the next step (see below image). In our example, the secret is `hello` whose hash corresponds to `324dcf027dd4a30a932c441f365a25e86b173defa4b8e58948253471b81b72cf` .

**IMPORTANT** You must use a different and strong secret.

[![response](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/e1abb26cad11c41447908ca6d52821f721dbe1b8_2_690x319.png)

response1157×536 19 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/e1abb26cad11c41447908ca6d52821f721dbe1b8.png "response")

# Update config file with API key hash

Edit the config file `ergo.conf` and paste the hash copied in the previous step. The file should look as follows:

```ergoscript
ergo {
  directory = ${ergo.directory}"/.ergo"
  node {
    mining = false
  }
  wallet.secretStorage.secretDir = ${ergo.directory}"/wallet/keystore"
}

scorex {
 restApi {
    # Hex-encoded Blake2b256 hash of an API key. 
    # Should be 64-chars long Base16 string.
    # below is the hash of the string 'hello'
    # replace with your actual hash 
    apiKeyHash = "324dcf027dd4a30a932c441f365a25e86b173defa4b8e58948253471b81b72cf"
  }
}
```

# Initialize wallet

Restart the node and go to <http://127.0.0.1:9053/panel> to access the panel. Then set the API key secret from the previous step. Note that you need to set the **secret** and not the hash from the config file. In our example, this is the string `hello` .

[![set API key](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/6b507299dc4e75db81efa24286b9ace92e198ebf_2_666x500.png)

set API key897×673 28.5 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/6b507299dc4e75db81efa24286b9ace92e198ebf.png "set API key")

Click on **Initialize wallet** . After the pop-up opens, there are two ways to proceed depending on your scenario.

1. If this is the first time you are running the node then you need to initialize it with a new mnemonic sentence.
2. If you had created a wallet earlier and would like to obtain the same address (possibly because there are funds stored in it), then you have to restore the wallet using the mnemonic sentence you had saved earlier.

Follow one of the below steps depending on your situation.

## Initialize wallet from scratch

[![Initialize wallet](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/c54fc782bcb590f7a2eb11b8baad8ebb57710421_2_662x500.png)

Initialize wallet1002×756 45.4 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/c54fc782bcb590f7a2eb11b8baad8ebb57710421.png "Initialize wallet")

In the pop-up that opens, you must enter a wallet password. The mnemonic password is optional. After you click send, the wallet will return a mnemonic sentence as shown below.

[![mnemonic sentence](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/41eff304668b146f068aba5d0393449cd2466a48_2_690x442.png)

mnemonic sentence896×574 41.3 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/41eff304668b146f068aba5d0393449cd2466a48.png "mnemonic sentence")

You must copy this sentence and save it in a safe place. This sentence will be needed to restore the wallet on a different computer.

## Restore wallet from earlier

Copy the mnemonic sentence from earlier paste it into the “Mnemonic” field in the Restore-wallet form. Enter a secure wallet password. Leave the Mnemonic password empty (it is only for advanced users). Refer to the figure below.

[![restore wallet](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/5bbf1227455961c86d4b239e6b26925639a8ed58_2_690x399.png)

restore wallet1513×876 73.4 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/5bbf1227455961c86d4b239e6b26925639a8ed58.png "restore wallet")

After the wallet has been successfully restored from the mnemonic sentence, you will see a confirmation as shown in the figure below.

[![successfully restored confirmation](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/431a4a08abd70dc87a0fb1aca09c23ff8921f32f_2_690x297.png)

successfully restored confirmation1755×756 97.3 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/431a4a08abd70dc87a0fb1aca09c23ff8921f32f.png "successfully restored confirmation")

# Get wallet addresses

This is a test to ensure you have set up the node properly. It will return the current addresses in the wallet. In the panel at <http://127.0.0.1:9053/panel> click on the `Wallet` tab on the left and then on `Get all wallet addresses` to view the addresses currently maintained by the wallet. It should return at least one address if the node is set correctly.

[![Get addresses](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/7ca8184afdbc81edf9d0491b250b4a8a87cde9e0_2_690x268.png)

Get addresses1158×451 38.7 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/7ca8184afdbc81edf9d0491b250b4a8a87cde9e0.png "Get addresses")

# Check if the node is synced

While the node is syncing, the panel will show “Active synchronization” (see the image below).

[![active synchronization](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/72b14bb8f87c7dbf2715428cfea4db5c3e5d5f26_2_690x403.png)

active synchronization996×583 26.6 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/72b14bb8f87c7dbf2715428cfea4db5c3e5d5f26.png "active synchronization")

After the node is fully synced, the text will change to “Node is synced”, as shown below.

[![synced](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/1b73a981a09ee4fc9b6e2ceaedbfc1f5e5b59c6c_2_690x206.png)

synced903×270 14.3 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/1b73a981a09ee4fc9b6e2ceaedbfc1f5e5b59c6c.png "synced")

# Check wallet balance

Once the node is synced, use the wallet API in the panel to see your balance, as shown below.

[![check balance](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/34a400d422640f0041478b82768e2dfea2ec16b0_2_690x404.png)

check balance1324×776 50.3 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/34a400d422640f0041478b82768e2dfea2ec16b0.png "check balance")

# Sending funds

If there is a non-zero balance, you can send Ergs to any other address using the panel as shown below:

[![send ergs](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/654f4f716e3da4ed7b0536e28a7d2b42b4d845ea_2_690x377.png)

send ergs1380×754 45.3 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/654f4f716e3da4ed7b0536e28a7d2b42b4d845ea.png "send ergs")

# View the Swagger UI

A Swagger UI is available at <http://127.0.0.1:9053/swagger>. You had already used it earlier to compute the hash of your secret. You can also use this UI to make API calls for advanced operations that are not (yet) available in the panel. Some examples of this are:

1. Creating non-standard transactions with registers and context variables.
2. Creating transactions that issue tokens.
3. Creating transactions that use certain boxes as inputs.

A future article will discuss each of these operations in detail.

Note that most methods in the API are protected and you would need to use your secret (from earlier) to access these methods. The following images show the process of setting this secret in the Swagger UI.

Navigate to the top of the page and click the “Authorize” button. Enter your secret in the form that pops-up as shown in the figure below.

[![Enter API key](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/9211418df9e5135e34d4dc2664dbcf39baff509e_2_690x388.png)

Enter API key896×505 28 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/9211418df9e5135e34d4dc2664dbcf39baff509e.png "Enter API key")

After the password is entered and you have clicked “Authorize”, you will be shown the popup below: ![Logged in](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/b3b4ef18b3c92719d3e37fd7837f1666a84c1f7e.png)

Now navigate to <http://127.0.0.1:9053/swagger#/wallet/walletAddresses> **in the same tab where you entered the password** and click on “Try it out”. You should see the same list of addresses as you saw earlier from the panel.

[![Get addresses](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/optimized/1X/0a14add193bd59d27c35499e5ff71167e4c4cae1_2_600x500.png)

Get addresses845×704 26.9 KB](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/0a14add193bd59d27c35499e5ff71167e4c4cae1.png "Get addresses")

---

### Post #2 — @bluesky (2019-12-21)

do you have guide by photo or video?

---

### Post #3 — @Martin-mx (2019-12-22)

![](https://github.githubassets.com/favicons/favicon.svg)
[GitHub](https://github.com/ergoplatform/ergo/wiki/Set-up-a-full-node)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/1X/46a3c2d015b23d114fafd4756ea7c173fad09cb2.png)

### [ergoplatform/ergo](https://github.com/ergoplatform/ergo/wiki/Set-up-a-full-node)

Ergo protocol description & reference client implementation - ergoplatform/ergo

---

### Post #4 — @kushti (2019-12-22)

The tutorial provided by Martin above is the latest and most accessible to the moment. For Linux operating systems, there’s also possibility to download and install the node by using one-line command: [Linux One-liners to download and run Ergo node](https://www.ergoforum.org/t/linux-one-liners-to-download-and-run-ergo-node/155) . There’s no such possibility for Windows yet but we can take a look (into a PowerShell script ) if this may help you. Unfortunately, no videos available yet, maybe you can make one!

---

### Post #5 — @fuzzycryptoz (2020-12-31)

Hello, I need some assistance. I am a non-technical person, and I have followed your helpful video to the letter on how to setup a full Ergo node. However, when I run the command

C:\ergo>java -jar ergo-3.3.7.jar --mainnet -c ergo.conf

I get this error

12:11:00.608 ERROR [ctor.default-dispatcher-8] scorex.db.StoreRegistry - Failed to initialize storage: org.fusesource.leveldbjni.internal.NativeDB$DBException: IO error: C:\ergo\history\index/MANIFEST-000002: The system cannot find the file specified.  
. Please check that directory C:\ergo\history\index exists and is not used by some other active node

I checked and the index folder is there. Is there something that I am doing wrong?
