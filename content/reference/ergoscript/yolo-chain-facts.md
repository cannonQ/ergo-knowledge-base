---
title: "YOLO SigmaChain — Chain Facts for Contract Audits"
description: "What differs from Ergo when the contract under audit runs on YOLO SigmaChain: block time, storage rent, relay limits, addresses, script version. Injected by audit_contract and audit_verify when chain is yolo."
category: reference
difficulty: advanced
tags: [yolo, sigmachain, audit, chain-parameters, storage-rent, sigma-6]
sdk: [none]
author: CannonQ
source: original
license: AGPL-3.0
updated: 2026-11-26
index: false
---
# Chain facts: YOLO SigmaChain

The contract under review runs on YOLO SigmaChain, a fork of the Ergo node at v6.0.8 with the same script language and the same eUTXO model. The audit method, the vulnerability categories and the traps apply unchanged. The numbers do not.

**Source of every value below:** the YOLO developer guide, <https://github.com/YOLO-Sigmachain/yolo-contracts/blob/main/docs/developer-guide.md>, as read on 26 November 2026 (guide dated 22 November 2026). The guide is the authority; if it differs from this page, the guide is right. YOLO has run only on private test chains. There is no public network yet, and the guide says its genesis values are settings that are not yet fixed for the public testnet. Confirm any value a finding depends on against the guide or a node before you rate the finding.

## How to read the rest of this audit context

The rest of this context was written for Ergo. Lines carrying a figure known to differ are marked `[Ergo figure; see Chain facts]`. The marking works from a short list of phrasings and can miss one, so apply these rules yourself as well:

- **Every block count is 4 times shorter in wall-clock time.** Advice such as "allow ±10 blocks" is correct as a block count on either chain; on YOLO 10 blocks is about 5 minutes, not 20. Check every timelock, window and deadline constant in the contract against the block counts below, and ask whether the author converted from Ergo block counts.
- **Amounts are in nanoYOLO**, 1 YOLO = 1,000,000,000 nanoYOLO. Ergo's minimum box value figures do not carry over (see storage rent below).
- **"Mainnet" means the YOLO public network**, which does not exist yet. Trap T7 and procedure E-1 apply as written.
- **No Ergo box or token exists on YOLO.** It is a separate chain with its own genesis, so a contract that names an Ergo oracle pool NFT, a SigmaUSD token or any other Ergo mainnet id is reading something that is not there. EIP-27 re-emission does not exist on YOLO either (guide, "Scripts").

## Time

| | Ergo | YOLO |
|---|---|---|
| Block time | 120 seconds | 30 seconds |
| 1 hour | 30 blocks | 120 blocks |
| 1 day | 720 blocks | 2,880 blocks |
| 1 week | 5,040 blocks | 20,160 blocks |
| 1 year | 262,800 blocks | 1,051,200 blocks |
| Ten confirmations | about 20 minutes | about 5 minutes |
| Block timestamp may run ahead of the node clock by | more (see the guide) | 4 block intervals (2 minutes) |

Guide sections "The short version", "Time", "Difficulty, limits and voting". The Ergo column is given for conversion.

## Storage rent

| | Ergo | YOLO |
|---|---|---|
| Rent chargeable after a box has not moved for | 1,051,200 blocks (4 years) | 1,051,200 blocks (1 year) |
| Storage fee factor at launch | 1,250,000 | 300,000 |
| Who can claim rent | no attestation rule | only a claim attested by the miner of the block that includes it (validation rule 308) |

- A long-lived box (a singleton, a registry, a vault) meets the rent clock after one year without a spend, not four. Ask what moves each long-lived box within a year, and whether the box holds enough value to pay rent if nothing does.
- By default a YOLO node refuses rent-claim transactions from the network (`rejectStorageRentTxs`); miners collect rent into their own blocks. Rule 308 can be switched off later by a miner soft-fork vote, so do not rate a design as safe because outsiders cannot claim rent today.
- The guide does not state a minimum box value. The fee factor differs, so compute the minimum from the serialized box size and the chain's current parameters, or ask a node.

Guide section "Storage rent".

## Fees and miner rewards

- A coinbase reward is locked for 2,880 blocks (about one day). On Ergo it is 720 blocks.
- The fee box lock is 720 blocks on both chains, and YOLO uses Ergo's standard fee script. On YOLO 720 blocks is about 6 hours.
- The emission transaction has four outputs: the emission box, treasury (4%), liquidity fund (3%) and miner (93%). A contract or builder that recognises reward boxes by position or script must be checked against this layout.

Guide section "Fees and miner rewards".

## Limits: a transaction can be valid and still not propagate

| Limit | Value at launch | Kind |
|---|---|---|
| Block cost limit | 1,500,000 | consensus; miners can vote to change it |
| Block size limit | 524,288 bytes | consensus; miners can vote to change it |
| Relay cost limit for one transaction | 1,000,000 | node setting, from the YOLO testnet settings file |
| Relay size limit for one transaction | 98,304 bytes | node setting, from the YOLO testnet settings file |

For category 9 (cost limits): a spend path whose cost is over 1,000,000 can be valid in a block and still never reach a miner through the network. Rate it as a path that only a miner can use. The relay limits are node policy, so they can differ between nodes and can change without a fork.

Guide sections "Difficulty, limits and voting", "Relay and block building policy".

## Rules active from block 1

Two rules that Ergo activates at height 1,885,000 are active on YOLO from the first block:

- the outputs of a rent claim must be distinct;
- the data inputs of a transaction must be unique.

For trap T1 and data-input findings: one box cannot be listed twice as a data input on YOLO at any height.

Guide section "Storage rent".

## Scripts

- Sigma 6.0 is available from block 1: version 3 trees and the 6.0 methods need no activation. See the tree version 3 section of this context.
- YOLO's proof of work uses the block height divided by 4 where Ergo uses the block height. `Header.checkPow` applies Ergo's rule and does not work for a YOLO header. A contract that verifies YOLO headers must use `Global.powHit` and pass height / 4 and the table size N for that same value itself.

Guide sections "The short version", "Scripts".

## Addresses

- Mainnet address prefix: 32 (Ergo: 0). Testnet prefix: 16, the same as Ergo testnet, so a YOLO testnet address and an Ergo testnet address cannot be told apart by prefix.
- The guide notes that prefix 32 is covered by unit tests in the YOLO wallet and the YOLO sigma-rust fork, and that no wallet has yet run on a prefix-32 chain.

Guide section "Addresses".

## Reorganisation depth

A node keeps 200 state versions by default, about 100 minutes, which is the deepest rollback it can make. Use it when rating confirmation-depth findings, and count depth in blocks of YOLO time, not Ergo time.

Guide section "Difficulty, limits and voting".

## Limits of this page

- Every value is copied from the guide on the date above. None was measured for this page.
- No YOLO value has been observed on a public network. None exists.
- This page is the only place in the EKB that holds YOLO numbers. Other pages link here.
