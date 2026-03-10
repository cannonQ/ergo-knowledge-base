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

// Extract key terms from ErgoScript code for semantic search
function extractSearchTerms(code: string): string {
  const terms: string[] = [];

  if (/HEIGHT/i.test(code)) terms.push("timelock HEIGHT");
  if (/OUTPUTS\.exists|tokens\(/.test(code)) terms.push("token preservation");
  if (/sigmaProp|proveDlog|atLeast/.test(code)) terms.push("signature verification");
  if (/dataInputs|CONTEXT\.dataInputs/.test(code)) terms.push("data input oracle");
  if (/blake2b256|hash/.test(code)) terms.push("commit reveal hashing");
  if (/propositionBytes/.test(code)) terms.push("script hash state continuation");
  if (/SELF\.R[4-9]|\.get/.test(code)) terms.push("register state box");
  if (/getVar/.test(code)) terms.push("context variable");
  if (/AvlTree|avlTree/.test(code)) terms.push("AVL tree plasma");

  if (terms.length === 0) terms.push("ErgoScript contract security");

  return terms.join(" ");
}

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

    // Tool 10: Audit an ErgoScript contract
    server.tool(
      "audit_contract",
      "Audit an ErgoScript smart contract for security vulnerabilities. " +
        "Returns the full audit context (known issues, secure patterns, LLM pitfalls) " +
        "plus relevant EKB documentation matched to the contract's patterns. " +
        "Includes two-pass audit methodology instructions. " +
        "The calling LLM performs the actual audit using this grounding data.",
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
      },
      async ({ code, description }) => {
        // 1. Load static audit context (known issues + pitfalls + methodology)
        const auditContext = getAuditContext();

        // 2. Semantic search for relevant EKB content based on the contract code
        const searchTerms = extractSearchTerms(code);
        const searchResults = await searchDocs(searchTerms, undefined, 5);

        const relevantDocs = searchResults.length > 0
          ? searchResults
              .map((r) => `### ${r.title}\n**Source:** ${r.file_path}\n\n${r.text}`)
              .join("\n\n---\n\n")
          : "No additional relevant documentation found.";

        // 3. Assemble the full audit package
        const auditPackage = [
          "# ErgoScript Contract Audit Package",
          "",
          "## Contract Under Review",
          description ? `**Description:** ${description}` : "",
          "```ergoscript",
          code,
          "```",
          "",
          "---",
          "",
          "## Audit Context & Methodology",
          "",
          auditContext,
          "",
          "---",
          "",
          "## Relevant EKB Documentation",
          "",
          relevantDocs,
          "",
          "---",
          "",
          "## Instructions",
          "",
          "Perform a **two-pass audit** of the contract above:",
          "",
          "**PASS 1:** Analyze the contract against the Known ErgoScript Security Issues, ",
          "Secure Design Patterns, and the contract description (if provided). ",
          "List all findings with severity (CRITICAL/HIGH/MEDIUM/LOW). ",
          "Rate overall security 1-10.",
          "",
          "**PASS 2:** Review your Pass 1 findings. Cross-reference against the ",
          "LLM Audit Pitfalls listed above. Remove any false positives. ",
          "Check for issues you missed. Produce a final consolidated report.",
        ]
          .filter(Boolean)
          .join("\n");

        return {
          content: [{ type: "text" as const, text: auditPackage }],
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
