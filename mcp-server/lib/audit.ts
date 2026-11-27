import fs from "fs";
import path from "path";

// Chain-specific and conditional sections for audit_contract and audit_verify.
// With chain "ergo", no 6.0 or cross-chain construct in the contract, and compact off,
// nothing in this file adds to or changes the tool output.

const ES_REF_DIR = path.join(process.cwd(), "..", "content", "reference", "ergoscript");

export const CHAINS = ["ergo", "yolo"] as const;
export type Chain = (typeof CHAINS)[number];

function readPage(name: string): string {
  const filePath = path.join(ES_REF_DIR, name);
  if (!fs.existsSync(filePath)) return "";
  const text = fs.readFileSync(filePath, "utf-8");
  // Drop the YAML frontmatter and demote headings one level so the page sits under a "##" section.
  const body = text.replace(/^---\n[\s\S]*?\n---\n/, "").trim();
  return body.replace(/^(#{1,5}) /gm, "#$1 ");
}

// Methods and types that exist only from Sigma 6.0 (tree version 3). Not exhaustive:
// a contract that uses another 6.0 method gets the section when chain is "yolo".
const SIGMA6_RE =
  /\b(deserializeTo|checkPow|powHit|decodeNbits|encodeNbits|UnsignedBigInt|toUnsigned|toUnsignedMod|getVarFromInput|bitwiseAnd|bitwiseOr|bitwiseXor|bitwiseInverse|shiftLeft|shiftRight)\b|Global\.serialize\b/;

// Constructs that mean the contract trusts another chain's headers or state.
const CROSS_CHAIN_RE = /\b(deserializeTo|checkPow|powHit|decodeNbits|encodeNbits)\b/;

export function usesSigma6(code: string): boolean {
  return SIGMA6_RE.test(code);
}

export function readsOtherChain(code: string): boolean {
  return CROSS_CHAIN_RE.test(code);
}

// "Chain facts" block, placed near the top of the output. Empty for ergo.
export function chainFactsSection(chain: Chain): string {
  if (chain !== "yolo") return "";
  const page = readPage("yolo-chain-facts.md");
  if (!page) return "";
  return [page, "", "---", ""].join("\n");
}

// Sections placed after the fixed audit context. Empty when neither applies.
export function conditionalSections(code: string, chain: Chain): string {
  const parts: string[] = [];
  if (chain === "yolo" || usesSigma6(code)) {
    const page = readPage("sigma6-tree-v3.md");
    if (page) parts.push(page);
  }
  if (readsOtherChain(code)) {
    const page = readPage("cross-chain-traps.md");
    if (page) parts.push(page);
  }
  if (parts.length === 0) return "";
  return parts.map((p) => [p, "", "---", ""].join("\n")).join("\n");
}

// Phrasings in Ergo-written context that carry a figure known to differ on another chain.
// The list holds phrasings only. The other chain's numbers live in its chain facts page.
const ERGO_FIGURE_RES: RegExp[] = [
  /\b(4|four)[ -]years?\b/i,
  /\d[\d.,_]*\s*M?\s*nanoERGs?\b/i,
  /\b0\.001\s*ERG\b/,
  /(min(imum)?[- ]?(box[- ]?)?value|storage[- ]rent|dust)[^\n]*\b\d[\d.,]*\s*ERG\b/i,
  /±\s*\d+/,
  /\+\/-\s*\d+\s*blocks?/i,
  /\b720\s+blocks?\b/i,
  /\b(2|two)[ -]minutes?\b/i,
  /\b120[ -]seconds?\b/i,
  /\b\d[\d,]*\s+blocks?\s*\((~|about|approx|roughly)?\s*\d/i,
  /\b(~|about|approx\.?|roughly)\s*\d[\d.,]*\s*(minutes?|hours?|days?|weeks?|months?|years?)\b/i,
];
const ERGO_FIGURE_MARK = "[Ergo figure; see Chain facts]";

// Mark lines that state an Ergo figure. Applied to Ergo-written context only,
// never to the contract or to the caller's own text.
export function qualifyForChain(text: string, chain: Chain): string {
  if (chain === "ergo") return text;
  return text
    .split("\n")
    .map((line) => {
      if (!ERGO_FIGURE_RES.some((re) => re.test(line))) return line;
      const row = line.match(/^(\s*\|.*?)(\s*\|\s*)$/);
      if (row) return `${row[1]} ${ERGO_FIGURE_MARK}${row[2]}`;
      return `${line} ${ERGO_FIGURE_MARK}`;
    })
    .join("\n");
}

// Compact mode: the four fixed pages are fetched once through other tools instead of
// being repeated in every call.
export const COMPACT_CONTEXT_NOTE = [
  "This is a compact result: the fixed audit context is NOT included. It is the same for every contract.",
  "If you have not read it in this session, fetch all four pages BEFORE auditing. The instructions below refer to them (the 13 known issues, the secure design patterns, the LLM pitfalls, the settled semantics, the procedures, the traps T1 onward and the full severity matrix):",
  "",
  "1. `get_ergoscript_ref` with topic `known-issues`",
  "2. `get_ergoscript_ref` with topic `audit-context`",
  "3. `get_pattern` with name `contract-audit-methodology`",
  "4. `get_ergoscript_ref` with topic `audit-program`",
  "",
  "An audit made without them does not follow the method. Call the tool again without `compact` to get everything in one result.",
].join("\n");

const COMPACT_DOC_CHARS = 1500;

export function formatMatchedDocs(
  results: { title: string; file_path: string; text: string }[],
  compact: boolean
): string {
  if (results.length === 0) return "No additional relevant documentation found.";
  return results
    .map((r) => {
      let text = r.text;
      if (compact && text.length > COMPACT_DOC_CHARS) {
        text =
          text.slice(0, COMPACT_DOC_CHARS) +
          `\n\n[cut at ${COMPACT_DOC_CHARS} characters in compact mode; the source file is named above]`;
      }
      return `### ${r.title}\n**Source:** ${r.file_path}\n\n${text}`;
    })
    .join("\n\n---\n\n");
}

// Instruction steps that make an auditor use the Chain facts block. Empty for ergo.
// They name no figures: the numbers are in the chain facts page.
export function chainPass1Steps(chain: Chain): string {
  if (chain === "ergo") return "";
  return [
    "   **Chain checks** (this contract does not run on Ergo; use the Chain facts section above):",
    "   - **Every block-count constant**: list each timelock, window, deadline, depth and tolerance in the contract with its value in blocks and its wall-clock time on this chain. Say whether the wall-clock time fits the purpose the contract gives it, and whether the value looks carried over from an Ergo block count.",
    "   - **Every long-lived box** (singleton, registry, vault, relay): name what spends it at least once inside the chain's storage-rent period, what happens to its value and tokens if nothing does, and who can claim the rent. Give a verdict even when the answer is that the box is safe.",
    "   - **Relay limits**: for the most expensive spend path, say whether its cost and size were measured against the chain's relay limits, and list it as needing validation if not.",
  ].join("\n");
}

export function chainPass2Checks(chain: Chain): string {
  if (chain === "ergo") return "";
  return [
    "- Chain checks the first auditor may have skipped (use the Chain facts section above): a block-count constant with no wall-clock time given for this chain; a long-lived box with no storage-rent verdict; an expensive path not compared with the relay limits; a figure, token id or deployment taken from Ergo that does not exist on this chain",
  ].join("\n");
}
