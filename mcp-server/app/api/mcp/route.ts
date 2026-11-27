import { z } from "zod";
import { createMcpHandler } from "mcp-handler";
import { searchDocs, listProjects } from "@/lib/search";
import {
  getConcept,
  getPattern,
  getContract,
  getCookbook,
  getEip,
  getErgoscriptRef,
  getSkill,
  getAuditContext,
  listAvailableConcepts,
  listAvailablePatterns,
  listAvailableCookbooks,
  listAvailableEips,
  listAvailableErgoscriptRefs,
  listAvailableSkills,
} from "@/lib/docs";
import {
  CHAINS,
  COMPACT_CONTEXT_NOTE,
  chainFactsSection,
  chainPass1Steps,
  chainPass2Checks,
  conditionalSections,
  formatMatchedDocs,
  qualifyForChain,
} from "@/lib/audit";

// Inputs shared by both audit tools. Left at their defaults they change nothing.
const CHAIN_INPUT = z
  .enum(CHAINS)
  .default("ergo")
  .describe(
    "Chain the contract runs on: 'ergo' (default) or 'yolo' (YOLO SigmaChain: 30 second blocks, Sigma 6.0 from block 1). 'yolo' adds a Chain facts block and marks Ergo figures in the context."
  );
const COMPACT_INPUT = z
  .boolean()
  .default(false)
  .describe(
    "Set true to leave out the fixed audit context (about 54,000 characters, the same for every contract) so the result fits in one tool result. The result then lists the four calls that fetch it once."
  );

// Extract key terms from ErgoScript code for semantic search
function extractSearchTerms(code: string): string {
  const terms: string[] = [];

  // State & time
  if (/HEIGHT/i.test(code)) terms.push("timelock HEIGHT block");
  if (/SELF\.R[4-9]|\.get/.test(code)) terms.push("register state box continuation");
  if (/propositionBytes/.test(code)) terms.push("script hash state continuation multi-stage");

  // Tokens & value
  if (/OUTPUTS\.exists|OUTPUTS\.forall|tokens\(/.test(code)) terms.push("token preservation output");
  if (/tokens\(0\)\._1|tokenId/.test(code)) terms.push("singleton NFT identity token");
  if (/minerFee|MINER_FEE|\.value/.test(code)) terms.push("ERG value fee conservation");

  // Cryptographic
  if (/sigmaProp|proveDlog|atLeast/.test(code)) terms.push("signature verification multisig");
  if (/blake2b256|hash/.test(code)) terms.push("commit reveal hashing front-running");
  if (/GroupElement|decodePoint|proveDHTuple/.test(code)) terms.push("sigma protocol point-at-infinity");

  // Data access
  if (/dataInputs|CONTEXT\.dataInputs/.test(code)) terms.push("data input oracle authentication");
  if (/getVar/.test(code)) terms.push("context variable off-chain");
  if (/AvlTree|avlTree/.test(code)) terms.push("AVL tree plasma authenticated dictionary");

  // Control flow
  if (/\|\|/.test(code)) terms.push("OR branch bypass spending path");
  if (/fold|flatMap|map\(/.test(code)) terms.push("collection operation JIT cost limit");
  if (/INPUTS\.size|OUTPUTS\.size/.test(code)) terms.push("input output count constraint");

  // Box identity
  if (/SELF\.id|\.id/.test(code)) terms.push("box identity minting token");
  if (/creationInfo|SELF\.creationInfo/.test(code)) terms.push("box creation height");

  if (terms.length === 0) terms.push("ErgoScript contract security audit");

  return terms.join(" ");
}

// Quick severity matrix, used in both audit passes
const QUICK_SEVERITY_MATRIX = [
  "### Severity: quick matrix",
  "",
  "| Whose value, what happens | Anyone, now | Anyone, given a realistic state | Needs collusion, hashrate, a victim's mistake, or a keeper offline | A trusted key |",
  "|---|---|---|---|---|",
  "| All of it, or every pool | CRITICAL | HIGH | MEDIUM | KEY-RISK |",
  "| Other people's funds, bounded | HIGH | HIGH | MEDIUM | KEY-RISK |",
  "| A protection others rely on is broken | HIGH | MEDIUM | MEDIUM | KEY-RISK |",
  "| Funds or function permanently locked | HIGH | MEDIUM | MEDIUM | LOW |",
  "| Temporary delay, no value lost | LOW | LOW | INFO | INFO |",
  "| Only the actor's own funds | LOW | LOW | LOW | INFO |",
  "| Nothing | INFO | INFO | INFO | INFO |",
  "",
  "Pick the row by whose value is affected and the column by who can do it. The severity is the cell.",
  "There are six outcomes: CRITICAL, HIGH, MEDIUM, LOW, INFO, KEY-RISK. KEY-RISK is reported separately from defects.",
  "\"A trusted key\" means a key used for what the design grants it. A key or token that does more than it was issued for (one unit of a credential passes a quorum, a key for one box reaches another, a \"singleton\" minted in several units) is not a trusted key: use the \"Anyone, given a realistic state\" column.",
  "This is the plain-language form of the severity matrix in the Audit Program above. Where a finding needs that matrix's modifiers, the Audit Program governs.",
  "Never rate a finding down because the code is not deployed yet.",
];

// Rating rule for the end of Pass 2
const PASS2_RATING_RULE = [
  "- **Rating** (last line of the report, in this form): `Rating: N/10. If fixed: should go to X-Y. Key risks: <ids or none>. Pending: <ids or none>.`",
  "  - The rating is derived, not estimated. The worst open finding sets the band:",
  "",
  "    | Worst open finding | Band |",
  "    |---|---|",
  "    | LOW or INFO only | 9-10 |",
  "    | MEDIUM | 7-8 |",
  "    | HIGH | 4-6 |",
  "    | CRITICAL | 1-3 |",
  "",
  "  - Inside the band, how many findings sit at that level and how large their fixes are set the score.",
  "  - \"If fixed\" is the band of the worst finding left after every recommended CODE fix is applied. A finding the code cannot fix (accepted by design, operational, or affecting boxes already deployed) stays in, and the reason goes in an `until <reason>` clause inside the \"If fixed\" sentence, for example: `If fixed: should go to 7-8 until the older live boxes are spent or moved to a separate payee address.`",
  "  - If no code fix would change the band, write `If fixed: stays at X-Y.`",
  "  - KEY-RISK items do not move the band. Name them after `Key risks:` on the rating line.",
  "  - Needs-validation items do not move the rating. Name them after `Pending:` on the rating line.",
  "  - If it is not known whether any boxes are already deployed, give the band for the code and state the condition instead, for example: `If fixed: should go to 9-10, provided no unfixed boxes are already deployed.`",
];

const handler = createMcpHandler(
  (server) => {
    // Tool 1: Semantic search across all EKB content
    server.tool(
      "search_docs",
      "Search the Ergo Developer Knowledge Base using semantic vector search. " +
        "Returns the most relevant documentation chunks for a given query. " +
        "Use this for open-ended questions like 'how do oracle pools work?' or " +
        "'what is the eUTXO model?'",
      {
        query: z.string().describe("Natural language search query"),
        category: z
          .string()
          .optional()
          .describe(
            "Filter by category: concept, guide, reference, ecosystem, pattern"
          ),
        limit: z
          .number()
          .int()
          .min(1)
          .max(20)
          .default(5)
          .describe("Number of results to return (default 5)"),
      },
      async ({ query, category, limit }) => {
        const results = await searchDocs(query, category, limit);

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: "No relevant documents found for that query.",
              },
            ],
          };
        }

        const formatted = results
          .map((r, i) => {
            const tags = JSON.parse(r.tags);
            return [
              `## Result ${i + 1}: ${r.title}`,
              `**File:** ${r.file_path}`,
              `**Category:** ${r.category} | **Project:** ${r.project || "n/a"}`,
              tags.length > 0 ? `**Tags:** ${tags.join(", ")}` : "",
              `**Relevance:** ${(1 - r._distance).toFixed(3)}`,
              "",
              r.text,
            ]
              .filter(Boolean)
              .join("\n");
          })
          .join("\n\n---\n\n");

        return {
          content: [{ type: "text" as const, text: formatted }],
        };
      }
    );

    // Tool 2: Get a specific concept document
    server.tool(
      "get_concept",
      "Retrieve a specific Ergo concept document by name. " +
        "Available concepts include: eutxo-model, boxes-and-registers, " +
        "sigma-protocols, storage-rent, and more.",
      {
        name: z
          .string()
          .describe(
            "Concept name (e.g. 'eutxo-model', 'sigma-protocols', 'storage-rent')"
          ),
      },
      async ({ name }) => {
        const content = getConcept(name);
        if (!content) {
          const available = listAvailableConcepts();
          return {
            content: [
              {
                type: "text" as const,
                text: `Concept '${name}' not found. Available concepts: ${available.join(", ")}`,
              },
            ],
          };
        }
        return {
          content: [{ type: "text" as const, text: content }],
        };
      }
    );

    // Tool 3: Get contract analysis for an ecosystem project
    server.tool(
      "get_contract",
      "Retrieve contract analysis or project overview for an Ergo ecosystem project. " +
        "Covers 65 projects including spectrum-dex, sigmausd, rosen-bridge, " +
        "oracle-pools, paideia, skyharbor, and more.",
      {
        project: z
          .string()
          .describe(
            "Project name (e.g. 'spectrum-dex', 'sigmausd', 'rosen-bridge')"
          ),
        contract: z
          .string()
          .optional()
          .describe(
            "Specific contract name within the project (omit for project overview)"
          ),
      },
      async ({ project, contract }) => {
        const content = getContract(project, contract);
        if (!content) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Project '${project}'${contract ? ` contract '${contract}'` : ""} not found. Use list_projects to see available projects.`,
              },
            ],
          };
        }
        return {
          content: [{ type: "text" as const, text: content }],
        };
      }
    );

    // Tool 4: Get a cross-cutting pattern guide
    server.tool(
      "get_pattern",
      "Retrieve a cross-cutting development pattern guide. " +
        "Patterns cover common Ergo development approaches like " +
        "EIP-12 dApp connector, ErgoPay signing, transaction building, " +
        "headless dApp architecture, and more.",
      {
        name: z
          .string()
          .describe(
            "Pattern name (e.g. 'eip12-dapp-connector', 'transaction-building', 'headless-dapp')"
          ),
      },
      async ({ name }) => {
        const content = getPattern(name);
        if (!content) {
          const available = listAvailablePatterns();
          return {
            content: [
              {
                type: "text" as const,
                text: `Pattern '${name}' not found. Available patterns: ${available.join(", ")}`,
              },
            ],
          };
        }
        return {
          content: [{ type: "text" as const, text: content }],
        };
      }
    );

    // Tool 5: Get a cookbook recipe
    server.tool(
      "get_cookbook",
      "Retrieve a specific cookbook recipe with working code examples. " +
        "Recipes cover token operations (mint, transfer, burn), contract patterns " +
        "(simple-send, timelock, multi-sig, state-machine), and more. " +
        "Each recipe includes ErgoScript + Fleet SDK TypeScript code.",
      {
        name: z
          .string()
          .describe(
            "Recipe name (e.g. 'mint-token', 'timelock', 'multi-sig', 'simple-send')"
          ),
      },
      async ({ name }) => {
        const content = getCookbook(name);
        if (!content) {
          const available = listAvailableCookbooks();
          return {
            content: [
              {
                type: "text" as const,
                text: `Recipe '${name}' not found. Available recipes: ${available.join(", ")}`,
              },
            ],
          };
        }
        return {
          content: [{ type: "text" as const, text: content }],
        };
      }
    );

    // Tool 6: Get an EIP by number
    server.tool(
      "get_eip",
      "Retrieve an Ergo Improvement Proposal (EIP) by number. " +
        "Covers EIP-1 through EIP-44 including asset standards (EIP-4), " +
        "contract templates (EIP-6), dApp connector (EIP-12/EIP-20), " +
        "and more.",
      {
        number: z
          .string()
          .describe(
            "EIP number (e.g. '4', '0004', 'eip-4', or 'eip-0004')"
          ),
      },
      async ({ number }) => {
        const content = getEip(number);
        if (!content) {
          const available = listAvailableEips();
          return {
            content: [
              {
                type: "text" as const,
                text: `EIP '${number}' not found. Available EIPs: ${available.join(", ")}`,
              },
            ],
          };
        }
        return {
          content: [{ type: "text" as const, text: content }],
        };
      }
    );

    // Tool 7: Get ErgoScript language reference
    server.tool(
      "get_ergoscript_ref",
      "Retrieve ErgoScript language reference documentation. " +
        "Covers built-in functions (sigmaProp, blake2b256, atLeast, etc.), " +
        "the type system (Int, Long, BigInt, Coll, Box, SigmaProp), " +
        "and context variables (SELF, INPUTS, OUTPUTS, HEIGHT).",
      {
        topic: z
          .string()
          .describe(
            "Reference topic: 'built-in-functions', 'types', 'context-variables', or 'language-spec'"
          ),
      },
      async ({ topic }) => {
        const content = getErgoscriptRef(topic);
        if (!content) {
          const available = listAvailableErgoscriptRefs();
          return {
            content: [
              {
                type: "text" as const,
                text: `ErgoScript reference '${topic}' not found. Available topics: ${available.join(", ")}`,
              },
            ],
          };
        }
        return {
          content: [{ type: "text" as const, text: content }],
        };
      }
    );

    // Tool 8: List all ecosystem projects
    server.tool(
      "list_projects",
      "List all Ergo ecosystem projects in the knowledge base with their categories.",
      {},
      async () => {
        const projects = await listProjects();

        if (projects.length === 0) {
          return {
            content: [
              {
                type: "text" as const,
                text: "No projects found in the knowledge base.",
              },
            ],
          };
        }

        const formatted = projects
          .map(
            (p) =>
              `- **${p.project}** (${p.category}) — ${p.title}`
          )
          .join("\n");

        return {
          content: [
            {
              type: "text" as const,
              text: `# Ergo Ecosystem Projects\n\n${formatted}`,
            },
          ],
        };
      }
    );

    // Tool 9: Get a complete skill document
    server.tool(
      "get_skill",
      "Retrieve a complete actionable skill document for Ergo development. " +
        "Skills are step-by-step instruction sets for specific tasks: " +
        "connecting Nautilus wallet, building transactions with Fleet SDK, " +
        "implementing Babel fees, using ergo-lib-wasm, deploying nodes, " +
        "AVL tree operations with Plasma-Toolkit, and more. " +
        "Returns the FULL document (not chunks) so the instructions can be followed completely.",
      {
        name: z
          .string()
          .describe(
            "Skill name (e.g. 'nautilus', 'babel-fees', 'fleet-sdk', 'plasma-avl', 'appkit', 'ergo-wasm', 'node-deployment', 'eip004'). Use 'list' to see all available skills."
          ),
      },
      async ({ name }) => {
        if (name.toLowerCase() === "list") {
          const available = listAvailableSkills();
          return {
            content: [
              {
                type: "text" as const,
                text: `# Available Skills\n\n${available.map((s) => `- ${s}`).join("\n")}`,
              },
            ],
          };
        }

        const content = getSkill(name);
        if (!content) {
          const available = listAvailableSkills();
          return {
            content: [
              {
                type: "text" as const,
                text: `Skill '${name}' not found. Available skills: ${available.join(", ")}`,
              },
            ],
          };
        }
        return {
          content: [{ type: "text" as const, text: content }],
        };
      }
    );

    // Tool 10: Audit an ErgoScript contract (Pass 1 — Initial Audit)
    server.tool(
      "audit_contract",
      "PASS 1 of a two-pass ErgoScript contract audit. " +
        "Returns security context (known issues, secure patterns, LLM pitfalls), " +
        "relevant EKB documentation matched to the contract's patterns, " +
        "and detailed Pass 1 audit instructions. " +
        "Optional: chain ('ergo' default, or 'yolo') and compact (true returns the per-contract part only). " +
        "After completing Pass 1, call audit_verify with your findings for independent verification.",
      {
        code: z
          .string()
          .describe("The ErgoScript contract code to audit"),
        description: z
          .string()
          .optional()
          .describe(
            "Optional description of what the contract should do (enables intent-based auditing)"
          ),
        chain: CHAIN_INPUT,
        compact: COMPACT_INPUT,
      },
      async ({ code, description, chain, compact }) => {
        // 1. Load static audit context (known issues + pitfalls + methodology)
        const auditContext = getAuditContext();

        // 2. Semantic search for relevant EKB content based on the contract code
        //    Search both code patterns AND description (if provided)
        const codeTerms = extractSearchTerms(code);
        const searchQueries = [codeTerms];
        if (description) {
          searchQueries.push(description);
        }

        const allResults = [];
        for (const query of searchQueries) {
          const results = await searchDocs(query, undefined, 5);
          allResults.push(...results);
        }

        // Deduplicate by file_path + title
        const seen = new Set<string>();
        const uniqueResults = allResults.filter((r) => {
          const key = `${r.file_path}:${r.title}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });

        const relevantDocs = qualifyForChain(
          formatMatchedDocs(uniqueResults, compact),
          chain
        );
        // Chain facts (non-ergo only) and the sections that depend on what the contract uses
        const chainFacts = chainFactsSection(chain);
        const extraSections = conditionalSections(code, chain);
        const fixedContext = compact
          ? COMPACT_CONTEXT_NOTE
          : qualifyForChain(auditContext, chain);

        // 3. Assemble the Pass 1 audit package
        const auditPackage = [
          "# ErgoScript Contract Audit — Pass 1 (Initial Analysis)",
          "",
          "## Contract Under Review",
          description ? `**Intended behavior:** ${description}` : "",
          "```ergoscript",
          code,
          "```",
          "",
          "---",
          "",
          chainFacts,
          "## eUTXO Model — Core Reference",
          "",
          "Ergo uses the extended UTXO model. Key principles for auditing:",
          "- **Box** = value (ERG) + tokens (up to 255) + registers (R4-R9) + guarding script",
          "- **ErgoScript** = predicate that must evaluate TRUE to spend a box",
          "- **State transition** = old boxes spent (destroyed) → new boxes created",
          "- **INPUTS** = boxes being spent (scripts evaluated). **DATA INPUTS** = read-only (scripts NOT evaluated)",
          "- **OUTPUTS** = new boxes created. Total ERG in + fee must equal total ERG out",
          "- **Tokens must be explicitly preserved** in OUTPUTS — any unaccounted tokens are lost",
          "- **Singleton NFT** = a token with quantity 1 that uniquely identifies a box (cannot be faked)",
          "- **Multi-stage protocols** = box consumed → recreated with updated registers. NFT travels with box for identity",
          "- **Determinism** = transaction outcome is fully determined before submission (no gas surprises)",
          "- Context variables: SELF, INPUTS, OUTPUTS, HEIGHT, CONTEXT.dataInputs, CONTEXT.preHeader",
          "- Core references: [LangSpec](https://github.com/ergoplatform/sigmastate-interpreter/blob/develop/docs/LangSpec.md), [ErgoScript PDF](https://storage.googleapis.com/ergo-cms-media/docs/ErgoScript.pdf)",
          "",
          "---",
          "",
          "## Audit Context — Known Issues, Secure Patterns & LLM Pitfalls",
          "",
          fixedContext,
          "",
          "---",
          "",
          extraSections,
          "## Relevant EKB Documentation",
          "",
          relevantDocs,
          "",
          "---",
          "",
          "## Pass 1 Instructions",
          "",
          "Perform the initial comprehensive audit of the contract above:",
          "",
          "1. **Explain** what the contract does in simple terms",
          "2. **Enumerate all spend paths** — trace every branch in the script's boolean logic",
          "3. **Check against all 13 Known ErgoScript Security Issues:**",
          "   - Unvalidated data inputs (is every data input whose registers are read authenticated by a singleton NFT or box ID? A script-hash match proves the script, not who wrote the registers)",
          "   - Token loss (are ALL tokens in inputs accounted for in outputs? Is the output that holds them checked for script, token ID and amount AND bound to this input (`SELF.id` in the output, an input-index pin, or a sum over same-script inputs)? An output-index pin or `OUTPUTS.exists` alone lets two inputs share one output)",
          "   - OR-branch bypasses (can any `||` branch be satisfied independently in an unintended way?)",
          "   - Missing signature requirements (are all spend paths gated by `sigmaProp`/`proveDlog`/`atLeast`?)",
          "   - Point-at-infinity edge cases (are GroupElement values from registers validated?)",
          "   - Front-running (is sensitive data revealed in the spending transaction?)",
          "   - Incorrect HEIGHT comparisons (off-by-one errors? tolerance window too tight for mempool? Is a height the builder writes bounded on both sides relative to `HEIGHT`, or can a one-sided bound be backdated or pushed far out?)",
          "   - Cyclic script hash dependencies (does the contract reference another contract's hash that references this one?)",
          "   - JIT cost limits (complex folds, deep nesting, large collection operations?)",
          "   - One output satisfying several inputs (what binds each checked output to this input alone? Consider two boxes of this script in one transaction, another script, an older live version, another product paying the same address)",
          "   - Positional trust (is every box read by index identified by its NFT?)",
          "   - Unpinned residual (inputs minus pinned outputs: who gets the rest?)",
          "   - Context-variable collections without a distinctness check (`getVar` collections used for a sum, count or payout)",
          "4. **Verify against Secure Design Patterns** — does the contract use the right pattern for its purpose?",
          "   (CommitReveal, PerpetualToken, MultiStage, Multisig, EmergencyRefund, StateContinuation, OracleAuth, ExclusiveOutput)",
          "5. **Check ERG and token conservation** — all value must be accounted for across INPUTS → OUTPUTS",
          "6. **Validate register usage** — are R4-R9 accessed with correct types? Are `.get` calls safe?",
          description
            ? "7. **Intent verification** — does the code actually implement the described behavior? Look for logic bugs where the code is secure but does the wrong thing"
            : "",
          chainPass1Steps(chain),
          "8. **List all findings** with severity taken from the quick matrix below (name the row and the column used for each)",
          "",
          ...QUICK_SEVERITY_MATRIX,
          "",
          "Do not give an overall rating or score in Pass 1. The rating is produced once, at the end of Pass 2.",
          "",
          "---",
          "",
          "## Next Step",
          "",
          "After completing this Pass 1 audit, call **`audit_verify`** with the original contract code, " +
          "your complete Pass 1 findings, and the contract description (if provided). " +
          "This sends your audit to an independent verification pass that will catch false positives " +
          "and find issues you may have missed.",
        ]
          .filter(Boolean)
          .join("\n");

        return {
          content: [{ type: "text" as const, text: auditPackage }],
        };
      }
    );

    // Tool 11: Verify an ErgoScript audit (Pass 2 — Independent Review)
    server.tool(
      "audit_verify",
      "PASS 2 of a two-pass ErgoScript contract audit. " +
        "Takes the original contract code and Pass 1 audit findings, " +
        "then returns security context with independent reviewer instructions. " +
        "Designed to catch false positives and find issues the first pass missed. " +
        "Optional: chain and compact, as in audit_contract; pass the same values in both passes. " +
        "Call this after audit_contract with your Pass 1 output.",
      {
        code: z
          .string()
          .describe("The original ErgoScript contract code"),
        pass1_findings: z
          .string()
          .describe("The complete Pass 1 audit output to verify"),
        description: z
          .string()
          .optional()
          .describe(
            "Optional description of what the contract should do"
          ),
        chain: CHAIN_INPUT,
        compact: COMPACT_INPUT,
      },
      async ({ code, pass1_findings, description, chain, compact }) => {
        // 1. Load the same static audit context
        const auditContext = getAuditContext();

        // 2. Same semantic search as Pass 1
        const codeTerms = extractSearchTerms(code);
        const searchQueries = [codeTerms];
        if (description) {
          searchQueries.push(description);
        }

        const allResults = [];
        for (const query of searchQueries) {
          const results = await searchDocs(query, undefined, 5);
          allResults.push(...results);
        }

        const seen = new Set<string>();
        const uniqueResults = allResults.filter((r) => {
          const key = `${r.file_path}:${r.title}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });

        const relevantDocs = qualifyForChain(
          formatMatchedDocs(uniqueResults, compact),
          chain
        );
        // Chain facts (non-ergo only) and the sections that depend on what the contract uses
        const chainFacts = chainFactsSection(chain);
        const extraSections = conditionalSections(code, chain);
        const fixedContext = compact
          ? COMPACT_CONTEXT_NOTE
          : qualifyForChain(auditContext, chain);

        // 3. Assemble the Pass 2 verification package
        const verifyPackage = [
          "# ErgoScript Contract Audit — Pass 2 (Independent Verification)",
          "",
          "## Role",
          "",
          "You are an **independent security reviewer**. Another auditor produced the findings below. " +
          "Your job is to verify their work. Assume the first auditor made mistakes — " +
          "look for false positives they reported and real issues they missed.",
          "",
          "---",
          "",
          "## Contract Under Review",
          description ? `**Intended behavior:** ${description}` : "",
          "```ergoscript",
          code,
          "```",
          "",
          "---",
          "",
          "## First Auditor's Findings (Pass 1)",
          "",
          pass1_findings,
          "",
          "---",
          "",
          chainFacts,
          "## eUTXO Model — Core Reference",
          "",
          "Ergo uses the extended UTXO model. Key principles for verification:",
          "- **Box** = value (ERG) + tokens (up to 255) + registers (R4-R9) + guarding script",
          "- **ErgoScript** = predicate that must evaluate TRUE to spend a box",
          "- **State transition** = old boxes spent (destroyed) → new boxes created",
          "- **INPUTS** = boxes being spent (scripts evaluated). **DATA INPUTS** = read-only (scripts NOT evaluated)",
          "- **OUTPUTS** = new boxes created. Total ERG in + fee must equal total ERG out",
          "- **Tokens must be explicitly preserved** in OUTPUTS — any unaccounted tokens are lost",
          "- **Singleton NFT** = a token with quantity 1 that uniquely identifies a box (cannot be faked)",
          "- **Multi-stage protocols** = box consumed → recreated with updated registers. NFT travels with box for identity",
          "- Context variables: SELF, INPUTS, OUTPUTS, HEIGHT, CONTEXT.dataInputs, CONTEXT.preHeader",
          "",
          "---",
          "",
          "## Audit Context — Known Issues, Secure Patterns & LLM Pitfalls",
          "",
          fixedContext,
          "",
          "---",
          "",
          extraSections,
          "## Relevant EKB Documentation",
          "",
          relevantDocs,
          "",
          "---",
          "",
          "## Pass 2 Verification Instructions",
          "",
          "Review the first auditor's findings against the contract code. You are looking for errors in their analysis.",
          "",
          "### Step 1: Verify each finding against LLM Audit Pitfalls",
          "",
          "For EVERY finding the first auditor reported, check:",
          "- Is the token ID actually checked indirectly (via tuple, register lookup, helper value)?",
          "- Is additional identity verification redundant because a singleton NFT already authenticates the box?",
          "- Is the apparent issue cancelled out by a matching constraint on the other side of the transaction?",
          "- Is the type conversion required by ErgoScript's type system (e.g., Long→Int for Coll indexing)?",
          "- Are the values bounded by fixed constants that make overflow impossible?",
          "- Is the pattern an intentional optimization/tradeoff rather than a mistake?",
          "",
          "### Step 2: Remove false positives",
          "",
          "For each finding you determine is a false positive, explain WHY it was removed. " +
          "Be specific — cite the code that disproves the finding.",
          "",
          "### Step 3: Check for missed issues",
          "",
          "The first auditor may have missed vulnerabilities. Look specifically for:",
          "- Hidden OR-branch bypasses (test each `||` branch in complete isolation)",
          "- Subtle token preservation failures (tokens present in inputs but not enforced in outputs)",
          "- Edge cases in HEIGHT comparisons (Ergo's CleanupWorker re-validates mempool txs against new HEIGHT)",
          "- Data input manipulation vectors (can an attacker substitute a different data input box?)",
          "- Front-running opportunities (is sensitive data revealed before commitment?)",
          "- Off-chain assumptions (\"can a different backend construct a transaction that violates this assumption while still satisfying the script?\")",
          "- One output satisfying several inputs (co-spend two boxes of this contract; co-spend this box beside any other script, older version or product that pays the same address; does one output satisfy both?)",
          "- A box read by position without an NFT check",
          "- A residual that no checked output is required to hold",
          chainPass2Checks(chain),
          description
            ? "- Intent mismatches (does the code actually do what the description says it should?)"
            : "",
          "",
          "### Step 4: Re-derive severity",
          "",
          "Re-derive the severity of every confirmed and new finding from the quick matrix below, independently of the first auditor's label, and state the row and column used.",
          "",
          ...QUICK_SEVERITY_MATRIX,
          "",
          "### Step 5: Produce final consolidated report",
          "",
          "Your output must include:",
          "- **Contract summary** (1-2 sentences)",
          "- **Confirmed vulnerabilities** from Pass 1 (with the re-derived severity + specific code references)",
          "- **Removed false positives** (with explanation for each removal)",
          "- **New findings** (clearly marked as \"VERIFICATION FINDING\" with the re-derived severity)",
          "- **Key risks** (KEY-RISK items), listed separately from defects",
          "- **Needs validation**: items whose deciding fact could not be settled from the code, listed as pending with what would settle them",
          "- **Final recommendations** with code fixes where applicable",
          ...PASS2_RATING_RULE,
        ]
          .filter(Boolean)
          .join("\n");

        return {
          content: [{ type: "text" as const, text: verifyPackage }],
        };
      }
    );
  },
  {
    serverInfo: {
      name: "ergo-ekb",
      version: "1.0.0",
    },
  },
  {
    basePath: "/api",
  }
);

export { handler as GET, handler as POST, handler as DELETE };
