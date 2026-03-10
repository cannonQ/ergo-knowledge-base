---
title: "ergo-lib-wasm Cryptographic Toolkit Guide"
category: skill
difficulty: advanced
tags: [ergo-lib-wasm, wasm, sigma-rust, addresses, transactions]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Skills/tree/main/skills/ergo-wasm-cryptographic-toolkit"
updated: 2026-03-09
---

# Ergo WASM Cryptographic Toolkit

A comprehensive client-side toolkit for creating, signing, and manipulating Ergo blockchain data structures like transactions, addresses, and contracts using WASM-compiled sigma-rust cryptographic libraries.

# Ergo WASM Cryptographic Toolkit

## 1. Overview

This skill provides access to the powerful `ergo-lib-wasm` library, a WebAssembly (WASM) implementation of the core cryptographic and data structure primitives of the Ergo blockchain. It enables AI agents to perform complex, low-level cryptographic operations directly, without needing to trust a third-party service for key management or transaction construction.

Critically, this skill operates **client-side**. It does **not** communicate with the Ergo blockchain network. Its purpose is to prepare data structures (like signed transactions) that can then be broadcast to the network using a separate tool or Ergo node.

Key capabilities include:

- **Address Generation & Validation**: Create and validate Ergo P2PK (Pay-to-Public-Key) and P2S (Pay-to-Script) addresses for both mainnet and testnet.
- **ErgoTree Manipulation**: Work with the ErgoTree contract language, deriving addresses from scripts.
- **Unsigned Transaction Construction**: Build complex transactions from scratch, specifying inputs (UTXOs), outputs (including those with tokens and registers), data-inputs, and fees.
- **Transaction Signing**: Securely sign transactions using a provided private key.
- **Cryptographic Utilities**: Includes tools for Merkle tree generation and verification.

This skill is essential for any agent that needs to build applications, wallets, or services that interact with the Ergo blockchain in a decentralized and secure manner.

## 2. Architecture

The skill is a wrapper around the `@ergoplatform/ergo-lib-wasm` NPM package. This package contains Rust code from the `sigma-rust` project, which has been compiled into a WebAssembly module. JavaScript/TypeScript bindings provide a user-friendly API to interact with the underlying WASM functions.

**Execution Flow:**
1. The AI agent invokes the skill with a specific `command` and its associated parameters.
2. The skill's runtime loads the WASM module and its JS bindings.
3. The specified command is mapped to the corresponding JS function call.
4. Input parameters (often JSON objects or hex strings) are serialized into formats the WASM functions can understand.
5. The WASM functions execute the cryptographic operations entirely in the local environment.
6. The result is returned from WASM, deserialized into a user-friendly JSON format, and provided as the skill's output.

This architecture ensures that sensitive data, especially private keys, never leaves the execution environment, providing the highest level of security.

## 3. Authentication & Security

This skill has no traditional authentication (e.g., API keys) because it runs locally. Security is managed through careful handling of cryptographic secrets.

### **Private Key Management**

**THIS IS THE MOST CRITICAL SECURITY CONSIDERATION.**

The `sign_transaction` command requires a 32-byte private key (represented as a 64-character hex string). The security of all funds controlled by this key depends on its confidentiality.

- **NEVER** store private keys in plain text.
- **NEVER** log private keys.
- **NEVER** hard-code private keys in prompts or scripts.
- **ALWAYS** source private keys from a secure, encrypted vault or secrets manager *at the moment of signing*.
- **ALWAYS** clear the private key from memory immediately after the signing operation is complete.

An agent MUST treat any input parameter named `privateKey` or similar as extremely sensitive data, equivalent to a password for a bank account.

### Input Validation

All inputs, especially those used for transaction construction, must be rigorously validated. Malformed inputs could lead to the creation of invalid transactions, loss of funds, or unexpected errors in the WASM module. The agent should verify address formats, amounts, and box structures before calling the skill.

## 4. Operations (Commands)

This skill is controlled via the `command` parameter. Each command performs a distinct operation.

### `validate_address`

Validates if a given string is a correctly formatted Ergo address. It checks encoding, checksum, and network prefix.

- **Request Parameters**:
  - `address` (string, required): The Base58-encoded Ergo address string to validate.

- **Success Response**:
  - `isValid` (boolean): `true` if the address is valid.
  - `network` (string): The network the address belongs to (`mainnet` or `testnet`).
  - `address` (string): The input address that was validated.

- **Error Response**: Throws an error for invalid formats, which is caught and returned as a structured error object.

### `address_from_pk`

Creates a standard P2PK (Pay-to-Public-Key) address from a public key.

- **Request Parameters**:
  - `publicKey` (string, required): The hex-encoded SEC1-encoded compressed public key (33 bytes).
  - `network` (string, optional, default: `mainnet`): `mainnet` or `testnet`.

- **Success Response**:
  - `address` (string): The generated Base58-encoded Ergo address.

### `address_from_ergo_tree`

Derives an address from a serialized ErgoTree (a contract script).

- **Request Parameters**:
  - `ergoTree` (string, required): The hex-encoded string of the serialized ErgoTree.
  - `network` (string, optional, default: `mainnet`): `mainnet` or `testnet`.

- **Success Response**:
  - `address` (string): The generated Base58-encoded P2S (Pay-to-Script) address.

### `create_unsigned_transaction`

Constructs an unsigned Ergo transaction. This is the most complex operation, requiring careful assembly of inputs and outputs.

- **Request Parameters**:
  - `inputs` (array, required): An array of `UnspentBox` objects to be used as inputs.
  - `outputs` (array, required): An array of `BoxCandidate` objects to be created as outputs.
  - `fee` (string, required): The transaction fee in nanoERGs, as a string.
  - `changeAddress` (string, required): The Ergo address where change (inputs minus outputs and fee) will be sent.
  - `dataInputs` (array, optional): An array of `DataInput` objects, used to provide read-only context to scripts.
  - `currentHeight` (integer, required): The current blockchain height, necessary for transaction validity.

- **Success Response**:
  - `unsignedTransaction` (object): A JSON representation of the created unsigned transaction, which can be passed to `sign_transaction`.

- **Error Response**: Will fail if input values do not cover output values + fee, or if any structures are malformed.

### `sign_transaction`

Signs a previously created unsigned transaction with a private key.

- **Request Parameters**:
  - `unsignedTransaction` (object, required): The JSON object returned by `create_unsigned_transaction`.
  - `inputs` (array, required): The same array of `UnspentBox` objects that were used to create the unsigned transaction. This is required by the library for context.
  - `dataInputs` (array, optional): The same array of `DataInput` objects used for creation.
  - `privateKey` (string, required): The 64-character hex-encoded private key for signing. **EXTREMELY SENSITIVE.**

- **Success Response**:
  - `signedTransaction` (object): A JSON representation of the fully signed transaction, ready to be broadcast to an Ergo node.
  - `transactionId` (string): The ID of the signed transaction.

## 5. Data Structures

Understanding these structures is crucial for using the skill effectively.

| Structure | Description |
|---|---|
| **UnspentBox** | Represents a UTXO (Unspent Transaction Output) on the blockchain. Used as an `input` for new transactions. |
| `boxId` | string (hex) | The unique identifier of the box. |
| `transactionId` | string (hex) | The ID of the transaction that created this box. |
| `index` | integer | The output index in the creation transaction. |
| `value` | string | The amount of ERG in the box, in nanoERGs, as a string. |
| `ergoTree` | string (hex) | The serialized contract script that guards the box. |
| `creationHeight`| integer | The block height at which this box was created. |
| `assets` | array | An array of `Token` objects contained in the box. `[{ tokenId: string, amount: string }]` |
| `additionalRegisters` | object | Key-value store of non-mandatory registers (R4-R9) in the box. e.g., `{"R4": "05a00f"}` |

| Structure | Description |
|---|---|
| **BoxCandidate** | Represents a new output to be created in a transaction. |
| `value` | string | The amount of ERG for this new box, in nanoERGs, as a string. |
| `ergoTree` | string (hex) | The serialized contract script that will guard this new box. |
| `creationHeight`| integer | The current block height; the height at which this box will be created. |
| `assets` | array | An array of `Token` objects to be included. `[{ tokenId: string, amount: string }]` |
| `additionalRegisters`| object | Key-value store of registers (R4-R9) for this new box. |

| Structure | Description |
|---|---|
| **DataInput** | Represents a read-only input to a transaction, providing context to scripts without spending the box. |
| `boxId` | string (hex) | The unique identifier of the box to be used as a data-input. |

## 6. Error Handling

Errors from the underlying WASM library are caught and surfaced as a structured JSON object. Always check for the presence of an `error` field in the response.

**Common Error Patterns:**

| Error Code | Description | Suggested Action |
|---|---|---|
| `InvalidAddress` | The provided address string has an invalid format, checksum, or network prefix. | Check the address for typos. Ensure it's a valid Base58 string for the correct network. |
| `InvalidHex` | An input string (e.g., `publicKey`, `ergoTree`, `privateKey`) is not valid hexadecimal. | Ensure the string contains only characters 0-9 and a-f, and has the correct length. |
| `WasmPanic` | An unrecoverable error occurred inside the WASM module, often due to malformed input structures. | This is a bug or invalid input. Double-check all input object structures, especially for `create_unsigned_transaction`. |
| `InsufficientFunds` | The total value of `inputs` is less than the total value of `outputs` plus the `fee`. | Correct the transaction logic; ensure `sum(inputs) >= sum(outputs) + fee`. |
| `SigningError` | The private key could not sign the transaction. May be due to a malformed key or a mismatch between the key and the input boxes' ErgoTrees. | Verify the private key is correct and corresponds to the public key that guards the input boxes. |

## 7. Constraints & Edge Cases

- **Execution Environment**: This skill executes locally. Performance depends on the host machine's CPU. Operations are generally very fast (<50ms).
- **No Network I/O**: The skill does not perform any network requests itself.
- **Idempotency**: All operations are deterministic. Given the same inputs, the skill will always produce the same output.
- **Private Key Format**: Must be a 64-character hex string representing 32 bytes.
- **Public Key Format**: Must be a 66-character hex string representing a 33-byte compressed SEC1-encoded point.
- **Amounts**: All ERG values (`value`, `fee`) are specified in **nanoERGs** (1 ERG = 1,000,000,000 nanoERGs) and must be passed as strings to avoid precision loss with large numbers.

## Input Schema

```json
{
  "type": "object",
  "required": [
    "command"
  ],
  "properties": {
    "fee": {
      "type": "string",
      "pattern": "^[0-9]+$",
      "description": "Transaction fee in nanoERGs, as a string to preserve precision. Required for `create_unsigned_transaction`."
    },
    "inputs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "boxId",
          "transactionId",
          "index",
          "value",
          "ergoTree",
          "creationHeight",
          "assets",
          "additionalRegisters"
        ],
        "properties": {
          "boxId": {
            "type": "string",
            "pattern": "^[a-fA-F0-9]{64}$"
          },
          "index": {
            "type": "integer"
          },
          "value": {
            "type": "string",
            "pattern": "^[0-9]+$"
          },
          "assets": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "amount": {
                  "type": "string",
                  "pattern": "^[0-9]+$"
                },
                "tokenId": {
                  "type": "string",
                  "pattern": "^[a-fA-F0-9]{64}$"
                }
              }
            }
          },
          "ergoTree": {
            "type": "string",
            "pattern": "^[a-fA-F0-9]+$"
          },
          "transactionId": {
            "type": "string",
            "pattern": "^[a-fA-F0-9]{64}$"
          },
          "creationHeight": {
            "type": "integer"
          },
          "additionalRegisters": {
            "type": "object"
          }
        }
      },
      "description": "Array of UnspentBox objects. Required for `create_unsigned_transaction` and `sign_transaction`."
    },
    "address": {
      "type": "string",
      "description": "Base58-encoded Ergo address. Required for `validate_address`."
    },
    "command": {
      "enum": [
        "validate_address",
        "address_from_pk",
        "address_from_ergo_tree",
        "create_unsigned_transaction",
        "sign_transaction"
      ],
      "type": "string",
      "description": "The specific Ergo WASM operation to execute."
    },
    "network": {
      "enum": [
        "mainnet",
        "testnet"
      ],
      "type": "string",
      "default": "mainnet",
      "description": "The target Ergo network."
    },
    "outputs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "value": {
            "type": "string",
            "pattern": "^[0-9]+$"
          },
          "assets": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "amount": {
                  "type": "string",
                  "pattern": "^[0-9]+$"
                },
                "tokenId": {
                  "type": "string",
                  "pattern": "^[a-fA-F0-9]{64}$"
                }
              }
            }
          },
          "ergoTree": {
            "type": "string",
            "pattern": "^[a-fA-F0-9]+$"
          },
          "creationHeight": {
            "type": "integer"
          },
          "additionalRegisters": {
            "type": "object"
          }
        }
      },
      "description": "Array of BoxCandidate objects. Required for `create_unsigned_transaction`."
    },
    "ergoTree": {
      "type": "string",
      "pattern": "^[a-fA-F0-9]+$",
      "description": "A hex-encoded serialized ErgoTree (contract script). Required for `address_from_ergo_tree` and fields within boxes."
    },
    "publicKey": {
      "type": "string",
      "pattern": "^0[23][a-fA-F0-9]{64}$",
      "description": "A 33-byte SEC1-encoded compressed public key, as a 66-character hex string. Required for `address_from_pk`."
    },
    "dataInputs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "boxId": {
            "type": "string",
            "pattern": "^[a-fA-F0-9]{64}$"
          }
        }
      },
      "description": "Array of DataInput objects. Optional for `create_unsigned_transaction` and `sign_transaction`."
    },
    "privateKey": {
      "type": "string",
      "pattern": "^[a-fA-F0-9]{64}$",
      "description": "A 32-byte private key, as a 64-character hex string. EXTREMELY SENSITIVE. Required for `sign_transaction`."
    },
    "changeAddress": {
      "type": "string",
      "description": "The Ergo address for change. Required for `create_unsigned_transaction`."
    },
    "currentHeight": {
      "type": "integer",
      "minimum": 1,
      "description": "The current blockchain height. Required for `create_unsigned_transaction`."
    },
    "unsignedTransaction": {
      "type": "object",
      "description": "A JSON object representing an unsigned transaction, typically the output of `create_unsigned_transaction`. Required for `sign_transaction`."
    }
  }
}
```

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "error": {
      "type": "object",
      "properties": {
        "code": {
          "type": "string",
          "description": "A short error identifier, e.g., 'InvalidAddress'."
        },
        "message": {
          "type": "string",
          "description": "A human-readable description of the error."
        }
      },
      "description": "Present only on failure."
    },
    "address": {
      "type": "string",
      "description": "The result of an address generation or validation command."
    },
    "isValid": {
      "type": "boolean",
      "description": "Present for `validate_address`. True if the address format is correct."
    },
    "network": {
      "enum": [
        "mainnet",
        "testnet"
      ],
      "type": "string",
      "description": "Present for `validate_address`. Indicates the address network."
    },
    "transactionId": {
      "type": "string",
      "description": "The ID of the signed transaction. Output of `sign_transaction`."
    },
    "signedTransaction": {
      "type": "object",
      "description": "The JSON representation of the signed transaction, ready for broadcast. Output of `sign_transaction`."
    },
    "unsignedTransaction": {
      "type": "object",
      "description": "The JSON representation of the unsigned transaction. Output of `create_unsigned_transaction`."
    }
  }
}
```

## Examples

### Happy path: successfully validate a mainnet P2PK address.

**Input:**
```json
{
  "address": "9f4qgDprA2e4sY83shmsz9L9uE4S4y2t5x5i3a2c5H4vG3cJ2F",
  "command": "validate_address"
}
```

**Output:**
```json
{
  "address": "9f4qgDprA2e4sY83shmsz9L9uE4S4y2t5x5i3a2c5H4vG3cJ2F",
  "isValid": true,
  "network": "mainnet"
}
```

### Happy path: generate a testnet address from a compressed public key.

**Input:**
```json
{
  "command": "address_from_pk",
  "network": "testnet",
  "publicKey": "02a7955281885bf0f0ca4a4563a344937441f9011703417573463e203fe35b1281"
}
```

**Output:**
```json
{
  "address": "3Wwecbp6S22R2ai1evwQ12r5aCA2Ea2m5M8u3h2qjN4L7f5g2A"
}
```

### Complex path: create an unsigned transaction with one input, one recipient output, and a change output.

**Input:**
```json
{
  "fee": "1100000",
  "inputs": [
    {
      "boxId": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
      "index": 0,
      "value": "5000000000",
      "assets": [],
      "ergoTree": "0008cd02a7955281885bf0f0ca4a4563a344937441f9011703417573463e203fe35b1281",
      "transactionId": "f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2",
      "creationHeight": 800000,
      "additionalRegisters": {}
    }
  ],
  "command": "create_unsigned_transaction",
  "outputs": [
    {
      "value": "1000000000",
      "assets": [],
      "ergoTree": "0008cd035b1281a7955281885bf0f0ca4a4563a344937441f9011703417573463e203fe3",
      "creationHeight": 850000,
      "additionalRegisters": {}
    }
  ],
  "changeAddress": "9f4qgDprA2e4sY83shmsz9L9uE4S4y2t5x5i3a2c5H4vG3cJ2F",
  "currentHeight": 850000
}
```

**Output:**
```json
{
  "unsignedTransaction": {
    "id": null,
    "inputs": [
      {
        "boxId": "a1b2c3d4e5f6...",
        "extension": {}
      }
    ],
    "outputs": [
      {
        "value": "1000000000",
        "ergoTree": "0008cd035..."
      },
      {
        "value": "3998900000",
        "ergoTree": "0008cd02a..."
      }
    ],
    "dataInputs": []
  }
}
```

### Error case: validation fails due to an invalid Base58 address string.

**Input:**
```json
{
  "address": "9f4qgDprA2e4sY83shmsz9L9uE4S4y2t5x5i3a2c5H4vG3cINVALID",
  "command": "validate_address"
}
```

**Output:**
```json
{
  "error": {
    "code": "InvalidAddress",
    "message": "Address decoding failed: checksum mismatch or invalid characters."
  }
}
```

## Permissions

- `compute:execute:wasm`
- `secrets:read:ergo_private_key`

## Constraints

- Runtime: Local execution (no network calls)
- Timeout: 3s per operation
- Idempotency: All operations are deterministic
- Payload size limit: 128KB
- Private key format: 64-character hex string
- Public key format: 66-character hex string (compressed SEC1)
- Address format: Base58 encoded with checksum
- All ERG values must be strings in nanoERGs (1 ERG = 1e9 nanoERGs)
