---
title: Ergo Node Loses Connection
description: 'ErgoForum discussion: Ergo Node Loses Connection'
tags:
- ergoforum
- full-node
- mempool
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/ergo-node-loses-connection/1881
created: '2021-07-01'
last_activity: '2021-08-18'
posts_count: 3
views: 833
likes: 0
glossary_hits:
- Full node
- Mempool
- Transaction
---

# Ergo Node Loses Connection

> **Forum thread:** [https://ergoforum.org/t/ergo-node-loses-connection/1881](https://ergoforum.org/t/ergo-node-loses-connection/1881)
> **Category:** Support | **Created:** 2021-07-01 | **Posts:** 3 | **Views:** 833

**Related concepts:** Full node, Mempool, Transaction

---

### Post #1 — @Ignatious11 (2021-07-01)

Hello, I can active the API and unlock the wallet and let it synchronize on Windows 10 via Powershell. After a couple hours (or so?) the Ergo Node Interface says “Node Connection lost” and the last of the Powershell readout is as follows. Any help would be greatly appreciated.

12:22:48.757 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/54.36.175.140:9030, local=/10.117.0.6:49789, direction=Outgoing)  
12:22:48.757 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/54.36.175.140:9030, local=/10.117.0.6:49789, direction=Outgoing)  
12:22:48.757 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/54.36.175.140:9030, local=/10.117.0.6:49789, direction=Outgoing)  
12:22:48.757 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/54.36.175.140:9030, local=/10.117.0.6:49789, direction=Outgoing)  
12:22:48.757 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.760 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing)  
12:22:48.756 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/51.222.82.16:9030, local=/10.117.0.6:51430, direction=Outgoing)  
12:22:48.761 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/51.222.82.16:9030, local=/10.117.0.6:51430, direction=Outgoing)  
12:22:48.761 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/51.222.82.16:9030, local=/10.117.0.6:51430, direction=Outgoing)  
12:22:48.761 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/51.222.82.16:9030, local=/10.117.0.6:51430, direction=Outgoing)  
12:22:48.761 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/51.222.82.16:9030, local=/10.117.0.6:51430, direction=Outgoing)  
12:22:48.756 INFO [ctor.default-dispatcher-8] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/147.135.97.19:9030, local=/10.117.0.6:51438, direction=Outgoing)  
12:22:48.761 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/51.222.82.16:9030, local=/10.117.0.6:51430, direction=Outgoing)  
12:22:48.756 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/207.244.240.82:9030, local=/10.117.0.6:51424, direction=Outgoing)  
12:22:48.757 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/159.89.116.15:9030, local=/10.117.0.6:58758, direction=Outgoing)  
12:22:48.757 INFO [tor.default-dispatcher-13] o.e.n.UtxoNodeViewHolder - Apply modifier 917e6b82ded04ac7b456c49cf7f0d4efa170f7a28694aabffa396c5987281826 of type 104 to nodeViewHolder  
12:22:48.762 DEBUG [tor.default-dispatcher-13] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier 917e6b82ded04ac7b456c49cf7f0d4efa170f7a28694aabffa396c5987281826 of type 104 to history  
12:22:48.762 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.762 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.762 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.762 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.762 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.762 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(22: RequestModifier) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.762 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/207.244.240.82:9030, local=/10.117.0.6:51424, direction=Outgoing)  
12:22:48.762 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/159.89.116.15:9030, local=/10.117.0.6:58758, direction=Outgoing)  
12:22:48.763 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Connection closed to ConnectionId(remote=/91.199.118.161:9030, local=/10.117.0.6:58755, direction=Outgoing), reason: error: Connection reset  
12:22:48.763 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/91.199.118.161:9030, local=/10.117.0.6:58755, direction=Outgoing) destroyed  
12:22:48.763 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/207.244.240.82:9030, local=/10.117.0.6:51424, direction=Outgoing)  
12:22:48.763 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing)  
12:22:48.763 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/207.244.240.82:9030, local=/10.117.0.6:51424, direction=Outgoing)  
12:22:48.763 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.763 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/207.244.240.82:9030, local=/10.117.0.6:51424, direction=Outgoing)  
12:22:48.763 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.765 DEBUG [tor.default-dispatcher-13] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:48.765 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.770 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.771 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.771 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.771 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.771 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.771 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.780 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Connection closed to ConnectionId(remote=/135.181.17.240:9030, local=/10.117.0.6:51434, direction=Outgoing), reason: error: Connection reset  
12:22:48.781 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/135.181.17.240:9030, local=/10.117.0.6:51434, direction=Outgoing) destroyed  
12:22:48.782 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Connection closed to ConnectionId(remote=/45.33.17.155:9030, local=/10.117.0.6:51414, direction=Outgoing), reason: error: Connection reset  
12:22:48.783 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/45.33.17.155:9030, local=/10.117.0.6:51414, direction=Outgoing) destroyed  
12:22:48.787 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Connection closed to ConnectionId(remote=/51.77.52.137:9030, local=/10.117.0.6:51429, direction=Outgoing), reason: error: Connection reset  
12:22:48.787 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/51.77.52.137:9030, local=/10.117.0.6:51429, direction=Outgoing) destroyed  
12:22:48.787 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(22: RequestModifier) from ConnectionId(remote=/94.130.168.191:9030, local=/10.117.0.6:51432, direction=Outgoing)  
12:22:48.788 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/94.130.168.191:9030, local=/10.117.0.6:51432, direction=Outgoing)  
12:22:48.788 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(22: RequestModifier) from ConnectionId(remote=/94.130.168.191:9030, local=/10.117.0.6:51432, direction=Outgoing)  
12:22:48.788 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Connection closed to ConnectionId(remote=/93.123.180.164:9030, local=/10.117.0.6:51417, direction=Outgoing), reason: error: Connection reset  
12:22:48.788 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/93.123.180.164:9030, local=/10.117.0.6:51417, direction=Outgoing) destroyed  
12:22:48.789 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Connection closed to ConnectionId(remote=/207.244.240.82:9030, local=/10.117.0.6:51424, direction=Outgoing), reason: error: Connection reset  
12:22:48.789 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/207.244.240.82:9030, local=/10.117.0.6:51424, direction=Outgoing) destroyed  
12:22:48.791 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.763 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing)  
12:22:48.763 INFO [ctor.default-dispatcher-8] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/147.135.97.19:9030, local=/10.117.0.6:51438, direction=Outgoing)  
12:22:48.765 INFO [tor.default-dispatcher-13] o.e.n.UtxoNodeViewHolder - Got locally generated modifier d42d480783852df70f104c86de53dc0db8241a4c9781002c222e8bc4e04f9bb0 of type 104  
12:22:48.772 INFO [tor.default-dispatcher-12] o.e.local.MempoolAuditor - Initiating cleanup. Switching to working mode  
12:22:48.792 INFO [tor.default-dispatcher-12] o.e.local.MempoolAuditor - Cleanup done. Switching to awaiting mode  
12:22:48.792 DEBUG [tor.default-dispatcher-12] o.e.local.MempoolAuditor - Rebroadcasting transactions  
12:22:48.793 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/147.135.97.19:9030, local=/10.117.0.6:51438, direction=Outgoing)  
12:22:48.793 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/147.135.97.19:9030, local=/10.117.0.6:51438, direction=Outgoing)  
12:22:48.793 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/147.135.97.19:9030, local=/10.117.0.6:51438, direction=Outgoing)  
12:22:48.793 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/147.135.97.19:9030, local=/10.117.0.6:51438, direction=Outgoing)  
12:22:48.794 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Connection closed to ConnectionId(remote=/51.222.82.16:9030, local=/10.117.0.6:51430, direction=Outgoing), reason: error: Connection reset  
12:22:48.794 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/51.222.82.16:9030, local=/10.117.0.6:51430, direction=Outgoing) destroyed  
12:22:48.792 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing)  
12:22:48.795 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing)  
12:22:48.795 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing)  
12:22:48.795 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing)  
12:22:48.795 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing)  
12:22:48.795 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing)  
12:22:48.792 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(22: RequestModifier) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.794 INFO [tor.default-dispatcher-13] o.e.n.UtxoNodeViewHolder - Apply modifier d42d480783852df70f104c86de53dc0db8241a4c9781002c222e8bc4e04f9bb0 of type 104 to nodeViewHolder  
12:22:48.796 DEBUG [tor.default-dispatcher-13] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier d42d480783852df70f104c86de53dc0db8241a4c9781002c222e8bc4e04f9bb0 of type 104 to history  
12:22:48.796 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Connection closed to ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing), reason: error: Connection reset  
12:22:48.796 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/139.99.46.39:9030, local=/10.117.0.6:51504, direction=Outgoing) destroyed  
12:22:48.796 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(22: RequestModifier) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.798 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.798 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(22: RequestModifier) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.798 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.798 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.798 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(55: Inv) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.798 INFO [tor.default-dispatcher-16] s.c.n.PeerConnectionHandler - Received message MessageSpec(65: Sync) from ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing)  
12:22:48.800 DEBUG [tor.default-dispatcher-13] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:48.800 INFO [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Got locally generated modifier 75cab7f106554c017bc32854a828ac3b236c1099da7efd0baf8145f79da5915e of type 104  
12:22:48.802 INFO [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Apply modifier 75cab7f106554c017bc32854a828ac3b236c1099da7efd0baf8145f79da5915e of type 104 to nodeViewHolder  
12:22:48.809 DEBUG [tor.default-dispatcher-16] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier 75cab7f106554c017bc32854a828ac3b236c1099da7efd0baf8145f79da5915e of type 104 to history  
12:22:48.820 DEBUG [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:48.820 INFO [ctor.default-dispatcher-8] o.e.local.MempoolAuditor - Initiating cleanup. Switching to working mode  
12:22:48.820 INFO [ctor.default-dispatcher-8] o.e.local.MempoolAuditor - Cleanup done. Switching to awaiting mode  
12:22:48.820 DEBUG [ctor.default-dispatcher-8] o.e.local.MempoolAuditor - Rebroadcasting transactions  
12:22:48.820 INFO [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Got locally generated modifier 9984553a345aca324bffda13e0ade132438efbd38e7b2e849c48b1f584c4a0e0 of type 104  
12:22:48.820 WARN [shutdownHook2] org.ergoplatform.ErgoApp$ - Terminating Actors  
12:22:50.710 ERROR [Thread-0] org.ergoplatform.ErgoApp - Unexpected shutdown  
12:22:50.713 INFO [Thread-0] org.ergoplatform.ErgoApp - Stopping network services  
12:22:50.713 WARN [shutdownHook2] org.ergoplatform.ErgoApp$ - Terminating ActorSystem  
12:22:50.710 INFO [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Apply modifier 9984553a345aca324bffda13e0ade132438efbd38e7b2e849c48b1f584c4a0e0 of type 104 to nodeViewHolder  
12:22:50.715 DEBUG [tor.default-dispatcher-16] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier 9984553a345aca324bffda13e0ade132438efbd38e7b2e849c48b1f584c4a0e0 of type 104 to history  
12:22:50.718 DEBUG [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:50.716 INFO [Thread-0] org.ergoplatform.ErgoApp - Stopping actors (incl. block generator)  
12:22:50.717 INFO [ctor.default-dispatcher-8] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/65.21.107.123:9030, local=/10.117.0.6:51435, direction=Outgoing) destroyed  
12:22:50.717 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/209.58.173.154:9030, local=/10.117.0.6:51436, direction=Outgoing) destroyed  
12:22:50.720 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/209.217.206.254:9030, local=/10.117.0.6:64128, direction=Outgoing) destroyed  
12:22:50.718 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/157.90.215.183:9030, local=/10.117.0.6:51437, direction=Outgoing) destroyed  
12:22:50.721 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/159.89.116.15:9030, local=/10.117.0.6:58758, direction=Outgoing) destroyed  
12:22:50.721 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/159.65.11.55:9030, local=/10.117.0.6:56227, direction=Outgoing) destroyed  
12:22:50.721 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/54.36.175.140:9030, local=/10.117.0.6:49789, direction=Outgoing) destroyed  
12:22:50.721 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/94.130.168.191:9030, local=/10.117.0.6:51432, direction=Outgoing) destroyed  
12:22:50.718 INFO [tor.default-dispatcher-16] o.e.local.MempoolAuditor - Initiating cleanup. Switching to working mode  
12:22:50.718 INFO [tor.default-dispatcher-13] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/147.135.97.19:9030, local=/10.117.0.6:51438, direction=Outgoing) destroyed  
12:22:50.722 INFO [tor.default-dispatcher-16] o.e.local.MempoolAuditor - Cleanup done. Switching to awaiting mode  
12:22:50.722 DEBUG [tor.default-dispatcher-16] o.e.local.MempoolAuditor - Rebroadcasting transactions  
12:22:50.718 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/195.154.92.37:9030, local=/10.117.0.6:51461, direction=Outgoing) destroyed  
12:22:50.720 INFO [ctor.default-dispatcher-8] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/213.239.193.208:9030, local=/10.117.0.6:58753, direction=Outgoing) destroyed  
12:22:50.721 INFO [ctor.default-dispatcher-7] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/138.201.189.122:9030, local=/10.117.0.6:51422, direction=Outgoing) destroyed  
12:22:50.722 INFO [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Got locally generated modifier bba7d49daf3d007d20e4b0313471e2739a0ac53937e5d2478268de7a254ab615 of type 104  
12:22:50.724 INFO [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Apply modifier bba7d49daf3d007d20e4b0313471e2739a0ac53937e5d2478268de7a254ab615 of type 104 to nodeViewHolder  
12:22:50.724 DEBUG [tor.default-dispatcher-10] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier bba7d49daf3d007d20e4b0313471e2739a0ac53937e5d2478268de7a254ab615 of type 104 to history  
12:22:50.729 DEBUG [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:50.729 INFO [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Got locally generated modifier 5aae2b0019f9225adc0a2bb390bfcc36ad8793a1ac23084d98b7d555916dcbbf of type 104  
12:22:50.729 INFO [tor.default-dispatcher-16] o.e.local.MempoolAuditor - Initiating cleanup. Switching to working mode  
12:22:50.734 INFO [tor.default-dispatcher-16] o.e.local.MempoolAuditor - Cleanup done. Switching to awaiting mode  
12:22:50.734 DEBUG [tor.default-dispatcher-16] o.e.local.MempoolAuditor - Rebroadcasting transactions  
12:22:50.734 INFO [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Apply modifier 5aae2b0019f9225adc0a2bb390bfcc36ad8793a1ac23084d98b7d555916dcbbf of type 104 to nodeViewHolder  
12:22:50.734 DEBUG [tor.default-dispatcher-10] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier 5aae2b0019f9225adc0a2bb390bfcc36ad8793a1ac23084d98b7d555916dcbbf of type 104 to history  
12:22:50.736 DEBUG [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:50.736 INFO [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Got locally generated modifier 21ec588262d853ea3babd6c06a01ff5f6088de1547569e94284a26ab4514188a of type 104  
12:22:50.740 INFO [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Apply modifier 21ec588262d853ea3babd6c06a01ff5f6088de1547569e94284a26ab4514188a of type 104 to nodeViewHolder  
12:22:50.741 DEBUG [tor.default-dispatcher-10] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier 21ec588262d853ea3babd6c06a01ff5f6088de1547569e94284a26ab4514188a of type 104 to history  
12:22:50.742 DEBUG [tor.default-dispatcher-10] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:50.743 INFO [tor.default-dispatcher-10] o.e.local.MempoolAuditor - Initiating cleanup. Switching to working mode  
12:22:50.743 INFO [tor.default-dispatcher-10] o.e.local.MempoolAuditor - Cleanup done. Switching to awaiting mode  
12:22:50.743 DEBUG [tor.default-dispatcher-10] o.e.local.MempoolAuditor - Rebroadcasting transactions  
12:22:50.743 INFO [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Got locally generated modifier db060a0faa04c572a23f3790f5db5167d12dd46630682364f06b0e2e9bb19797 of type 104  
12:22:50.744 INFO [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Apply modifier db060a0faa04c572a23f3790f5db5167d12dd46630682364f06b0e2e9bb19797 of type 104 to nodeViewHolder  
12:22:50.745 DEBUG [tor.default-dispatcher-16] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier db060a0faa04c572a23f3790f5db5167d12dd46630682364f06b0e2e9bb19797 of type 104 to history  
12:22:50.752 DEBUG [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:50.752 INFO [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Got locally generated modifier bcbba6675637c50c427649aae772d9062ab1e4c4e88bff3568845794e2a445a4 of type 104  
12:22:50.752 INFO [ctor.default-dispatcher-7] o.e.local.MempoolAuditor - Initiating cleanup. Switching to working mode  
12:22:50.756 INFO [ctor.default-dispatcher-7] o.e.local.MempoolAuditor - Cleanup done. Switching to awaiting mode  
12:22:50.758 DEBUG [ctor.default-dispatcher-7] o.e.local.MempoolAuditor - Rebroadcasting transactions  
12:22:50.760 INFO [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Apply modifier bcbba6675637c50c427649aae772d9062ab1e4c4e88bff3568845794e2a445a4 of type 104 to nodeViewHolder  
12:22:50.760 DEBUG [tor.default-dispatcher-16] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier bcbba6675637c50c427649aae772d9062ab1e4c4e88bff3568845794e2a445a4 of type 104 to history  
12:22:50.764 INFO [tor.default-dispatcher-13] o.e.local.MempoolAuditor - Mempool auditor stopped  
12:22:50.764 INFO [ergoref-api-dispatcher-22] o.e.n.w.ErgoWalletActor - Wallet actor stopped  
12:22:52.725 DEBUG [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
12:22:52.725 WARN [tor.default-dispatcher-16] o.e.n.UtxoNodeViewHolder - Stopping ErgoNodeViewHolder  
12:22:52.729 WARN [tor.default-dispatcher-16] o.e.n.h.s.HistoryStorage - Closing history storage…  
12:22:52.788 WARN [tor.default-dispatcher-16] o.e.n.state.UtxoState - Closing state’s store.  
12:22:52.838 INFO [tor.default-dispatcher-10] org.ergoplatform.ErgoApp - Exiting from the app…  
12:22:52.842 WARN [shutdownHook2] org.ergoplatform.ErgoApp$ - Application has been terminated.

---

### Post #2 — @Ignatious11 (2021-07-11)

Tried again recently after doing some reading and same thing, however the last few lines in the log look a little different:

16:42:25.778 INFO [Thread-0] org.ergoplatform.ErgoApp - Stopping network services  
16:42:25.782 INFO [tor.default-dispatcher-11] o.e.n.UtxoNodeViewHolder - Got locally generated modifier 1435128d23c9bb43c4a5d8482440d6fb2f2fa9589d2205e4643785c0cefd4f65 of type 104  
16:42:25.784 INFO [tor.default-dispatcher-10] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/51.222.82.16:9030, local=/10.11.0.6:64173, direction=Outgoing) destroyed  
16:42:27.386 INFO [tor.default-dispatcher-12] s.c.n.PeerConnectionHandler - Peer handler to ConnectionId(remote=/45.95.203.19:9030, local=/10.11.0.6:56202, direction=Outgoing) destroyed  
16:42:27.386 INFO [ctor.default-dispatcher-7] o.e.local.MempoolAuditor - Initiating cleanup. Switching to working mode  
16:42:27.393 INFO [ctor.default-dispatcher-7] o.e.local.MempoolAuditor - Cleanup done. Switching to awaiting mode  
16:42:27.394 DEBUG [ctor.default-dispatcher-7] o.e.local.MempoolAuditor - Rebroadcasting transactions  
16:42:27.393 INFO [tor.default-dispatcher-11] o.e.n.UtxoNodeViewHolder - Apply modifier 1435128d23c9bb43c4a5d8482440d6fb2f2fa9589d2205e4643785c0cefd4f65 of type 104 to nodeViewHolder  
16:42:27.399 DEBUG [tor.default-dispatcher-11] o.e.n.h.ErgoHistory$$anon$3 - Trying to append modifier 1435128d23c9bb43c4a5d8482440d6fb2f2fa9589d2205e4643785c0cefd4f65 of type 104 to history  
16:42:27.392 INFO [Thread-0] org.ergoplatform.ErgoApp - Stopping actors (incl. block generator)  
16:42:27.400 DEBUG [tor.default-dispatcher-11] o.e.n.UtxoNodeViewHolder - Going to apply modifications to the state: ProgressInfo(BranchPoint: None, to remove: List(), to apply: List())  
16:42:27.399 INFO [tor.default-dispatcher-10] o.e.local.MempoolAuditor - Mempool auditor stopped  
16:42:27.399 INFO [ergoref-api-dispatcher-34] o.e.n.w.ErgoWalletActor - Wallet actor stopped  
16:42:27.400 WARN [tor.default-dispatcher-11] o.e.n.UtxoNodeViewHolder - Stopping ErgoNodeViewHolder  
16:42:27.401 WARN [tor.default-dispatcher-11] o.e.n.h.s.HistoryStorage - Closing history storage…  
16:42:27.436 WARN [tor.default-dispatcher-11] o.e.n.state.UtxoState - Closing state’s store.  
16:42:29.136 WARN [shutdownHook2] org.ergoplatform.ErgoApp$ - Application has been terminated.  
16:42:29.137 INFO [ctor.default-dispatcher-8] org.ergoplatform.ErgoApp - Exiting from the app…

---

### Post #3 — @kushti (2021-08-18)

Looks like external kill signal in the latter case, can PowerShell do this ?
