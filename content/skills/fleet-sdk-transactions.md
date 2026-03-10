---
title: "Fleet SDK Transaction Builder Guide"
category: skill
difficulty: intermediate
tags: [fleet-sdk, transactions, tokens, registers]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Skills/tree/main/skills/ergo-fleet-sdk"
updated: 2026-03-09
---

# Fleet SDK: Ergo Transaction Builder

Build and sign a transaction for the Ergo blockchain using the Fleet SDK. This skill constructs a transaction from specified inputs and outputs, signs it with a provided key, and returns the EIP-12 compliant transaction object.


## Fleet SDK: Ergo Transaction Builder

### Overview

This skill provides a high-level interface for creating, signing, and broadcasting transactions on the Ergo blockchain. Leveraging the powerful [Fleet SDK for Ergo](https://github.com/fleet-sdk/fleet), it abstracts away the complexities of Ergo's extended Unspent Transaction Output (eUTXO) model. This enables developers to focus on application logic rather than intricate, low-level transaction assembly. You can define inputs (the "coins" you want to spend), outputs (where the coins are going), reference data from the blockchain without spending it, and attach arbitrary data to your transactions.

### The Ergo eUTXO Model

To effectively use this skill, it's essential to understand the eUTXO model that Ergo employs. Unlike the account-based model of Ethereum, where balances are stored in accounts, Ergo uses a model similar to Bitcoin but with significant enhancements.

- **Boxes**: In Ergo, funds and data are stored in "boxes" on the blockchain. Each box is protected by a script (called an `ergoTree`) and contains a value in the native currency (ERG), optional tokens (assets), and several programmable registers for storing data.
- **Transactions**: A transaction consumes one or more existing boxes (called `inputs`) and creates one or more new boxes (called `outputs`). The fundamental rule is that the total value of ERG and any other tokens in the inputs must equal the total value in the outputs, plus a small transaction fee.
- **Statefulness**: The scripts and data within boxes allow for the creation of smart contracts. The `ergoTree` of a box dictates the conditions under which it can be spent. This allows for complex dApp logic, where the state of the application is encoded across a set of UTXOs.

This skill simplifies the process by allowing you to define the contents of your transaction in a straightforward JSON format. It handles the complexities of script compilation, serialization, and cryptographic signing.

### Core Concepts of Transaction Building

A transaction is fundamentally a declaration of intent: to consume specific boxes and create new ones. Here’s a breakdown of the primary components you'll provide as input.

#### **Inputs (`inputs`)**

These are the boxes you intend to spend. To spend a box, you must possess the private key corresponding to the address that controls it. You must provide a complete representation of each input box.

- `boxId`: The unique identifier for the box.
- `transactionId` & `index`: Identifies the transaction and output index that created this box.
- `ergoTree`: The hex-encoded locking script. The skill needs this to create the context for the signature.
- `creationHeight`: The block height at which the box was created.
- `value`: The amount of ERG in the box, specified in nanoERGs (1 ERG = 1,000,000,000 nanoERGs).
- `assets`: An array of tokens held in the box.
- `additionalRegisters`: Any data stored in the box's non-mandatory registers (R4-R9).

Typically, you would get this information by querying a public Ergo node API or an explorer for all unspent boxes at your address.

#### **Outputs (`outputs`)**

These are the new boxes that will be created when the transaction is successfully mined. 

- `address`: The recipient's public address (P2PK or P2S). The skill will compile this into the necessary `ergoTree`.
- `value`: The amount of nanoERGs to send to this output.
- `assets`: An array of tokens to include in the output box.
- `registers`: An object allowing you to write data to registers R4-R9. This is how you attach custom data to an output, which is essential for most dApp interactions. The data must be a Sigma-serialized, hex-encoded string.

#### **Data Inputs (`dataInputs`)**

A revolutionary feature of Ergo, data inputs allow a transaction to reference data from any box on the blockchain without spending it. This is incredibly powerful for dApps. For instance, an oracle can publish data (like an asset price) in a box, and other contracts can reference this data in their transactions without needing to consume the oracle's box. You only need to provide the `boxId` of the box you wish to reference.

#### **Fees and Change**

- `fee`: Every transaction must include a fee for the miners. The fee is paid from the sum of the inputs. The current minimum transaction fee on Ergo is 1,000,000 nanoERGs (0.001 ERG).
- `changeAddress`: In the UTXO model, you must spend a box in its entirety. If the total value of your inputs is greater than the value of your outputs plus the fee, the remainder is "change." You must specify a `changeAddress` where this remainder (including any un-spent tokens) will be sent. The skill automatically calculates the correct change amount and creates a new box for it.

### Advanced Features

#### **Working with Tokens**

Ergo treats tokens as first-class citizens. You can transfer them just like ERG. 
- **Transferring Tokens**: To transfer a token, you must use an input box that contains that token. Then, you simply add that token to the `assets` array of one of your outputs.
- **Minting Tokens**: You can mint new tokens in a transaction. According to Ergo protocol rules, the `tokenId` of a newly minted token is the `boxId` of the *first input* in the transaction. To mint, you create a transaction where the `assets` array of an output contains an object with the new `tokenId` (matching `inputs[0].boxId`) and the desired `amount` to create.

#### **Custom Data with Registers (R4-R9)**

The ability to store custom data in boxes is what makes complex smart contracts possible. Registers `R4` through `R9` are available for arbitrary data. However, the data cannot be a simple string; it must be valid, Sigma-serialized, and then hex-encoded. 

**Example of Sigma Serialization**:

Let's say you want to store the integer `12345` in register `R4`. You can't just use `"R4": "12345"`. You must serialize it first. An `SInt(12345)` value serializes to `0e29c2d101`. So your output register would look like:

`"registers": { "R4": "0e29c2d101" }`

The Fleet SDK offers tools to correctly serialize various data types (Int, Long, Coll[Byte], Tuple, etc.) into this format.

### Security Best Practices

**CRITICAL: `signingKey` Management**

The `signingKey` field expects your raw 32-byte private key, encoded as a hex string. This is extremely sensitive information. 

- **DO NOT** hardcode private keys in your code.
- **DO NOT** commit keys to version control (e.g., Git, Subversion).
- **DO NOT** expose this skill's endpoint publicly without a robust authentication and authorization layer.
- **DO** load the key from a secure source at runtime, such as an environment variable, a managed secret store (like AWS Secrets Manager, Google Secret Manager, or HashiCorp Vault), or a Hardware Security Module (HSM).

Failure to secure your signing keys will almost certainly result in the permanent loss of your funds.

#### **Transaction Verification**

Before sending a transaction request to this skill, especially in an automated environment, it is wise to have a verification step. Log and double-check the final structure of the transaction JSON. Ensure the output addresses, values, and token amounts are exactly what you intend. A small mistake in your application logic could lead to sending funds to an incorrect address.

### Full Walkthrough Example

Let's build a simple P2PK (Pay-to-Public-Key) transaction.

1.  **Goal**: Send 0.5 ERG from our address to a recipient.
2.  **Gather Inputs**: First, we use an explorer API to find an unspent box at our address. Let's say we find one with 1 ERG in it.
    - We get its full JSON representation (boxId, value, ergoTree, etc.).
3.  **Define Outputs**:
    - One output for the recipient: `address` will be their address, `value` will be "500000000" (0.5 ERG).
    - We don't need to define the change output; the skill will do that for us.
4.  **Define Fee and Change**: 
    - We set the `fee` to the minimum: "1000000".
    - We set our `changeAddress` to our own address, so the remaining ~0.499 ERG comes back to us.
5.  **Provide Key**: We provide our hex-encoded `signingKey`.
6.  **Construct and Send**: We assemble all this into the final JSON input and call the skill. The skill will return a signed EIP-12 transaction object, ready to be broadcast to any Ergo node.

### Error Handling

If transaction construction fails, the skill will return an error message. Common causes of failure include:

- **Insufficient Funds**: The total value of `inputs` is less than the `outputs` + `fee`.
- **Invalid Signature**: The provided `signingKey` does not correspond to the `ergoTree` of the input boxes.
- **Invalid Register Data**: The data provided in a `registers` field is not correctly Sigma-serialized.
- **Violated Protocol Rules**: The transaction violates a constraint, such as creating tokens with a `tokenId` that isn't the first input's `boxId`.
- **Exceeding Constraints**: The transaction has too many inputs/outputs or the payload is too large.


## Input Schema

```json
{
  "required": [
    "inputs",
    "outputs",
    "signingKey",
    "changeAddress"
  ],
  "properties": {},
  "type": "object"
}
```

## Output Schema

```json
{
  "properties": {},
  "required": [
    "id",
    "inputs",
    "dataInputs",
    "outputs",
    "size"
  ],
  "type": "object"
}
```

## Examples

### A simple P2PK (pay-to-public-key) transfer of 1 ERG from one address to another, accounting for transaction fees and change.

**Input:**
```json
{}
```

**Output:**
```json
{}
```

**Code Example:**
```
curl -X POST 'https://<skill_endpoint>/build-transaction' \
-H 'Content-Type: application/json' \
-d '{
  "inputs": [
    {
      "boxId": "e56847ed19b3dc6b72828fcfb0b9f81211b9c9f21c231a4c281728c738d098a3",
      "transactionId": "f9e5ce5aa0d95f5d54a7bc89c46730d9a623271d7b4d6209f7a4a9829f7f9e57",
      "index": 0,
      "ergoTree": "0008cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798",
      "creationHeight": 667000,
      "value": "1100000000",
      "assets": [],
      "additionalRegisters": {}
    }
  ],
  "outputs": [
    {
      "address": "9f4QF8AD1nQ3n6vTce4s1g8d3Gci42e1a1f2y3z4A5b6c7d8e9f0",
      "value": "1000000000"
    }
  ],
  "fee": "1000000",
  "changeAddress": "9hY1As6kFAa46s1s5v8d7f9g0h1j2k3l4m5n6b7v8c9x0z1y2w3",
  "signingKey": "...your_securely_handled_private_key..."
}'
```

### A complex transaction that consolidates two inputs, sends ERG and a custom token to a dApp address, references an oracle's data box, and attaches custom register data.

**Input:**
```json
{}
```

**Output:**
```json
{}
```

**Code Example:**
```
import requests
import json

skill_url = 'https://<skill_endpoint>/build-transaction'

# This is example data. In a real application, you would fetch unspent boxes
# and construct this dynamically.
transaction_input = {
    "inputs": [
        {
            "boxId": "1a2b3c4d...",
            "transactionId": "5e6f7a8b...",
            "index": 0,
            "ergoTree": "0008cd02...",
            "creationHeight": 650000,
            "value": "2000000000",
            "assets": [],
            "additionalRegisters": {}
        },
        {
            "boxId": "9z8y7x6w...",
            "transactionId": "5v4u3t2s...",
            "index": 1,
            "ergoTree": "0008cd02...",
            "creationHeight": 651000,
            "value": "1500000000",
            "assets": [
                {"tokenId": "abcdef0123...", "amount": "100"}
            ],
            "additionalRegisters": {}
        }
    ],
    "dataInputs": [
        {"boxId": "oraclebox123..."}
    ],
    "outputs": [
        {
            "address": "dAppAddress...",
            "value": "3000000000",
            "assets": [
                {"tokenId": "abcdef0123...", "amount": "50"}
            ],
            "registers": {
                "R4": "0e0568656c6c6f" # Sigma-serialized 'hello'
            }
        }
    ],
    "fee": "2000000",
    "changeAddress": "myChangeAddress...",
    "signingKey": "...your_securely_handled_private_key..."
}

response = requests.post(skill_url, json=transaction_input)

if response.status_code == 200:
    signed_transaction = response.json()
    print("Successfully built transaction:")
    print(json.dumps(signed_transaction, indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)

```

### A transaction that mints a new custom token. The first input box's ID becomes the token ID. The new token is sent to the creator's address.

**Input:**
```json
{}
```

**Output:**
```json
{}
```

**Code Example:**
```
import axios from 'axios';

const skillEndpoint = 'https://<skill_endpoint>/build-transaction';

// The boxId of this first input will become the tokenId of the new asset.
const mintingInput = {
  boxId: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
  transactionId: 'b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2',
  index: 0,
  ergoTree: '0008cd03...your_ergo_tree...',
  creationHeight: 670000,
  value: '200000000',
  assets: [],
  additionalRegisters: {},
};

const transactionData = {
  inputs: [mintingInput],
  outputs: [
    {
      address: '9hY1As6kFAa46s1s5v8d7f9g0h1j2k3l4m5n6b7v8c9x0z1y2w3', // Your address
      value: '198000000', // Input value minus fee
      assets: [
        {
          tokenId: mintingInput.boxId, // New token ID MUST match the first input's boxId
          amount: '1000', // Mint 1000 new tokens
        },
      ],
      registers: {
        // You can optionally add token details here
        R4: '0e044e414d45', // Serialized token name 'NAME'
        R5: '0e0a4445534352495054494f4e', // Serialized 'DESCRIPTION'
        R6: '0e0132', // Serialized decimals '2'
      },
    },
  ],
  fee: '2000000',
  changeAddress: '9hY1As6kFAa46s1s5v8d7f9g0h1j2k3l4m5n6b7v8c9x0z1y2w3',
  signingKey: process.env.MY_WALLET_PRIVATE_KEY, // Loaded from environment variables
};

async function mintToken() {
  try {
    const response = await axios.post(skillEndpoint, transactionData);
    console.log('Signed Token Mint Transaction:', JSON.stringify(response.data, null, 2));
    return response.data;
  } catch (error) {
    console.error('Error minting token:', error.response?.data || error.message);
  }
}

mintToken();
```

## Permissions

- `keystore:read:signingKey`
- `ergo_blockchain:read:utxoInfo`

## Constraints

- Maximum execution time: 15 seconds. Transactions that require complex computations or involve a very large number of inputs/outputs might time out.
- Maximum inputs per transaction: 70. This is a hard limit imposed by the underlying Ergo protocol.
- Maximum outputs per transaction: 70. Similar to the input limit, this is a protocol-level constraint.
- Maximum request payload size: 32KB. The entire JSON input for the transaction build must not exceed this size.
