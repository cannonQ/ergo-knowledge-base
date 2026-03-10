---
title: "Nautilus Wallet dApp Connector Guide"
category: skill
difficulty: intermediate
tags: [nautilus, eip-12, dapp-connector, wallet]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Skills/tree/main/skills/nautilus"
updated: 2026-03-09
---

# Nautilus Wallet dApp Connector

Connect to a user's Nautilus wallet on the Ergo blockchain to check balances, get addresses, sign transactions, and submit them to the network, following the EIP-12 dApp Connector standard.

# Nautilus Wallet dApp Connector (EIP-12)

## Overview
This skill provides a comprehensive interface for AI agents to interact with the Nautilus Wallet, a popular browser extension wallet for the Ergo blockchain. It implements the Ergo Improvement Proposal 12 (EIP-12) dApp Connector standard, allowing a dApp (in this case, the AI agent) to request information and actions from the user's wallet securely.

The interaction is asynchronous and brokered entirely by the Nautilus browser extension. The user must manually approve all sensitive actions, such as connecting their wallet, signing transactions, or signing data, via a pop-up dialog from the extension. This ensures user control and security.

### Key Features:
- **Wallet Connection**: Establish and manage a connection to the user's wallet.
- **Balance Inquiry**: Check ERG (the native currency) and other token balances.
- **Address Management**: Retrieve used, unused, and change addresses.
- **Transaction Signing**: Request the user to sign complex Ergo transactions.
- **Data Signing**: Request the user to sign arbitrary string data with a specific address.
- **Transaction Submission**: Submit a signed transaction to the Ergo blockchain through the wallet's node.

## Architecture
The EIP-12 dApp Connector API is injected into the web page's context by the Nautilus Wallet extension. The agent's requests using this skill simulate Javascript code running on that page.

The API is divided into two logical parts:
1.  **Connection API (`ergoConnector`)**: This is always available on any webpage when the extension is active. Its primary purpose is to discover available EIP-12 wallets and initiate a connection request. We will primarily use `ergoConnector.nautilus.connect()`.

2.  **Context API (`ergo`)**: This API becomes available *only after* a successful connection has been approved by the user. It provides the methods to interact with the connected wallet's data and functions (e.g., `get_balance`, `sign_tx`). A successful `connect` command makes this context available for all subsequent commands in this skill.

### Interaction Flow
1.  **Connect**: The agent uses the `connect` command. This triggers a pop-up in the user's wallet asking for permission to connect.
2.  **Wait for Approval**: The agent must wait for the user to approve or deny the connection. The API call is asynchronous and will resolve only after user action.
3.  **Interact**: Once connected, the agent can use other commands like `get_balance` or `sign_tx`. Each sensitive action will again require explicit user approval via a wallet pop-up.

## Authentication and Connection
Authentication is not based on API keys. It is managed entirely through user consent. The `connect` command is the entry point for establishing a session with the wallet.

### Methods

#### `connect`
Initiates a connection request to the Nautilus wallet. This will prompt the user to approve or deny the connection.
- **Returns**: A boolean indicating success or failure of the connection approval.

```javascript
// Simulates the agent's action
const isConnected = await ergoConnector.nautilus.connect();
if (isConnected) {
  // Now the `ergo` object is available
  console.log("Wallet connected successfully.");
} else {
  console.error("User rejected the connection request.");
}
```

#### `is_connected`
Checks if the dApp is currently connected to the wallet.
- **Returns**: A boolean `true` if a connection is active, `false` otherwise.

```javascript
const connectionStatus = await ergoConnector.nautilus.is_connected();
console.log(`Currently connected: ${connectionStatus}`);
```

#### `disconnect`
Terminates the connection to the wallet. This is not typically required but can be used to reset the connection state.
- **Returns**: A boolean indicating if the disconnection was successful.

## Operations (Context API)
These operations are available after a successful `connect` call.

### `get_balance(token_id)`
Retrieves the confirmed balance for a specific token. By default, it fetches the balance for ERG, the native currency.

- **Parameters**:
  - `token_id` (string, optional): The ID of the token to check the balance of. Defaults to `'ERG'`. For other tokens, this is a 32-byte (64-char hex) string.
- **Returns**: A string representing the balance in the smallest unit of the token (nanoERGs for ERG). For an asset with 2 decimal places, a balance of 12.34 would be returned as `'1234'`.

### `get_used_addresses(paging)`
Retrieves a paginated list of addresses that have been used (i.e., have appeared in a transaction on the blockchain).

- **Parameters**:
  - `limit` (integer, optional): The number of addresses to return per page. Defaults to 10.
  - `offset` (integer, optional): The number of addresses to skip. Defaults to 0.
- **Returns**: An array of Base58-encoded address strings.

### `get_unused_addresses()`
Retrieves a list of unused addresses from the wallet's keychain. These are addresses that have been generated but have not yet been involved in any transactions.

- **Parameters**: None.
- **Returns**: An array of Base58-encoded address strings.

### `get_change_address()`
Returns the current designated change address for the wallet. This is where unspent funds from a transaction are typically sent.

- **Parameters**: None.
- **Returns**: A single Base58-encoded address string.

### `sign_tx(tx)`
Requests the user to sign a given unsigned transaction. This is the most complex operation and requires a correctly structured transaction object. The wallet will validate the transaction, display its details to the user, and ask for signing approval.

- **Parameters**:
  - `tx` (`UnsignedTransaction`, required): A JSON object representing the transaction to be signed. See the [Data Structures](#data-structures) section for its format.
- **Returns**: A `SignedTransaction` object, which is the input transaction with `spendingProof` added to each input.

### `sign_tx_input(tx, index)`
Requests the user to sign a single input of an unsigned transaction.

- **Parameters**:
  - `tx` (`UnsignedTransaction`, required): The unsigned transaction containing the input.
  - `index` (integer, required): The 0-based index of the input within the `tx.inputs` array to be signed.
- **Returns**: A `SignedInput` object containing the `boxId` and the generated `spendingProof`.

### `sign_data(address, message)`
Requests the user to sign an arbitrary string message using the private key associated with a specific address in their wallet.

- **Parameters**:
  - `address` (string, required): A Base58-encoded address from the user's wallet that will be used for signing.
  - `message` (string, required): The UTF-8 string message to be signed.
- **Returns**: A string containing the signed message data (often in a structured format like JSON, depending on wallet implementation).

### `submit_tx(tx)`
Submits a signed transaction to the Ergo blockchain via the node connected to the user's wallet.

- **Parameters**:
  - `tx` (`SignedTransaction`, required): A fully signed transaction object.
- **Returns**: A string representing the Transaction ID (`TxId`) if the submission was successful.

## Data Structures

#### `UnsignedTransaction` and `SignedTransaction`
This is the core object for building and signing transactions.

| Field        | Type                          | Description                                                                                                                              |
|--------------|-------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| `id`         | string (optional)             | 32-byte transaction ID (present in `SignedTransaction`).                                                                                 |
| `inputs`     | Array<`UnsignedInput` | `SignedInput`> | The inputs for the transaction, spending existing UTXOs.                                                                                 |
| `dataInputs` | Array<`DataInput`>            | Inputs that are used for context only and are not spent.                                                                                 |
| `outputs`    | Array<`ErgoBoxCandidate`>     | The new boxes (UTXOs) being created by this transaction.                                                                                 |

#### `UnsignedInput`
| Field           | Type              | Description                                                               |
|-----------------|-------------------|---------------------------------------------------------------------------|
| `boxId`         | string            | The ID of the `ErgoBox` (UTXO) to be spent.                                 |
| `extension`     | object            | An empty object `{}` by convention.                                       |

#### `SignedInput`
| Field           | Type              | Description                                                              |
|-----------------|-------------------|--------------------------------------------------------------------------|
| `boxId`         | string            | The ID of the `ErgoBox` (UTXO) to be spent.                                |
| `spendingProof` | `SpendingProof`   | The cryptographic proof that spending is allowed. This is added by the wallet. |

#### `SpendingProof`
| Field      | Type   | Description                                                              |
|------------|--------|--------------------------------------------------------------------------|
| `proofBytes` | string | Hex-encoded string of the proof.                                         |
| `extension`  | object | Context variables, represented as a key-value map. Usually empty.      |

#### `DataInput`
| Field   | Type   | Description                               |
|---------|--------|-------------------------------------------|
| `boxId` | string | The ID of the `ErgoBox` to use as a data-source. |

#### `ErgoBoxCandidate` (Output)
| Field              | Type                      | Description                                                                                               |
|--------------------|---------------------------|-----------------------------------------------------------------------------------------------------------|
| `value`            | string                    | The amount of nanoERGs in the box, as a string.                                                           |
| `ergoTree`         | string                    | Hex-encoded, serialized ErgoTree script that locks the box.                                               |
| `creationHeight`   | integer                   | The blockchain height at which this transaction is valid.                                                 |
| `assets`           | Array<`Token`>            | An array of tokens contained in the box.                                                                  |
| `additionalRegisters` | object                    | A map of non-mandatory registers (R4-R9) containing custom data. E.g., `{"R4": "05a00f..."}`.     |

## Error Handling
The API returns standardized errors as defined by EIP-12.

| Code | Name             | Description                                                                                                  | Agent Action                                                                               |
|------|------------------|--------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| 0    | `APIError`       | An error occurred within the wallet's internal API implementation.                                           | Inform the user of the generic wallet error and suggest they check the wallet for details. |
| 1    | `Refused`        | The user rejected the request (e.g., denied a connection, refused to sign a transaction).                    | Inform the user that they cancelled the request. Do not retry automatically.               |
| 2    | `InvalidRequest` | The request from the dApp (the agent) was malformed (e.g., invalid transaction structure, bad parameters). | This indicates a bug in the agent's request generation. Log the error and the request.     |

An error response object will look like this:
```json
{
  "success": false,
  "error": {
    "code": 1,
    "message": "The user rejected the request."
  }
}
```

## Security Considerations
- **User Consent is Paramount**: The agent must never assume an action will be approved. It should clearly state its intent to the user before calling a sensitive method (e.g., "I will now request to sign a transaction to send 1 ERG. Please review and approve it in your Nautilus wallet.").
- **No Private Key Access**: This skill *never* gives the agent access to private keys. All cryptographic signing happens securely inside the wallet extension.
- **Validate Inputs**: The agent should validate data before constructing transactions to avoid `InvalidRequest` errors.
- **Transaction Verification**: The wallet will display the transaction details for the user to verify. The agent's description of the transaction should match what the user will see in their wallet.

## Troubleshooting
- **`ergoConnector` Not Found**: This means the Nautilus Wallet extension is not installed or enabled in the browser environment where the agent is operating. The skill cannot function without it. Also ensure the page is served over `http://` or `https://` — browser extensions cannot inject `ergoConnector` into `file://` pages (see Protocol Requirement below).
- **Connection Refused**: The user explicitly clicked 'Cancel' or 'Reject' on the connection prompt. The agent should respect this choice.
- **Transaction Signing Fails**: Could be due to `InvalidRequest` (a malformed transaction object sent by the agent) or `Refused` (user cancelled). If it's `InvalidRequest`, the agent must debug the structure of the `tx` object it generated.



## Protocol Requirement

Pages must be served over `http://` or `https://`. Browser extensions cannot inject `ergoConnector` into `file://` pages. Use a local dev server (`npx serve`, `python -m http.server`, VS Code Live Server) during development.

## Extension Injection Timing

`window.ergoConnector` is injected asynchronously by the extension after page load. Do NOT check for it synchronously. Poll for it:

```javascript
function waitForErgoConnector(timeout = 3000) {
    return new Promise(resolve => {
        if (window.ergoConnector) return resolve(true);
        const t0 = Date.now();
        const timer = setInterval(() => {
            if (window.ergoConnector) { clearInterval(timer); resolve(true); }
            else if (Date.now() - t0 >= timeout) { clearInterval(timer); resolve(false); }
        }, 100);
    });
}
```

## Input Schema

```json
{
  "type": "object",
  "required": [
    "command"
  ],
  "properties": {
    "tx": {
      "type": "object",
      "required": [
        "inputs",
        "dataInputs",
        "outputs"
      ],
      "properties": {
        "id": {
          "type": "string"
        },
        "inputs": {
          "type": "array",
          "items": {
            "type": "object"
          }
        },
        "outputs": {
          "type": "array",
          "items": {
            "type": "object"
          }
        },
        "dataInputs": {
          "type": "array",
          "items": {
            "type": "object"
          }
        }
      },
      "description": "A JSON object representing an UnsignedTransaction for 'sign_tx'/'sign_tx_input' or a SignedTransaction for 'submit_tx'."
    },
    "index": {
      "type": "integer",
      "minimum": 0,
      "description": "The 0-based index of the transaction input to sign for the 'sign_tx_input' command."
    },
    "limit": {
      "type": "integer",
      "default": 10,
      "maximum": 100,
      "minimum": 1,
      "description": "Pagination limit for list operations like get_used_addresses."
    },
    "offset": {
      "type": "integer",
      "default": 0,
      "minimum": 0,
      "description": "Pagination offset for list operations like get_used_addresses."
    },
    "address": {
      "type": "string",
      "pattern": "^9[a-zA-Z0-9]{50}$",
      "description": "The Base58-encoded address to use for signing a message with the 'sign_data' command."
    },
    "command": {
      "enum": [
        "connect",
        "is_connected",
        "disconnect",
        "get_balance",
        "get_used_addresses",
        "get_unused_addresses",
        "get_change_address",
        "sign_tx",
        "sign_tx_input",
        "sign_data",
        "submit_tx"
      ],
      "type": "string",
      "description": "The Nautilus wallet operation to perform."
    },
    "message": {
      "type": "string",
      "description": "The UTF-8 message string to sign for the 'sign_data' command."
    },
    "token_id": {
      "type": "string",
      "default": "ERG",
      "description": "The token ID for getting a balance. Defaults to 'ERG'. For other tokens, this is a 64-character hex string."
    }
  }
}
```

## Output Schema

```json
{
  "type": "object",
  "required": [
    "success"
  ],
  "properties": {
    "error": {
      "type": "object",
      "properties": {
        "code": {
          "enum": [
            0,
            1,
            2
          ],
          "type": "integer",
          "description": "EIP-12 error code (0: APIError, 1: Refused, 2: InvalidRequest)."
        },
        "message": {
          "type": "string",
          "description": "A human-readable error message."
        }
      },
      "description": "Present only on failure."
    },
    "status": {
      "type": "string",
      "description": "Provides a high-level status of the response, e.g., 'connected', 'balance_retrieved', 'transaction_signed'."
    },
    "balance": {
      "type": "string",
      "description": "The retrieved token balance, in its smallest unit (e.g., nanoERG). Only present on successful 'get_balance' calls."
    },
    "success": {
      "type": "boolean",
      "description": "Indicates if the operation was successful."
    },
    "addresses": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "An array of Base58-encoded address strings. Present on successful calls to 'get_used_addresses', 'get_unused_addresses'."
    },
    "signed_input": {
      "type": "object",
      "description": "The signed input object with spending proof. Present on successful 'sign_tx_input' calls."
    },
    "change_address": {
      "type": "string",
      "description": "A single Base58-encoded change address. Present on successful 'get_change_address' calls."
    },
    "signed_message": {
      "type": "string",
      "description": "The signature result from a 'sign_data' call."
    },
    "transaction_id": {
      "type": "string",
      "description": "The ID of the submitted transaction. Present on successful 'submit_tx' calls."
    },
    "connection_state": {
      "type": "boolean",
      "description": "The result of 'connect', 'is_connected', and 'disconnect' commands."
    },
    "signed_transaction": {
      "type": "object",
      "description": "The signed transaction object. Present on successful 'sign_tx' calls."
    }
  }
}
```

## Examples

### Happy path for getting the native ERG balance. Assumes a connection is already established. The balance is 15 ERG.

**Input:**
```json
{
  "command": "get_balance",
  "token_id": "ERG"
}
```

**Output:**
```json
{
  "status": "balance_retrieved",
  "balance": "15000000000",
  "success": true
}
```

### Error case where the user denies the initial connection request from the dApp.

**Input:**
```json
{
  "command": "connect"
}
```

**Output:**
```json
{
  "error": {
    "code": 1,
    "message": "The user rejected the request."
  },
  "status": "connection_refused",
  "success": false
}
```

### Complex example to sign a transaction sending 1 ERG to one address and returning the change. The output includes the `spendingProof` added by the wallet.

**Input:**
```json
{
  "tx": {
    "inputs": [
      {
        "boxId": "e56847ed19b3dc6b72828fcfb992fdf731087481716529f057144043b23e3f3b",
        "extension": {}
      }
    ],
    "outputs": [
      {
        "value": "1000000000",
        "assets": [],
        "ergoTree": "1005040004000e3610027300000193c27201c2a7017301007302720205040004000d830d19d1edededab0272030d1a4c7201",
        "creationHeight": 850000,
        "additionalRegisters": {}
      },
      {
        "value": "13500000000",
        "assets": [],
        "ergoTree": "1002070100e402d192a39a8cc7a70173007301",
        "creationHeight": 850000,
        "additionalRegisters": {}
      }
    ],
    "dataInputs": []
  },
  "command": "sign_tx"
}
```

**Output:**
```json
{
  "status": "transaction_signed",
  "success": true,
  "signed_transaction": {
    "id": "f9e5ce5aa0d95f5d54a7bc89c46730d9a623271d7b427284c7959a803a52d9a6",
    "inputs": [
      {
        "boxId": "e56847ed19b3dc6b72828fcfb992fdf731087481716529f057144043b23e3f3b",
        "spendingProof": {
          "extension": {},
          "proofBytes": "f8a2f64608c02a7ea634447362a7a516599182ff5e01b349cf2a9f775d71a856a4220202"
        }
      }
    ],
    "outputs": [
      {
        "value": "1000000000",
        "assets": [],
        "ergoTree": "1005040004000e3610027300000193c27201c2a7017301007302720205040004000d830d19d1edededab0272030d1a4c7201",
        "creationHeight": 850000,
        "additionalRegisters": {}
      },
      {
        "value": "13500000000",
        "assets": [],
        "ergoTree": "1002070100e402d192a39a8cc7a70173007301",
        "creationHeight": 850000,
        "additionalRegisters": {}
      }
    ],
    "dataInputs": []
  }
}
```

### Paginated request to get the first 5 used addresses from the user's wallet.

**Input:**
```json
{
  "limit": 5,
  "offset": 0,
  "command": "get_used_addresses"
}
```

**Output:**
```json
{
  "status": "addresses_retrieved",
  "success": true,
  "addresses": [
    "9f5q4Y5d1jV3fXz5fC2b3gH4jK5lM6nN7pQ8rT9vXwY2zZ1bC",
    "9hA2xR8cT3Z9Y1vF4bW6kL7mM8pD9qS5vXzZ1bC3gF4jK5lM",
    "9gE7yZ3kL5nM7pQ9rT1vXwY2zZ1bC3fXz5fC2b3gH4jK5lM",
    "9iB3fXz5fC2b3gH4jK5lM6nN7pQ8rT9vXwY2zZ1bC3hA2xR",
    "9eR8cT3Z9Y1vF4bW6kL7mM8pD9qS5vXzZ1bC3gF4jK5lM7pQ"
  ]
}
```

## Permissions

- `browser:extension:read:nautilus`
- `browser:extension:execute:nautilus`
- `pii:read:financial_balance`
- `pii:read:wallet_address`
- `pii:execute:financial_transaction`

## Constraints

- This skill requires the user to have the Nautilus Wallet browser extension installed and active.
- Sensitive operations (connect, sign_tx, sign_data) require manual user approval and may time out if the user does not respond.
- Recommended timeout for waiting on user interaction: 300 seconds.
- Transaction object payloads should not exceed 32KB.
- GET operations (get_balance, get_*_addresses) are idempotent. Signing and submitting operations are not.
- All ERG amounts are specified in nanoERG (1 ERG = 1,000,000,000 nanoERG) as strings.
