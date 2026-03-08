---
title: Need Help - NVCC Fatal
description: 'ErgoForum discussion: Need Help - NVCC Fatal'
tags:
- autolykos
- ergoforum
- support
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/need-help-nvcc-fatal/672
created: '2021-02-16'
last_activity: '2021-02-16'
posts_count: 1
views: 414
likes: 0
glossary_hits:
- Autolykos
---

# Need Help - NVCC Fatal

> **Forum thread:** [https://ergoforum.org/t/need-help-nvcc-fatal/672](https://ergoforum.org/t/need-help-nvcc-fatal/672)
> **Category:** Support | **Created:** 2021-02-16 | **Posts:** 1 | **Views:** 414

**Related concepts:** Autolykos

---

### Post #1 — @yakovsadove (2021-02-16)

Having an issue getting the miner file built. When running winbuild.cmd i am getting this error:

c:\Autolykos-GPU-miner\secp256k1\src>nvcc -o …/miner.exe -Xcompiler “/std:c++14” -gencode arch=compute\_52,code=sm\_52 -gencode arch=compute\_52,code=compute\_52 -DBLOCK\_DIM=64 -DNONCES\_PER\_ITER=0x400000 -I C:\Program Files\OpenSSL-Win64\include -I C:\curl\include -l C:\curl\builds\libcurl-vc-x64-release-dll-ipv6-sspi-schannel-obj-lib/libcurl -l C:\Program Files\OpenSSL-Win64\lib\libeay32 -L C:\Program Files\OpenSSL-Win64/lib -lnvml conversion.cc cryptography.cc definitions.cc jsmn.c httpapi.cc mining.cu prehash.cu processing.cc request.cc easylogging++.cc bip39/bip39.cc bip39/util.cc autolykos.cu  
nvcc fatal : Don’t know what to do with ‘Files/OpenSSL-Win64/lib’

Any idea what the issue is and how to fix it?  
Thank You
