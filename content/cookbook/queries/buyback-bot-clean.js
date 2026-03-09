/**
 * ===== Module Description ===== //
 * Name: Unified Buyback Bot
 * Description: Automated buyback bot for DORT and GORT tokens via Spectrum DEX LP.
 *              Supports token selection at startup via CLI argument or interactive prompt.
 * Version: 2.0.0
 * Author: CannonQ
 * License: AGPL-3.0
 * 
 * ===== What This Module Does ===== //
 * 
 * 1. Prompts user to select token (DORT or GORT) or accepts --token CLI arg
 * 2. Loads wallet from mnemonic for paying transaction fees
 * 3. Fetches current LP and Buyback box states from blockchain
 * 4. Calculates optimal swap amount (~1% of buyback ERG balance)
 * 5. Builds a swap transaction: ERG → Token via Spectrum LP
 * 6. Signs transaction (contract boxes self-validate, fee box requires signature)
 * 7. Submits via binary serialization to preserve 64-bit integer precision
 * 
 * ===== Supported Tokens ===== //
 * 
 * DORT (Dexy Oracle Reward Token):
 *   - Token ID:     ae399fcb751e8e247d0da8179a2bcca2aa5119fff9c85721ffab9cdc9a3cb2dd
 *   - LP NFT:       35bc71897cd44d1a624285c54a0be66b69d1c61674603ed89dfe136f32035f0e
 *   - Buyback NFT:  dcce07af04ea4f9b7979336476594dc16321547bcc9c6b95a67cb1a94192da4f
 *   - LP Fee:       1% (990/1000)
 *   - Decimals:     0
 * 
 * GORT (Gold Oracle Reward Token / DexyGold):
 *   - Token ID:     7ba2a85fdb302a181578b1f64cb4a533d89b3f8de4159efece75da41041337f9
 *   - LP NFT:       d1c9e20657b4e37de3cd279a994266db34b18e6e786371832ad014fd46583198
 *   - Buyback NFT:  bf24ed4af7eb5a7839c43aa6b240697d81b196120c837e1a94192da4f
 *   - LP Fee:       0.3% (997/1000)
 *   - Decimals:     0
 * 
 * ===== Usage ===== //
 * 
 * Interactive:      node buyback-bot.js
 * CLI token:        node buyback-bot.js --token DORT
 *                   node buyback-bot.js --token GORT
 * Dry run:          node buyback-bot.js --token DORT --dry-run
 * Custom amount:    node buyback-bot.js --token GORT --erg 0.5
 * 
 * For scheduled execution, use cron or Task Scheduler.
 * Example cron: 0 0,12 * * * cd /path/to/bot && node buyback-bot.js --token DORT
 */

import dotenv from 'dotenv';
import * as readline from 'readline';
import * as fs from 'fs';
import * as path from 'path';
dotenv.config({ path: '.env.local' });

// ===== Notification Configuration ===== //

const NOTIFICATIONS = {
  telegram: {
    enabled: true,
    botToken: process.env.TELEGRAM_BOT_TOKEN || '',
    chatId: process.env.TELEGRAM_CHAT_ID || ''
  },
  windows: {
    enabled: true
  },
  logFile: {
    enabled: true,
    dir: './logs'
  }
};

// ===== Notification Functions ===== //

/**
 * Send Telegram notification
 */
async function sendTelegram(message) {
  if (!NOTIFICATIONS.telegram.enabled) return;
  
  const { botToken, chatId } = NOTIFICATIONS.telegram;
  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  
  try {
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text: message,
        parse_mode: 'HTML',
        disable_web_page_preview: false
      })
    });
  } catch (err) {
    console.log(`Telegram notification failed: ${err.message}`);
  }
}

/**
 * Send Windows toast notification
 */
async function sendWindowsNotification(title, message) {
  if (!NOTIFICATIONS.windows.enabled) return;
  
  try {
    const notifier = await import('node-notifier');
    notifier.default.notify({
      title: title,
      message: message,
      sound: true,
      wait: false
    });
  } catch (err) {
    // node-notifier not installed, skip silently
    console.log(`Windows notification skipped (install node-notifier for popups)`);
  }
}

/**
 * Append to log file
 */
function appendLog(message) {
  if (!NOTIFICATIONS.logFile.enabled) return;
  
  const logDir = NOTIFICATIONS.logFile.dir;
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  
  const timestamp = new Date().toISOString();
  const logFile = path.join(logDir, 'buyback.log');
  const logEntry = `[${timestamp}] ${message}\n`;
  
  fs.appendFileSync(logFile, logEntry);
}

/**
 * Send all notifications (success)
 */
async function notifySuccess(tokenName, ergAmount, tokenAmount, txId) {
  const ergFmt = (Number(ergAmount) / 1e9).toFixed(4);
  const txUrl = `https://ergexplorer.com/transactions#${txId}`;
  
  // Telegram (HTML format)
  const tgMessage = `✅ <b>${tokenName} Buyback Success</b>\n` +
    `${ergFmt} ERG → ${tokenAmount} ${tokenName}\n` +
    `<a href="${txUrl}">View on Explorer</a>`;
  await sendTelegram(tgMessage);
  
  // Windows popup
  await sendWindowsNotification(
    `${tokenName} Buyback ✅`,
    `${ergFmt} ERG → ${tokenAmount} ${tokenName}`
  );
  
  // Log file
  appendLog(`SUCCESS | ${tokenName} | ${ergFmt} ERG -> ${tokenAmount} ${tokenName} | TX: ${txId}`);
}

/**
 * Send all notifications (failure)
 */
async function notifyFailure(tokenName, errorMessage) {
  // Telegram
  const tgMessage = `❌ <b>${tokenName} Buyback Failed</b>\n` +
    `Error: ${errorMessage}`;
  await sendTelegram(tgMessage);
  
  // Windows popup
  await sendWindowsNotification(
    `${tokenName} Buyback ❌`,
    `Error: ${errorMessage.slice(0, 100)}`
  );
  
  // Log file
  appendLog(`FAILED | ${tokenName} | Error: ${errorMessage}`);
}

/**
 * Fetch from node with automatic fallback to backup nodes
 */
async function fetchFromNode(path) {
  let lastError;
  
  for (const node of ERGO_NODES) {
    try {
      const response = await fetch(`${node}${path}`, { timeout: 10000 });
      if (response.ok) {
        ERGO_NODE = node; // Remember working node
        return response;
      }
    } catch (err) {
      lastError = err;
      console.log(`Node ${node} failed: ${err.message}, trying next...`);
    }
  }
  
  throw lastError || new Error('All nodes failed');
}

// ===== Token Configurations ===== //

const TOKEN_CONFIGS = {
  DORT: {
    name: 'DORT',
    fullName: 'Dexy Oracle Reward Token',
    tokenId: 'ae399fcb751e8e247d0da8179a2bcca2aa5119fff9c85721ffab9cdc9a3cb2dd',
    lpNft: '35bc71897cd44d1a624285c54a0be66b69d1c61674603ed89dfe136f32035f0e',
    buybackNft: 'dcce07af04ea4f9b7979336476594dc16321547bcc9c6b95a67cb1a94192da4f',
    decimals: 0,
    defaultFeeNum: 990n  // 1% fee (990/1000)
  },
  GORT: {
    name: 'GORT',
    fullName: 'Gold Oracle Reward Token',
    tokenId: '7ba2a85fdb302a181578b1f64cb4a533d89b3f8de4159efece75da41041537f9',
    lpNft: 'd1c9e20657b4e37de3cd279a994266db34b18e6e786371832ad014fd46583198',
    buybackNft: 'bf24ed4af7eb5a7839c43aa6b240697d81b196120c837e1a941832c266d3755c',
    // Alternative buyback NFTs (multiple NFTs used for parallel execution)
    buybackNfts: [
      'bf24ed4af7eb5a7839c43aa6b240697d81b196120c837e1a941832c266d3755c',
      '119a068a0119670de8a5d2467da33df572903c64aaa7b6ea4c9668ef0cfe0325'
    ],
    buybackAddress: '<GORT_BUYBACK_CONTRACT_ADDRESS>',
    decimals: 0,
    defaultFeeNum: 997n  // 0.3% fee (997/1000)
  }
};

// ===== Constants ===== //

const ERGO_EXPLORER = 'https://api.ergoplatform.com/api/v1';

// Node configuration with fallback
const ERGO_NODES = [
  'http://<LOCAL_NODE_IP>:9053',   // Primary: local node
  'http://<REMOTE_NODE_IP>:9053'   // Backup: remote node
];
let ERGO_NODE = ERGO_NODES[0];

// Transaction parameters
const TX_FEE = 1_100_000n;           // 0.0011 ERG miner fee
const MIN_BOX_VALUE = 1_000_000n;    // 0.001 ERG minimum box value
const LP_FEE_DENOM = 1000n;

// EIP-27 Miner Fee Contract
const MINER_FEE_ERGO_TREE = "1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304";

// Auto-run configuration
const AUTO_SWAP_PERCENT = 0.01;      // 1% of buyback balance per run


// ===== Token Selection ===== //

/**
 * Prompt user to select a token interactively
 * @returns {Promise<string>} Selected token key (DORT or GORT)
 */
async function promptTokenSelection() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    console.log('\nSelect token:');
    console.log('  1. DORT (Dexy Oracle Reward Token)');
    console.log('  2. GORT (Gold Oracle Reward Token)');
    
    rl.question('> ', (answer) => {
      rl.close();
      const trimmed = answer.trim().toUpperCase();
      
      if (trimmed === '1' || trimmed === 'DORT') {
        resolve('DORT');
      } else if (trimmed === '2' || trimmed === 'GORT') {
        resolve('GORT');
      } else {
        console.error('Invalid selection. Use 1/DORT or 2/GORT');
        process.exit(1);
      }
    });
  });
}

/**
 * Get token selection from CLI args or prompt
 * @param {string[]} args - Command line arguments
 * @returns {Promise<Object>} Token configuration
 */
async function getTokenConfig(args) {
  const tokenIndex = args.indexOf('--token');
  
  let tokenKey;
  if (tokenIndex !== -1 && args[tokenIndex + 1]) {
    tokenKey = args[tokenIndex + 1].toUpperCase();
  } else {
    tokenKey = await promptTokenSelection();
  }
  
  const config = TOKEN_CONFIGS[tokenKey];
  if (!config) {
    console.error(`Unknown token: ${tokenKey}. Use DORT or GORT.`);
    process.exit(1);
  }
  
  return config;
}


// ===== API Functions ===== //

/**
 * Fetch JSON from URL with large number handling
 */
async function fetchJsonSafe(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`);
  const text = await response.text();
  const safeText = text.replace(/:(\s*)(\d{12,})(\s*[,\}\]])/g, ':"$2"$3');
  return JSON.parse(safeText);
}

/**
 * Find a box by its identifying NFT
 * @param {string|string[]} nftId - Token ID(s) of the identifying NFT
 * @param {boolean} selectRichest - If true AND multiple NFTs provided, return the box with most ERG
 */
async function findBoxByNft(nftId, selectRichest = false) {
  const nftIds = Array.isArray(nftId) ? nftId : [nftId];
  
  // Single NFT - use original simple logic (return first found)
  if (nftIds.length === 1) {
    const data = await fetchJsonSafe(`${ERGO_EXPLORER}/boxes/unspent/byTokenId/${nftIds[0]}`);
    if (!data.items?.length) throw new Error(`Box not found for NFT: ${nftIds[0]}`);
    return data.items[0];
  }
  
  // Multiple NFTs - collect all boxes and select richest
  let allItems = [];
  for (const id of nftIds) {
    try {
      const data = await fetchJsonSafe(`${ERGO_EXPLORER}/boxes/unspent/byTokenId/${id}`);
      if (data.items?.length) {
        allItems = allItems.concat(data.items);
      }
    } catch (e) {
      // Skip NFTs that aren't found
    }
  }
  
  if (!allItems.length) throw new Error(`Box not found for NFT(s): ${nftIds.join(', ')}`);
  
  if (selectRichest && allItems.length > 1) {
    // Sort by ERG value descending and return the richest
    const sorted = allItems.sort((a, b) => {
      const aVal = BigInt(a.value);
      const bVal = BigInt(b.value);
      return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
    });
    console.log(`  (found ${allItems.length} buyback boxes)`);
    for (const box of sorted) {
      console.log(`    - ${box.boxId.slice(0,12)}... ${(Number(box.value)/1e9).toFixed(4)} ERG`);
    }
    return sorted[0];
  }
  
  return allItems[0];
}

/**
 * Get unspent boxes for an address
 */
async function getUtxos(address) {
  const data = await fetchJsonSafe(`${ERGO_EXPLORER}/boxes/unspent/byAddress/${address}`);
  return data.items || [];
}

/**
 * Get current blockchain height from node
 */
async function getCurrentHeight() {
  const response = await fetchFromNode('/info');
  const data = await response.json();
  return data.fullHeight;
}


// ===== Wallet Functions ===== //

let ergolib = null;
async function loadErgoLib() {
  if (!ergolib) {
    ergolib = await import('ergo-lib-wasm-nodejs');
  }
  return ergolib;
}

/**
 * Initialize wallet from mnemonic
 */
async function initWallet(lib) {
  const mnemonic = process.env.ERGO_SERVER_MNEMONIC;
  if (!mnemonic) throw new Error('ERGO_SERVER_MNEMONIC not set in environment');
  
  const seed = lib.Mnemonic.to_seed(mnemonic, '');
  const root = lib.ExtSecretKey.derive_master(seed);
  const path = lib.DerivationPath.new(0, new Uint32Array([0]));
  const derived = root.derive(path);
  
  return {
    address: derived.public_key().to_address().to_base58(lib.NetworkPrefix.Mainnet),
    secretKey: lib.SecretKey.dlog_from_bytes(derived.secret_key_bytes())
  };
}

/**
 * Create ErgoStateContext for transaction signing
 */
async function createStateContext(lib) {
  const response = await fetchFromNode('/blocks/lastHeaders/10');
  const headersData = await response.json();
  
  const blockHeaders = lib.BlockHeaders.from_json(headersData);
  const latestHeader = lib.BlockHeader.from_json(JSON.stringify(headersData[0]));
  const preHeader = lib.PreHeader.from_block_header(latestHeader);
  
  let parameters = null;
  if (lib.Parameters?.default) {
    parameters = lib.Parameters.default();
  } else if (lib.Parameters?.default_parameters) {
    parameters = lib.Parameters.default_parameters();
  }
  
  if (parameters) {
    return new lib.ErgoStateContext(preHeader, blockHeaders, parameters);
  }
  return new lib.ErgoStateContext(preHeader, blockHeaders);
}


// ===== LP Math Functions ===== //

/**
 * Parse LP box to extract reserve amounts and fee
 */
function parseLpBox(lpBox, tokenId, defaultFeeNum) {
  const ergReserve = BigInt(lpBox.value);
  
  let tokenReserve = 0n;
  for (const asset of lpBox.assets) {
    if (asset.tokenId === tokenId) {
      tokenReserve = BigInt(asset.amount);
      break;
    }
  }
  
  // Fee is stored in R4 register
  let feeNum = defaultFeeNum;
  if (lpBox.additionalRegisters?.R4) {
    const r4 = lpBox.additionalRegisters.R4;
    const rendered = typeof r4 === 'object' ? r4.renderedValue : r4;
    if (rendered) feeNum = BigInt(rendered);
  }
  
  return { ergReserve, tokenReserve, feeNum };
}

/**
 * Calculate token output for a given ERG input (buy order)
 * Uses constant product formula with fee
 */
function calcBuyOutput(ergInput, ergReserve, tokenReserve, feeNum) {
  const num = tokenReserve * ergInput * feeNum;
  const denom = ergReserve * LP_FEE_DENOM + ergInput * feeNum;
  return num / denom;
}


// ===== Box Utilities ===== //

/**
 * Clean box data for ergo-lib consumption
 */
function cleanBoxForErgoLib(box) {
  const cleaned = {
    boxId: box.boxId,
    value: typeof box.value === 'string' ? box.value : box.value.toString(),
    ergoTree: box.ergoTree,
    creationHeight: box.creationHeight,
    assets: (box.assets || []).map(a => ({
      tokenId: a.tokenId,
      amount: typeof a.amount === 'string' ? a.amount : a.amount.toString()
    })),
    additionalRegisters: {}
  };
  
  if (box.additionalRegisters) {
    for (const [reg, data] of Object.entries(box.additionalRegisters)) {
      if (data) {
        if (typeof data === 'object' && data.serializedValue) {
          cleaned.additionalRegisters[reg] = data.serializedValue;
        } else if (typeof data === 'string') {
          cleaned.additionalRegisters[reg] = data;
        }
      }
    }
  }
  
  if (box.transactionId) cleaned.transactionId = box.transactionId;
  if (box.index !== undefined) cleaned.index = box.index;
  
  return cleaned;
}


// ===== Transaction Building ===== //

/**
 * Build the buyback swap transaction
 * 
 * Transaction Structure:
 *   Input 0:  LP Box (contract - no signature needed)
 *   Input 1:  Buyback Box (contract with context extension, action=0)
 *   Input 2+: Fee payer boxes (requires wallet signature)
 *   
 *   Output 0: LP Box (+ERG, -token)
 *   Output 1: Buyback Box (-ERG, +token, R4=input box ID)
 *   Output 2: Change to fee payer
 *   Output 3: Miner fee (EIP-27)
 */
async function buildBuybackTx(lib, lpBox, buybackBox, feeBoxes, height, ergToSwap, tokenToReceive, tokenConfig) {
  const tokenId = tokenConfig.tokenId;
  const tokenName = tokenConfig.name;
  
  // Parse current box values
  const lpErg = BigInt(lpBox.value);
  const bbErg = BigInt(buybackBox.value);
  
  let lpToken = 0n, bbToken = 0n;
  for (const a of lpBox.assets) {
    if (a.tokenId === tokenId) lpToken = BigInt(a.amount);
  }
  for (const a of buybackBox.assets) {
    if (a.tokenId === tokenId) bbToken = BigInt(a.amount);
  }
  
  // Calculate new values after swap
  const newLpErg = lpErg + ergToSwap;
  const newLpToken = lpToken - tokenToReceive;
  const newBbErg = bbErg - ergToSwap;
  const newBbToken = bbToken + tokenToReceive;
  
  console.log(`\n=== Swap Details ===`);
  console.log(`LP:  ${(Number(lpErg)/1e9).toFixed(4)} → ${(Number(newLpErg)/1e9).toFixed(4)} ERG`);
  console.log(`BB:  ${(Number(bbErg)/1e9).toFixed(4)} → ${(Number(newBbErg)/1e9).toFixed(4)} ERG`);
  console.log(`LP ${tokenName}: ${lpToken} → ${newLpToken}`);
  console.log(`BB ${tokenName}: ${bbToken} → ${newBbToken}`);
  
  // ===== OUTPUT 0: LP Box =====
  const lpTree = lib.ErgoTree.from_base16_bytes(lpBox.ergoTree);
  const lpAddr = lib.Address.recreate_from_ergo_tree(lpTree);
  const lpOutBuilder = new lib.ErgoBoxCandidateBuilder(
    lib.BoxValue.from_i64(lib.I64.from_str(newLpErg.toString())),
    lib.Contract.pay_to_address(lpAddr),
    height
  );
  
  // Add LP tokens in exact order
  for (const asset of lpBox.assets) {
    const tid = lib.TokenId.from_str(asset.tokenId);
    let amtStr;
    if (asset.tokenId === tokenId) {
      amtStr = newLpToken.toString();
    } else {
      amtStr = typeof asset.amount === 'string' ? asset.amount : String(asset.amount);
    }
    const amt = lib.TokenAmount.from_i64(lib.I64.from_str(amtStr));
    lpOutBuilder.add_token(tid, amt);
  }
  
  // Preserve R4 (fee numerator)
  if (lpBox.additionalRegisters) {
    for (const [reg, data] of Object.entries(lpBox.additionalRegisters)) {
      const regId = lib.NonMandatoryRegisterId[reg];
      if (regId !== undefined && data) {
        const hex = typeof data === 'string' ? data : data.serializedValue;
        if (hex) lpOutBuilder.set_register_value(regId, lib.Constant.decode_from_base16(hex));
      }
    }
  }
  
  // ===== OUTPUT 1: Buyback Box =====
  const bbTree = lib.ErgoTree.from_base16_bytes(buybackBox.ergoTree);
  const bbAddr = lib.Address.recreate_from_ergo_tree(bbTree);
  const bbOutBuilder = new lib.ErgoBoxCandidateBuilder(
    lib.BoxValue.from_i64(lib.I64.from_str(newBbErg.toString())),
    lib.Contract.pay_to_address(bbAddr),
    height
  );
  
  // Add buyback tokens in order
  for (const asset of buybackBox.assets) {
    const tid = lib.TokenId.from_str(asset.tokenId);
    const amt = asset.tokenId === tokenId
      ? lib.TokenAmount.from_i64(lib.I64.from_str(newBbToken.toString()))
      : lib.TokenAmount.from_i64(lib.I64.from_str(
          typeof asset.amount === 'string' ? asset.amount : asset.amount.toString()
        ));
    bbOutBuilder.add_token(tid, amt);
  }
  
  // CRITICAL: Set R4 = input buyback box ID
  const bbInputId = Buffer.from(buybackBox.boxId, 'hex');
  bbOutBuilder.set_register_value(
    lib.NonMandatoryRegisterId.R4,
    lib.Constant.from_byte_array(Array.from(bbInputId))
  );
  
  // ===== OUTPUT 2: Change Box =====
  const feeTotal = feeBoxes.reduce((s, b) => 
    s + BigInt(typeof b.value === 'string' ? b.value : b.value.toString()), 0n);
  const changeAmt = feeTotal - TX_FEE;
  
  // Build all outputs
  const outputs = new lib.ErgoBoxCandidates(lpOutBuilder.build());
  outputs.add(bbOutBuilder.build());
  
  if (changeAmt >= MIN_BOX_VALUE) {
    const changeAddr = lib.Address.from_base58(feeBoxes[0].address);
    const changeBuilder = new lib.ErgoBoxCandidateBuilder(
      lib.BoxValue.from_i64(lib.I64.from_str(changeAmt.toString())),
      lib.Contract.pay_to_address(changeAddr),
      height
    );
    outputs.add(changeBuilder.build());
  }
  
  // ===== OUTPUT 3: Miner Fee =====
  const feeTree = lib.ErgoTree.from_base16_bytes(MINER_FEE_ERGO_TREE);
  const feeAddr = lib.Address.recreate_from_ergo_tree(feeTree);
  const feeOutBuilder = new lib.ErgoBoxCandidateBuilder(
    lib.BoxValue.from_i64(lib.I64.from_str(TX_FEE.toString())),
    lib.Contract.pay_to_address(feeAddr),
    height
  );
  outputs.add(feeOutBuilder.build());
  
  // ===== INPUTS =====
  const inputs = new lib.UnsignedInputs();
  
  // Input 0: LP Box (no context extension)
  inputs.add(lib.UnsignedInput.from_box_id(lib.BoxId.from_str(lpBox.boxId)));
  
  // Input 1: Buyback Box with context extension (action=0 for swap)
  const contextExt = new lib.ContextExtension();
  contextExt.set_pair(0, lib.Constant.from_i32(0));
  const bbInput = new lib.UnsignedInput(lib.BoxId.from_str(buybackBox.boxId), contextExt);
  inputs.add(bbInput);
  
  // Input 2+: Fee boxes
  for (const box of feeBoxes) {
    inputs.add(lib.UnsignedInput.from_box_id(lib.BoxId.from_str(box.boxId)));
  }
  
  // Verify balance
  const inTotal = lpErg + bbErg + feeTotal;
  const outTotal = newLpErg + newBbErg + changeAmt + TX_FEE;
  
  if (inTotal !== outTotal) {
    throw new Error(`Balance mismatch! In: ${inTotal}, Out: ${outTotal}`);
  }
  
  // Create unsigned transaction
  const unsignedTx = new lib.UnsignedTransaction(
    inputs,
    new lib.DataInputs(),
    outputs,
    lib.BoxValue.from_i64(lib.I64.from_str(MIN_BOX_VALUE.toString()))
  );
  
  return {
    unsignedTx,
    inputBoxes: [lpBox, buybackBox, ...feeBoxes]
  };
}


// ===== Transaction Signing & Submission ===== //

/**
 * Sign the transaction
 */
async function signTx(lib, secretKey, unsignedTx, inputBoxes) {
  const ctx = await createStateContext(lib);
  
  const keys = new lib.SecretKeys();
  keys.add(secretKey);
  const wallet = lib.Wallet.from_secrets(keys);
  
  const boxes = lib.ErgoBoxes.empty();
  for (const b of inputBoxes) {
    const cleaned = cleanBoxForErgoLib(b);
    boxes.add(lib.ErgoBox.from_json(JSON.stringify(cleaned)));
  }
  
  const signedTx = wallet.sign_transaction(ctx, unsignedTx, boxes, lib.ErgoBoxes.empty());
  const signedJson = JSON.parse(signedTx.to_json());
  
  return { signedTx, signedJson };
}

/**
 * Submit transaction to the network
 */
async function submitTx({ signedTx, signedJson }) {
  let txBytes = null;
  try {
    if (signedTx.sigma_serialize_bytes) {
      txBytes = Buffer.from(signedTx.sigma_serialize_bytes()).toString('hex');
    }
  } catch (e) {
    console.log(`Warning: Could not get TX bytes: ${e.message}`);
  }
  
  // Try binary submission to each node
  if (txBytes) {
    console.log(`\n=== Submitting (${txBytes.length / 2} bytes) ===`);
    for (const node of ERGO_NODES) {
      try {
        const response = await fetch(`${node}/transactions/bytes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(txBytes)
        });
        
        if (response.ok) {
          const txId = (await response.text()).replace(/"/g, '');
          return { id: txId, source: `node (binary) - ${node}` };
        }
        
        const errorText = await response.text();
        console.log(`${node} submission failed: ${errorText.slice(0, 200)}`);
      } catch (err) {
        console.log(`${node} submission error: ${err.message}`);
      }
    }
  }
  
  // Fallback to JSON submission via explorer
  console.log(`Falling back to JSON submission...`);
  const response = await fetch(`${ERGO_EXPLORER}/mempool/transactions/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(signedJson)
  });
  
  if (response.ok) {
    const result = await response.json();
    return { id: result.id || result, source: 'explorer (JSON)' };
  }
  
  throw new Error(`Transaction submission failed: ${await response.text()}`);
}


// ===== Main Execution ===== //

/**
 * Format token amount with decimals
 */
function formatTokenAmount(amount, decimals) {
  if (decimals === 0) return amount.toString();
  const divisor = BigInt(10 ** decimals);
  const whole = amount / divisor;
  const frac = amount % divisor;
  if (frac === 0n) return whole.toString();
  return `${whole}.${frac.toString().padStart(decimals, '0').replace(/0+$/, '')}`;
}

/**
 * Main entry point
 */
async function main() {
  // Parse command line arguments
  const args = process.argv.slice(2);
  const isDryRun = args.includes('--dry-run') || args.includes('-d');
  
  // Get token configuration
  const tokenConfig = await getTokenConfig(args);
  currentTokenName = tokenConfig.name;  // For error notifications
  
  console.log('╔═══════════════════════════════════════════╗');
  console.log(`║      ${tokenConfig.name} Buyback Bot v2.0.0`.padEnd(44) + '║');
  console.log('╚═══════════════════════════════════════════╝');
  
  let customErg = null;
  const ergIndex = args.indexOf('--erg');
  if (ergIndex !== -1 && args[ergIndex + 1]) {
    customErg = parseFloat(args[ergIndex + 1]);
  }
  
  // Initialize
  const lib = await loadErgoLib();
  console.log('✓ ergo-lib loaded');
  
  const { address, secretKey } = await initWallet(lib);
  console.log(`✓ Wallet: ${address.slice(0, 20)}...`);
  
  // Fetch blockchain state
  console.log('\nFetching blockchain state...');
  const buybackNftIds = tokenConfig.buybackNfts || [tokenConfig.buybackNft];
  const [lpBox, buybackBox, height, feeBoxes] = await Promise.all([
    findBoxByNft(tokenConfig.lpNft),
    findBoxByNft(buybackNftIds, true),  // Select richest buyback box
    getCurrentHeight(),
    getUtxos(address)
  ]);
  
  console.log(`✓ LP Box: ${lpBox.boxId.slice(0, 16)}...`);
  console.log(`✓ Buyback: ${buybackBox.boxId.slice(0, 16)}...`);
  console.log(`✓ Height: ${height}`);
  console.log(`✓ Fee boxes: ${feeBoxes.length}`);
  
  // Parse LP state
  const { ergReserve, tokenReserve, feeNum } = parseLpBox(lpBox, tokenConfig.tokenId, tokenConfig.defaultFeeNum);
  const bbErg = BigInt(buybackBox.value);
  
  // Calculate fee percentage for display
  const feePercent = (1000 - Number(feeNum)) / 10;
  
  console.log(`\n=== Current State ===`);
  console.log(`LP ERG Reserve:   ${(Number(ergReserve)/1e9).toFixed(2)} ERG`);
  console.log(`LP ${tokenConfig.name} Reserve:  ${formatTokenAmount(tokenReserve, tokenConfig.decimals)} ${tokenConfig.name}`);
  console.log(`LP Fee:           ${feeNum}/1000 (${feePercent}%)`);
  console.log(`Buyback ERG:      ${(Number(bbErg)/1e9).toFixed(2)} ERG`);
  
  // Calculate swap amount
  let ergToSwap;
  if (customErg) {
    ergToSwap = BigInt(Math.floor(customErg * 1e9));
    console.log(`\nCustom swap: ${customErg} ERG`);
  } else {
    ergToSwap = bbErg * BigInt(Math.floor(AUTO_SWAP_PERCENT * 1000)) / 1000n;
    console.log(`\nAuto swap: ${(AUTO_SWAP_PERCENT * 100).toFixed(1)}% of buyback balance`);
  }
  
  // Ensure minimum viable swap (0.2 ERG minimum to avoid contract integer math issues)
  const MIN_SWAP = 200_000_000n;  // 0.2 ERG
  if (ergToSwap < MIN_SWAP) {
    ergToSwap = MIN_SWAP;
    console.log(`  (adjusted to minimum: ${(Number(MIN_SWAP)/1e9).toFixed(2)} ERG)`);
  }
  
  // Calculate expected output
  let tokenOut = calcBuyOutput(ergToSwap, ergReserve, tokenReserve, feeNum);
  
  // If token output is too low (< 2), increase ERG to get at least 2 tokens
  // This handles expensive tokens like GORT where small ERG amounts yield 0 tokens
  const MIN_TOKEN_OUT = 2n;
  if (tokenOut < MIN_TOKEN_OUT) {
    // Calculate minimum ERG needed for MIN_TOKEN_OUT tokens
    // Rearranging: ergIn = (tokenOut * ergReserve * 1000) / (tokenReserve * feeNum - tokenOut * feeNum)
    const targetTokens = MIN_TOKEN_OUT;
    const num = targetTokens * ergReserve * LP_FEE_DENOM;
    const denom = (tokenReserve - targetTokens) * feeNum;
    const minErgNeeded = (num / denom) + 1n; // +1 for rounding
    
    if (minErgNeeded <= bbErg - MIN_BOX_VALUE) {
      console.log(`  (token output too low, adjusting ERG to get ${MIN_TOKEN_OUT} ${tokenConfig.name})`);
      ergToSwap = minErgNeeded;
      tokenOut = calcBuyOutput(ergToSwap, ergReserve, tokenReserve, feeNum);
    } else {
      throw new Error(`Insufficient buyback balance. Need ~${(Number(minErgNeeded)/1e9).toFixed(4)} ERG to buy ${MIN_TOKEN_OUT} ${tokenConfig.name}, but only ${(Number(bbErg)/1e9).toFixed(4)} ERG available.`);
    }
  }
  
  const tokenOutWithSlippage = tokenOut - 1n;
  
  const spotPriceErg = Number(ergReserve) / Number(tokenReserve) / 1e9;
  const effectivePriceErg = Number(ergToSwap) / Number(tokenOut) / 1e9;
  const priceImpact = ((effectivePriceErg / spotPriceErg) - 1) * 100;
  
  // Calculate theoretical output without integer rounding (to show fee-only impact)
  const theoreticalTokens = (Number(tokenReserve) * Number(ergToSwap) * Number(feeNum)) / 
                            (Number(ergReserve) * 1000 + Number(ergToSwap) * Number(feeNum));
  const feeOnlyImpact = ((1000 / Number(feeNum)) - 1) * 100;  // Just the LP fee
  
  console.log(`\n=== Swap Calculation ===`);
  console.log(`ERG to swap:     ${(Number(ergToSwap)/1e9).toFixed(4)} ERG`);
  console.log(`${tokenConfig.name} to receive: ${tokenOut} (min: ${tokenOutWithSlippage}) ${tokenConfig.name}`);
  console.log(`Spot price:      ${spotPriceErg.toFixed(6)} ERG/${tokenConfig.name}`);
  console.log(`Effective price: ${effectivePriceErg.toFixed(6)} ERG/${tokenConfig.name}`);
  console.log(`Price impact:    ${priceImpact.toFixed(3)}% (fee: ${feeOnlyImpact.toFixed(2)}%, slippage+rounding: ${(priceImpact - feeOnlyImpact).toFixed(2)}%)`);
  
  if (priceImpact > 5.0) {
    console.log(`⚠️  High price impact! Consider increasing swap size for better efficiency.`);
  }
  
  // Check fee balance
  const feeBalance = feeBoxes.reduce((s, b) => s + BigInt(b.value), 0n);
  if (feeBalance < TX_FEE + MIN_BOX_VALUE) {
    throw new Error(`Insufficient fee balance: ${(Number(feeBalance)/1e9).toFixed(4)} ERG`);
  }
  
  // Build transaction
  const { unsignedTx, inputBoxes } = await buildBuybackTx(
    lib, lpBox, buybackBox, feeBoxes, height, ergToSwap, tokenOutWithSlippage, tokenConfig
  );
  
  // Dry run check
  if (isDryRun) {
    const unsignedJson = JSON.parse(unsignedTx.to_json());
    console.log(`\n════════════════════════════════════════`);
    console.log(`   DRY RUN - Transaction NOT submitted`);
    console.log(`════════════════════════════════════════`);
    console.log(`\nInputs: ${unsignedJson.inputs.length}`);
    console.log(`Outputs: ${unsignedJson.outputs.length}`);
    return;
  }
  
  // Sign transaction
  console.log(`\n=== Signing ===`);
  const { signedTx, signedJson } = await signTx(lib, secretKey, unsignedTx, inputBoxes);
  console.log(`TX ID: ${signedJson.id}`);
  
  // Submit transaction
  const result = await submitTx({ signedTx, signedJson });
  
  console.log(`\n✅ SUCCESS!`);
  console.log(`Source: ${result.source}`);
  console.log(`TX: https://ergexplorer.com/transactions#${result.id}`);
  
  // Send notifications
  await notifySuccess(tokenConfig.name, ergToSwap, tokenOutWithSlippage, result.id);
  
  // Log summary
  const timestamp = new Date().toISOString();
  console.log(`\n[${timestamp}] ${tokenConfig.name} Buyback: ${(Number(ergToSwap)/1e9).toFixed(4)} ERG → ${formatTokenAmount(tokenOutWithSlippage, tokenConfig.decimals)} ${tokenConfig.name} | TX: ${result.id}`);
}

// Track token name for error notifications
let currentTokenName = 'Unknown';

// Run
main().catch(async err => {
  console.error('\n✗ Error:', err.message);
  await notifyFailure(currentTokenName, err.message);
  process.exit(1);
});
