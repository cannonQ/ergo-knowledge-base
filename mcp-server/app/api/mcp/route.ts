import { z } from "zod";
import { createMcpHandler } from "mcp-handler";
import { searchDocs, listProjects } from "@/lib/search";
import {
  getConcept,
  getPattern,
  getContract,
  listAvailableConcepts,
  listAvailablePatterns,
} from "@/lib/docs";

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
        "Covers 55 projects including spectrum-dex, sigmausd, rosen-bridge, " +
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

    // Tool 5: List all ecosystem projects
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
