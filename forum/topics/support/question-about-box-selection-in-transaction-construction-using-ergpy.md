---
title: Question about Box Selection in Transaction Construction Using ergpy
description: 'ErgoForum discussion: Question about Box Selection in Transaction Construction
  Using ergpy'
tags:
- addresses
- appkit
- box
- box-selection
- emission-schedule
- ergo-python-appkit
- ergoforum
- ergoscript
- ergoscript-context
- native-tokens
- registers
- support
- transaction
category: forum
forum_category: Support
source: ergoforum
source_url: https://ergoforum.org/t/question-about-box-selection-in-transaction-construction-using-ergpy/4844
created: '2024-08-24'
last_activity: '2024-08-25'
posts_count: 3
views: 125
likes: 4
glossary_hits:
- Addresses
- AppKit
- Box
- Box selection
- Emission schedule
- ErgoScript
- ErgoScript context
- Native tokens
- Registers
- Transaction
- ergo-python-appkit
---

# Question about Box Selection in Transaction Construction Using ergpy

> **Forum thread:** [https://ergoforum.org/t/question-about-box-selection-in-transaction-construction-using-ergpy/4844](https://ergoforum.org/t/question-about-box-selection-in-transaction-construction-using-ergpy/4844)
> **Category:** Support | **Created:** 2024-08-24 | **Posts:** 3 | **Views:** 125

**Related concepts:** Addresses, AppKit, Box, Box selection, Emission schedule, ErgoScript, ErgoScript context, Native tokens, Registers, Transaction, ergo-python-appkit

---

### Post #1 — @jossemii (2024-08-24)

### Question about Box Selection in Transaction Construction Using `ergpy`

**Context:**

While attempting to construct a transaction using `ergpy` (the Python wrapper for the appkit), I encountered an unusual situation related to the selection of input boxes. In my case, I have two available input boxes:

1. **InputBox 1**: `90ea90ca0cd4af9465f94d90bf667aca21ef5984c4e9196b83e862fe028301c8` with a balance of `796,500,000` nanoERGs.
2. **InputBox 2**: `9ec3c2608afab30dd3a7140ed0e508908d99fe3b86eef68c99539106dd3b2654` with a balance of `794,500,000` nanoERGs.

When constructing the transaction, I need an output of `795,500,000` nanoERGs and a fee of `1,000,000` nanoERGs.

**Issue:**

Despite the fact that the first box (`InputBox 1`) has more ERGs and should be sufficient to cover the output and the fee, the method `buildUnsignedTransaction()` ends up selecting the second box (`InputBox 2`), which has fewer ERGs. This results in an error, as the selected box does not have enough balance to cover both the output and the fee.

The specific error encountered is:

`reason: NotEnoughErgsError(not enough boxes to meet ERG needs 796499900 (found only 796500000),796500000)`

This error is thrown at the following line of code in the `ergo-appkit` repository:

[github.com/ergoplatform/ergo-appkit](https://github.com/ergoplatform/ergo-appkit/blob/29418943a96a5e0965826142617c8cbcbae2ab99/lib-api/src/main/java/org/ergoplatform/appkit/InputBoxesValidator.scala#L55)

#### [lib-api/src/main/java/org/ergoplatform/appkit/InputBoxesValidator.scala](https://github.com/ergoplatform/ergo-appkit/blob/29418943a96a5e0965826142617c8cbcbae2ab99/lib-api/src/main/java/org/ergoplatform/appkit/InputBoxesValidator.scala#L55)

[`29418943a`](https://github.com/ergoplatform/ergo-appkit/blob/29418943a96a5e0965826142617c8cbcbae2ab99/lib-api/src/main/java/org/ergoplatform/appkit/InputBoxesValidator.scala#L55)

```ergoscript
45. case Right(changeBoxes) => Right(new BoxSelectionResult(res.toSeq, changeBoxes, None))
46. case Left(error) => Left(error)
47. }
48. } else {
49. Left(NotEnoughTokensError(
50. s"Not enough tokens in input boxes to send $targetAssets (found only $currentAssets)", currentAssets.toMap)
51. )
52. }
53. } else {
54. Left(NotEnoughErgsError(
55. s"not enough boxes to meet ERG needs $targetBalance (found only $currentBalance)", currentBalance)
56. )
57. }
58. }

60. /**
61. * Helper method to construct change outputs
62. *
63. * @param foundBalance    - ERG balance of boxes collected
64. *                        (spendable only, so after possibly deducting re-emission tokens)
65. * @param targetBalance   - ERG amount to be transferred to recipients
```

**Additional Observation:**

If the transaction is built using the box with the smaller balance (`InputBox 2`), the transaction executes correctly. In this case, the output is the same balance as the selected box minus the fee. You can see the relevant code in the following link for testing:

[github.com/celaut-project/nodo](https://github.com/celaut-project/nodo/blob/28b600d0cb6bf4464544aee4a4042369cab64e79/src/reputation_system/contracts/ergo.py#L61)

#### [src/reputation\_system/contracts/ergo.py](https://github.com/celaut-project/nodo/blob/28b600d0cb6bf4464544aee4a4042369cab64e79/src/reputation_system/contracts/ergo.py#L61)

[`28b600d0c`](https://github.com/celaut-project/nodo/blob/28b600d0cb6bf4464544aee4a4042369cab64e79/src/reputation_system/contracts/ergo.py#L61)

```ergoscript
52. # 2. Prepare transaction inputs (get UTXOs)
53. input_boxes = ergo.getInputBoxCovering(amount_list=[fee], sender_address=sender_address)
54. print(f"Input boxes: {input_boxes}", flush=True)

56. # 3. Build transaction outputs
57. outputs = []
58. contract_address = sender_address.toString()
59. print(f"Contract address: {contract_address}", flush=True)

61. # Get the input box with min value to avoid NotEnoughErgsError.
62. _input_box = min(input_boxes, key=lambda box: input_box_to_dict(box)['value'], default=input_boxes[0])  # bad practice (two times converted to dict)
63. input_box = input_box_to_dict(_input_box)
64. print(f"Selected input box {input_box['boxId']}", flush=True)
65. value_in_ergs = (input_box["value"] - fee) / 10**9  # Convert from nanoErgs to Ergs
66. print(f"Requested value in Ergs: {value_in_ergs}", flush=True)

68. # Currently not adding proof box, as the buildProofBox function returns None
69. # proof_box = build_proof_box(ergo, value=value_in_ergs, address=contract_address, tokens=[], registers={})
70. output_boxes = ergo.buildOutBox(receiver_wallet_addresses=[contract_address], amount_list=[value_in_ergs])
```

**Questions:**

1. **Why is the box selection algorithm in `ergpy` choosing the box with the smaller amount of ERGs (`InputBox 2`) instead of the one with more (`InputBox 1`)?**
2. **Is there a mechanism in transaction construction that prioritizes spending from boxes with smaller amounts of ERGs before those with larger amounts?**
3. **If box selection is handled automatically, what is the purpose of specifying input boxes when constructing the transaction if the `buildUnsignedTransaction()` function might ignore the optimal box?**
4. **How can I ensure that the appropriate box (the one with more ERGs) is selected to avoid errors in the transaction?**
5. **Is it known if the version of `appkit` used in `ergpy` is the same as the version in the `ergo-appkit` repository? A discrepancy in versions might be causing this unexpected behavior.**

---

### Post #2 — @deathgripson (2024-08-24)

A few things.

1. Noticed you committed “avoid notEnoughErgs error” around the time you posted this, did you find the solution?
2. I copied and ran this locally and it got past the `buildUnsignedTransaction` call so I just want to highlight this edge case is somewhat difficult to reproduce (assuming you didnt commit the fix already, just noticed that).
3. The mnemonic hardcoded in the file is convenient (assuming its testnet only lol) but is really bad practice so please avoid that in the future.
4. Ergpy could overall use some work to make it more intuitive and less prone to throwing exceptions all over the place

---

### Post #3 — @jossemii (2024-08-25)

Thank you for the response.

As a temporary solution, I select as input the box with the lowest balance. This way, the error doesn’t occur. I understand that it might not reproduce in all cases. I’ve been reviewing the AppKit code, and I still don’t see why the error would occur when currentBalance == targetBalance.

P.S.: The mnemonic key comes from the Ergpy repository, but thanks for the advice.

P.S-2: If I have some free time, I might work on improving a few things in Ergpy, as I plan to use it.
