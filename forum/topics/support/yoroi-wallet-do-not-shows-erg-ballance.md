---
title: Yoroi wallet do not shows ERG ballance
description: 'ErgoForum discussion: Yoroi wallet do not shows ERG ballance'
tags:
- addresses
- ergo-explorer
- ergoforum
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/yoroi-wallet-do-not-shows-erg-ballance/2727
created: '2021-10-09'
last_activity: '2021-10-22'
posts_count: 11
views: 2031
likes: 2
glossary_hits:
- Addresses
- Ergo Explorer
---

# Yoroi wallet do not shows ERG ballance

> **Forum thread:** [https://ergoforum.org/t/yoroi-wallet-do-not-shows-erg-ballance/2727](https://ergoforum.org/t/yoroi-wallet-do-not-shows-erg-ballance/2727)
> **Category:** Support | **Created:** 2021-10-09 | **Posts:** 11 | **Views:** 2031

**Related concepts:** Addresses, Ergo Explorer

---

### Post #1 — @Tom1 (2021-10-09)

Hi,

My yoroi wallet for Ergo first was showing wrong balance. I clicked to resync it. Now the wallet is re-syncing more than 24 hours and still not showing any balance.

I recovered the same wallet on Microsoft Edge and it also do not show any balance but probably syncing. Please advise what to do and how long synchronization can take place.

Thanks

---

### Post #2 — @Haskell_plus (2021-10-09)

Check your address balance via explorer

<https://explorer.ergoplatform.com/en/>

---

### Post #3 — @Tom1 (2021-10-10)

I checked and balace is correct via explorer. But unfortunately Yoroi do not show it still at all

---

### Post #4 — @Haskell_plus (2021-10-12)

OK, if you have your seed phrase you can try to restore your wallet again, when I am having issues I usually delete all traces of whatever I having a problem with - resync my computer time, erase all browsing history manually, cache cookies and everything I do not need, then I reinstall a fresh download and restore my wallet.

---

### Post #5 — @Tom1 (2021-10-13)

Hi. Thank you for reply. I restored Ergo Wallet on completely fresh system. And the situation is the same. This is what I get in error log:

[2021-10-13T06:26:59+02:00] WalletStore::refreshWalletFromRemote {  
“message”: “api.errors.getTxHistoryForAddressesApiError: undefined”,  
“name”: “P”,  
“stack”: “P: api.errors.getTxHistoryForAddressesApiError: undefined  
at Object.errorFactory (chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/618.bundle.js:1:91160)  
at chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/618.bundle.js:1:89104  
at async i (chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/618.bundle.js:1:90873)  
at async chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/618.bundle.js:1:91450  
at async P (chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/618.bundle.js:1:87489)  
at async chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/618.bundle.js:1:86160  
at async Promise.all (index 0)  
at async chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/618.bundle.js:1:86197  
at async chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/618.bundle.js:1:86082  
at async chrome-extension://akoiaibnepcedcplijmiamnaigbepmcb/js/yoroi\_206d589d.bundle.js:1:10241”,  
“id”: “api.errors.getTxHistoryForAddressesApiError”,  
“defaultMessage”: “!!!Error received from server while getting txs.”,  
“values”: {}

---

### Post #6 — @Haskell_plus (2021-10-14)

Can you try the mobile wallet?

I do not know what those logs say, looks like communication problems that could have something to do with your settings or router or what have you, I have no clue, if you can use the mobile wallet here is a link [Wallet | Ergo](https://ergoplatform.org/en/android_wallet/) pulled from [Ergonaut | The Ergonaut Handbook](https://ergonaut.space/en/home) you could take the problem to discord and ask for someone to take a look at the logs [Ergo Platform](https://discord.gg/eFHFFVDb)

---

### Post #7 — @Tom1 (2021-10-14)

Hello,

I got remark on forum to use ERGO Wallet on Android. It helped immediately. In 3 seconds I got balance.

So thank you for support .

Have a nice day ![:slight_smile:](https://emoji.discourse-cdn.com/twitter/slight_smile.png?v=10 ":slight_smile:")

BR

T

---

### Post #8 — @d1g174l (2021-10-21)

Did ERGO Wallet on Android help you recover the funds from a wallet created using Yoroi browser extension? This is the one thing I haven’t tried yet in recovering my own ERG which is sitting orphaned in a wallet created by Yoroi chrome extension. Even Yoroi’s own iOS app doesn’t recognize that it exists. I can see my 722 ERGO on the blockchain. But Yoroi has orphaned it there for me.

---

### Post #9 — @Tom1 (2021-10-22)

Yes. Please use ERGO Android Wallet - put your KEY phrase to Android Wallet and you will recover it

---

### Post #10 — @glasgowm (2021-10-22)

There’s an issue with miner dust on Yoroi right now, the dev is working hard trying to fix. He would appreciate error logs. If you still have access to your wallet send all assets to a new address.

![](https://telegram.org/favicon.ico?3)
[Telegram](https://t.me/ergosupport)

![](https://canada1.discourse-cdn.com/flex030/uploads/ergoforum/original/2X/5/54af5ef397b8138b19b7a834c427dde69a5193f4.jpeg)

### [Ergo Support](https://t.me/ergosupport)

This group is related to technical question regarding Development, Mining and Wallets only! Please refrain from any other questions. #ERGOPlatform

---

### Post #11 — @Tom1 (2021-10-22)

Hello,

Error LOG below:

[INFO] Yoroi v.4.7.400  
[INFO] Commit: 64ae9837afe3347f8ae7d7af0b8ec98d03e2a1c2  
[INFO] Network: mainnet  
[INFO] User Agent: { ua: ‘Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36’,  
browser: { name: ‘Chrome’, version: ‘94.0.4606.81’, major: ‘94’ },  
engine: { name: ‘Blink’, version: ‘94.0.4606.81’ },  
os: { name: ‘Windows’, version: ‘10’ },  
device: { vendor: undefined, model: undefined, type: undefined },  
cpu: { architecture: ‘amd64’ } }
