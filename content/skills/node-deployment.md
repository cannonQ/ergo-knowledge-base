---
title: "Ergo Node Deployment Guide"
category: skill
difficulty: intermediate
tags: [node, deployment, configuration, api-security]
source: degens-world
source_url: "https://github.com/Degens-World/Ergo-Skills/tree/main/skills/ergo-node"
updated: 2026-03-09
---

# Local Ergo Node Deployment

Deploys a local Ergo full node by downloading the client, creating a configuration file, and launching the node process.


## Overview

This skill automates the manual process of setting up and running a full Ergo node on a local machine. It provides a simplified interface for developers and users who need a local node for interacting with the Ergo blockchain, developing applications, or simply supporting the network. The skill handles downloading the required Ergo node software (JAR file) from official GitHub releases, generating a a configuration file with essential settings, and launching the node as a background process.

By parameterizing key settings such as the network (mainnet or testnet), memory allocation, and API key, the skill makes it easy to spin up a node tailored to specific needs without manually performing each step. It streamlines the "Getting Started" guide provided in the official Ergo documentation, making local node deployment accessible even to users with limited command-line experience.

Upon successful execution, the skill returns crucial information, including the process ID (PID) of the running node, the location of the node directory and configuration file, and the URLs for the web-based panel and the REST API, allowing for immediate interaction and monitoring.

## Architecture

The skill operates by executing a sequence of tasks on the local filesystem and operating system:

1.  **Directory Creation**: It first creates a dedicated directory for the Ergo node files at a user-specified path. This keeps the node's data, configuration, and software organized and isolated.

2.  **Software Download**: The skill then accesses the official Ergo Platform GitHub releases page (`https://api.github.com/repos/ergoplatform/ergo/releases`) to find and download the specified version of the Ergo node client (`.jar` file). It handles finding the correct asset from the release and saving it to the newly created directory.

3.  **Configuration File Generation**: A configuration file named `ergo.conf` is dynamically generated within the node directory. The skill populates this file based on the parameters provided by the user. At a minimum, it configures:
    *   `ergo.node.mining`: Typically set to `false` as per the documentation's recommendation for a standard node.
    *   `scorex.restApi.apiKeyHash`: To secure the node's API, the skill takes a user-provided plaintext password, hashes it using SHA-256, and writes the resulting hash to the configuration file. This is a critical security step.
    *   It also allows for advanced users to inject any additional configuration settings through a dedicated parameter.

4.  **Node Execution**: Finally, the skill constructs and executes the `java -jar` command to launch the Ergo node. The command includes:
    *   The Java memory allocation flag (`-Xmx`) based on the user's input (e.g., `-Xmx4G`).
    *   The path to the downloaded `.jar` file.
    *   A network flag (`--mainnet` or `--testnet`).
    *   A configuration flag (`-c ergo.conf`) pointing to the generated config file.

The node is launched as a detached, background process. The skill captures the Process ID (PID) of this new process, which can be used for later management (e.g., monitoring or terminating the node).

## Authentication and API Security

The Ergo node's REST API is protected by an API key. Instead of storing a plaintext key, the node requires a SHA-256 hash of the key to be placed in the `ergo.conf` file. This skill simplifies the process by accepting a plaintext password via the `api_key_password` parameter. It then calculates the necessary SHA-256 hash internally and injects the `apiKeyHash` into the configuration. The user never has to handle the hashing process manually.

**Example**:
If the user provides `api_key_password: "hello"`, the skill calculates:
`SHA256("hello")` = `324dcf027dd4a30a932c441f365a25e86b173defa4b8e58948253471b81b72cf`

And generates the following entry in `ergo.conf`:
```conf
scorex.restApi {
  apiKeyHash = "324dcf027dd4a30a932c441f365a25e86b173defa4b8e58948253471b81b72cf"
}
```
To interact with the API (e.g., via `curl` or other clients), the user must then provide the original plaintext password (`"hello"`) in the `api_key` HTTP header.

## Methods and Parameters

This skill exposes a single command for deploying the node. The following table details all available input parameters.

| Parameter               | Type    | Required | Default          | Description                                                                                                                                                                                                                                                                                       | 
|-------------------------|---------|----------|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| 
| `directory`             | string  | No       | `ergo_node`      | The name of the folder to create for the Ergo node files (e.g., node data, config, JAR). The folder will be created in the current working directory.                                                                                                                                              | 
| `version`               | string  | Yes      | -                | The version of the Ergo node to download (e.g., "5.0.16"). You can also use "latest" to automatically fetch the most recent stable release from GitHub.                                                                                                                                      | 
| `network`               | string  | No       | `mainnet`        | The network to connect to. Must be one of `mainnet` or `testnet`.                                                                                                                                                                                                                                  | 
| `memory_allocation_gb`  | integer | No       | `4`              | The amount of RAM (in Gigabytes) to allocate to the Java Virtual Machine (JVM) using the `-Xmx` flag. More RAM generally improves performance.                                                                                                                                                        | 
| `api_key_password`      | string  | Yes      | -                | A plaintext password for securing the node's REST API. The skill will hash this password and set the `apiKeyHash` in the configuration file. **Do not use a password you use elsewhere.**                                                                                                                | 
| `mining`                | boolean | No       | `false`          | Whether to enable mining on the node. For most use cases, this should be set to `false` as recommended by the official documentation.                                                                                                                                                           | 
| `config_options`        | object  | No       | `{}` (empty)     | An object containing advanced key-value pairs to add to the `ergo.conf` file. Use this to override default settings or add custom configurations not covered by other parameters. For example: `{"scorex.network.nodeName": "my-ergo-node"}`.                                                  | 

## Response Format

Upon successful execution, the skill returns a JSON object with details about the running node.

| Field               | Type   | Description                                                                                                                                                                    | 
|---------------------|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| 
| `status`            | string | Indicates the outcome of the operation. Will be "success" on successful launch.                                                                                                      | 
| `message`           | string | A human-readable message describing the result, e.g., "Ergo node v5.0.16 launched successfully on mainnet."                                                                          | 
| `node_directory`    | string | The absolute path to the directory where the node was installed.                                                                                                                     | 
| `pid`               | integer| The Process ID (PID) of the launched Java process. This can be used to monitor or terminate the node.                                                                                | 
| `web_panel_url`     | string | The URL for the node's web monitoring panel. This is `http://127.0.0.1:9053/panel` for mainnet and `http://127.0.0.1:9052/panel` for testnet.                                       | 
| `api_url`           | string | The base URL for the node's REST API. This is `http://127.0.0.1:9053` for mainnet and `http://127.0.0.1:9052` for testnet.                                                          | 
| `command_executed`  | string | The exact command-line string that was executed to start the node. This is useful for debugging.                                                                                     | 

In case of an error, the `status` field will be "error" and the `message` field will contain a detailed description of the problem.

## Verification and Monitoring

After the skill reports a successful launch, the node begins the synchronization process. This can take several hours to days. You can monitor its progress using the `web_panel_url` provided in the output. The web panel will show "Active synchronization" and the current block height.

Once the "Full height" in the panel matches the height shown on a public explorer (like [explorer.ergoplatform.com](https://explorer.ergoplatform.com)), your node is fully synced and ready to use.

You can also query the API's `/info` endpoint programmatically:

`curl -X GET "http://127.0.0.1:9053/info" -H "api_key: your_password"`


## Error Handling

| Error Condition                      | `status` | Example `message`                                                      | Likely Cause & Solution                                                                                                                                                           | 
|--------------------------------------|----------|--------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| 
| Java not installed or not in PATH    | `error`  | "Error: 'java' command not found. Please ensure Java is installed and in your system's PATH." | The Java runtime is not installed or the `java` executable is not accessible. Install a JDK (version 8 or newer) and ensure it's added to your system's PATH environment variable. | 
| Invalid version string               | `error`  | "Error: Could not find release version '5.99.9'. Please check the version number." | The specified version does not exist in the Ergo GitHub releases. Use "latest" or a valid, existing version number.                                                            | 
| Network or Download Failure          | `error`  | "Error: Failed to download Ergo JAR from GitHub. Check your internet connection." | There was a problem connecting to GitHub or downloading the file. Check your network connectivity and firewall settings.                                                            | 
| Port Conflict                        | `error`  | "Error: Could not start node. Port 9053 may already be in use."          | Another application (or another Ergo node) is already using the required network port. Stop the conflicting application or specify a different port using `config_options`.    | 
| Filesystem/Permission Error          | `error`  | "Error: Failed to create directory 'ergo_node'. Permission denied."    | The skill does not have the necessary permissions to create files or directories in the target location. Run the agent with appropriate permissions or choose a different directory. | 

## Constraints and Security

*   **Idempotency**: This skill is **not** idempotent. Executing it multiple times with the same `directory` will result in errors if the first node is still running (port conflicts) or may lead to unpredictable behavior. A running node should be stopped before attempting to deploy a new one in the same location.
*   **Retry Logic**: The skill does not implement automatic retry logic. If a deployment fails, the underlying issue (e.g., no Java, port conflict, lack of permissions) must be resolved by the user before re-running the command.
*   **Security**: The `api_key_password` is a critical security parameter. Choose a strong, unique password. Do not expose the node's API port (`9053` or `9052`) to the public internet unless you have configured a secure reverse proxy (e.g., Nginx) with SSL/TLS and robust firewall rules.
*   **Process Permissions**: This skill requires permission to execute and monitor local processes (`process:execute:java`, `process:read:pid`). While scoped to the Java runtime and process information retrieval, this permission is powerful. Ensure the agent running this skill operates in a trusted, isolated environment to mitigate the risk of unintended system interactions.
*   **Resource Usage**: Running a full node is resource-intensive, particularly during the initial sync. Ensure the host machine has sufficient RAM (as specified by `memory_allocation_gb`), CPU, and disk space (100GB+ recommended).
*   **Timeout**: The skill itself should execute within 60-120 seconds (depending on download speeds). The node launch is asynchronous; the skill returns immediately after starting the process, while the node synchronization will continue in the background for much longer.


## Input Schema

```json
{
  "properties": {},
  "required": [
    "version",
    "api_key_password"
  ],
  "type": "object"
}
```

## Output Schema

```json
{
  "properties": {},
  "required": [
    "status",
    "message"
  ],
  "type": "object"
}
```

## Examples

### A basic, happy-path deployment on mainnet using a specific node version and a strong password.

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
client.deploy_ergo_node(version="5.0.22", api_key_password="strong-password-for-api")
```

### Deploys a node on the testnet with a specific version, a custom directory, and increased memory allocation.

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
client.deploy_ergo_node(
    version="5.0.20", 
    api_key_password="testnet-password-123",
    network="testnet",
    directory="ergo_testnet_node",
    memory_allocation_gb=8
)
```

### Deploys a mainnet node with advanced configuration options, setting a custom node name and enabling UTXO snapshot bootstrap.

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
client.deploy_ergo_node(
    version="latest",
    api_key_password="another-secure-pwd",
    config_options={
        "scorex.network.nodeName": "MyPersonalNode",
        "ergo.node.utxoBootstrap": True
    }
)
```

### Example of a failed deployment due to requesting a version that does not exist.

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
client.deploy_ergo_node(version="9.9.9", api_key_password="any-password")
```

### Deploys a mainnet node with the latest version using cURL.

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
curl -X POST 'https://<your_tool_server>/run_skill' \
-H 'Content-Type: application/json' \
-H 'Authorization: Bearer <YOUR_API_KEY>' \
-d '{
  "tool_name": "deploy_ergo_node",
  "parameters": {
    "version": "latest",
    "api_key_password": "a-curl-password"
  }
}'
```

## Permissions

- `filesystem:read:local`
- `filesystem:write:local`
- `network:request:github.com`
- `process:execute:java`
- `process:read:pid`

## Constraints

- The skill is not idempotent. Running it twice with the same directory without cleanup will cause errors.
- Execution timeout is approximately 120 seconds to allow for file download. The node synchronization is a long-running background process not covered by this timeout.
- The host machine must have Java installed and available in the system PATH.
- Sufficient disk space (100GB+) and RAM are required for the node to operate correctly.
